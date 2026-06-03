"""
Rutas para descargar reportes SRI
Formulario 104, Anexo ICE/PVP, ATS
"""
from flask import Blueprint, send_file, request, jsonify
from flask_login import login_required, current_user
from services.generador_formulario_104 import GeneradorFormulario104
from services.generador_anexo_ice import GeneradorAnexoICE
from services.generador_ats import GeneradorATS
from services.generador_retenciones import GeneradorRetenciones
from datetime import datetime
import json
import io

reportes = Blueprint('reportes', __name__, url_prefix='/reportes')


@reportes.route('/formulario_104/<int:anio>/<int:mes>')
@login_required
def descargar_formulario_104(anio, mes):
    """Descarga Formulario 104 en formato especificado

    Path params:
        - anio: Año fiscal (2026, 2027, etc.)
        - mes: Mes fiscal (1-12)

    Query params:
        - formato: excel (default), json, xml

    Returns:
        Archivo descargable en formato solicitado
    """
    # Validar parámetros
    if not (1 <= mes <= 12):
        return jsonify({'error': 'Mes debe estar entre 1 y 12'}), 400

    if anio < 2020 or anio > datetime.now().year:
        return jsonify({'error': f'Año debe estar entre 2020 y {datetime.now().year}'}), 400

    formato = request.args.get('formato', 'excel').lower()
    if formato not in ['excel', 'json', 'xml']:
        return jsonify({'error': 'Formato debe ser: excel, json, xml'}), 400

    try:
        if formato == 'excel':
            archivo = GeneradorFormulario104.generar_excel(current_user.id, anio, mes)
            return send_file(
                archivo,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                as_attachment=True,
                download_name=f'Formulario_104_{anio}_{mes:02d}.xlsx'
            )

        elif formato == 'json':
            datos = GeneradorFormulario104.generar_json(current_user.id, anio, mes)
            return jsonify(datos)

        elif formato == 'xml':
            xml = GeneradorFormulario104.generar_xml(current_user.id, anio, mes)
            return send_file(
                io.BytesIO(xml.encode('utf-8')),
                mimetype='application/xml',
                as_attachment=True,
                download_name=f'Formulario_104_{anio}_{mes:02d}.xml'
            )

    except Exception as e:
        return jsonify({'error': f'Error generando reporte: {str(e)}'}), 500


