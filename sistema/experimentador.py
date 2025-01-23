import shutil
import zipfile
from flask import (
    Blueprint, render_template, request, url_for, redirect, flash, send_from_directory,
    session, jsonify, json, Response
)

from .auth import login_required
from sistema import db, RUTA_BASE
from .models import Proyecto, Modelos,DataSet, Modelos_generados, Evaluacion_modelo
import os
from ultralytics import YOLO, RTDETR
import os
import time  
from datetime import date  
from werkzeug.utils import secure_filename
import cv2
import numpy as np
import pandas as pd

bp = Blueprint('experimentador', __name__, url_prefix='/experimentador')

@login_required
@bp.route('/inicio')
def inicio():
    return render_template('experimentador/inicio.html')

# Función para obtener proyectos de un usuario
def obtener_proyectos_por_usuario(id_usuario):
    return Proyecto.query.filter_by(Usuario=id_usuario).all()

# Función para obtener datasets de todos los proyectos
def obtener_datasets_por_proyecto():
    datasets = DataSet.query.all()
    datasets_dict = {}
    for dataset in datasets:
        if dataset.idProyecto not in datasets_dict:
            datasets_dict[dataset.idProyecto] = []
        datasets_dict[dataset.idProyecto].append(dataset.Nombre)
    return datasets_dict


@bp.route('/rtdetr_cero', methods=['GET', 'POST'])
def rtdetr_cero():
    if request.method == 'POST':
        # Obtener datos del formulario
        proyecto_id = request.form.get('proyecto_id')
        dataset_id = request.form.get('dataset_id')
        model_name = request.form.get('model_name')
        epochs = request.form.get('epochs')
        batch_size = request.form.get('batch_size')
        optimizador = request.form.get('optimizer')

        # Validar datos del formulario
        if not (proyecto_id and dataset_id and model_name and epochs and batch_size):
            flash("Todos los campos son obligatorios", 'warning')
            return redirect(url_for('experimentador.rtdetr_cero'))
        # Obtener los nombres del proyecto y del dataset
        proyecto = Proyecto.query.get_or_404(proyecto_id)
      
        dataset = DataSet.query.filter_by(Nombre=dataset_id).first()
        
        # Construir la ruta completa del archivo data.yaml
        base_path = os.path.join(RUTA_BASE, proyecto.Nombre, 'DATASET', dataset.Nombre, 'data.yaml')
        # Verificar si el archivo data.yaml existe en la ruta
        if os.path.isfile(base_path):
            session['data'] = base_path
            session['epocas'] = epochs
            session['proyecto'] = proyecto_id
            session['tipo'] = "rtdetr_cero"
            session['optimizador'] = optimizador
            session['batch'] = batch_size
            session['nombre_modelo'] = model_name
            session['id_data'] = dataset.idDataset
            flash('Iniciando entrenamiento', 'success')
            return redirect(url_for('experimentador.entrenando'))
        else:
            flash(f"Archivo 'data.yaml' no encontrado en {base_path}", 'warning')
            return redirect(url_for('experimentador.rtdetr_cero'))

    # Obtener el id del usuario desde la sesión
    id_usuario = session.get('user')
    if not id_usuario:
        return "Usuario no autenticado", 401

    proyectos = obtener_proyectos_por_usuario(id_usuario)
    datasets_dict = obtener_datasets_por_proyecto()
    return render_template('experimentador/rtdetr_desde0.html', proyectos=proyectos, datasets=datasets_dict)


