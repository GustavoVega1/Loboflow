from flask import (
    Blueprint, render_template,
    request, url_for, redirect, flash,render_template_string, send_file,
    session, g, send_from_directory)
from .auth import login_required
from sistema import db, RUTA_BASE
from .models import Proyecto, Reporte, Modelos_generados, Evaluacion_modelo, DataSet, Modelos
from datetime import date
import os
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from reportlab.pdfgen import canvas
from PIL import Image
from reportlab.lib.pagesizes import letter
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from datetime import datetime
from reportlab.platypus import Table, TableStyle

# Creación de un Blueprint para la autenticación con prefijo de URL '/proyecto'
bp = Blueprint('reporte', __name__, url_prefix='/reporte')

@login_required
@bp.route('/inicio')
def inicio():
    # Obtener el ID del usuario desde la sesión
    usuario_id = session.get('user')  # Asumiendo que el ID del usuario está almacenado en la sesión
    reportes = Reporte.query.filter_by(Usuario=usuario_id).order_by(Reporte.Fecha.desc()).all()
    return render_template('reporte/inicio.html', reportes=reportes)

@bp.route('/reporte/progreso', methods=['GET', 'POST'])
@login_required
def registrar_reporte_progreso():
    if request.method == 'POST':
        proyecto_id = request.form.get('proyecto')
        nombre = request.form.get('nombre')
        descripcion = request.form.get('descripcion')

        proyecto = Proyecto.query.get(proyecto_id)
        if not proyecto:
            flash('Proyecto no encontrado', 'danger')
            return redirect(url_for('reporte.registrar_reporte_progreso'))

        reporte_existente = Reporte.query.filter_by(Nombre=nombre).first()
        if reporte_existente:
            flash('Ya existe un reporte con este nombre. Por favor, elige otro nombre.', 'warning')
            return redirect(url_for('reporte.registrar_reporte_progreso'))

        ruta_proyecto = os.path.join(RUTA_BASE, proyecto.Nombre)
        ruta_reportes = os.path.join(ruta_proyecto, "REPORTES")
        if not os.path.exists(ruta_reportes):
            os.makedirs(ruta_reportes)

        pdf_filename = f"{nombre}.pdf"
        pdf_path = os.path.join(ruta_reportes, pdf_filename)

        try:
            datasets = DataSet.query.filter_by(idProyecto=proyecto_id).all()
            modelos = Modelos.query.filter_by(Proyecto_id=proyecto_id).all()
            modelos_generados = Modelos_generados.query.filter_by(Proyecto=proyecto_id).all()  # Nuevas consultas

            c = canvas.Canvas(pdf_path, pagesize=letter)
            width, height = letter

            margen_x = 50
            margen_y = 50
            color_principal = colors.HexColor("#44004d")  # Color principal
            subtitulo_color = colors.HexColor("#660066")
            texto_color = colors.black  # Color negro para el texto

            logo_path = os.path.join(os.path.dirname(__file__), "static", "images", "LOGO_SISTEMA.png")
            logo_path = os.path.abspath(logo_path)
            if os.path.exists(logo_path):
                c.drawImage(logo_path, margen_x, height - margen_y - 60, width=100, height=50, preserveAspectRatio=True, mask='auto')

            c.setFont("Helvetica-Bold", 20)
            c.setFillColor(color_principal)
            c.drawString(margen_x + 110, height - margen_y - 30, f"Reporte de Progreso del Proyecto")
            c.setFont("Helvetica", 14)
            c.drawString(margen_x + 110, height - margen_y - 55, f"{proyecto.Nombre}")

            c.setStrokeColor(color_principal)
            c.setLineWidth(1.5)
            c.line(margen_x, height - margen_y - 70, width - margen_x, height - margen_y - 70)

            c.setFont("Helvetica-Bold", 16)
            c.setFillColor(subtitulo_color)
            c.drawString(margen_x, height - margen_y - 100, "Información General del Proyecto")

            c.setFont("Helvetica", 12)
            c.setFillColor(texto_color)
            c.drawString(margen_x, height - margen_y - 120, f"Nombre: {proyecto.Nombre}")
            c.drawString(margen_x, height - margen_y - 140, f"Descripción: {proyecto.Descripcion or 'No especificada'}")
            c.drawString(margen_x, height - margen_y - 160, f"Tipo de Proyecto: {proyecto.TipoProyecto}")
            c.drawString(margen_x, height - margen_y - 180, f"Objetivo: {proyecto.Objetivo or 'No especificado'}")

            c.setFont("Helvetica-Bold", 16)
            c.setFillColor(subtitulo_color)
            c.drawString(margen_x, height - margen_y - 210, "Resumen del Proyecto")

            c.setFont("Helvetica", 12)
            c.setFillColor(texto_color)
            c.drawString(margen_x, height - margen_y - 230, f"Cantidad de Datasets Registrados: {len(datasets)}")
            c.drawString(margen_x, height - margen_y - 250, f"Cantidad de Modelos Subidos: {len(modelos)}")
            c.drawString(margen_x, height - margen_y - 270, f"Cantidad de Modelos Entrenados: {len(modelos_generados)}")  # Información adicional

            # Información de los datasets
            c.setFont("Helvetica-Bold", 16)
            c.setFillColor(subtitulo_color)
            c.drawString(margen_x, height - margen_y - 290, "Datasets Registrados")
            c.setFont("Helvetica", 12)
            c.setFillColor(texto_color)  # Cambié a color negro
            y = height - margen_y - 310  # Comienza después del título de Datasets
            for dataset in datasets:
                c.drawString(margen_x, y, f"- {dataset.Nombre}")
                y -= 15
                c.setFont("Helvetica", 10)
                c.drawString(margen_x + 20, y, f"Descripción: {dataset.Descripcion or 'Sin descripción'}")
                y -= 20
                if y < margen_y:
                    c.showPage()
                    y = height - margen_y

            c.setFont("Helvetica-Bold", 16)
            c.setFillColor(subtitulo_color)
            c.drawString(margen_x, y - 20, "Modelos Subidos")

            # Cambiar el color a negro para la información de los modelos
            y -= 40
            for modelo in modelos:
                c.setFont("Helvetica-Bold", 12)
                c.drawString(margen_x, y, f"- {modelo.Nombre}")
                y -= 15
                c.setFont("Helvetica", 10)
                c.setFillColor(texto_color)  # Cambié a color negro aquí
                c.drawString(margen_x + 20, y, f"Descripción: {modelo.Descripcion or 'Sin descripción'}")
                y -= 20
                if y < margen_y:
                    c.showPage()
                    y = height - margen_y

            c.setFont("Helvetica-Bold", 16)
            c.setFillColor(subtitulo_color)
            c.drawString(margen_x, y - 20, "Modelos Entrenados")  # Título para los modelos entrenados
            y -= 40

            # Información de los modelos entrenados
            for modelo_generado in modelos_generados:
                c.setFont("Helvetica-Bold", 12)
                c.drawString(margen_x, y, f"- {modelo_generado.Nombre}")
                y -= 15
                c.setFont("Helvetica", 10)
                c.setFillColor(texto_color)  # Asegúrate de que el color sea negro aquí
                c.drawString(margen_x + 20, y, f"Descripción: {modelo_generado.Descripcion or 'Sin descripción'}")
                y -= 20
                if y < margen_y:
                    c.showPage()
                    y = height - margen_y

        
            c.showPage()
            c.save()

            nuevo_reporte = Reporte(
                nombre=nombre,
                desc=descripcion,
                fecha = datetime.now().strftime("%Y-%m-%d %H:%M"),
                evaluacion=None,
                usuario=session.get('user'),
                ruta=pdf_path
            )
            db.session.add(nuevo_reporte)
            db.session.commit()

            flash('Reporte generado exitosamente.', 'success')
            return redirect(url_for('reporte.inicio'))
        except Exception as e:
            flash(f'Error al generar el reporte: {e}', 'danger')
            return redirect(url_for('reporte.registrar_reporte_progreso'))

    usuario_id = session.get('user')
    proyectos = Proyecto.query.filter_by(Usuario=usuario_id).all()
    return render_template('reporte/general.html', proyectos=proyectos)