@reportes.route('/formulario_104/<int:anio>/<int:mes>/preview')
@login_required
def preview_formulario_104(anio, mes):
    """Vista previa del Formulario 104 en JSON

    Returns:
        JSON con detalles del formulario para preview en el navegador
    """
    try:
        datos = GeneradorFormulario104.obtener_datos_declaracion(
            current_user.id, anio, mes
        )
        return jsonify({
            'status': 'success',
            'formulario': datos
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@reportes.route('/lista_periodos')
@login_required
def lista_periodos_disponibles():
    """Lista todos los períodos con datos disponibles para descargar

    Returns:
        JSON con lista de períodos (año/mes) con datos
    """
    from models.user import Factura
    from models import db
    from sqlalchemy import extract, distinct

    # Obtener períodos únicos de facturas del usuario
    periodos = db.session.query(
        extract('year', Factura.fecha_emision).label('anio'),
        extract('month', Factura.fecha_emision).label('mes')
    ).filter(
        Factura.usuario_id == current_user.id
    ).distinct().order_by('anio', 'mes').all()

    return jsonify({
        'usuario_id': current_user.id,
        'periodos': [
            {'anio': int(p.anio), 'mes': int(p.mes), 'label': f"{int(p.anio)}/{int(p.mes):02d}"}
            for p in periodos
        ],
        'total': len(periodos)
    })


@reportes.route('/resumen_anio/<int:anio>')
@login_required
def resumen_anio(anio):
    """Obtiene resumen IVA anual

    Path params:
        - anio: Año fiscal

    Returns:
        JSON con resumen mensual del año
    """
    from services.credito_tributario import CreditoTributario

    try:
        resumen = CreditoTributario.obtener_resumen_anio(current_user.id, anio)
        if not resumen:
            return jsonify({'error': f'No hay datos para el año {anio}'}), 404

        return jsonify({
            'status': 'success',
            'resumen': resumen
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@reportes.route('/anexo_ice/<int:anio>/<int:mes>')
@login_required
def descargar_anexo_ice(anio, mes):
    """Descarga Anexo ICE en formato especificado

    Query params:
        - formato: excel (default), json, xml
    """
    if not (1 <= mes <= 12):
        return jsonify({'error': 'Mes debe estar entre 1 y 12'}), 400

    formato = request.args.get('formato', 'excel').lower()
    if formato not in ['excel', 'json', 'xml']:
        return jsonify({'error': 'Formato debe ser: excel, json, xml'}), 400

    try:
        if formato == 'excel':
            archivo = GeneradorAnexoICE.generar_excel(current_user.id, anio, mes)
            return send_file(
                archivo,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                as_attachment=True,
                download_name=f'Anexo_ICE_{anio}_{mes:02d}.xlsx'
            )
        elif formato == 'json':
            datos = GeneradorAnexoICE.generar_json(current_user.id, anio, mes)
            return jsonify(datos)
        elif formato == 'xml':
            xml = GeneradorAnexoICE.generar_xml(current_user.id, anio, mes)
            return send_file(
                io.BytesIO(xml.encode('utf-8')),
                mimetype='application/xml',
                as_attachment=True,
                download_name=f'Anexo_ICE_{anio}_{mes:02d}.xml'
            )
    except Exception as e:
        return jsonify({'error': f'Error generando reporte: {str(e)}'}), 500


@reportes.route('/ats/<int:anio>/<int:mes>')
@login_required
def descargar_ats(anio, mes):
    """Descarga ATS (Archivo Técnico Tributario)

    Query params:
        - formato: plano (default), json, xml
    """
    if not (1 <= mes <= 12):
        return jsonify({'error': 'Mes debe estar entre 1 y 12'}), 400

    formato = request.args.get('formato', 'plano').lower()
    if formato not in ['plano', 'json', 'xml']:
        return jsonify({'error': 'Formato debe ser: plano, json, xml'}), 400

    try:
        if formato == 'plano':
            contenido = GeneradorATS.generar_archivo_plano(current_user.id, anio, mes)
            return send_file(
                io.BytesIO(contenido.encode('utf-8')),
                mimetype='text/plain',
                as_attachment=True,
                download_name=f'ATS_{anio}_{mes:02d}.txt'
            )
        elif formato == 'json':
            datos = GeneradorATS.generar_json(current_user.id, anio, mes)
            return jsonify(datos)
        elif formato == 'xml':
            xml = GeneradorATS.generar_xml(current_user.id, anio, mes)
            return send_file(
                io.BytesIO(xml.encode('utf-8')),
                mimetype='application/xml',
                as_attachment=True,
                download_name=f'ATS_{anio}_{mes:02d}.xml'
            )
    except Exception as e:
        return jsonify({'error': f'Error generando reporte: {str(e)}'}), 500


@reportes.route('/retenciones/<int:anio>/<int:mes>')
@login_required
def descargar_retenciones(anio, mes):
    """Descarga Certificado de Retención

    Query params:
        - formato: html (default), json, xml
    """
    if not (1 <= mes <= 12):
        return jsonify({'error': 'Mes debe estar entre 1 y 12'}), 400

    formato = request.args.get('formato', 'html').lower()
    if formato not in ['html', 'json', 'xml']:
        return jsonify({'error': 'Formato debe ser: html, json, xml'}), 400

    try:
        if formato == 'html':
            contenido = GeneradorRetenciones.generar_certificado_html(current_user.id, anio, mes)
            return send_file(
                io.BytesIO(contenido.encode('utf-8')),
                mimetype='text/html',
                as_attachment=True,
                download_name=f'Certificado_Retenciones_{anio}_{mes:02d}.html'
            )
        elif formato == 'json':
            datos = GeneradorRetenciones.generar_json(current_user.id, anio, mes)
            return jsonify(datos)
        elif formato == 'xml':
            xml = GeneradorRetenciones.generar_xml(current_user.id, anio, mes)
            return send_file(
                io.BytesIO(xml.encode('utf-8')),
                mimetype='application/xml',
                as_attachment=True,
                download_name=f'Retenciones_{anio}_{mes:02d}.xml'
            )
    except Exception as e:
        return jsonify({'error': f'Error generando reporte: {str(e)}'}), 500


@reportes.route('/paquete_completo/<int:anio>/<int:mes>')
@login_required
def descargar_paquete_completo(anio, mes):
    """Descarga todos los reportes SRI en una carpeta (ZIP)

    Incluye:
        - Formulario 104
        - Anexo ICE/PVP
        - ATS
        - Certificado de Retenciones
    """
    if not (1 <= mes <= 12):
        return jsonify({'error': 'Mes debe estar entre 1 y 12'}), 400

    try:
        import zipfile
        import tempfile
        import os

        # Crear archivo temporal
        temp_zip = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')
        temp_zip.close()

        with zipfile.ZipFile(temp_zip.name, 'w', zipfile.ZIP_DEFLATED) as zf:
            # Formulario 104
            f104_excel = GeneradorFormulario104.generar_excel(current_user.id, anio, mes)
            zf.writestr(f'Formulario_104_{anio}_{mes:02d}.xlsx', f104_excel.getvalue())

            # Anexo ICE
            anexo_excel = GeneradorAnexoICE.generar_excel(current_user.id, anio, mes)
            zf.writestr(f'Anexo_ICE_{anio}_{mes:02d}.xlsx', anexo_excel.getvalue())

            # ATS
            ats_plano = GeneradorATS.generar_archivo_plano(current_user.id, anio, mes)
            zf.writestr(f'ATS_{anio}_{mes:02d}.txt', ats_plano.encode('utf-8'))

            # Retenciones
            ret_html = GeneradorRetenciones.generar_certificado_html(current_user.id, anio, mes)
            zf.writestr(f'Retenciones_{anio}_{mes:02d}.html', ret_html.encode('utf-8'))

        # Enviar archivo ZIP
        with open(temp_zip.name, 'rb') as f:
            contenido = f.read()

        os.unlink(temp_zip.name)

        return send_file(
            io.BytesIO(contenido),
            mimetype='application/zip',
            as_attachment=True,
            download_name=f'Reportes_SRI_{anio}_{mes:02d}.zip'
        )

    except Exception as e:
        return jsonify({'error': f'Error generando paquete: {str(e)}'}), 500
