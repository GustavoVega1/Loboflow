from sistema import db

class Usuario(db.Model):
    idUsuario = db.Column(db.Integer, primary_key = True, nullable=False)
    nombre = db.Column(db.String(50), nullable = False)
    Contra = db.Column(db.Text, nullable = False)
    Rol = db.Column(db.String(50), nullable = False)
    Correo = db.Column(db.String(50), nullable = False)
    confirmed = db.Column(db.Boolean, default=False)
    ocupacion = db.Column(db.String(100), nullable=True)  
    intereses = db.Column(db.String(200), nullable=True)  
    fecha_registro = db.Column(db.DateTime, default=db.func.current_timestamp())  

    def __init__(self, nombre, Contra, Tipo, Correo, ocupacion=None, intereses=None):
        self.nombre = nombre
        self.Contra = Contra
        self.Rol = Tipo
        self.Correo = Correo
        self.ocupacion = ocupacion
        self.intereses = intereses
    
    def __repr__(self):
        return f'<Usuario: {self.nombre}>'

class Modelos(db.Model):
    idModelos = db.Column(db.Integer, primary_key = True, nullable=False)
    Nombre = db.Column(db.String(50), nullable = False)
    Descripcion = db.Column(db.String(250), nullable = True)
    Estado = db.Column(db.Boolean, nullable = True)
    Proyecto_id = db.Column(db.Integer, db.ForeignKey('proyecto.idProyecto'), nullable=False)
    Proyecto = db.relationship('Proyecto', backref='modelos')
    Arquitectura = db.Column(db.String(200), nullable = False)
    Ruta = db.Column(db.String(250), nullable=False)

    def __init__(self, nombre, descripcion, proyecto, estado, arquitectura, ruta):
        self.Nombre = nombre
        self.Descripcion = descripcion
        self.Estado = estado
        self.Proyecto_id = proyecto
        self.Arquitectura = arquitectura
        self.Ruta = ruta

    def __repr__(self) -> str:
        return f'<Modelo: {self.Nombre}'       
    
class Proyecto(db.Model):
    idProyecto = db.Column(db.Integer, primary_key=True, nullable=False)
    Nombre = db.Column(db.String(50), nullable=False)
    Descripcion = db.Column(db.String(250), nullable=True)
    Estatus = db.Column(db.Boolean, nullable=True)
    Usuario = db.Column(db.Integer, nullable=False)
    TipoProyecto = db.Column(db.String(50), nullable=False) 
    Objetivo = db.Column(db.String(250), nullable=True)    
    
    def __init__(self, nombre, descripcion, estatus, usuario, tipo_proyecto, objetivo=None):
        self.Nombre = nombre
        self.Descripcion = descripcion
        self.Estatus = estatus
        self.Usuario = usuario
        self.TipoProyecto = tipo_proyecto
        self.Objetivo = objetivo

    def __repr__(self) -> str:
        return f'<Proyecto: {self.Nombre}, Tipo: {self.TipoProyecto}, Objetivo: {self.Objetivo}>'

class DataSet(db.Model):
    idDataset = db.Column(db.Integer, primary_key=True)
    Nombre = db.Column(db.String(100))
    Descripcion = db.Column(db.String(200))
    Fecha_creada = db.Column(db.DateTime)
    Estado = db.Column(db.Boolean, default=True)
    Tipo = db.Column(db.String(100))
    # Relación con Proyecto
    idProyecto = db.Column(db.Integer, db.ForeignKey('proyecto.idProyecto'))
    Proyecto = db.relationship('Proyecto', backref='datasets')


    def __init__(self, nombre, descripcion, proyecto, fecha, estado, tipo):
        self.Nombre = nombre
        self.Descripcion = descripcion
        self.idProyecto = proyecto
        self.Fecha_creada = fecha
        self.Estado = estado
        self.Tipo = tipo

    def __repr__(self) -> str:
        return f'<Dataset: {self.Nombre}'   
    
class Modelos_generados(db.Model):
    idModelo_generados = db.Column(db.Integer, primary_key = True, nullable=False)
    Nombre = db.Column(db.String(250), nullable=False)
    Descripcion = db.Column(db.String(200), nullable = True)
    epocas = db.Column(db.Integer, nullable = False)
    batch = db.Column(db.Integer, nullable = False)
    Modelo_checkpoint = db.Column(db.Integer)
    Fecha_creacion = db.Column(db.Date, nullable=False)
    Arquitectura = db.Column(db.String(250), nullable = False)
    Proyecto = db.Column(db.Integer, nullable = False)
    optimizador = db.Column(db.String(100))
    Dataset = db.Column(db.Integer)
    Ruta = db.Column(db.String(200))


    def __init__(self, nombre, desc, epocas, batch, fecha, arquitectura, proyecto, optimizador, dataset, ruta):
        self.Nombre = nombre
        self.Descripcion = desc
        self.epocas = epocas
        self.batch = batch
        self.Fecha_creacion = fecha
        self.Arquitectura = arquitectura
        self.Proyecto = proyecto
        self.optimizador = optimizador
        self.Dataset = dataset
        self.Ruta = ruta

    def __repr__(self) -> str:
        return f'Modelo: {self.Nombre}'

class Evaluacion_modelo(db.Model):
    id_Evaluacion = db.Column(db.Integer, primary_key = True, nullable=False)
    F1_score = db.Column(db.Float, nullable = False)
    Recall = db.Column(db.Float)
    mAP50 = db.Column(db.Float)
    Precision = db.Column(db.Float)
    mAP50_95 = db.Column(db.Float)
    mAP75 = db.Column(db.Float)
    Modelo = db.Column(db.Integer)
    tiempo = db.Column(db.Float)

    def __init__(self, score, recall, map50, precision, map50_95, map75, modelo, tiempo):
        self.F1_score = score
        self.Recall = recall
        self.mAP50 = map50
        self.Precision = precision
        self.mAP50_95 = map50_95
        self.mAP75 = map75
        self.Modelo = modelo
        self.tiempo = tiempo

    def __repr__(self) -> str:
        return f'Evaluacion: {self.id_Evaluacion}'

class Reporte(db.Model):
    idReporte = db.Column(db.Integer, primary_key = True, nullable=False)
    Nombre = db.Column(db.String(250), nullable=False)
    Descripcion = db.Column(db.String(200), nullable = True)
    Fecha = db.Column(db.Date, nullable=False)
    Evaluacion = db.Column(db.Integer)
    Usuario = db.Column(db.Integer)
    ruta = db.Column(db.String(200))

    def __init__(self, nombre, desc, fecha, evaluacion, usuario, ruta):
        self.Nombre = nombre
        self.Descripcion = desc
        self.Fecha = fecha
        self.Evaluacion = evaluacion
        self.Usuario = usuario
        self.ruta = ruta

    def __repr__(self):
        return f'Reporte: {self.Nombre}'
        