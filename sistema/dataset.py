from flask import (
    Blueprint, render_template, request, url_for, redirect, flash, session, send_file
)
import os
import random
import shutil
import yaml
import numpy as np
import cv2
from datetime import datetime
from datetime import date
from .models import DataSet, Proyecto
from sistema import db, RUTA_BASE
import json
from flask import send_from_directory
from werkzeug.utils import secure_filename
import zipfile
from .auth import login_required

bp = Blueprint('dataset', __name__, url_prefix='/dataset')

@bp.route('/generar-dataset', methods=['POST', 'GET'])
@login_required
def generar():
    if request.method == 'POST':
        # Recuperar las imágenes de la sesión
        imagenes_a_eliminar = session.get('imagenes_a_eliminar')
        clases = session.get('clases_dataset')
        
        # Obtener el valor de 'formato' desde el formulario
        formato = request.form.get('formato')
        print(f"Formato recibido: {formato}")  # Verificar qué valor llega aquí
        
        if not imagenes_a_eliminar:
            flash('No hay imágenes seleccionadas para generar el dataset', 'warning')
            return redirect(url_for('imagenes.visualizar'))
        
        if not clases:
            return redirect(url_for('dataset.registrar_clases'))

        # Inicia el proceso de generación de etiquetas
        proyecto = session.get('proyecto')
        ruta_proyecto = os.path.join(RUTA_BASE, proyecto)

        if not formato:
            flash('No se ha seleccionado el formato', 'warning')
        elif formato == "yolo":
            dividir_imagenes(ruta_proyecto)
            cargar_imagenes_y_etiquetar()
            crear_archivo_yaml(ruta_proyecto, clases)
        elif formato == "transformer":
            dividir_imagenes_coco(ruta_proyecto)
            cargar_imagenes_y_etiquetar_coco()
        return redirect(url_for('dataset.registrar'))
    return render_template('dataset/generar.html')

def dividir_imagenes(ruta_base_imagenes, proporciones=(0.7, 0.1, 0.2)):
    carpetas = ['train', 'valid', 'test']
    for carpeta in carpetas:
        os.makedirs(os.path.join(ruta_base_imagenes, carpeta, 'images'), exist_ok=True)
        os.makedirs(os.path.join(ruta_base_imagenes, carpeta, 'labels'), exist_ok=True)

    imagenes = [f for f in os.listdir(ruta_base_imagenes) if os.path.isfile(os.path.join(ruta_base_imagenes, f))]
    random.shuffle(imagenes)

    total = len(imagenes)
    train_split = int(proporciones[0] * total)
    val_split = int(proporciones[1] * total) + train_split

    for i, imagen in enumerate(imagenes):
        if i < train_split:
            conjunto = 'train'
        elif i < val_split:
            conjunto = 'valid'
        else:
            conjunto = 'test'

        shutil.move(os.path.join(ruta_base_imagenes, imagen), os.path.join(ruta_base_imagenes, conjunto, 'images', imagen))

import cv2