@login_required
@bp.route('/reporte/comparativo', methods=['GET', 'POST'])
def registrar_reporte_comparativo():
    usuario_id = session.get('user')

    # Obtener proyectos del usuario autenticado
    proyectos = Proyecto.query.filter_by(Usuario=usuario_id).all()

    # Obtener modelos generados agrupados por dataset
    modelos_base = {}
    for proyecto in proyectos:
        modelos_por_dataset = {}
        modelos = Modelos_generados.query.filter_by(Proyecto=proyecto.idProyecto).all()
        for modelo in modelos:
            dataset = modelo.Dataset
            if dataset not in modelos_por_dataset:
                modelos_por_dataset[dataset] = []
            modelos_por_dataset[dataset].append({
                "idModelo": modelo.idModelo_generados,
                "Nombre": modelo.Nombre,
            })
        modelos_base[proyecto.idProyecto] = modelos_por_dataset

    def buscar_graficas(modelo):
        carpeta_modelos = os.path.join(ruta_proyecto, "MODELOS_ENTRENADOS")
        carpeta_modelo = os.path.join(carpeta_modelos, modelo.Nombre)
        carpeta_metricas = os.path.join(carpeta_modelo, modelo.Nombre)
        grafica_f1_confianza = os.path.join(carpeta_metricas, "F1_curve.png")
        grafica_matriz_confusion_normalizada = os.path.join(carpeta_metricas, "confusion_matrix_normalized.png")
        grafica_matriz_confusion = os.path.join(carpeta_metricas, "confusion_matrix.png")
        return [
            ("Curva F1-Score", grafica_f1_confianza),
            ("Matriz de Confusión Normalizada", grafica_matriz_confusion_normalizada),
            ("Matriz de Confusión", grafica_matriz_confusion),
        ]

    if request.method == 'POST':
        nombre = request.form['nombre']
        descripcion = request.form['descripcion']
        proyecto_id = request.form['proyecto']
        modelo_id_1 = request.form['modelo1']
        modelo_id_2 = request.form['modelo2']
        fecha = datetime.now().strftime("%Y-%m-%d %H:%M")

        if modelo_id_1 == modelo_id_2:
            flash("Debes seleccionar dos modelos diferentes.", "danger")
            return redirect(url_for('reporte.registrar_reporte_comparativo'))

        modelo_1 = Modelos_generados.query.get(modelo_id_1)
        modelo_2 = Modelos_generados.query.get(modelo_id_2)
        evaluacion_1 = Evaluacion_modelo.query.filter_by(Modelo=modelo_id_1).first()
        evaluacion_2 = Evaluacion_modelo.query.filter_by(Modelo=modelo_id_2).first()

        if not evaluacion_1 or not evaluacion_2:
            flash("Uno o ambos modelos seleccionados no tienen evaluaciones disponibles.", "danger")
            return redirect(url_for('reporte.registrar_reporte_comparativo'))

        proyecto = Proyecto.query.get(proyecto_id)
        ruta_proyecto = os.path.join(RUTA_BASE, proyecto.Nombre)
        ruta_reportes = os.path.join(ruta_proyecto, "REPORTES")
        os.makedirs(ruta_reportes, exist_ok=True)

        pdf_filename = f"{nombre}.pdf"
        pdf_path = os.path.join(ruta_reportes, pdf_filename)

        try:
            c = canvas.Canvas(pdf_path, pagesize=letter)
            width, height = letter

            margen_x = 50
            margen_y = 50
            espaciado_seccion = 30
            espaciado_texto = 20
            color_principal = colors.HexColor("#44004d")
            subtitulo_color = colors.HexColor("#660066")
            texto_color = colors.black

            def verificar_espacio(c, current_y, requerido):
                """Salta a una nueva página si no hay suficiente espacio"""
                if current_y - requerido < margen_y:
                    c.showPage()
                    return height - margen_y
                return current_y

            # Logo de la empresa
            logo_path = os.path.join(os.path.dirname(__file__), "static", "images", "LOGO_SISTEMA.png")
            logo_path = os.path.abspath(logo_path)
            if os.path.exists(logo_path):
                c.drawImage(logo_path, margen_x, height - margen_y - 60, width=100, height=50, preserveAspectRatio=True, mask='auto')

            # Título principal
            c.setFont("Helvetica-Bold", 20)
            c.setFillColor(color_principal)
            c.drawString(margen_x, height - margen_y - 30, "Reporte Comparativo de Modelos")
            c.setFont("Helvetica", 14)
            c.drawString(margen_x, height - margen_y - 55, proyecto.Nombre)
            c.line(margen_x, height - margen_y - 70, width - margen_x, height - margen_y - 70)

            # Gráficas de cada modelo
            current_y = height - margen_y - 100
            for i, (modelo, evaluacion) in enumerate([(modelo_1, evaluacion_1), (modelo_2, evaluacion_2)]):
                current_y = verificar_espacio(c, current_y, 200)

                c.setFont("Helvetica-Bold", 16)
                c.setFillColor(subtitulo_color)
                c.drawString(margen_x, current_y, f"Modelo {i + 1}: {modelo.Nombre}")
                current_y -= espaciado_texto

                c.setFont("Helvetica", 12)
                c.setFillColor(texto_color)
                c.drawString(margen_x, current_y, f"Descripción: {modelo.Descripcion or 'No especificada'}")
                current_y -= espaciado_texto
                c.drawString(margen_x, current_y, f"Épocas: {modelo.epocas}")
                current_y -= espaciado_texto
                c.drawString(margen_x, current_y, f"Tamaño del batch: {modelo.batch}")
                current_y -= espaciado_texto
                c.drawString(margen_x, current_y, f"Optimizador: {modelo.optimizador}")
                current_y -= espaciado_texto

                # Métricas
                current_y = verificar_espacio(c, current_y, 150)
                c.setFont("Helvetica-Bold", 16)
                c.setFillColor(subtitulo_color)
                c.drawString(margen_x, current_y, "Métricas del Modelo")
                current_y -= espaciado_texto

                table_data = [
                    ["Métrica", "Valor"],
                    ["F1-Score", f"{evaluacion.F1_score:.2f}"],
                    ["Precisión", f"{evaluacion.Precision:.2f}"],
                    ["Recall", f"{evaluacion.Recall:.2f}"],
                    ["mAP50", f"{evaluacion.mAP50:.2f}"],
                    ["mAP50-95", f"{evaluacion.mAP50_95:.2f}"],
                    ["mAP75", f"{evaluacion.mAP75:.2f}"],
                ]

                table = Table(table_data, colWidths=[200, 200])
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), color_principal),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.lightgrey),
                    ('TEXTCOLOR', (0, 1), (-1, -1), texto_color),
                    ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.grey),
                    ('BOX', (0, 0), (-1, -1), 1, color_principal),
                ]))
                table.wrapOn(c, width, height)
                table.drawOn(c, margen_x, current_y - 100)
                current_y -= 150

                # Buscar gráficas del modelo
                graficas = buscar_graficas(modelo)
                for titulo, grafica in graficas:
                    current_y = verificar_espacio(c, current_y, 250)
                    if os.path.exists(grafica):
                        c.setFont("Helvetica-Bold", 14)
                        c.drawString(margen_x, current_y, titulo)
                        current_y -= espaciado_texto
                        c.drawImage(grafica, margen_x, current_y - 200, width=400, height=200, mask='auto')
                        current_y -= 220

            c.save()

            nuevo_reporte = Reporte(
                nombre=nombre,
                desc=descripcion,
                fecha=fecha,
                evaluacion=0,
                usuario=usuario_id,
                ruta=pdf_path
            )
            db.session.add(nuevo_reporte)
            db.session.commit()

            flash("Reporte comparativo generado exitosamente.", "success")
            return redirect(url_for('reporte.inicio'))
        except Exception as e:
            flash(f"Error al generar el reporte: {e}", "danger")
            return redirect(url_for('reporte.registrar_reporte_comparativo'))
    return render_template('reporte/comparativo.html', proyectos=proyectos, modelos=modelos_base)

