# Importación de módulos y paquetes necesarios
import functools
from flask import (
    Blueprint, render_template,
    request, url_for, redirect, flash,render_template_string,
    session, g)

from werkzeug.security import generate_password_hash, check_password_hash
from .models import Usuario, Proyecto, Modelos, DataSet, Modelos_generados, Reporte
from sistema import db, mail, s
import string
import random
from flask_mail import Message


# Creación de un Blueprint para la autenticación con prefijo de URL '/auth'
bp = Blueprint('auth', __name__, url_prefix='/auth')

# Ruta para el inicio de sesión ('/login') con métodos GET y POST
@bp.route('/login', methods=('GET', 'POST'))
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        error = None
        user = Usuario.query.filter_by(nombre=username).first()
        if user is None or not check_password_hash(user.Contra, password):
            error = 'Usuario y/o contraseña incorrecta'
        elif not user.confirmed:
            error = 'Tu cuenta no ha sido confirmada. Revisa tu correo para confirmarla.'

        if error is None:
            session.clear()
            session['user'] = user.idUsuario
            if user.Rol == "Administrador":
                return redirect(url_for('auth.admin'))
            elif user.Rol == "Experto":
                return redirect(url_for('auth.experto'))
            elif user.Rol == "Tester":
                return redirect(url_for('auth.tester'))
        flash(error, 'danger')
    return render_template('auth/login.html')

@bp.route('/registrar', methods=('GET', 'POST'))
def registrar():
    if request.method == "POST":
        nombre = request.form["username"]
        correo = request.form["email"]
        rol = request.form["role"]
        ocupacion = request.form["ocupacion"]
        intereses = request.form["intereses"]
        
        # Verificar si el nombre de usuario ya existe
        usuario = Usuario.query.filter_by(nombre=nombre).first()
        if usuario is None:
            # Verificar si el correo ya está en uso
            usuario = Usuario.query.filter_by(Correo=correo).first()
            if usuario is None:
                # Generar una nueva contraseña y hashearla
                nueva_contrasena = generar_contrasena_aleatoria()
                nueva_contrasena_hash = generate_password_hash(nueva_contrasena)

                # Crear nuevo usuario con los datos proporcionados
                usuario = Usuario(nombre, nueva_contrasena_hash, rol, correo)
                usuario.ocupacion = ocupacion  # Asignar ocupación
                usuario.intereses = intereses  # Asignar intereses

                db.session.add(usuario)
                db.session.commit()

                # Enviar correo con el token de verificación
                token = s.dumps(correo, salt='confirm-email')
                enlace_confirmacion = url_for('auth.confirmar_email', token=token, _external=True)
                asunto = 'Confirmación de Registro'
                cuerpo_template = '''
                    <html>
                        <head>
                            <style>
                                body { font-family: Arial, sans-serif; text-align: center; background-color: #f4f4f4; }
                                #container { max-width: 600px; margin: 0 auto; padding: 20px; background-color: #fff; border-radius: 10px; box-shadow: 0 0 10px rgba(0, 0, 0, 0.1); }
                                h1 { color: #007BFF; }
                                p { font-size: 18px; }
                            </style>
                        </head>
                        <body>
                            <div id="container">
                                <h1>LOBOFLOW</h1>
                                <p>Hola {{ nombre }},</p>
                                <p>Hemos registrado tu cuenta exitosamente. Por favor, confirma tu dirección de correo electrónico haciendo clic en el siguiente enlace:</p>
                                <p><a href="{{ enlace_confirmacion }}">Confirmar mi correo electrónico</a></p>
                                <p>Ten en cuenta que el enlace expirará en 5 minutos.</p>
                                <p>Gracias por registrarte.</p>
                            </div>
                        </body>
                    </html>
                '''
                cuerpo_renderizado = render_template_string(cuerpo_template, nombre=nombre, enlace_confirmacion=enlace_confirmacion)
                if enviar_correo(correo, asunto, cuerpo_renderizado):
                    flash("Usuario registrado exitosamente. Por favor, revisa tu correo para confirmar tu cuenta.", 'success')
                    return redirect(url_for('auth.inicio'))
                else:
                    flash("Error al enviar el correo de confirmación.", 'danger')
            else:
                flash("El correo electrónico ya está en uso", 'danger')
        else:
            flash("El nombre de usuario ya está en uso", 'danger')
    return render_template('auth/register.html')