@login_required
@bp.route('/rtdetr_transferencia', methods=['GET', 'POST'])
def rtdetr_transferencia():
    if request.method == 'POST':
        # Obtener datos del formulario
        proyecto_id = request.form.get('proyecto_id')
        dataset_id = request.form.get('dataset_id')
        model_name = request.form.get('model_name')
        base_model = request.form.get('base_model')  # Campo del modelo base
        epochs = int(request.form.get('epochs'))
        batch_size = request.form.get('batch_size')
        optimizador = request.form.get('optimizer')

        # Validar datos del formulario
        if not (proyecto_id and dataset_id and model_name and base_model and epochs and batch_size):
            flash("Todos los campos son obligatorios", 'warning')
            return redirect(url_for('experimentador.rtdetr_transferencia'))

        # Obtener proyecto y dataset
        proyecto = Proyecto.query.get_or_404(proyecto_id)
        dataset = DataSet.query.filter_by(Nombre=dataset_id).first()
        if not dataset:
            flash("Dataset no encontrado", 'warning')
            return redirect(url_for('experimentador.rtdetr_transferencia'))

        # Construir las rutas completas
        base_path = os.path.join(RUTA_BASE, proyecto.Nombre, 'DATASET', dataset.Nombre, 'data.yaml')
        # Agregar la extensión .pt al nombre del modelo base
        base_modelo = os.path.join(RUTA_BASE, proyecto.Nombre, 'MODELOS', f"{base_model}.pt")


        # Validar existencia del archivo data.yaml
        if not os.path.isfile(base_path):
            flash(f"Archivo 'data.yaml' no encontrado en {base_path}", 'warning')
            return redirect(url_for('experimentador.rtdetr_transferencia'))

        # Validar existencia del modelo en la carpeta MODELOS
        if not os.path.isfile(base_modelo):
            flash(f"Modelo base '{base_model}' no encontrado en la carpeta MODELOS: {base_modelo}", 'warning')
            return redirect(url_for('experimentador.rtdetr_transferencia'))
        print(base_modelo)
        # Guardar datos en la sesión para iniciar el entrenamiento
        session['data'] = base_path
        session['epocas'] = epochs
        session['proyecto'] = proyecto_id
        session['base_model'] = base_modelo  # Guardar la ruta del modelo en la sesión
        session['tipo'] = "rtdetr_trans"
        session['optimizador'] = optimizador
        session['batch'] = batch_size
        session['nombre_modelo'] = model_name
        session['id_data'] = dataset.idDataset
        flash('Iniciando entrenamiento', 'success')
        return redirect(url_for('experimentador.entrenando'))

    # Obtener datos para llenar el formulario
    id_usuario = session.get('user')
    if not id_usuario:
        return "Usuario no autenticado", 401

    proyectos = obtener_proyectos_por_usuario(id_usuario)
    modelos_base_dict = obtener_modelos_base_por_proyecto()
    # Dentro de la función rtdetr_transferencia
    datasets_dict = obtener_datasets_por_proyecto()
    print(datasets_dict)
    return render_template(
        'experimentador/rtdetr_transferencia.html',
        proyectos=proyectos,
        datasets=datasets_dict,  # Asegúrate de pasar datasets
        modelos_base=modelos_base_dict
    )


def obtener_modelos_base_por_proyecto():
    modelos_base = {}
    proyectos = Proyecto.query.all()
    for proyecto in proyectos:
        modelos_base[proyecto.idProyecto] = [
            modelo.Nombre for modelo in Modelos.query.filter_by(Proyecto_id=proyecto.idProyecto).filter_by(Arquitectura='Transformer').all()
        ]
    return modelos_base

@login_required
@bp.route('yolo_desde0', methods=['GET', 'POST'])
def yolo_cero():
    if request.method == 'POST':
        # Obtener datos del formulario
        proyecto_id = request.form.get('proyecto_id')
        dataset_id = request.form.get('dataset_id')
        model_name = request.form.get('model_name')
        epochs = request.form.get('epochs')
        batch_size = request.form.get('batch_size')
        optimizador = request.form.get('optimizer')

        # Validar datos del formulario
        if not (proyecto_id and dataset_id and model_name and epochs and batch_size):
            flash("Todos los campos son obligatorios", 'warning')
            return redirect(url_for('experimentador.yolo_cero'))

        # Obtener los nombres del proyecto y del dataset
        proyecto = Proyecto.query.get_or_404(proyecto_id)
        dataset = DataSet.query.filter_by(Nombre=dataset_id).first()
        
        # Construir la ruta completa del archivo data.yaml
        base_path = os.path.join(RUTA_BASE, proyecto.Nombre, 'DATASET', dataset.Nombre, 'data.yaml')
        if os.path.isfile(base_path):
            # Guardar los datos necesarios en la sesión
            session['data'] = base_path
            session['epocas'] = epochs
            session['proyecto'] = proyecto_id
            session['tipo'] = "yolo_cero"
            session['optimizador'] = optimizador
            session['batch'] = batch_size
            session['nombre_modelo'] = model_name
            session['id_data'] = dataset.idDataset
            return redirect(url_for('experimentador.entrenando'))
            
        else:
            flash(f"Archivo 'data.yaml' no encontrado en {base_path}", 'warning')
            return redirect(url_for('experimentador.yolo_cero'))

    # Obtener el id del usuario desde la sesión
    id_usuario = session.get('user')
    if not id_usuario:
        return "Usuario no autenticado", 401

    proyectos = obtener_proyectos_por_usuario(id_usuario)
    datasets_dict = obtener_datasets_por_proyecto()
    return render_template('experimentador/yolo_desde0.html', proyectos=proyectos, datasets=datasets_dict)