def cargar_imagenes_y_etiquetar():
    ruta_imagenes = os.path.join(RUTA_BASE, session.get('proyecto'))
    clases = session.get('clases_dataset')
    global imagen, puntos_poligono, rect_inicio, clase_actual, colores_clases, rect_final
    puntos_poligono = []
    rect_inicio = None
    rect_final = None
    colores_clases = {}
    clase_actual = 0  # Inicializar clase_actual en la primera clase

    # Asignar colores aleatorios a cada clase
    for i, clase in enumerate(clases):
        colores_clases[i] = tuple([random.randint(0, 255) for _ in range(3)])

    carpetas_conjunto = ['train', 'valid', 'test']
    total_imagenes = 0
    imagenes_procesadas = 0

    # Primero, contar cuántas imágenes hay en total
    for carpeta_conjunto in carpetas_conjunto:
        ruta_imagenes_conjunto = os.path.join(ruta_imagenes, carpeta_conjunto, 'images')
        archivos_imagenes = [f for f in os.listdir(ruta_imagenes_conjunto) if os.path.isfile(os.path.join(ruta_imagenes_conjunto, f))]
        total_imagenes += len(archivos_imagenes)

    for carpeta_conjunto in carpetas_conjunto:
        ruta_imagenes_conjunto = os.path.join(ruta_imagenes, carpeta_conjunto, 'images')
        archivos_imagenes = [f for f in os.listdir(ruta_imagenes_conjunto) if os.path.isfile(os.path.join(ruta_imagenes_conjunto, f))]

        if not archivos_imagenes:
            flash(f"No se encontraron imágenes en {ruta_imagenes_conjunto}", 'warning')
            continue

        for archivo_imagen in archivos_imagenes:
            ruta_imagen_completa = os.path.join(ruta_imagenes_conjunto, archivo_imagen)
            imagen = cv2.imread(ruta_imagen_completa)
            
            # Verifica si la imagen se cargó correctamente
            if imagen is None:
                flash(f"Error al cargar la imagen: {ruta_imagen_completa}", 'error')
                continue

            alto_imagen, ancho_imagen = imagen.shape[:2]

            # Crear la ventana con la opción para no maximizar
            cv2.namedWindow('ANOTACIONES', cv2.WINDOW_NORMAL)  # Permite cambiar el tamaño de la ventana
            cv2.resizeWindow('ANOTACIONES', ancho_imagen, alto_imagen)  # Ajustar el tamaño de la ventana al tamaño de la imagen
            cv2.setWindowProperty('ANOTACIONES', cv2.WND_PROP_TOPMOST, 1)  # Asegura que la ventana esté siempre encima

            # Establecer los callbacks de mouse solo una vez
            cv2.setMouseCallback('ANOTACIONES', dibujar_poligono)  # Establecer el callback para el polígono
            rect_inicio = None
            rect_final = None

            while True:
                imagen_display = imagen.copy()
                
                # Verificar que la imagen se copió correctamente
                if imagen_display is None:
                    flash("Error al procesar la imagen", 'error')
                    continue

                # Colocar texto en la imagen
                cv2.putText(imagen_display, f"Clase actual: {clases[clase_actual]}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 200, 200), 2)

                # Mostrar el nombre de la imagen y el progreso
                progreso = f"{imagenes_procesadas + 1}/{total_imagenes}"
                cv2.putText(imagen_display, f"Imagen: {archivo_imagen} ({progreso})", (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 200, 200), 2)

                # Mostrar imagen
                cv2.imshow('ANOTACIONES', imagen_display)  # Usar el mismo nombre de la ventana

                tecla = cv2.waitKey(10) & 0xFF  # Aumentar el tiempo de espera a 10 ms

                if tecla == ord('p'):
                    puntos_poligono = []
                    cv2.setMouseCallback('ANOTACIONES', dibujar_poligono)
                elif tecla == ord('r'):
                    rect_inicio = None
                    rect_final = None
                    cv2.setMouseCallback('ANOTACIONES', dibujar_rectangulo)
                elif tecla == ord('s'):
                    if puntos_poligono:
                        guardar_anotacion(puntos_poligono, 'poligono', clase_actual, archivo_imagen, ruta_imagenes_conjunto, ancho_imagen, alto_imagen)
                        puntos_poligono = []  # Reiniciar puntos del polígono
                    elif rect_inicio and rect_final:
                        guardar_anotacion([rect_inicio, rect_final], 'rectangulo', clase_actual, archivo_imagen, ruta_imagenes_conjunto, ancho_imagen, alto_imagen)
                        rect_inicio = None
                        rect_final = None

                    # Cambiar a la siguiente clase
                    clase_actual = (clase_actual + 1) % len(clases)
                elif tecla == ord('n'):
                    break
                elif tecla == ord('q'):
                    # Cerrar todas las ventanas abiertas de OpenCV
                    cv2.destroyAllWindows()
                    return

            # Después de procesar una imagen, aumentar el contador de imágenes procesadas
            imagenes_procesadas += 1

            # Asegúrate de cerrar la ventana antes de continuar con la siguiente imagen
            cv2.destroyAllWindows()

    # Al finalizar el proceso para todas las imágenes, redirigir al siguiente paso
    return redirect(url_for('dataset.generar'))





def guardar_anotacion(puntos, tipo, clase, archivo_imagen, ruta_imagenes_conjunto, ancho_imagen, alto_imagen):
    """Guarda la anotación de la imagen en un archivo con el mismo nombre de la imagen."""
    nombre_base, _ = os.path.splitext(archivo_imagen)
    archivo_anotacion_yolo = os.path.join(ruta_imagenes_conjunto.replace('images', 'labels'), f"{nombre_base}.txt")
    
    if not os.path.exists(os.path.dirname(archivo_anotacion_yolo)):
        os.makedirs(os.path.dirname(archivo_anotacion_yolo))
    
    with open(archivo_anotacion_yolo, 'a') as archivo:
        if tipo == 'poligono':
            puntos_normalizados = [(x / ancho_imagen, y / alto_imagen) for x, y in puntos]
            puntos_str = ' '.join([f'{x:.6f} {y:.6f}' for x, y in puntos_normalizados])
            archivo.write(f'{clase} {puntos_str}\n')
        elif tipo == 'rectangulo':
            x_min = min(puntos[0][0], puntos[1][0]) / ancho_imagen
            y_min = min(puntos[0][1], puntos[1][1]) / alto_imagen
            x_max = max(puntos[0][0], puntos[1][0]) / ancho_imagen
            y_max = max(puntos[0][1], puntos[1][1]) / alto_imagen
            x_centro = (x_min + x_max) / 2
            y_centro = (y_min + y_max) / 2
            ancho = x_max - x_min
            alto = y_max - y_min
            archivo.write(f'{clase} {x_centro:.6f} {y_centro:.6f} {ancho:.6f} {alto:.6f}\n')

# Función para crear archivo YAML en el directorio raíz
def crear_archivo_yaml(ruta_base, clases):
    contenido = {
        'train': '../train/images',
        'val': '../valid/images',
        'test': '../test/images',
        'nc': len(clases),
        'names': clases
    }

    with open(os.path.join(ruta_base, 'data.yaml'), 'w') as archivo_yaml:
        yaml.dump(contenido, archivo_yaml, default_flow_style=False)

# Función para dividir imágenes en train, val y test
def dividir_imagenes_coco(ruta_base_imagenes, proporciones=(0.7, 0.1, 0.2)):
    carpetas = ['train', 'valid', 'test']
    for carpeta in carpetas:
        os.makedirs(os.path.join(ruta_base_imagenes, carpeta), exist_ok=True)

    imagenes = [f for f in os.listdir(ruta_base_imagenes) if os.path.isfile(os.path.join(ruta_base_imagenes, f))]
    random.shuffle(imagenes)

    total = len(imagenes)
    train_split = int(proporciones[0] * total)
    val_split = int(proporciones[1] * total) + train_split

    for i, imagen in enumerate(imagenes):
        if i < train_split:
            conjunto = 'train'
        elif i < val_split:
            conjunto = 'valid'
        else:
            conjunto = 'test'

        shutil.move(os.path.join(ruta_base_imagenes, imagen), os.path.join(ruta_base_imagenes, conjunto, imagen))

def cargar_imagenes_y_etiquetar_coco():
    ruta_imagenes = os.path.join(RUTA_BASE, session.get('proyecto'))
    clases = session.get('clases_dataset')
    global imagen, puntos_poligono, rect_inicio, clase_actual, colores_clases, rect_final
    puntos_poligono = []
    rect_inicio = None
    rect_final = None
    colores_clases = {}
    clase_actual = 0  # Inicializar clase_actual en la primera clase

    # Asignar colores aleatorios a cada clase
    for i, clase in enumerate(clases):
        colores_clases[i] = tuple([random.randint(0, 255) for _ in range(3)])

    # Carpetas de conjuntos
    carpetas_conjunto = ['train', 'valid', 'test']
    
    # Lista para almacenar las anotaciones a nivel global
    anotaciones = []
    categorias = [{'id': i, 'name': clase} for i, clase in enumerate(clases)]

    for carpeta_conjunto in carpetas_conjunto:
        ruta_imagenes_conjunto = os.path.join(ruta_imagenes, carpeta_conjunto)
        
        # Verificamos si la carpeta existe y contiene archivos de imagen
        if not os.path.exists(ruta_imagenes_conjunto):
            flash(f"No se encontró la carpeta {carpeta_conjunto}", 'warning')
            continue

        archivos_imagenes = [f for f in os.listdir(ruta_imagenes_conjunto) if os.path.isfile(os.path.join(ruta_imagenes_conjunto, f))]

        if not archivos_imagenes:
            flash(f"No se encontraron imágenes en {ruta_imagenes_conjunto}", 'warning')
            continue

        for i, archivo_imagen in enumerate(archivos_imagenes):
            ruta_imagen_completa = os.path.join(ruta_imagenes_conjunto, archivo_imagen)
            imagen = cv2.imread(ruta_imagen_completa)
            if imagen is None:
                flash(f"Error al cargar la imagen: {ruta_imagen_completa}", 'error')
                continue

            alto_imagen, ancho_imagen = imagen.shape[:2]
            
            image_id = i  # Usamos el índice como ID de imagen
            cv2.namedWindow('ANOTACIÓN')

            while True:
                imagen_display = imagen.copy()
                cv2.putText(imagen_display, f"Clase actual: {clases[clase_actual]}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 200, 200), 2)

                cv2.imshow('ANOTACIÓN', imagen_display)

                tecla = cv2.waitKey(1) & 0xFF

                if tecla == ord('p'):
                    puntos_poligono = []
                    cv2.setMouseCallback('ANOTACIÓN', dibujar_poligono)
                elif tecla == ord('r'):
                    rect_inicio = None
                    rect_final = None
                    cv2.setMouseCallback('ANOTACIÓN', dibujar_rectangulo)
                elif tecla == ord('s'):
                    if puntos_poligono:
                        guardar_anotacion_coordenadas(image_id, 'poligono', puntos_poligono, clase_actual, ancho_imagen, alto_imagen, anotaciones, categorias)
                        puntos_poligono = []  # Limpiar la lista de puntos para el siguiente polígono
                    elif rect_inicio and rect_final:
                        x1, y1 = rect_inicio
                        x2, y2 = rect_final
                        guardar_anotacion_coordenadas(image_id, 'rectangulo', (x1, y1, x2, y2), clase_actual, ancho_imagen, alto_imagen, anotaciones, categorias)
                        rect_inicio = None
                        rect_final = None

                    clase_actual = (clase_actual + 1) % len(clases)
                elif tecla == ord('n'):
                    break
                elif tecla == ord('q'):
                    cv2.destroyAllWindows()
                    return

            # Guardar las anotaciones por cada imagen (si deseas guardar los resultados inmediatamente)
            guardar_etiquetas_coco_1(anotaciones, categorias, ruta_imagenes, carpeta_conjunto, archivo_imagen)

        # Llamada para guardar el archivo COCO después de procesar todas las imágenes de la carpeta
        guardar_etiquetas_coco_1(anotaciones, categorias, ruta_imagenes, carpeta_conjunto)

    cv2.destroyAllWindows()
    return redirect(url_for('dataset.generar'))


def guardar_etiquetas_coco_1(anotaciones, categorias, ruta_imagenes, carpeta_conjunto, archivo_imagen=None):
    archivos_imagenes = [f for f in os.listdir(os.path.join(ruta_imagenes, carpeta_conjunto)) if f.endswith('.jpg') or f.endswith('.png')]
    
    coco_data = {
        'images': [],
        'annotations': anotaciones,
        'categories': categorias
    }

    for i, img in enumerate(archivos_imagenes):
        imagen = cv2.imread(os.path.join(ruta_imagenes, carpeta_conjunto, img))
        if imagen is None:
            continue

        coco_data['images'].append({
            'id': i,
            'file_name': img,
            'width': imagen.shape[1],
            'height': imagen.shape[0]
        })

    # Guarda las anotaciones por cada conjunto
    archivo_json = os.path.join(ruta_imagenes, carpeta_conjunto, '_annotations.json')
    if not os.path.exists(os.path.join(ruta_imagenes, carpeta_conjunto)):
        os.makedirs(os.path.join(ruta_imagenes, carpeta_conjunto))
    
    with open(archivo_json, 'w') as f:
        json.dump(coco_data, f)

    print(f"Archivo JSON guardado en: {archivo_json}")



def guardar_anotacion_coordenadas(image_id, tipo, puntos, clase, ancho_imagen, alto_imagen, anotaciones, categorias):
    if tipo == 'poligono':
        puntos_normalizados = normalizar_coordenadas(puntos, ancho_imagen, alto_imagen)
        segmentation = [point for tuple_point in puntos_normalizados for point in tuple_point]
        
        puntos_np = np.array(puntos_normalizados)
        x_min, y_min = np.min(puntos_np, axis=0)
        x_max, y_max = np.max(puntos_np, axis=0)
        bbox = [x_min, y_min, x_max - x_min, y_max - y_min]
        
        annotation = {
            'image_id': image_id,
            'category_id': clase,
            'segmentation': [segmentation],
            'bbox': bbox,
            'area': bbox[2] * bbox[3],
            'iscrowd': 0
        }
        anotaciones.append(annotation)

    elif tipo == 'rectangulo':
        x1, y1, x2, y2 = puntos
        x1_norm, y1_norm = x1 / ancho_imagen, y1 / alto_imagen
        x2_norm, y2_norm = x2 / ancho_imagen, y2 / alto_imagen
        bbox = [x1_norm, y1_norm, x2_norm - x1_norm, y2_norm - y1_norm]
        
        annotation = {
            'image_id': image_id,
            'category_id': clase,
            'segmentation': [],
            'bbox': bbox,
            'area': (x2 - x1) * (y2 - y1),
            'iscrowd': 0
        }
        anotaciones.append(annotation)

        
def normalizar_coordenadas(puntos, ancho, alto):
    return [(x / ancho, y / alto) for x, y in puntos]

def dibujar_rectangulo(event, x, y, flags, param):
    global rect_inicio, rect_final, clase_actual

    if event == cv2.EVENT_LBUTTONDOWN:
        rect_inicio = (x, y)  # Establece el punto inicial del rectángulo
        rect_final = None  # Reinicia el punto final

    elif event == cv2.EVENT_MOUSEMOVE:
        if rect_inicio is not None:
            rect_final = (x, y)  # Actualiza el punto final mientras se mueve el ratón

    elif event == cv2.EVENT_LBUTTONUP:
        rect_final = (x, y)  # Establece el punto final al soltar el botón
        if clase_actual is not None:
            # Verifica que clase_actual esté definida
            cv2.rectangle(imagen, rect_inicio, rect_final, colores_clases[clase_actual], 2)
        else:
            flash("Error: No se ha seleccionado ninguna clase.", 'error')


def dibujar_poligono(event, x, y, flags, param):
    global puntos_poligono, colores_clases, clase_actual, imagen

    if event == cv2.EVENT_LBUTTONDOWN:
        puntos_poligono.append((x, y))
        if clase_actual is not None and clase_actual in colores_clases:
            cv2.circle(imagen, (x, y), 3, colores_clases[clase_actual], -1)
        if len(puntos_poligono) > 1:
            cv2.line(imagen, puntos_poligono[-2], puntos_poligono[-1], colores_clases[clase_actual], 2)

    elif event == cv2.EVENT_RBUTTONDOWN:
        if len(puntos_poligono) > 1 and clase_actual is not None and clase_actual in colores_clases:
            cv2.polylines(imagen, [np.array(puntos_poligono)], isClosed=True, color=colores_clases[clase_actual], thickness=2)
        puntos_poligono = []  # Reiniciar puntos después de cerrar el polígono

# FUNCIONES PARA MANIPULAR EL DATASET
@bp.route('/agregar_clases', methods=['POST', 'GET'])
@login_required
def registrar_clases():
    if request.method == 'POST':
        clases = request.form.getlist('clases[]')  # Capturamos las clases ingresadas
        if clases:
            session['clases_dataset'] = clases
            flash(f'Se han registrado las siguientes clases: {clases}', 'success')  # Mensaje de éxito
            return redirect(url_for('dataset.generar')) 
        flash('No se han registrado clases', 'warning')  # Mensaje de advertencia si no hay clases
    return render_template('dataset/registrar_clases.html')

@bp.route('/registrar', methods=['POST', 'GET'])  # Asegúrate de que la ruta acepte métodos POST y GET
@login_required
def registrar():
    if request.method == 'POST':
        nombre = request.form.get('nombre_dataset').strip()  # Eliminar espacios extra en el nombre del dataset
        descripcion = request.form.get('descripcion_dataset')
        proyecto_nombre = session.get('proyecto')  # Obtén el nombre del proyecto de la sesión
        fecha = date.today()  # Ya que importaste 'date' directamente
        estado = True
        tipo = "YOLO"
        
        # Extraer el ID del proyecto a partir de su nombre
        proyecto = Proyecto.query.filter_by(Nombre=proyecto_nombre).first()  # Asegúrate de que 'Nombre' sea el campo correcto
        if proyecto is None:
            flash('Proyecto no encontrado', 'danger')  # Manejar el caso en que el proyecto no exista
            return render_template('dataset/registrar.html')
        
        proyecto_id = proyecto.idProyecto  # Asumiendo que tu modelo tiene un campo 'idProyecto'

        # Registrar el dataset en la base de datos
        dataset = DataSet(nombre=nombre, descripcion=descripcion, proyecto=proyecto_id, fecha=fecha, estado=estado, tipo=tipo)
        db.session.add(dataset)
        db.session.commit()

        # Crear la carpeta "DATASET" dentro del proyecto
        ruta_proyecto = os.path.join(RUTA_BASE, proyecto_nombre)  # Ruta del proyecto
        ruta_datasets = os.path.join(ruta_proyecto, "DATASET")  # Ruta de la carpeta "DATASET" dentro del proyecto

        if not os.path.exists(ruta_datasets):
            os.makedirs(ruta_datasets)  # Crear la carpeta "DATASET" si no existe

        # Crear la carpeta del dataset dentro de "DATASET"
        carpeta_dataset = os.path.join(ruta_datasets, nombre)  # Ruta específica para el nuevo dataset

        if not os.path.exists(carpeta_dataset):
            os.makedirs(carpeta_dataset)  # Crear la carpeta del dataset si no existe
            print(f"Carpeta creada: {carpeta_dataset}")
        else:
            print(f"Carpeta ya existente: {carpeta_dataset}")

        # Crear el archivo `data.yaml` si no existe
        ruta_data_yaml = os.path.join(carpeta_dataset, 'data.yaml')
        if not os.path.exists(ruta_data_yaml):
            with open(ruta_data_yaml, 'w') as f:
                f.write("# YAML data placeholder\n")  # Placeholder para data.yaml
            print(f"Archivo creado: {ruta_data_yaml}")
        else:
            print(f"Archivo ya existente: {ruta_data_yaml}")

        # Mover contenido del proyecto al nuevo dataset, excluyendo "MODELOS" y "MODELOS_GENERADOS"
        for item in os.listdir(ruta_proyecto):
            if item in ["DATASET", "MODELOS", "MODELOS_GENERADOS"]:
                continue  # Ignorar las carpetas "DATASET", "MODELOS" y "MODELOS_GENERADOS"
            
            ruta_origen = os.path.join(ruta_proyecto, item)
            ruta_destino = os.path.join(carpeta_dataset, item)

            if os.path.isfile(ruta_origen):
                shutil.move(ruta_origen, ruta_destino)  # Mover archivos
            elif os.path.isdir(ruta_origen):
                shutil.move(ruta_origen, ruta_destino)  # Mover carpetas

        flash('Dataset generado exitosamente', 'success')  # Mensaje de éxito
        return redirect(url_for('dataset.inicio'))
    
    return render_template('dataset/registrar.html')


@bp.route('/inicio_datasets')
@login_required
def inicio():
    # Obtén el usuario actual de la sesión
    usuario_actual = session.get('user')

    # Primero, obtenemos los proyectos del usuario actual
    proyectos_usuario = Proyecto.query.filter_by(Usuario=usuario_actual).all()

    # Luego, obtenemos los IDs de los proyectos
    proyecto_ids = [p.idProyecto for p in proyectos_usuario]

    # Filtra los datasets usando los IDs de los proyectos
    datasets = DataSet.query.filter(DataSet.idProyecto.in_(proyecto_ids)).all()

    return render_template('dataset/inicio.html', datasets=datasets)

@bp.route('/eliminar', methods=['POST'])
@login_required
def eliminar():
    dataset_id = request.form.get('id')  # Obtén el ID del dataset desde el formulario
    if dataset_id and dataset_id.isdigit():
        data = DataSet.query.get(int(dataset_id))
        if data:
            data.Estado = False  # Cambia el estatus del dataset a 0 (eliminado o inactivo)
            db.session.commit()
            flash('Dataset eliminado correctamente.', 'success')
        else:
            flash('Dataset no encontrado.', 'danger')
    else:
        flash('ID de Dataset no válido.', 'danger')

    return redirect(url_for('dataset.inicio'))

@bp.route('/habilitar', methods=['POST'])
@login_required
def habilitar():
    dataset_id = request.form.get('id')  # Obtén el ID del dataset desde el formulario
    if dataset_id and dataset_id.isdigit():
        data = DataSet.query.get(int(dataset_id))
        if data:
            data.Estado = True  # Cambia el estatus del dataset a 0 (eliminado o inactivo)
            db.session.commit()
            flash('Dataset habilitado correctamente.', 'success')
        else:
            flash('Dataset no encontrado.', 'danger')
    else:
        flash('ID de Dataset no válido.', 'danger')

    return redirect(url_for('dataset.inicio'))

@bp.route('/modificar/<int:id>', methods=['POST', 'GET'])
@login_required
def modificar(id):
    dataset = DataSet.query.get_or_404(id)

    if request.method == 'POST':
        # Obtener los nuevos valores del formulario
        nuevo_nombre = request.form.get('nombre_dataset')
        nueva_descripcion = request.form.get('descripcion_dataset')
        modificar_completo = request.form.get('modificar_completo')

        # Variables de rutas
        ruta_proyecto = os.path.join(RUTA_BASE, dataset.Proyecto.Nombre)
        ruta_antigua = os.path.join(ruta_proyecto, "DATASET", dataset.Nombre)
        ruta_nueva = os.path.join(ruta_proyecto, "DATASET", nuevo_nombre)
     
        try:
            # Cambiar el nombre de la carpeta solo si el nombre cambia
            if dataset.Nombre != nuevo_nombre:
                if not os.path.exists(ruta_antigua):
                    flash('La carpeta del dataset no existe.', 'danger')
                    return redirect(url_for('dataset.modificar', id=id))
                
                os.rename(ruta_antigua, ruta_nueva)

            if modificar_completo == 'si':
                flash('Las imágenes serán movidas fuera de la carpeta del dataset.', 'warning')
                for item in os.listdir(ruta_nueva):
                    origen = os.path.join(ruta_nueva, item)
                    destino = os.path.join(RUTA_BASE, dataset.Proyecto.Nombre, item)
                    shutil.move(origen, destino)
                shutil.rmtree(ruta_nueva)  # Eliminar carpeta antigua
                registrar_clases(dataset)

            # Actualizar datos del dataset
            dataset.Nombre = nuevo_nombre
            dataset.Descripcion = nueva_descripcion
            dataset.Fecha_creada = date.today()
            db.session.commit()

            flash('Dataset modificado exitosamente', 'success')
            return redirect(url_for('dataset.inicio'))

        except Exception as e:
            print(f"Error: {e}")
            flash('Error al modificar el dataset.', 'danger')
            return redirect(url_for('dataset.modificar', id=id))

    return render_template('dataset/modificar.html', dataset=dataset)


@bp.route('/visualizar_dataset/<int:id>', methods=['GET'])
@login_required
def visualizar(id):
    dataset_id = id
    if not dataset_id:
        flash('ID del dataset no proporcionado', 'danger')
        return redirect(url_for('dataset.inicio'))

    dataset = DataSet.query.get(dataset_id)
    if not dataset:
        flash('Dataset no encontrado', 'danger')
        return redirect(url_for('dataset.inicio'))

    # Ruta del proyecto y carpeta del dataset
    ruta_proyecto = os.path.join(RUTA_BASE, dataset.Proyecto.Nombre)
    dataset_folder = os.path.join(ruta_proyecto, 'DATASET', dataset.Nombre)
    imagenes = []

    # Inicializar conteos
    conteos = {
        "train": 0,
        "test": 0,
        "valid": 0,
        "total": 0
    }

    if os.path.exists(dataset_folder):
        if dataset.Tipo == "YOLO":
            # Para YOLO, buscar en las subcarpetas 'train/images', 'test/images', 'valid/images'
            subcarpetas = ['train', 'test', 'valid']
            for subcarpeta in subcarpetas:
                images_folder = os.path.join(dataset_folder, subcarpeta, 'images')
                if os.path.exists(images_folder):
                    # Contar imágenes en la subcarpeta
                    conteos[subcarpeta] = len([imagen for imagen in os.listdir(images_folder) if imagen.endswith(('.png', '.jpg', '.jpeg', '.gif'))])
                    # Agregar imágenes a la lista
                    imagenes += [(imagen, subcarpeta) for imagen in os.listdir(images_folder) if imagen.endswith(('.png', '.jpg', '.jpeg', '.gif'))]
        else:
            # Para COCO, buscar directamente en las carpetas 'train', 'test', 'valid'
            subcarpetas = ['train', 'test', 'valid']
            for subcarpeta in subcarpetas:
                images_folder = os.path.join(dataset_folder, subcarpeta)
                if os.path.exists(images_folder):
                    # Contar imágenes en la subcarpeta
                    conteos[subcarpeta] = len([imagen for imagen in os.listdir(images_folder) if imagen.endswith(('.png', '.jpg', '.jpeg', '.gif'))])
                    # Agregar imágenes a la lista
                    imagenes += [(imagen, subcarpeta) for imagen in os.listdir(images_folder) if imagen.endswith(('.png', '.jpg', '.jpeg', '.gif'))]
    else:
        imagenes = []

    # Calcular el total de imágenes
    conteos['total'] = sum(conteos.values())

    # Renderizar la plantilla con los conteos y las imágenes
    return render_template('dataset/visualizar.html', imagenes=imagenes, dataset=dataset, conteos=conteos)


@bp.route('/dataset/yolo/<path:filename>')
@login_required
def servir_imagenes_yolo(filename):
    """
    Servir imágenes para datasets tipo YOLO desde las subcarpetas train/images, test/images, valid/images
    """
    # Obtener el ID del dataset de los parámetros de la URL
    dataset_id = request.args.get('dataset_id')
    datr = DataSet.query.get(dataset_id)
    if not dataset_id:
        flash("No se proporcionó el dataset_id", 'danger')
        return redirect(url_for('dataset.inicio'))  # Redirigir a la página de inicio o a otra página en caso de error

    # Obtener el nombre del dataset dinámicamente desde el filename
    dataset_nombre = filename.split('/')[0]  # Nombre del dataset está al principio del filename
    proy = Proyecto.query.get(datr.idProyecto)
    pr = os.path.join(RUTA_BASE, proy.Nombre)
    datas = os.path.join(pr, "DATASET")
    dataset_base_path = os.path.join(datas, dataset_nombre)  # Usamos el nombre del dataset dinámicamente

    # Aquí manejamos el filename recibido
    parts = filename.split('/')
    if len(parts) == 3:
        subcarpeta, categoria, imagen = parts
    else:
        flash("Ruta de imagen no válida", 'danger')
        return redirect(url_for('dataset.inicio'))

    # Verificamos que la categoría sea válida
    if categoria not in ['train', 'test', 'valid']:
        flash("Categoría inválida", 'danger')
        return redirect(url_for('dataset.inicio'))

    # Construimos la ruta completa donde se encuentra la imagen
    imagen_path = os.path.join(dataset_base_path, categoria, 'images', imagen)

    # Verificamos si el archivo existe y lo servimos
    if os.path.exists(imagen_path):
        return send_from_directory(os.path.join(dataset_base_path, categoria, 'images'), imagen)
    else:
        flash("La imagen no existe en la ruta especificada", 'danger')
        return redirect(url_for('dataset.inicio'))

@bp.route('/dataset/coco/<path:filename>')
@login_required
def servir_imagenes_coco(filename):
    """
    Servir imágenes para datasets tipo COCO desde las carpetas train, test, valid
    """
    dataset_base_path = os.path.join(RUTA_BASE, 'DATASET', filename.split('/')[0])  # Se agrega el nombre del proyecto
    return send_from_directory(dataset_base_path, filename)



def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() == 'zip'

@bp.route('/subir', methods=['GET', 'POST'])
@login_required
def subir_dataset():
    usuario_actual = session.get('user')
    if not usuario_actual:
        flash('No estás autenticado.', 'danger')
        return redirect(url_for('auth.login'))

    proyectos_usuario = Proyecto.query.filter_by(Usuario=usuario_actual).all()

    if request.method == 'POST':
        if 'file' not in request.files or 'project' not in request.form:
            flash('Debe seleccionar un archivo y especificar el proyecto.', 'danger')
            return redirect(request.url)

        file = request.files['file']
        project_id = request.form['project']
        project = Proyecto.query.get(project_id)

        if not project:
            flash('El proyecto no existe o no pertenece al usuario actual.', 'danger')
            return redirect(request.url)

        if file.filename == '':
            flash('No se seleccionó ningún archivo.', 'danger')
            return redirect(request.url)

        if not allowed_file(file.filename):
            flash('Solo se permiten archivos .zip.', 'danger')
            return redirect(request.url)

        filename = secure_filename(file.filename)
        upload_path = os.path.join(RUTA_BASE, project.Nombre, filename)
        
        # Guardar archivo
        try:
            file.save(upload_path)
        except Exception as e:
            flash(f'Ocurrió un error al guardar el archivo: {str(e)}', 'danger')
            return redirect(request.url)

        dataset_folder_name = os.path.splitext(os.path.basename(upload_path))[0]
        dataset_extract_path = os.path.join(RUTA_BASE, dataset_folder_name)

        # Extraer el archivo ZIP
        try:
            with zipfile.ZipFile(upload_path, 'r') as zip_ref:
                zip_ref.extractall(dataset_extract_path)
        except zipfile.BadZipFile:
            flash('El archivo subido no es un archivo ZIP válido.', 'danger')
            return redirect(request.url)
        except Exception as e:
            flash(f'Ocurrió un error al procesar el archivo: {str(e)}', 'danger')
            return redirect(request.url)

        # Validar el dataset
        es_yolo, mensaje_yolo = validar_yolo(dataset_extract_path)
        es_coco, mensaje_coco = validar_coco(dataset_extract_path)

        if es_yolo:
            formato = 'YOLO'
            mensaje = mensaje_yolo
        elif es_coco:
            formato = 'COCO'
            mensaje = mensaje_coco
        else:
            flash('El dataset no cumple con los formatos YOLO o COCO.', 'danger')
            return redirect(request.url)

        # Registrar dataset en la base de datos
        nuevo_dataset = DataSet(
            nombre=dataset_folder_name,
            descripcion=f"Dataset en formato {formato}",
            proyecto=project.idProyecto,
            fecha=datetime.now(),
            estado=True,
            tipo=formato
        )
        
        try:
            db.session.add(nuevo_dataset)
            db.session.commit()
            flash('Dataset registrado exitosamente.', 'success')
        except Exception as e:
            flash(f'Ocurrió un error al registrar el dataset: {str(e)}', 'danger')
            return redirect(request.url)

        return redirect(url_for('dataset.inicio'))

    return render_template('dataset/subir.html', proyectos=proyectos_usuario)


def validar_yolo(folder):
    subsets = ['train', 'test', 'valid']
    data_yaml_path = os.path.join(folder, 'data.yaml')
    # Verificar si el archivo data.yaml existe
    if not os.path.exists(data_yaml_path):
        return False, "El archivo 'data.yaml' es obligatorio en el nivel superior del dataset."
    for subset in subsets:
        print("S", subset)
        subset_path = os.path.join(folder, subset)
        if not os.path.exists(subset_path):
            continue
        
        images_path = os.path.join(subset_path, 'images')
        labels_path = os.path.join(subset_path, 'labels')
        if not os.path.exists(images_path) or not os.path.exists(labels_path):
            return False, f"La estructura YOLO requiere las carpetas 'images/' y 'labels/' dentro de {subset}/."
        images = set(os.listdir(images_path))
        labels = set(os.listdir(labels_path))
        if not images or not labels:
            return False, f"Las carpetas 'images/' y 'labels/' están vacías en {subset}/."
  
    return True, "Estructura YOLO válida."

def validar_coco(folder):
    subsets = ['train', 'test', 'valid']
    for subset in subsets:
        subset_path = os.path.join(folder, subset)
        annotations_path = os.path.join(subset_path, 'annotations.json')
        if not os.path.exists(subset_path):
            continue

        if not os.path.exists(annotations_path):
            return False, f"El formato COCO requiere el archivo 'annotations.json' dentro de {subset}/."

        try:
            with open(annotations_path, 'r') as f:
                data = json.load(f)
            if 'images' not in data or 'annotations' not in data:
                return False, f"El archivo 'annotations.json' en {subset}/ no contiene las claves necesarias."
        except json.JSONDecodeError:
            return False, f"El archivo 'annotations.json' en {subset}/ no es un JSON válido."

    return True, "Estructura COCO válida."

@bp.route('/descargar/<int:id>', methods=['GET'])
def descargar(id):
    # Obtener el dataset por ID
    dataset = DataSet.query.get_or_404(id)
    proyecto = Proyecto.query.get_or_404(dataset.idProyecto)
    # Construir la ruta completa al dataset dentro de la carpeta del proyecto
    carpeta_dataset = os.path.join(RUTA_BASE, proyecto.Nombre, "DATASET", dataset.Nombre)

    # Imprimir la ruta para depuración
    print(f"Carpeta del dataset: {carpeta_dataset}")

    # Verificar que la carpeta existe
    if not os.path.exists(carpeta_dataset):
        flash("El dataset solicitado no fue encontrado.", "danger")
        return redirect(url_for('dataset.inicio'))  # Redirigir a la página principal de datasets

    # Crear un archivo zip temporal en la misma ruta base
    zip_path = os.path.join(RUTA_BASE, "temp", f"{dataset.Nombre}.zip")
    os.makedirs(os.path.dirname(zip_path), exist_ok=True)  # Crear directorio si no existe

    try:
        # Comprimir el dataset
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, _, files in os.walk(carpeta_dataset):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, carpeta_dataset)  # Ruta relativa dentro del zip
                    zipf.write(file_path, arcname)
    except Exception as e:
        flash(f"Error al comprimir el dataset: {e}", "danger")
        return redirect(url_for('dataset.inicio'))

    # Enviar el archivo zip para descarga
    return send_file(zip_path, as_attachment=True, download_name=f"{dataset.Nombre}.zip")