@bp.route('/confirmar/<token>')
def confirmar_email(token):
    try:
        correo = s.loads(token, salt='confirm-email', max_age=300)  # El token expira en 5 minutos (300 segundos)
    except Exception as e:
        flash('El enlace de confirmación ha expirado o no es válido.', 'danger')
        return redirect(url_for('auth.login'))

    usuario = Usuario.query.filter_by(Correo=correo).first_or_404()
    if usuario.confirmed:
        flash('Tu cuenta ya ha sido confirmada.', 'info')
    else:
        usuario.confirmed = True
        db.session.commit()
        flash('Tu cuenta ha sido confirmada exitosamente. Por favor, cambia tu contraseña.', 'success')
    
    # Redirigir al formulario para cambiar la contraseña
    return redirect(url_for('auth.cambiar_contrasena', correo=correo))


# Función auxiliar para obtener un objeto Usuario por su nombre
def get_user(nombre):
    """
    Descripción: Obtiene un objeto Usuario por su nombre.
    Entradas: Nombre de usuario.
    Salidas: Objeto Usuario o error 404 si no se encuentra.
    """
    usuario = Usuario.query.get_or_404(nombre)
    return usuario

@bp.route('/send_email')
def send_email():
    try:
        # Crear el mensaje de correo
        msg = Message(
            "Asunto del correo",  # Asunto
            recipients=["gvegaestrada@gmail.com", "vego210232@upemor.edu.mx"],  # Destinatarios
            body="Este es el contenido del correo",  # Cuerpo del mensaje
        )
        
        # Enviar el correo
        mail.send(msg)
        flash("Correo enviado correctamente", "success")
    except Exception as e:
        flash(f"Error al enviar el correo: {str(e)}", "error")
    return render_template("index.html")


@bp.route('/recuperar_contrasena', methods=('GET', 'POST'))
def recuperar_contrasena():
    """
    Maneja el proceso de recuperación de contraseña.
    """
    if request.method == 'POST':
        correo = request.form['email']
        user = Usuario.query.filter_by(Correo=correo).first()
        if user is None:
            flash('Usuario no encontrado', 'danger')
        else:
            # Generar un token de recuperación
            token = s.dumps({'user_id': user.idUsuario})
            
            # Enviar el correo con el enlace de recuperación
            destinatario = correo
            asunto = 'Recuperación de Contraseña'
            
            # Enlace de recuperación con el token
            url_recuperacion = url_for('auth.reset_password', token=token, _external=True)
            
            # Utiliza triple comillas sin saltos de línea
            cuerpo_template = '''
                        <html>
                            <head>
                                <style>
                                    body {
                                        font-family: Arial, sans-serif;
                                        background-color: #f9f9f9;
                                        margin: 0;
                                        padding: 0;
                                    }

                                    .email-container {
                                        max-width: 600px;
                                        margin: 30px auto;
                                        background-color: #ffffff;
                                        border-radius: 8px;
                                        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                                        overflow: hidden;
                                        border: 1px solid #ddd;
                                    }

                                    .header {
                                        background-color: #007BFF;
                                        color: white;
                                        text-align: center;
                                        padding: 20px 10px;
                                    }

                                    .header h1 {
                                        font-size: 2rem;
                                        margin: 0;
                                    }

                                    .content {
                                        padding: 20px;
                                        text-align: left;
                                        color: #333;
                                    }

                                    .content h2 {
                                        font-size: 1.5rem;
                                        margin-bottom: 10px;
                                    }

                                    .content p {
                                        font-size: 1rem;
                                        line-height: 1.6;
                                        margin-bottom: 15px;
                                    }

                                    .button-container {
                                        text-align: center;
                                        margin-top: 20px;
                                    }

                                    .button {
                                        display: inline-block;
                                        padding: 12px 24px;
                                        font-size: 1rem;
                                        color: white;
                                        background-color: #007BFF;
                                        text-decoration: none;
                                        border-radius: 5px;
                                        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
                                    }

                                    .button:hover {
                                        background-color: #0056b3;
                                    }

                                    .footer {
                                        background-color: #f1f1f1;
                                        color: #777;
                                        text-align: center;
                                        padding: 15px 10px;
                                        font-size: 0.9rem;
                                    }

                                    .footer p {
                                        margin: 0;
                                    }
                                </style>
                            </head>
                            <body>
                                <div class="email-container">
                                    <div class="header">
                                        <h1>LOBOFLOW</h1>
                                    </div>
                                    <div class="content">
                                        <h2>Hola {{ username }},</h2>
                                        <p>
                                            Hemos recibido tu solicitud para restablecer tu contraseña en el sistema <strong>LOBOFLOW</strong>.
                                            Para continuar, haz clic en el botón de abajo para establecer una nueva contraseña.
                                        </p>
                                        <div class="button-container">
                                            <a href="{{ url_recuperacion }}" class="button">Restablecer Contraseña</a>
                                        </div>
                                        <p>
                                            Si no solicitaste restablecer tu contraseña, ignora este correo. Este enlace expira en una hora.
                                        </p>
                                        <p>
                                            Gracias por usar <strong>LOBOFLOW</strong>.
                                        </p>
                                    </div>
                                    <div class="footer">
                                        <p>© 2024 LOBOFLOW. Todos los derechos reservados.</p>
                                    </div>
                                </div>
                            </body>
                            </html>

                        '''
            cuerpo_renderizado = render_template_string(cuerpo_template, username=correo, url_recuperacion=url_recuperacion)
            if enviar_correo(destinatario, asunto, cuerpo_renderizado):
                flash('Se ha enviado un enlace para restablecer la contraseña a tu correo', 'success')
                return redirect(url_for('auth.login'))

            flash('Error al enviar el correo', 'danger')

    return render_template('auth/recuperar.html')