@login_required
@bp.route('yolo_transferencia', methods=['GET', 'POST'])
def yolo_transferencia():
    if request.method == 'POST':
        # Obtener datos del formulario
        proyecto_id = request.form.get('proyecto_id')
        dataset_id = request.form.get('dataset_id')
        model_name = request.form.get('model_name')
        base_model = request.form.get('base_model')  # Campo del modelo base
        epochs = request.form.get('epochs')
        batch_size = request.form.get('batch_size')
        optimizador = request.form.get('optimizer')
     
        # Obtener proyecto y dataset
        proyecto = Proyecto.query.get_or_404(proyecto_id)
        dataset = DataSet.query.filter_by(Nombre=dataset_id).first()
        if not dataset:
            flash("Dataset no encontrado", 'warning')
            return redirect(url_for('experimentador.rtdetr_transferencia'))

        # Construir las rutas completas
        base_path = os.path.join(RUTA_BASE, proyecto.Nombre, 'DATASET', dataset.Nombre, 'data.yaml')
        # Agregar la extensión .pt al nombre del modelo base
        base_modelo = os.path.join(RUTA_BASE, proyecto.Nombre, 'MODELOS', f"{base_model}.pt")

        # Validar existencia del archivo data.yaml
        if not os.path.isfile(base_path):
            flash(f"Archivo 'data.yaml' no encontrado en {base_path}", 'warning')
            return redirect(url_for('experimentador.rtdetr_transferencia'))

        # Validar existencia del modelo en la carpeta MODELOS
        if not os.path.isfile(base_modelo):
            flash(f"Modelo base '{base_model}' no encontrado en la carpeta MODELOS: {base_modelo}", 'warning')
            return redirect(url_for('experimentador.yolo_transferencia'))

        # Guardar datos en la sesión para iniciar el entrenamiento
        session['data'] = base_path
        session['epocas'] = epochs
        session['proyecto'] = proyecto_id
        session['base_model'] = base_modelo  # Guardar la ruta del modelo en la sesión
        session['tipo'] = "yolo_trans"
        session['optimizador'] = optimizador
        session['batch'] = batch_size
        session['nombre_modelo'] = model_name
        session['id_data'] = dataset.idDataset
        flash('Iniciando entrenamiento', 'success')

        # Llamar directamente a la función de entrenamiento
        return redirect(url_for('experimentador.entrenando'))

    # Obtener datos para llenar el formulario
    id_usuario = session.get('user')
    if not id_usuario:
        return "Usuario no autenticado", 401

    proyectos = obtener_proyectos_por_usuario(id_usuario)
    datasets_dict = obtener_datasets_por_proyecto()
    modelos_base_dict = modelos_yolo()

    return render_template(
        'experimentador/yolo_transferencia.html',
        proyectos=proyectos,
        datasets=datasets_dict,
        modelos_base=modelos_base_dict
    )



def modelos_yolo():
    modelos_base = {}
    proyectos = Proyecto.query.all()
    for proyecto in proyectos:
        modelos_base[proyecto.idProyecto] = [
            modelo.Nombre for modelo in Modelos.query.filter_by(Proyecto_id=proyecto.idProyecto).filter_by(Arquitectura='Yolo').all()
        ]
    return modelos_base


@login_required
@bp.route('/entrenando', methods=['GET', 'POST'])
def entrenando():
    if request.method == 'POST':
        flash('Entrenamiento comenzado', 'success')
        tipo = session.get('tipo')
        if tipo == "yolo_cero":
            entrenamiento_yolo_cero()
            return redirect(url_for('experimentador.modelos_generados'))
        elif tipo == "yolo_trans":
            entrenamiento_yolo_trans()
            return redirect(url_for('experimentador.modelos_generados'))
        elif tipo == "rtdetr_trans":
            entrenamiento_rtdetr_trans()
            return redirect(url_for('experimentador.modelos_generados'))
        else:
            entrenamiento_rtdetr_cero()
            return redirect(url_for('experimentador.modelos_generados'))
    return render_template('experimentador/entrenando.html')

