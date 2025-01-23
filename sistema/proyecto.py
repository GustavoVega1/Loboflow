from flask import (
    Blueprint, render_template,
    request, url_for, redirect, flash,render_template_string,
    session, g)
from .auth import login_required
from sistema import db, RUTA_BASE
from .models import Proyecto
import os

# Creación de un Blueprint para la autenticación con prefijo de URL '/proyecto'
bp = Blueprint('proyecto', __name__, url_prefix='/proyecto')


@bp.route('/inicio')
@login_required
def inicio():
    proyectos = Proyecto.query.filter_by(Usuario=session.get('user')).order_by(Proyecto.Estatus.desc()).all()
    return render_template('proyecto/inicio.html', proyectos=proyectos)


@bp.route('/registrar', methods=('GET', 'POST'))
@login_required
def registrar():
    if request.method == 'POST':
        nombre = request.form["nombre"]
        desc = request.form["descripcion"]
        objetivo = request.form.get("objetivo", "")  # Añadido para capturar el objetivo
        tipo_proyecto = request.form["tipo_proyecto"]
        usuario = session.get('user')
        estatus = True

        # Verificar si el proyecto ya existe
        veri = Proyecto.query.filter_by(Nombre=nombre).first()
        if veri is None:
            # Registrar el proyecto en la base de datos
            proyecto = Proyecto(nombre=nombre, descripcion=desc, objetivo=objetivo, tipo_proyecto=tipo_proyecto, estatus=estatus, usuario=usuario)
            db.session.add(proyecto)
            db.session.commit()
            
            # Crear una carpeta con el nombre del proyecto
            project_path = os.path.join(RUTA_BASE, nombre)  # Usa RUTA_BASE como la ruta base donde se creará la carpeta
            os.makedirs(project_path, exist_ok=True)  # Crea la carpeta si no existe

            flash('Proyecto registrado satisfactoriamente y carpeta creada', 'success')
            return redirect(url_for('proyecto.inicio'))
        else:
            flash('Ya existe un proyecto con ese nombre', 'danger')
    
    return render_template('proyecto/registrar.html')

@bp.route('/proyecto/modificar/<int:id>', methods=('GET', 'POST'))
@login_required
def modificar_proyecto(id):
    proyecto = Proyecto.query.filter_by(idProyecto=id).first()
    if not proyecto:
        flash("Proyecto no encontrado", 'danger')
        return redirect(url_for('proyecto.inicio'))

    if request.method == 'POST':
        nuevo_nombre = request.form['nombre']
        nueva_desc = request.form['descripcion']
        tipo_proyecto = request.form['tipo_proyecto']
        objetivo = request.form['objetivo']
        
        # Verificar si el nuevo nombre ya está en uso
        existing_project = Proyecto.query.filter_by(Nombre=nuevo_nombre).first()
        if existing_project and existing_project.idProyecto != proyecto.idProyecto:
            flash('Ya existe un proyecto con ese nombre', 'danger')
            return redirect(url_for('proyecto.modificar_proyecto', id=proyecto.idProyecto))
        
        # Actualizar los datos del proyecto en la base de datos
        proyecto.Nombre = nuevo_nombre
        proyecto.Descripcion = nueva_desc
        proyecto.TipoProyecto = tipo_proyecto
        proyecto.Objetivo = objetivo
        db.session.commit()
        
        # Renombrar la carpeta correspondiente al proyecto
        old_project_path = os.path.join(RUTA_BASE, proyecto.Nombre)  # Carpeta con el nombre antiguo
        new_project_path = os.path.join(RUTA_BASE, nuevo_nombre)  # Nueva carpeta con el nombre actualizado
        if old_project_path != new_project_path:
            try:
                os.rename(old_project_path, new_project_path)  # Renombrar la carpeta
            except OSError as e:
                flash(f'Error al renombrar la carpeta: {e}', 'danger')
                return redirect(url_for('proyecto.inicio'))
        
        flash("¡Datos actualizados y carpeta renombrada!", 'success')
        return redirect(url_for('proyecto.inicio'))
    
    return render_template('proyecto/modificar.html', Proyecto=proyecto)

@bp.route('/proyecto/eliminar', methods=['POST'])
def eliminar():
    proyecto_id = request.form.get('id')  # Obtén el ID del proyecto desde el formulario
    if proyecto_id and proyecto_id.isdigit():
        proyecto = Proyecto.query.get(int(proyecto_id))
        if proyecto:
            proyecto.Estatus = False  # Cambia el estatus del proyecto a 0 (eliminado o inactivo)
            db.session.commit()
            flash('Proyecto eliminado correctamente.', 'success')
        else:
            flash('Proyecto no encontrado.', 'danger')
    else:
        flash('ID de Proyecto no válido.', 'danger')

    return redirect(url_for('proyecto.inicio'))

@bp.route('/proyecto/habilitar', methods=['POST'])
def habilitar():
    proyecto_id = request.form.get('id')  # Obtén el ID del proyecto desde el formulario
    if proyecto_id and proyecto_id.isdigit():
        proyecto = Proyecto.query.get(int(proyecto_id))
        if proyecto:
            proyecto.Estatus = True  # Cambia el estatus del proyecto a 0 (eliminado o inactivo)
            db.session.commit()
            flash('Proyecto recuperado correctamente.', 'success')
        else:
            flash('Proyecto no encontrado.', 'danger')
    else:
        flash('ID de Proyecto no válido.', 'danger')

    return redirect(url_for('proyecto.inicio'))