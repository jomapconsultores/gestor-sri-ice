"""Conciliación Bancaria Odoo con Mistral AI (basado en Conciliar.py)"""
import json, io, os
from flask import Blueprint, render_template, request, flash, redirect, url_for, Response, current_app
from flask_login import login_required, current_user
from routes.payments import usuario_tiene_modulo

conciliacion = Blueprint('conciliacion', __name__)

MISTRAL_API_KEY = "y3ShMpYFn7Spry3zB44epJu7FbIPgIfn"


def _requiere_modulo():
    if current_user.is_admin:
        return None
    if not usuario_tiene_modulo('conciliacion'):
        flash('Requieres el módulo Conciliación Bancaria para usar esta herramienta.', 'warning')
        return redirect(url_for('payments.ver_planes'))
    return None


@conciliacion.route('/')
@login_required
def index():
    r = _requiere_modulo()
    if r:
        return r
    return render_template('conciliacion/index.html')


@conciliacion.route('/procesar', methods=['POST'])
@login_required
def procesar():
    r = _requiere_modulo()
    if r:
        return {'error': 'Sin acceso'}, 403

    archivos = request.files.getlist('pdfs')
    diarios = request.form.getlist('diarios')  # uno por PDF

    if not archivos:
        return {'error': 'No se subieron archivos PDF'}, 400

    try:
        import pdfplumber
        from mistralai import Mistral
    except ImportError:
        return {'error': 'Faltan librerías: pdfplumber o mistralai'}, 500

    client = Mistral(api_key=MISTRAL_API_KEY)
    transacciones = []
    errores = []

    for i, (archivo, diario) in enumerate(zip(archivos, diarios)):
        if not archivo.filename.lower().endswith('.pdf'):
            continue
        diario = diario.strip() or 'Diario Bancario'
        try:
            texto = ''
            with pdfplumber.open(io.BytesIO(archivo.read())) as pdf:
                for page in pdf.pages:
                    texto += (page.extract_text() or '')

            prompt = (
                "Extrae TODAS las transacciones/movimientos de este estado de cuenta bancario. "
                "Responde ÚNICAMENTE con un JSON con esta estructura: "
                '{"transacciones": [{"fecha": "YYYY-MM-DD", "descripcion": "...", "monto": 0.00}]}. '
                "Los montos de gastos/débitos van negativos. "
                f"Texto del estado de cuenta:\n{texto[:25000]}"
            )

            resp = client.chat.complete(
                model="mistral-large-latest",
                messages=[{"role": "user", "content": prompt}]
            )
            contenido = resp.choices[0].message.content

            # Extraer JSON del contenido
            idx_start = contenido.find('{')
            idx_end = contenido.rfind('}')
            if idx_start != -1 and idx_end != -1:
                data = json.loads(contenido[idx_start:idx_end + 1])
                for t in data.get('transacciones', []):
                    try:
                        monto = float(t.get('monto', 0))
                    except (ValueError, TypeError):
                        monto = 0.0
                    transacciones.append({
                        'fecha': str(t.get('fecha', '')),
                        'descripcion': str(t.get('descripcion', '')),
                        'diario': diario,
                        'monto': round(monto, 2)
                    })
        except Exception as e:
            errores.append(f"{archivo.filename}: {str(e)}")

    transacciones.sort(key=lambda x: x.get('fecha', ''))

    return {
        'transacciones': transacciones,
        'errores': errores,
        'total': len(transacciones)
    }


@conciliacion.route('/exportar_excel', methods=['POST'])
@login_required
def exportar_excel():
    r = _requiere_modulo()
    if r:
        return {'error': 'Sin acceso'}, 403

    data = request.get_json(force=True)
    transacciones = data.get('transacciones', [])
    nombre_archivo = data.get('nombre_archivo', 'Importacion_Odoo').strip() or 'Importacion_Odoo'

    if not transacciones:
        return {'error': 'No hay transacciones para exportar'}, 400

    try:
        import xlsxwriter
        output = io.BytesIO()
        wb = xlsxwriter.Workbook(output)
        ws = wb.add_worksheet('Importacion_Odoo')

        fmt_head = wb.add_format({'bold': True, 'bg_color': '#007bff', 'font_color': 'white', 'border': 1})
        fmt_curr = wb.add_format({'num_format': '$#,##0.00'})
        fmt_date = wb.add_format({'num_format': 'yyyy-mm-dd'})

        headers = ['Date', 'Label', 'Journal', 'Amount']
        for i, h in enumerate(headers):
            ws.write(0, i, h, fmt_head)

        for row_i, t in enumerate(transacciones, 1):
            ws.write(row_i, 0, t.get('fecha', ''))
            ws.write(row_i, 1, t.get('descripcion', ''))
            ws.write(row_i, 2, t.get('diario', ''))
            try:
                ws.write(row_i, 3, float(t.get('monto', 0)), fmt_curr)
            except (ValueError, TypeError):
                ws.write(row_i, 3, 0.0, fmt_curr)

        ws.set_column(0, 0, 12)
        ws.set_column(1, 1, 50)
        ws.set_column(2, 2, 25)
        ws.set_column(3, 3, 14)

        wb.close()
        output.seek(0)

        return Response(
            output.getvalue(),
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            headers={'Content-Disposition': f'attachment; filename={nombre_archivo}.xlsx'}
        )
    except Exception as e:
        return {'error': str(e)}, 500