def entrenamiento_yolo_cero():
    data = session.get('data')
    epocas = session.get('epocas')
    proyecto_id = session.get('proyecto')
    optimizador = session.get('optimizador')
    batch = session.get('batch')
    nombre_modelo = session.get('nombre_modelo')

    # Consultar el proyecto por su ID y obtener la ruta
    proyecto = Proyecto.query.filter_by(idProyecto=proyecto_id).first()

    # Crear la carpeta para guardar el modelo con el nombre obtenido de la sesión
    modelo_entrenado_path = os.path.join(proyecto.Nombre, "MODELOS_ENTRENADOS", nombre_modelo)
    os.makedirs(modelo_entrenado_path, exist_ok=True)  # Crear la carpeta si no existe

    # Definir la ruta para guardar el modelo entrenado
    model_save_path = os.path.join(modelo_entrenado_path, f"{nombre_modelo}.pt")

    # Cargar el modelo base YOLOv8
    model = YOLO("yolov8s.yaml")  # Cambiar a otro tamaño como 'yolov8s', 'yolov8m', etc.

    # Registrar el tiempo de inicio
    start_time = time.time()

    # Entrenar el modelo
    results = model.train(
        data=data,
        epochs=int(epocas),
        batch=int(batch),
        imgsz=640,
        optimizer=optimizador,
        project=modelo_entrenado_path,
        name=nombre_modelo,
        save=True,
        plots=True  # Activar la generación de gráficas
    )

    # Calcular el tiempo total de entrenamiento
    total_time = time.time() - start_time

    # Guardar el modelo entrenado
    model.save(model_save_path)

    # Extraer métricas y otros resultados
    box_metrics = results.box
    precision = box_metrics.p
    recall = box_metrics.r
    f1_score = box_metrics.f1.mean()
    map50 = box_metrics.map50
    map95 = box_metrics.map
    map75 = box_metrics.map75

    # Guardar las métricas en la base de datos
    nuevo_modelo = Modelos_generados(
        nombre=nombre_modelo,
        desc="Modelo entrenado con YOLOv8",
        epocas=epocas,
        batch=batch,
        fecha=date.today(),
        arquitectura="YOLOv8",
        proyecto=proyecto_id,
        optimizador=optimizador,
        dataset=session.get('id_data'),
        ruta=model_save_path
    )

    db.session.add(nuevo_modelo)
    db.session.commit()

    evaluacion_modelo = Evaluacion_modelo(
        score=f1_score,
        recall=recall.mean(),
        map50=map50,
        precision=precision.mean(),
        map50_95=map95,
        map75=map75,
        modelo=nuevo_modelo.idModelo_generados,
        tiempo=total_time
    )

    db.session.add(evaluacion_modelo)
    db.session.commit()

    # Imprimir información adicional
    flash(f"Modelo entrenado y guardado en {model_save_path}. Las gráficas se encuentran en la carpeta del modelo.", 'success')

def entrenamiento_yolo_trans():
    data = session.get('data')
    epocas = session.get('epocas')
    proyecto_id = session.get('proyecto')
    optimizador = session.get('optimizador')
    batch = session.get('batch')
    modelo_base = session.get('base_model')
    nombre_modelo = session.get('nombre_modelo')

    # Consultar el proyecto por su ID y obtener la ruta
    proyecto = Proyecto.query.filter_by(idProyecto=proyecto_id).first()

    # Crear la carpeta para guardar el modelo con el nombre obtenido de la sesión
    modelo_entrenado_path = os.path.join(proyecto.Nombre, "MODELOS_ENTRENADOS", nombre_modelo)
    os.makedirs(modelo_entrenado_path, exist_ok=True)  # Crear la carpeta si no existe

    # Definir la ruta para guardar el modelo entrenado
    model_save_path = os.path.join(modelo_entrenado_path, f"{nombre_modelo}.pt")

    # Cargar el modelo base YOLOv8
    model = YOLO(modelo_base)

    # Registrar el tiempo de inicio
    start_time = time.time()

    # Entrenar el modelo
    results = model.train(
        data=data,
        epochs=int(epocas),
        batch=int(batch),
        imgsz=640,
        optimizer=optimizador,
        project=modelo_entrenado_path,
        name=nombre_modelo,
        save=True,
        plots=True  # Activar la generación de gráficas
    )

    # Calcular el tiempo total de entrenamiento
    total_time = time.time() - start_time

    # Guardar el modelo entrenado
    model.save(model_save_path)

    # Extraer métricas y otros resultados
    box_metrics = results.box
    precision = box_metrics.p
    recall = box_metrics.r
    f1_score = box_metrics.f1.mean()
    map50 = box_metrics.map50
    map95 = box_metrics.map
    map75 = box_metrics.map75

    # Guardar las métricas en la base de datos
    nuevo_modelo = Modelos_generados(
        nombre=nombre_modelo,
        desc="Modelo entrenado con YOLOv8",
        epocas=epocas,
        batch=batch,
        fecha=date.today(),
        arquitectura="YOLOv8",
        proyecto=proyecto_id,
        optimizador=optimizador,
        dataset=session.get('id_data'),
        ruta=model_save_path
    )

    db.session.add(nuevo_modelo)
    db.session.commit()

    evaluacion_modelo = Evaluacion_modelo(
        score=f1_score,
        recall=recall.mean(),
        map50=map50,
        precision=precision.mean(),
        map50_95=map95,
        map75=map75,
        modelo=nuevo_modelo.idModelo_generados,
        tiempo=total_time
    )

    db.session.add(evaluacion_modelo)
    db.session.commit()

    # Imprimir información adicional
    flash(f"Modelo entrenado y guardado en {model_save_path}. Las gráficas se encuentran en la carpeta del modelo.", 'success')

