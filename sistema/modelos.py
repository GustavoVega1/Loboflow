from flask import (
    Blueprint, render_template, request, url_for, redirect, flash, send_from_directory, session
)
from .auth import login_required
from sistema import db, RUTA_BASE
from .models import Modelos, Proyecto
import os
from flask import current_app
from werkzeug.utils import secure_filename


# Creación de un Blueprint para la autenticación con prefijo de URL '/modelos'
bp = Blueprint('modelos', __name__, url_prefix='/modelos')


@bp.route('/inicio')
@login_required
def inicio():
    # Obtener los modelos de los proyectos que pertenecen al usuario que ha iniciado sesión
    modelos = Modelos.query.join(Proyecto).filter(Proyecto.Usuario == session.get('user')).all()
    return render_template('modelos/inicio.html', modelos=modelos)

@bp.route('/registrar', methods=['POST', 'GET'])
@login_required
def registrar():
    usuario = session.get('user')

    # Obtener proyectos habilitados para el usuario
    proyectos = Proyecto.query.filter_by(Estatus=True, Usuario=usuario).all()

    if request.method == 'POST':
        # Recoger los datos del formulario
        nombre = request.form.get('nombre')
        descripcion = request.form.get('descripcion')
        arquitectura = request.form.get('arquitectura')
        proyecto_id = request.form.get('proyecto_id')
        archivo = request.files.get('archivo')
        estatus = True

        # Validar que el archivo tenga la extensión .pt
        if archivo:
            extension = os.path.splitext(archivo.filename)[1].lower()  # Obtener la extensión del archivo en minúsculas
            if extension != '.pt':
                flash('Solo se permiten archivos con extensión .pt', 'danger')
                return redirect(request.url)  # Redirigir al mismo formulario para que el usuario intente nuevamente

        # Obtener el proyecto seleccionado
        proyecto = Proyecto.query.get(proyecto_id)
        if not proyecto:
            flash('El proyecto seleccionado no es válido.', 'danger')
            return redirect(url_for('modelos.seleccionar'))

        # Crear la carpeta del proyecto si no existe
        ruta_proyecto = os.path.join(RUTA_BASE, secure_filename(proyecto.Nombre))
        ruta_modelos = os.path.join(ruta_proyecto, 'MODELOS')

        os.makedirs(ruta_modelos, exist_ok=True)

        # Cambiar el nombre del archivo subido
        nuevo_nombre = f"{secure_filename(nombre)}{extension}"  # Asignar el nombre recibido con la extensión original
        ruta_archivo = os.path.join(ruta_modelos, nuevo_nombre)

        # Guardar el archivo con el nuevo nombre
        archivo.save(ruta_archivo)

        # Crear un nuevo modelo y guardar en la base de datos
        nuevo_modelo = Modelos(
            nombre=nombre,
            descripcion=descripcion,
            proyecto=proyecto_id,
            estado=estatus,
            arquitectura=arquitectura,
            ruta=ruta_archivo,  # Guardar la ruta completa donde se almacenó el archivo
        )

        try:
            db.session.add(nuevo_modelo)
            db.session.commit()
            flash('Modelo registrado correctamente.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Ocurrió un error al registrar el modelo: {str(e)}', 'danger')

        return redirect(url_for('modelos.inicio'))

    return render_template('modelos/registrar.html', proyectos=proyectos)

@bp.route('/eliminar', methods=['POST'])
def eliminar():
    proyecto_id = request.form.get('id')  # Obtén el ID del proyecto desde el formulario
    if proyecto_id and proyecto_id.isdigit():
        modelo = Modelos.query.get(int(proyecto_id))
        if modelo:
            modelo.Estado = False  # Cambia el estatus del proyecto a 0 (eliminado o inactivo)
            db.session.commit()
            flash('Modelo eliminado correctamente.', 'success')
        else:
            flash('Modelo no encontrado.', 'danger')
    else:
        flash('ID de Modelo no válido.', 'danger')

    return redirect(url_for('modelos.inicio'))


@bp.route('/habilitar', methods=['POST'])
def habilitar():
    proyecto_id = request.form.get('id')  # Obtén el ID del proyecto desde el formulario
    if proyecto_id and proyecto_id.isdigit():
        modelo = Modelos.query.get(int(proyecto_id))
        if modelo:
            modelo.Estado = True  # Cambia el estatus del proyecto a 0 (eliminado o inactivo)
            db.session.commit()
            flash('Modelo recuperado correctamente.', 'success')
        else:
            flash('Modelo no encontrado.', 'danger')
    else:
        flash('ID de Modelo no válido.', 'danger')

    return redirect(url_for('modelos.inicio'))


@bp.route('/modificar_modelo/<int:id>', methods=['GET', 'POST'])
def modificar_modelo(id):
    modelo = Modelos.query.get_or_404(id)
    proyectos = Proyecto.query.all()

    if request.method == 'POST':
        # Obtener los valores del formulario
        nombre = request.form['nombre']
        descripcion = request.form['descripcion']
        arquitectura = request.form['arquitectura']
        proyecto_id = request.form['proyecto_id']

        # Actualizar el modelo
        modelo.Nombre = nombre
        modelo.Descripcion = descripcion
        modelo.Arquitectura = arquitectura
        modelo.Proyecto_id = proyecto_id

        # Verificar si se subió un nuevo archivo
        archivo = request.files['archivo']
        if archivo and archivo.filename != '':
            # Guardar el nuevo archivo (esto debería incluir alguna lógica de validación)
            ruta_archivo = os.path.join(RUTA_BASE, archivo.filename)
            archivo.save(ruta_archivo)
            modelo.Ruta = ruta_archivo

        # Guardar los cambios en la base de datos
        try:
            db.session.commit()
            flash('Modelo modificado exitosamente', 'success')
            return redirect(url_for('modelos.inicio'))
        except:
            db.session.rollback()
            flash('Hubo un error al modificar el modelo', 'danger')

    return render_template('modelos/modificar.html', modelo=modelo, proyectos=proyectos)