@login_required
@bp.route('/reporte/metricas', methods=['GET', 'POST'])
def registrar_reporte_metricas():
    usuario_id = session.get('user')

    # Obtener proyectos del usuario autenticado
    proyectos = Proyecto.query.filter_by(Usuario=usuario_id).all()

    # Obtener modelos generados para los proyectos
    modelos_base = {}
    for proyecto in proyectos:
        modelos_base[proyecto.idProyecto] = [
            {
                "idModelo": modelo.idModelo_generados,
                "Nombre": modelo.Nombre
            }
            for modelo in Modelos_generados.query.filter_by(Proyecto=proyecto.idProyecto).all()
        ]

    if request.method == 'POST':
        # Recoger datos del formulario
        nombre = request.form['nombre']
        descripcion = request.form['descripcion']
        proyecto_id = request.form['proyecto']
        modelo_id = request.form['modelo']
        fecha = datetime.now().strftime("%Y-%m-%d %H:%M")

        # Obtener evaluación del modelo
        evaluacion = Evaluacion_modelo.query.filter_by(Modelo=modelo_id).first()
        modelo = Modelos_generados.query.get(modelo_id)
        dataset = DataSet.query.filter_by(idDataset=modelo.Dataset).first()

        if not evaluacion:
            flash("El modelo seleccionado no tiene evaluaciones disponibles.", "danger")
            return redirect(url_for('reporte.registrar_reporte_metricas'))

        # Crear la ruta para guardar el reporte
        proyecto = Proyecto.query.get(proyecto_id)
        ruta_proyecto = os.path.join(RUTA_BASE, proyecto.Nombre)
        ruta_reportes = os.path.join(ruta_proyecto, "REPORTES")
        os.makedirs(ruta_reportes, exist_ok=True)

        # Rutas de las gráficas
        carpeta_modelos = os.path.join(ruta_proyecto, "MODELOS_ENTRENADOS")
        carpeta_modelo = os.path.join(carpeta_modelos, modelo.Nombre)
        carpeta_metricas = os.path.join(carpeta_modelo, modelo.Nombre)
        grafica_f1_confianza = os.path.join(carpeta_metricas, "F1_curve.png")
        grafica_matriz_confusion_normalizada = os.path.join(carpeta_metricas, "confusion_matrix_normalized.png")
        grafica_matriz_confusion = os.path.join(carpeta_metricas, "confusion_matrix.png")

        # Generar el PDF
        pdf_filename = f"{nombre}.pdf"
        pdf_path = os.path.join(ruta_reportes, pdf_filename)

        try:
            c = canvas.Canvas(pdf_path, pagesize=letter)
            width, height = letter

            margen_x = 50
            margen_y = 50
            espaciado_seccion = 25
            espaciado_texto = 15
            color_principal = colors.HexColor("#44004d")
            subtitulo_color = colors.HexColor("#660066")
            texto_color = colors.black

            # Primera página: Información del modelo
            # Logo
            logo_path = os.path.join(os.path.dirname(__file__), "static", "images", "LOGO_SISTEMA.png")
            logo_path = os.path.abspath(logo_path)
            if os.path.exists(logo_path):
                c.drawImage(logo_path, margen_x, height - margen_y - 60, width=100, height=50, preserveAspectRatio=True, mask='auto')

            # Título principal
            c.setFont("Helvetica-Bold", 20)
            c.setFillColor(color_principal)
            c.drawString(margen_x + 120, height - margen_y - 30, "Reporte de Métricas del Modelo")
            c.setFont("Helvetica", 14)
            c.drawString(margen_x + 120, height - margen_y - 55, proyecto.Nombre)

            c.setStrokeColor(color_principal)
            c.setLineWidth(1.5)
            c.line(margen_x, height - margen_y - 70, width - margen_x, height - margen_y - 70)

            # Información del Modelo
            current_y = height - margen_y - 100
            c.setFont("Helvetica-Bold", 16)
            c.setFillColor(subtitulo_color)
            c.drawString(margen_x, current_y, "Información del Modelo")

            current_y -= espaciado_texto
            c.setFont("Helvetica", 12)
            c.setFillColor(texto_color)
            c.drawString(margen_x, current_y, f"Nombre: {modelo.Nombre}")
            current_y -= espaciado_texto
            c.drawString(margen_x, current_y, f"Descripción: {modelo.Descripcion or 'No especificada'}")
            current_y -= espaciado_texto
            c.drawString(margen_x, current_y, f"Épocas: {modelo.epocas}")
            current_y -= espaciado_texto
            c.drawString(margen_x, current_y, f"Tamaño del batch: {modelo.batch}")
            current_y -= espaciado_texto
            c.drawString(margen_x, current_y, f"Optimizador: {modelo.optimizador}")
            current_y -= espaciado_texto
            c.drawString(margen_x, current_y, f"Dataset: {dataset.Nombre}")

            # Métricas del Modelo
            current_y -= espaciado_seccion
            c.setFont("Helvetica-Bold", 16)
            c.setFillColor(subtitulo_color)
            c.drawString(margen_x, current_y, "Métricas del Modelo")

            current_y -= espaciado_texto
            c.setFont("Helvetica", 12)
            table_data = [
                ["Métrica", "Valor"],
                ["F1-Score", f"{evaluacion.F1_score:.2f}"],
                ["Precisión", f"{evaluacion.Precision:.2f}"],
                ["Recall", f"{evaluacion.Recall:.2f}"],
                ["mAP50", f"{evaluacion.mAP50:.2f}"],
                ["mAP50-95", f"{evaluacion.mAP50_95:.2f}"],
                ["mAP75", f"{evaluacion.mAP75:.2f}"],
            ]

            table = Table(table_data, colWidths=[200, 200])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), color_principal),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.lightgrey),
                ('TEXTCOLOR', (0, 1), (-1, -1), texto_color),
                ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('BOX', (0, 0), (-1, -1), 1, color_principal),
            ]))
            table.wrapOn(c, width, height)
            table.drawOn(c, margen_x, current_y - 100)
            current_y -= 150

            # Nueva página para las gráficas
            c.showPage()

            # Segunda página: Gráficas
            current_y = height - margen_y

            # Gráfica de F1-Score
            if os.path.exists(grafica_f1_confianza):
                c.setFont("Helvetica-Bold", 12)
                c.drawString(margen_x, current_y, "Gráfica de F1-Score")
                c.drawImage(grafica_f1_confianza, margen_x, current_y - 210, width=250, height=200)

            # Gráfica de Matriz de Confusión Normalizada
            if os.path.exists(grafica_matriz_confusion_normalizada):
                c.drawString(margen_x + 270, current_y, "Matriz de Confusión Normalizada")
                c.drawImage(grafica_matriz_confusion_normalizada, margen_x + 270, current_y - 210, width=250, height=200)

            # Espaciado antes de la siguiente fila de gráficas
            current_y -= 250

            # Gráfica de Matriz de Confusión
            if os.path.exists(grafica_matriz_confusion):
                c.drawString(margen_x, current_y, "Matriz de Confusión")
                c.drawImage(grafica_matriz_confusion, margen_x, current_y - 210, width=250, height=200)

            c.showPage()
            c.save()

            # Guardar en la base de datos
            nuevo_reporte = Reporte(
                nombre=nombre,
                desc=descripcion,
                fecha=fecha,
                evaluacion=evaluacion.id_Evaluacion,
                usuario=usuario_id,
                ruta=pdf_path
            )
            db.session.add(nuevo_reporte)
            db.session.commit()

            flash("Reporte generado exitosamente.", "success")
            return redirect(url_for('reporte.inicio'))
        except Exception as e:
            flash(f"Error al generar el reporte: {e}", "danger")
            return redirect(url_for('reporte.registrar_reporte_metricas'))

    return render_template('reporte/generar.html', proyectos=proyectos, modelos=modelos_base)

