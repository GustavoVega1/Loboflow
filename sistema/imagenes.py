from flask import (
    Blueprint, render_template, request, url_for, redirect, flash, send_from_directory,
    session
)

from .auth import login_required
from sistema import db, RUTA_BASE
from .models import Proyecto
import os
import zipfile
from PIL import Image


# Creación de un Blueprint para la autenticación con prefijo de URL '/imagenes'
bp = Blueprint('imagenes', __name__, url_prefix='/imagenes')

@bp.route('/inicio')
@login_required
def inicio():
    return render_template('imagenes/inicio.html')

@bp.route('/subir-imagenes', methods=('GET', 'POST'))
@login_required
def subir():
    if request.method == 'POST':
        archivo = request.files['archivo']
        proyecto_id = request.form.get('proyecto')

        # Obtener el proyecto actual
        proyecto = Proyecto.query.get(proyecto_id)
        if not proyecto:
            return "Proyecto no encontrado", 404

    

        if archivo and allowed_file(archivo.filename):
            archivo_path = os.path.join(RUTA_BASE, archivo.filename)
            archivo.save(archivo_path)
            print("GUARDANDO ARCHIVO")

            proyecto_folder = os.path.join(RUTA_BASE, proyecto.Nombre)
            os.makedirs(proyecto_folder, exist_ok=True)

            if archivo.filename.endswith('.zip'):
                try:
                    with zipfile.ZipFile(archivo_path, 'r') as zip_ref:
                        zip_ref.extractall(proyecto_folder)

                    # Eliminar el archivo .zip después de la extracción
                    os.remove(archivo_path)
                    # Redimensionar las imágenes extraídas
                    imagenes_extraidas = [
                        archivo for archivo in os.listdir(proyecto_folder)
                        if archivo.endswith(('.png', '.jpg', '.jpeg', '.gif'))
                    ]
                    redimensionar_imagenes(imagenes_extraidas, proyecto.Nombre)

                except zipfile.BadZipFile:
                    return "El archivo no es un ZIP válido", 400

            flash('Imágenes cargadas y redimensionadas satisfactoriamente', 'success')
            return redirect(url_for('imagenes.subir'))

    usuario = session.get('user')
    proyectos = Proyecto.query.filter_by(Estatus=True, Usuario=usuario).all()
    return render_template('imagenes/subir.html', proyectos=proyectos)


def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'zip'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@bp.route('/seleccionar', methods=['GET'])
@login_required
def seleccionar():
    usuario = session.get('user')

    proyectos = Proyecto.query.filter_by(Estatus=True, Usuario=usuario).all()

    if not proyectos:
        flash('No se encontraron proyectos activos para este usuario.', 'warning')

    return render_template('imagenes/seleccionar.html', proyectos=proyectos)


@bp.route('/visualizar', methods=['GET'])
@login_required
def visualizar():
    proyecto_id = request.args.get('proyecto_id')

    if not proyecto_id:
        flash('ID del proyecto no proporcionado', 'danger')
        return redirect(url_for('imagenes.seleccionar'))

    # Convertir a int
    proyecto_id = int(proyecto_id)

    # Obtener el proyecto desde la base de datos
    proyecto = Proyecto.query.get(proyecto_id)
    if not proyecto:
        flash('Proyecto no encontrado', 'danger')
        return redirect(url_for('imagenes.seleccionar'))

    proyecto_folder = os.path.join(RUTA_BASE, proyecto.Nombre)
    imagenes = [archivo for archivo in os.listdir(proyecto_folder) if archivo.endswith(('.png', '.jpg', '.jpeg', '.gif'))] if os.path.exists(proyecto_folder) else []

    # Paginación
    page = request.args.get('page', 1, type=int)
    per_page = 10
    total = len(imagenes)
    start = (page - 1) * per_page
    end = start + per_page
    imagenes_paginas = imagenes[start:end]

    return render_template('imagenes/visualizar.html', imagenes=imagenes_paginas, proyecto=proyecto, total=total, page=page, per_page=per_page)


@bp.route('/opciones/<int:proyecto_id>', methods=['POST', 'GET'])
@login_required
def opciones(proyecto_id):
    # Obtener el proyecto correspondiente
    proyecto = Proyecto.query.get(proyecto_id)
    if not proyecto:
        flash('Proyecto no encontrado', 'danger')
        return redirect(url_for('imagenes.visualizar', proyecto_id=proyecto_id))

    # Obtener la acción seleccionada
    accion = request.form.get('accion')
    imagenes_seleccionadas = request.form.getlist('imagenes_seleccionadas')  # Cambiar a getlist para obtener una lista

    # Verificar que las imágenes seleccionadas no sean None o una cadena vacía
    if not imagenes_seleccionadas:
        flash('No se seleccionaron imágenes', 'warning')
        return redirect(url_for('imagenes.visualizar', proyecto_id=proyecto_id))

    # Depurar imágenes seleccionadas
    print("Imágenes seleccionadas:", imagenes_seleccionadas)

    # Procesar la acción seleccionada
    if accion == 'eliminar':
        for imagen_nombre in imagenes_seleccionadas:
            ruta_imagen = os.path.join(RUTA_BASE, proyecto.Nombre, imagen_nombre)
            if os.path.exists(ruta_imagen):
                os.remove(ruta_imagen)
            else:
                flash(f'La imagen {imagen_nombre} no fue encontrada en el servidor', 'warning')

        flash('Imágenes eliminadas correctamente', 'success')

    elif accion == 'generar_dataset':
        if imagenes_seleccionadas:
            session['imagenes_a_eliminar'] = imagenes_seleccionadas
            session['proyecto'] = proyecto.Nombre
            
            return redirect(url_for('dataset.registrar_clases')) 
        else:
            flash('No hay imágenes seleccionadas para generar el dataset im', 'warning')

    return redirect(url_for('imagenes.visualizar', proyecto_id=proyecto_id))



@bp.route('/servir_imagenes/<path:filename>')
def servir_imagenes(filename):
    return send_from_directory(RUTA_BASE, filename)

def redimensionar_imagenes(imagenes, proyecto_nombre, ancho=640, alto=640):    
    for imagen_nombre in imagenes:
        ruta_imagen = os.path.join(RUTA_BASE, proyecto_nombre, imagen_nombre)

        if os.path.exists(ruta_imagen):
            try:
                with Image.open(ruta_imagen) as img:
                    img = img.resize((ancho, alto))
                    img.save(ruta_imagen)
            except Exception as e:
                print(f"Error redimensionando {imagen_nombre}: {e}")