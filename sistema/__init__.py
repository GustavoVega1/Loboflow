from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail
from itsdangerous import URLSafeTimedSerializer

db = SQLAlchemy()
mail = Mail()
RUTA_BASE = r'C:\Users\gv710\Documents\GUSTAVO\10MO CUATRIMESTE\CODIGO'
def create_app():
    global s
    app = Flask(__name__)
    
    app.config.from_mapping(
        DEBUG=True,
        SECRET_KEY='dev',  
        SQLALCHEMY_DATABASE_URI="mysql://root:@localhost/proyecto" #Conexion a la base de datos
    )

    # Inicialización de Flask-Mail para poder enviar correos electrónicos desde el sistema
    app.config['MAIL_SERVER'] = 'smtp.gmail.com'
    app.config['MAIL_PORT'] = 587
    app.config['MAIL_USE_SSL'] = False
    app.config['MAIL_USE_TLS'] = True
    app.config['MAIL_USERNAME'] = 'upemora886@gmail.com'  
    app.config['MAIL_PASSWORD'] = 'cfjx wyek pqkn fput'  # Contraseña de aplicación correcta
    app.config['MAIL_DEFAULT_SENDER'] = 'upemora886@gmail.com'


    db.init_app(app)
    mail.init_app(app)

    # Mueve la inicialización del serializer aquí
    s = URLSafeTimedSerializer(app.config['SECRET_KEY'])

    from . import auth
    app.register_blueprint(auth.bp)

    from . import proyecto
    app.register_blueprint(proyecto.bp)

    from . import imagenes
    app.register_blueprint(imagenes.bp)

    from . import dataset
    app.register_blueprint(dataset.bp)

    from . import modelos
    app.register_blueprint(modelos.bp)

    from . import experimentador
    app.register_blueprint(experimentador.bp)

    from . import reporte
    app.register_blueprint(reporte.bp)

    @app.route('/')
    def index():
        return render_template('index.html')

    with app.app_context():
        db.create_all()

    return app