def entrenamiento_rtdetr_cero():
    data = session.get('data')
    epocas = session.get('epocas')
    proyecto_id = session.get('proyecto')
    optimizador = session.get('optimizador')
    batch = session.get('batch')
    nombre_modelo = session.get('nombre_modelo')

    proyecto = Proyecto.query.filter_by(idProyecto=proyecto_id).first()

    modelo_entrenado_path = os.path.join(proyecto.Nombre, "MODELOS_ENTRENADOS", nombre_modelo)
    os.makedirs(modelo_entrenado_path, exist_ok=True)

    model_save_path = os.path.join(modelo_entrenado_path, f"{nombre_modelo}.pt")

    model = RTDETR()

    start_time = time.time()

    resultados = model.train(
        data=data,
        epochs=int(epocas),
        imgsz=640,
        batch=int(batch),
        optimizer=optimizador
    )

    total_time = time.time() - start_time

    model.save(model_save_path)

    exp_dir = resultados.save_dir
    renamed_exp_dir = os.path.join(os.path.dirname(exp_dir), nombre_modelo)

    try:
        # Si ya existe una carpeta con el nombre, eliminarla
        if os.path.exists(renamed_exp_dir):
            shutil.rmtree(renamed_exp_dir)

        # Mover la carpeta generada
        shutil.move(exp_dir, renamed_exp_dir)
        shutil.move(renamed_exp_dir, modelo_entrenado_path)
    except PermissionError as e:
        flash(f"Error de permisos al mover la carpeta: {e}", "danger")
        return

    # Procesar métricas y guardar en la base de datos
    results_csv_path = os.path.join(modelo_entrenado_path, nombre_modelo, "results.csv")
    if os.path.exists(results_csv_path):
        try:
            metrics_df = pd.read_csv(results_csv_path)

            recall = metrics_df["metrics/recall(B)"].iloc[-1]
            precision = metrics_df["metrics/precision(B)"].iloc[-1]
            map50 = metrics_df["metrics/mAP50(B)"].iloc[-1]
            map50_95 = metrics_df["metrics/mAP50-95(B)"].iloc[-1]

            nuevo_modelo = Modelos_generados(
                nombre=nombre_modelo,
                desc="Modelo entrenado con RTDETR",
                epocas=epocas,
                batch=batch,
                fecha=date.today(),
                arquitectura="RTDETR",
                proyecto=proyecto_id,
                optimizador=optimizador,
                dataset=session.get('id_data'),
                ruta=model_save_path
            )

            db.session.add(nuevo_modelo)
            db.session.commit()

            f1_score = 2 * (precision * recall) / (precision + recall) if precision + recall > 0 else 0.0

            evaluacion_modelo = Evaluacion_modelo(
                score=f1_score,
                recall=recall,
                map50=map50,
                precision=precision,
                map50_95=map50_95,
                map75=None,
                modelo=nuevo_modelo.idModelo_generados,
                tiempo=total_time
            )

            db.session.add(evaluacion_modelo)
            db.session.commit()

            flash(f"Modelo entrenado y guardado en {model_save_path}", 'success')
        except KeyError as e:
            flash(f"Error al procesar las métricas: {e}", "danger")
            print("Columnas disponibles en el CSV:", metrics_df.columns)
        except SQLAlchemyError as e:
            flash(f"Error al guardar en la base de datos: {e}", "danger")
    else:
        flash(f"No se encontró el archivo de métricas en {results_csv_path}", "danger")