@bp.route('/reporte/ver/<filename>')
def ver_reporte(filename):
    print(filename)

    # Buscar el reporte por la ruta directa
    reporte = Reporte.query.filter(Reporte.ruta.like(f"%{filename}")).first()
    if not reporte:
        flash('Reporte no encontrado en la base de datos', 'warning')
        return redirect(url_for('reporte.inicio'))

    # Extraer la ruta completa del archivo desde la base de datos
    file_path = reporte.ruta

    # Verificar si el archivo existe en la ruta especificada
    if os.path.exists(file_path):
        directory = os.path.dirname(file_path)
        return send_from_directory(directory, filename)
    else:
        flash('Archivo del reporte no encontrado en el sistema', 'warning')
        return redirect(url_for('reporte.inicio'))

@bp.route('/eliminar_reporte', methods=['POST'])
@login_required
def eliminar_reporte():
    """Ruta para eliminar un reporte."""
    reporte_id = request.form.get('id')
    if not reporte_id:
        flash('No se proporcionó un ID válido para el reporte.', 'warning')
        return redirect(url_for('reporte.gestionar_reportes'))

    reporte = Reporte.query.get(reporte_id)
    
    if reporte is None:
        flash('No se encontró el reporte con el ID proporcionado.', 'warning')
        return redirect(url_for('reporte.gestionar_reportes'))

    # Verifica si el reporte tiene ruta antes de intentar eliminar el archivo
    if reporte.ruta:
        try:
            os.remove(reporte.ruta)
            print(f"Archivo {reporte.ruta} eliminado.")
        except Exception as e:
            flash(f'Error al eliminar el archivo: {e}', 'warning')

    # Elimina el reporte de la base de datos
    db.session.delete(reporte)
    db.session.commit()

    flash('El reporte se eliminó correctamente.', 'success')
    return redirect(url_for('reporte.inicio'))

    

