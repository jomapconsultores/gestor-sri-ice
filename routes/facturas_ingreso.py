"""Módulo: Facturas de Ingreso - Procesa XMLs de facturas de venta"""

from flask import Blueprint, render_template, request, Response, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from routes.payments import usuario_tiene_modulo
from models import db
from models.user import Factura
from services.xml_parser import parse_xml_factura
import tempfile
import os
import io
from datetime import datetime

try:
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment
    OPENPYXL_AVAILABLE = True
except ImportError:
    OPENPYXL_AVAILABLE = False

facturas_ingreso = Blueprint('facturas_ingreso', __name__)


def _requiere():
    """Verifica si el usuario tiene el módulo Facturas de Ingreso."""
    if current_user.is_admin:
        return None
    if not usuario_tiene_modulo('facturas_ingreso'):
        flash('Requieres el módulo Facturas de Ingreso ($15/mes) para acceder.', 'warning')
        return redirect(url_for('payments.ver_planes'))
    return None


@facturas_ingreso.route('/')
@login_required
def index():
    """Página principal del módulo Facturas de Ingreso."""
    r = _requiere()
    if r:
        return r

    # Listar últimas facturas procesadas del usuario
    facturas = Factura.query.filter_by(
        usuario_id=current_user.id,
        tipo='ingreso'
    ).order_by(Factura.fecha_procesamiento.desc()).limit(50).all()

    resumen = db.session.query(
        db.func.count(Factura.id).label('cantidad'),
        db.func.sum(Factura.importe_total).label('total_ventas'),
        db.func.sum(Factura.valor_ice).label('total_ice'),
        db.func.sum(Factura.valor_iva).label('total_iva'),
    ).filter_by(usuario_id=current_user.id, tipo='ingreso').first()

    return render_template('facturas_ingreso/index.html',
                           facturas=facturas,
                           resumen=resumen)


@facturas_ingreso.route('/procesar', methods=['POST'])
@login_required
def procesar():
    """Procesa múltiples XMLs de facturas de ingreso."""
    r = _requiere()
    if r:
        return jsonify({'error': 'Sin acceso'}), 403

    try:
        if 'archivos' not in request.files:
            return jsonify({'error': 'No se enviaron archivos'}), 400

        archivos = request.files.getlist('archivos')
        resultados = {'exitosas': 0, 'errores': 0, 'detalles': []}

        for archivo in archivos:
            if not archivo.filename.endswith('.xml'):
                resultados['errores'] += 1
                resultados['detalles'].append({'archivo': archivo.filename, 'error': 'No es XML'})
                continue

            try:
                # Guardar temporalmente
                with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.xml') as tmp:
                    archivo.save(tmp.name)
                    temp_path = tmp.name

                # Parsear
                datos = parse_xml_factura(temp_path)
                os.unlink(temp_path)

                if not datos:
                    resultados['errores'] += 1
                    resultados['detalles'].append({'archivo': archivo.filename, 'error': 'No se pudo parsear'})
                    continue

                # Verificar si ya existe
                factura_existente = Factura.query.filter_by(
                    usuario_id=current_user.id,
                    clave_acceso=datos.get('clave_acceso', '')
                ).first()

                if factura_existente:
                    resultados['detalles'].append({'archivo': archivo.filename, 'estado': 'Ya existe'})
                    continue

                # Guardar en BD
                factura = Factura(
                    usuario_id=current_user.id,
                    clave_acceso=datos.get('clave_acceso', ''),
                    ruc_emisor=datos.get('ruc_emisor', ''),
                    razon_social_emisor=datos.get('razon_social_emisor', ''),
                    ruc_comprador=datos.get('ruc_comprador', ''),
                    razon_social_comprador=datos.get('razon_social_comprador', ''),
                    fecha_emision=datos.get('fecha_emision'),
                    numero_factura=datos.get('numero_factura', ''),
                    importe_total=datos.get('total', 0),
                    base_ice=datos.get('base_ice', 0),
                    valor_ice=datos.get('ice', 0),
                    base_iva=datos.get('base_iva', 0),
                    valor_iva=datos.get('iva', 0),
                    xml_original=datos.get('xml_raw', ''),
                    tipo='ingreso',
                )
                db.session.add(factura)
                db.session.commit()

                resultados['exitosas'] += 1
                resultados['detalles'].append({
                    'archivo': archivo.filename,
                    'estado': 'Procesada',
                    'total': float(datos.get('total', 0))
                })

            except Exception as e:
                resultados['errores'] += 1
                resultados['detalles'].append({'archivo': archivo.filename, 'error': str(e)})

        return jsonify(resultados)

    except Exception as e:
        return jsonify({'error': str(e)}), 400


@facturas_ingreso.route('/exportar_excel', methods=['POST'])
@login_required
def exportar_excel():
    """Exporta facturas a Excel (solo valores)."""
    r = _requiere()
    if r:
        return r

    if not OPENPYXL_AVAILABLE:
        flash('Excel no disponible.', 'danger')
        return redirect(url_for('facturas_ingreso.index'))

    try:
        facturas = Factura.query.filter_by(
            usuario_id=current_user.id,
            tipo='ingreso'
        ).order_by(Factura.fecha_emision.desc()).all()

        wb = Workbook()
        ws = wb.active
        ws.title = 'Ingresos'

        # Headers
        headers = ['Fecha', 'N° Factura', 'RUC Emisor', 'Razón Social', 'Total Venta', 'Base ICE', 'ICE', 'Base IVA', 'IVA']
        ws.append(headers)

        header_fill = PatternFill(start_color='0D1B2E', end_color='0D1B2E', fill_type='solid')
        header_font = Font(bold=True, color='FFFFFF')

        for col in ws[1]:
            col.fill = header_fill
            col.font = header_font

        # Datos
        for f in facturas:
            ws.append([
                f.fecha_emision.strftime('%Y-%m-%d') if f.fecha_emision else '',
                f.numero_factura or '',
                f.ruc_emisor or '',
                f.razon_social_emisor or '',
                float(f.importe_total or 0),
                float(f.base_ice or 0),
                float(f.valor_ice or 0),
                float(f.base_iva or 0),
                float(f.valor_iva or 0),
            ])

        # Totales
        ws.append(['TOTALES', '', '', ''] + [
            sum(float(f.importe_total or 0) for f in facturas),
            sum(float(f.base_ice or 0) for f in facturas),
            sum(float(f.valor_ice or 0) for f in facturas),
            sum(float(f.base_iva or 0) for f in facturas),
            sum(float(f.valor_iva or 0) for f in facturas),
        ])

        output = io.BytesIO()
        wb.save(output)
        output.seek(0)

        return Response(output.getvalue(),
                       mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                       headers={'Content-Disposition': 'attachment; filename=Facturas_Ingreso.xlsx'})

    except Exception as e:
        flash(f'Error al generar Excel: {str(e)}', 'danger')
        return redirect(url_for('facturas_ingreso.index'))