def entrenamiento_rtdetr_trans():
    data = session.get('data')
    epocas = session.get('epocas')
    proyecto_id = session.get('proyecto')
    optimizador = session.get('optimizador')
    batch = session.get('batch')
    nombre_modelo = session.get('nombre_modelo')
    modelo_base = session.get('model_base')

    proyecto = Proyecto.query.filter_by(idProyecto=proyecto_id).first()

    modelo_entrenado_path = os.path.join(proyecto.Nombre, "MODELOS_ENTRENADOS", nombre_modelo)
    os.makedirs(modelo_entrenado_path, exist_ok=True)

    model_save_path = os.path.join(modelo_entrenado_path, f"{nombre_modelo}.pt")

    model = RTDETR(modelo_base)

    start_time = time.time()

    resultados = model.train(
        data=data,
        epochs=int(epocas),
        imgsz=640,
        batch=int(batch),
        optimizer=optimizador
    )

    total_time = time.time() - start_time

    model.save(model_save_path)

    exp_dir = resultados.save_dir
    renamed_exp_dir = os.path.join(os.path.dirname(exp_dir), nombre_modelo)
    if os.path.exists(exp_dir):
        os.rename(exp_dir, renamed_exp_dir)

    shutil.move(renamed_exp_dir, modelo_entrenado_path)

    results_csv_path = os.path.join(modelo_entrenado_path, nombre_modelo, "results.csv")
    if os.path.exists(results_csv_path):
        try:
            metrics_df = pd.read_csv(results_csv_path)

            recall = metrics_df["metrics/recall(B)"].iloc[-1]
            precision = metrics_df["metrics/precision(B)"].iloc[-1]
            map50 = metrics_df["metrics/mAP50(B)"].iloc[-1]
            map50_95 = metrics_df["metrics/mAP50-95(B)"].iloc[-1]

            map75 = metrics_df.get("metrics/mAP_0.75", None)

            nuevo_modelo = Modelos_generados(
                nombre=nombre_modelo,
                desc="Modelo entrenado con RTDETR",
                epocas=epocas,
                batch=batch,
                fecha=date.today(),
                arquitectura="RTDETR",
                proyecto=proyecto_id,
                optimizador=optimizador,
                dataset=session.get('id_data'),
                ruta=model_save_path
            )

            db.session.add(nuevo_modelo)
            db.session.commit()

            f1_score = 2 * (precision * recall) / (precision + recall) if precision + recall > 0 else 0.0

            evaluacion_modelo = Evaluacion_modelo(
                score=f1_score,
                recall=recall,
                map50=map50,
                precision=precision,
                map50_95=map50_95,
                map75=map75,
                modelo=nuevo_modelo.idModelo_generados,
                tiempo=total_time
            )

            db.session.add(evaluacion_modelo)
            db.session.commit()

            flash(f"Modelo entrenado y guardado en {model_save_path}", 'success')
        except KeyError as e:
            flash(f"Error al procesar las métricas: {e}", "danger")
            print("Columnas disponibles en el CSV:", metrics_df.columns)
    else:
        flash(f"No se encontró el archivo de métricas en {results_csv_path}", 'danger')

@login_required
@bp.route('modelos_generados')
def modelos_generados():
    # Obtener el usuario actual desde la sesión
    id_usuario = session.get('user')
    # Consulta para obtener los modelos entrenados de los proyectos del usuario actual
    modelos = (
        db.session.query(Modelos_generados)
        .join(Proyecto, Proyecto.idProyecto == Modelos_generados.Proyecto)
        .filter(Proyecto.Usuario == id_usuario)
        .all()
    )
    return render_template('modelos_generados/inicio.html', modelos=modelos)