@bp.route('/reset_password/<token>', methods=('GET', 'POST'))
def reset_password(token):
    """
    Permite al usuario restablecer su contraseña usando un token.
    """
    try:
        data = s.loads(token, max_age=3600)  # Token expira en 1 hora
    except Exception as e:
        flash('El enlace ha expirado o no es válido.', 'danger')
        return redirect(url_for('auth.recuperar_contrasena'))
    user_id = data.get('user_id')
    user = Usuario.query.get_or_404(user_id)
    if request.method == 'POST':
        nueva_contrasena = request.form['new_password']
        confirmar_contrasena = request.form['confirm_password']
        if nueva_contrasena != confirmar_contrasena:
            flash('Las contraseñas no coinciden.', 'danger')
        else:
            nueva_contrasena_hash = generate_password_hash(nueva_contrasena)
            user.Contra = nueva_contrasena_hash
            db.session.commit()
            flash('Tu contraseña ha sido actualizada exitosamente.', 'success')
            return redirect(url_for('auth.login'))
    return render_template('auth/reset_password.html', token=token)



@bp.route('/cambiar_contrasena/<correo>', methods=('GET', 'POST'))
def cambiar_contrasena(correo):
    usuario = Usuario.query.filter_by(Correo=correo).first_or_404()

    if request.method == 'POST':
        nueva_contrasena = request.form['new_password']
        confirmar_contrasena = request.form['confirm_password']
        
        if nueva_contrasena != confirmar_contrasena:
            flash('Las contraseñas no coinciden.', 'danger')
        else:
            nueva_contrasena_hash = generate_password_hash(nueva_contrasena)
            usuario.password = nueva_contrasena_hash
            db.session.commit()
            
            flash('Tu contraseña ha sido actualizada exitosamente.', 'success')
            if usuario.Rol == "Administrador":
                return redirect(url_for('auth.login'))
            else:
                print("OTRO USUARIO")

    return render_template('auth/cambiar_contrasena.html', correo=correo)


# Función que se ejecuta antes de cada solicitud para cargar información del usuario en 'g'
@bp.before_app_request
def carga_pagina():
    """
    Descripción: Carga la información del usuario en 'g' antes de cada solicitud.
    """
    user = session.get('user')

    if user is None:
        g.user = None
    else:
        # Realizamos una consulta para obtener los datos del usuario
        g.user = Usuario.query.get_or_404(user)



# <- Le estamos diciendo para que la función se ejecute al momento de ingresar a cualquier vista del sitio
@bp.before_app_request
def loag_logged_in_user():
    # Si alguien inicio sesión nos devolverá el id del usuario
    # Si nadie ha iniciado sesión nos devolvera nulo
    user = session.get('user')
    # Evaluamos si alguien ha iniciado sesión
    if user is None:
        g.user = None
    else:
        # Realizamos una consulta a la base de datos
        g.user = Usuario.query.get_or_404(user)