@bp.route('/filtrar', methods=['POST', 'GET'])
@login_required
def filtrar():
    usuario_id = session.get('user')
    proyecto_id = request.form.get('proyecto_id')
    modelo_id = request.form.get('modelo_id')
    archivo_zip = request.files.get('archivo_zip')  # Obtener el archivo ZIP
    session['proyecto_in'] = proyecto_id
    imagenes_procesadas = []

    if archivo_zip and archivo_zip.filename:
        flash('Procesando archivo ZIP', 'success')
        filename = secure_filename(archivo_zip.filename)
        proy = Proyecto.query.get(int(proyecto_id))
        folder = os.path.join(RUTA_BASE, proy.Nombre)
        upload_folder = os.path.join(folder, "INFERENCIAS")
        os.makedirs(upload_folder, exist_ok=True)

        # Vaciar la carpeta INFERENCIAS
        for file in os.listdir(upload_folder):
            file_path = os.path.join(upload_folder, file)
            try:
                if os.path.isfile(file_path):
                    os.remove(file_path)
            except Exception as e:
                print(f"Error al eliminar {file_path}: {e}")

        # Guardar y procesar el archivo ZIP
        zip_path = os.path.join(upload_folder, filename)
        archivo_zip.save(zip_path)

        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(upload_folder)
        imagenes_extraidas = [
            os.path.join(upload_folder, img) for img in os.listdir(upload_folder) if img.endswith(('.png', '.jpg', '.jpeg'))
        ]
        if modelo_id:
            modelo = Modelos_generados.query.get(modelo_id)
            for imagen_path in imagenes_extraidas:
                if modelo.Arquitectura == "YOLOv8":
                    print("Aplicando inferencia a la imagen: ", imagen_path)
                    imagenes_procesadas.extend(inferencia_yolo(modelo.Ruta, imagen_path, upload_folder))
                elif modelo.Arquitectura == "RTDETR":
                    imagenes_procesadas.extend(inferencia_rtdetr(modelo.Ruta, imagen_path, upload_folder))

        flash('Archivo ZIP descomprimido y procesado exitosamente.', 'success')

    proyectos = Proyecto.query.filter_by(Usuario=usuario_id).all()
    modelos_por_proyecto = {
        proyecto.idProyecto: [
            {
                'idModelo_generados': modelo.idModelo_generados,
                'Nombre': modelo.Nombre
            }
            for modelo in Modelos_generados.query.filter_by(Proyecto=proyecto.idProyecto).all()
        ]
        for proyecto in proyectos
    }

    return render_template(
        'experimentador/filtrar.html',
        proyectos=proyectos,
        imagenes_procesadas=imagenes_procesadas[:10],  # Máximo 10 imágenes
        modelos_por_proyecto=modelos_por_proyecto
    )

def inferencia_yolo(Ruta, imagen, upload_folder):
    model_path = os.path.join(RUTA_BASE, Ruta)
    model = YOLO(model_path)

    # Cargar la imagen en formato NumPy (usando OpenCV)
    imagen_cargada = cv2.imread(imagen)

    # Verificar si la imagen se cargó correctamente
    if imagen_cargada is None:
        raise ValueError(f"No se pudo cargar la imagen: {imagen}")

    # Redimensionar la imagen a 640x640 antes de la inferencia
    imagen_resized = cv2.resize(imagen_cargada, (640, 640))

    # Realizar la inferencia en la imagen redimensionada
    results = model(imagen_resized)

    imagenes_procesadas = []

    for result in results:
        boxes = result.boxes
        if boxes:
            # Filtrar las detecciones con confianza superior a 0.75
            detecciones_filtradas = [box for box in boxes if box.conf > 0.75]

            if detecciones_filtradas:
                # Seleccionar solo la primera detección (o la más relevante)
                box = detecciones_filtradas[0]  # Tomar la primera caja detectada

                # Obtener el porcentaje de precisión (confianza)
                confianza = box.conf.item()  # Confianza de la detección
                class_id = int(box.cls.item())  # ID de la clase detectada
                class_name = model.names[class_id]  # Nombre de la clase detectada

                # Dibujar la caja en la imagen
                x1, y1, x2, y2 = box.xyxy[0]  # Coordenadas de la caja
                cv2.rectangle(imagen_resized, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)

                # Escribir el nombre de la clase y la confianza en la imagen
                label = f"{class_name} {confianza * 100:.2f}%"
                cv2.putText(imagen_resized, label, (int(x1), int(y1) - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

                # Guardar la imagen procesada con la caja dibujada
                imagen_name = os.path.join(upload_folder, f"resultado_{os.path.basename(imagen)}")
                cv2.imwrite(imagen_name, imagen_resized)  # Guardar imagen procesada

                # Añadir el nombre de la imagen y el porcentaje de precisión
                imagenes_procesadas.append({
                    'imagen': os.path.join('INFERENCIAS', f"resultado_{os.path.basename(imagen)}"),
                    'precisión': f"{confianza * 100:.2f}%",
                    'clase': class_name
                })

    return imagenes_procesadas



def inferencia_rtdetr(Ruta, imagen, upload_folder):
    model_path = os.path.join(RUTA_BASE, Ruta)
    model = RTDETR(model_path)

    # Cargar la imagen en formato NumPy (usando OpenCV)
    image = cv2.imread(imagen)
    
    # Realizar la inferencia con el modelo RTDETR
    results = model.predict(image)

    imagenes_procesadas = []

    # Filtrar las detecciones con confianza superior a 0.75
    detecciones_filtradas = [det for det in results if det['confidence'] > 0.75]

    if detecciones_filtradas:
        # Tomar solo la primera detección filtrada
        deteccion = detecciones_filtradas[0]

        # Obtener el porcentaje de precisión (confianza) y el nombre de la clase
        confianza = deteccion['confidence']
        class_name = deteccion['class_name']  # Asumiendo que 'class_name' es el nombre de la clase detectada

        # Visualizar y dibujar la caja de la detección
        resultado = model.visualize([deteccion], image)

        # Obtener las coordenadas de la caja para dibujar el texto
        x1, y1, x2, y2 = deteccion['bbox']
        label = f"{class_name} {confianza * 100:.2f}%"
        cv2.putText(resultado, label, (int(x1), int(y1) - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

        # Guardar imagen procesada con la caja dibujada
        imagen_name = os.path.join(upload_folder, f"resultado_{os.path.basename(imagen)}")
        cv2.imwrite(imagen_name, resultado)  # Guardar imagen procesada

        # Añadir el nombre de la imagen y el porcentaje de precisión
        imagenes_procesadas.append({
            'imagen': os.path.join('INFERENCIAS', f"resultado_{os.path.basename(imagen)}"),
            'precisión': f"{confianza * 100:.2f}%",
            'clase': class_name
        })

    return imagenes_procesadas


@bp.route('/inferencias/<path:filename>')
def serve_inferencia(filename):
    proyecto_id = session.get("proyecto_in")
    print("Proyecto ID:", proyecto_id)

    if not proyecto_id:
        return "Error: 'proyecto_id' no proporcionado", 400

    try:
        proy = Proyecto.query.get(int(proyecto_id))
    except ValueError:
        return "Error: 'proyecto_id' debe ser un número entero válido", 400

    if not proy:
        return "Error: Proyecto no encontrado", 404

    # Asegurarse de que filename no tenga directorios adicionales maliciosos
    safe_filename = os.path.basename(filename)
    folder = os.path.join(RUTA_BASE, proy.Nombre, "INFERENCIAS")
    file_path = os.path.join(folder, safe_filename)

    print("Ruta del directorio de inferencias:", folder)
    print(f"Intentando servir el archivo desde: {file_path}")

    if not os.path.exists(file_path):
        return f"Error: El archivo {safe_filename} no existe en el directorio {folder}", 404

    try:
        # Usar safe_filename para evitar problemas de ruta
        return send_from_directory(folder, safe_filename)
    except Exception as e:
        print(f"Error al servir el archivo: {e}")
        return f"Error al servir el archivo: {str(e)}", 500


@bp.route('/download_model/<int:modelo_id>', methods=['GET'])
def download_model(modelo_id):
    # Obtener el modelo por ID
    modelo = Modelos_generados.query.get_or_404(modelo_id)
    
    # Construir la ruta completa del archivo usando la ruta base
    archivo_path = os.path.join(RUTA_BASE, modelo.Ruta)  # Combina la ruta base con la ruta relativa almacenada
    
    # Verificar si el archivo existe
    if not os.path.exists(archivo_path):
        flash('El archivo solicitado no fue encontrado.', 'warning')
        return redirect(url_for('experimentador.modelos_generados'))  # Redirigir si no existe
    
    # Obtener el directorio y el nombre del archivo
    directorio = os.path.dirname(archivo_path)
    nombre_archivo = os.path.basename(archivo_path)
    

    
    # Enviar el archivo para su descarga
    return send_from_directory(directorio, nombre_archivo, as_attachment=True)