# Función para cerrar sesión
@bp.route('/logout')
def logout():
    """
    Descripción: Cierra la sesión del usuario.
    Salidas: Redirección al inicio del sitio.
    """
    # Limpiamos la sesión
    session.clear()
    # Redireccionamos al inicio de todo
    return redirect(url_for('index'))

# Decorador para requerir inicio de sesión en ciertas vistas
def login_required(view):
    """
    Descripción: Decorador que requiere que el usuario haya iniciado sesión.
    Entradas: Vista a decorar.
    Salidas: Vista decorada o redirección al inicio de sesión si el usuario no ha iniciado sesión.
    """
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        # Si nadie a iniciado sesión, se regresa al login
        if g.user is None:
            return redirect(url_for('auth.login'))
        # Si alguien a iniciado sesión se regresa a la vista donde estaba
        return view(**kwargs)
    return wrapped_view

# Ruta para la página de inicio del módulo de autenticación ('/principal-inicio')
@bp.route('/principal-inicio')
@login_required
def inicio():
    """
    Descripción: Página de inicio del módulo de autenticación (requiere inicio de sesión).
    """
    usuarios = Usuario.query.all()
    return render_template('auth/inicio.html', usuarios=usuarios)

# Función para generar una contraseña aleatoria
def generar_contrasena_aleatoria():
    """
    Descripción: Genera una contraseña aleatoria de longitud 12.
    Salidas: Contraseña aleatoria.
    """
    longitud = 12
    caracteres = string.ascii_letters + string.digits + string.punctuation
    contrasena_aleatoria = ''.join(random.choice(caracteres)
                                   for i in range(longitud))
    return contrasena_aleatoria

@bp.route('/auth/eliminar_usuario', methods=['POST'])
def eliminar_usuario():
    user_id = request.form.get('user_id')
    if user_id and user_id.isdigit():
        user_id = int(user_id)
        user = Usuario.query.get(user_id)
        if user:
            db.session.delete(user)
            db.session.commit()
            flash('Usuario eliminado correctamente.', 'success')
        else:
            flash('Usuario no encontrado.', 'danger')
    else:
        flash('ID de usuario no válido.', 'danger')
    return redirect(url_for('auth.inicio'))

def get_user(id):
    user = Usuario.query.get_or_404(id)
    return user

# Ruta para modificar la información de un usuario ('/modificar-user/<int:id>') con métodos GET y POST
@bp.route('/modificar_usuario/<int:id>', methods=('GET', 'POST'))
def modificar_usuario(id):
    """
    Descripción: Modifica la información de un usuario.
    """
    Usuario = get_user(id)  # Obtiene al usuario con el ID proporcionado
    if request.method == 'POST':
        # Actualiza los campos del usuario con los datos recibidos
        Usuario.Rol = request.form['role']
        Usuario.nombre = request.form['username']
        Usuario.ocupacion = request.form['ocupacion']
        Usuario.intereses = request.form['interes']
        
        # Guarda los cambios en la base de datos
        db.session.commit()
        flash("¡Datos actualizados!", 'success')
        return redirect(url_for('auth.inicio'))
    
    return render_template('auth/modificar.html', Usuario=Usuario)


def enviar_correo(destinatario, asunto, cuerpo):
    mensaje = Message(asunto, recipients=[destinatario])
    mensaje.html = cuerpo
    try:
        mail.send(mensaje)
        return True
    except Exception as e:
        print(f'Error al enviar el correo: {str(e)}')
        return False
    
@login_required
@bp.route('/admin')
def admin():
    # Obtener el usuario actual
    usuario_actual = session.get('user')
    
    # Contar los usuarios
    total_usuarios = Usuario.query.count()
    
    # Contar los proyectos del usuario actual
    total_proyectos = Proyecto.query.filter_by(Usuario=usuario_actual, Estatus=True).count()
    
    # Obtener los IDs de los proyectos del usuario actual
    proyectos_usuario = Proyecto.query.filter_by(Usuario=usuario_actual, Estatus=True).all()
    proyectos_ids = [proyecto.idProyecto for proyecto in proyectos_usuario]
    
    # Contar los modelos que pertenecen a los proyectos del usuario actual
    total_modelos = Modelos.query.filter(Modelos.Proyecto_id.in_(proyectos_ids), Modelos.Estado==True).count()
    
    # Contar los datasets que pertenecen a los proyectos del usuario actual
    total_datasets = DataSet.query.filter(DataSet.idProyecto.in_(proyectos_ids)).count()

    # Contar los modelos generados que pertenecen a los proyectos del usuario actual
    total_modelos_generados = Modelos_generados.query.filter(
        Modelos_generados.Proyecto.in_(proyectos_ids)
    ).count()
    
    # Contar los reportes generados por el usuario actual
    total_reportes = Reporte.query.filter_by(Usuario=usuario_actual).count()

    # Renderizar el template con las estadísticas
    return render_template(
        'admin/inicio.html',
        total_usuarios=total_usuarios,
        total_proyectos=total_proyectos,
        total_modelos=total_modelos,
        total_datasets=total_datasets,
        total_modelos_generados=total_modelos_generados,
        total_reportes=total_reportes
    )

@login_required
@bp.route('/experto')
def experto():
    # Obtener el usuario actual
    usuario_actual = session.get('user')
    
    # Contar los usuarios
    total_usuarios = Usuario.query.count()
    
    # Contar los proyectos del usuario actual
    total_proyectos = Proyecto.query.filter_by(Usuario=usuario_actual, Estatus=True).count()
    
    # Obtener los IDs de los proyectos del usuario actual
    proyectos_usuario = Proyecto.query.filter_by(Usuario=usuario_actual, Estatus=True).all()
    proyectos_ids = [proyecto.idProyecto for proyecto in proyectos_usuario]
    
    # Contar los modelos que pertenecen a los proyectos del usuario actual
    total_modelos = Modelos.query.filter(Modelos.Proyecto_id.in_(proyectos_ids), Modelos.Estado==True).count()
    
    # Contar los datasets que pertenecen a los proyectos del usuario actual
    total_datasets = DataSet.query.filter(DataSet.idProyecto.in_(proyectos_ids)).count()

    # Contar los modelos generados que pertenecen a los proyectos del usuario actual
    total_modelos_generados = Modelos_generados.query.filter(
        Modelos_generados.Proyecto.in_(proyectos_ids)
    ).count()
    
    # Contar los reportes generados por el usuario actual
    total_reportes = Reporte.query.filter_by(Usuario=usuario_actual).count()

    # Renderizar el template con las estadísticas
    return render_template(
        'experto/inicio.html',
        total_usuarios=total_usuarios,
        total_proyectos=total_proyectos,
        total_modelos=total_modelos,
        total_datasets=total_datasets,
        total_modelos_generados=total_modelos_generados,
        total_reportes=total_reportes
    )

@login_required
@bp.route('/tester')
def tester():
    # Obtener el usuario actual
    usuario_actual = session.get('user')
    
    # Contar los usuarios
    total_usuarios = Usuario.query.count()
    
    # Contar los proyectos del usuario actual
    total_proyectos = Proyecto.query.filter_by(Usuario=usuario_actual, Estatus=True).count()
    
    # Obtener los IDs de los proyectos del usuario actual
    proyectos_usuario = Proyecto.query.filter_by(Usuario=usuario_actual, Estatus=True).all()
    proyectos_ids = [proyecto.idProyecto for proyecto in proyectos_usuario]
    
    # Contar los modelos que pertenecen a los proyectos del usuario actual
    total_modelos = Modelos.query.filter(Modelos.Proyecto_id.in_(proyectos_ids), Modelos.Estado==True).count()
    
    # Contar los datasets que pertenecen a los proyectos del usuario actual
    total_datasets = DataSet.query.filter(DataSet.idProyecto.in_(proyectos_ids)).count()

    # Contar los modelos generados que pertenecen a los proyectos del usuario actual
    total_modelos_generados = Modelos_generados.query.filter(
        Modelos_generados.Proyecto.in_(proyectos_ids)
    ).count()
    
    # Contar los reportes generados por el usuario actual
    total_reportes = Reporte.query.filter_by(Usuario=usuario_actual).count()

    # Renderizar el template con las estadísticas
    return render_template(
        'tester/inicio.html',
        total_usuarios=total_usuarios,
        total_proyectos=total_proyectos,
        total_modelos=total_modelos,
        total_datasets=total_datasets,
        total_modelos_generados=total_modelos_generados,
        total_reportes=total_reportes
    )