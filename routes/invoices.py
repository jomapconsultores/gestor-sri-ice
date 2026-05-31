from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from models import db
from models.user import Factura
from services.xml_parser import parse_xml_factura
from datetime import datetime
import os

invoices = Blueprint('invoices', __name__)

UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)


def _tiene_modulo(modulo_id):
    from routes.payments import get_modulos_activos
    if current_user.is_admin:
        return True
    return modulo_id in get_modulos_activos(current_user.id)


# ─── GASTOS (facturas de compra) ─────────────────────────────────────────────

@invoices.route('/cargar')
@login_required
def pagina_carga():
    """Página para subir facturas de GASTOS (compras/proveedores)."""
    if not _tiene_modulo('facturas_gasto'):
        flash('Necesitas el módulo "Facturas de Gasto" para subir facturas de gasto.', 'warning')
        return redirect(url_for('payments.ver_planes'))
    facturas = Factura.query.filter_by(
        usuario_id=current_user.id, tipo='gasto'
    ).order_by(Factura.fecha_procesamiento.desc()).limit(50).all()
    return render_template('invoices/cargar.html', facturas=facturas, tipo='gasto')


@invoices.route('/subir', methods=['POST'])
@login_required
def subir_facturas():
    tipo = request.form.get('tipo', 'gasto')
    modulo_requerido = 'facturas_gasto' if tipo == 'gasto' else 'facturas_ingreso'
    if not _tiene_modulo(modulo_requerido):
        flash('Módulo no activo.', 'danger')
        return redirect(url_for('invoices.pagina_carga' if tipo == 'gasto' else 'invoices.cargar_ingresos'))

    archivos = request.files.getlist('archivos')
    if not archivos or archivos[0].filename == '':
        flash('No se seleccionaron archivos.', 'warning')
        return redirect(url_for('invoices.pagina_carga' if tipo == 'gasto' else 'invoices.cargar_ingresos'))

    procesadas = errores = duplicadas = 0
    for archivo in archivos:
        if not archivo.filename.lower().endswith('.xml'):
            continue
        ruta_temp = os.path.join(UPLOAD_FOLDER, archivo.filename)
        archivo.save(ruta_temp)
        try:
            datos = parse_xml_factura(ruta_temp)
            if datos is None:
                errores += 1
                continue
            existente = Factura.query.filter_by(clave_acceso=datos['clave_acceso']).first()
            if existente:
                duplicadas += 1
                continue
            descuento_total = datos.get('descuento_total', 0)
            factura = Factura(
                usuario_id=current_user.id,
                clave_acceso=datos['clave_acceso'],
                ruc_emisor=datos.get('ruc', ''),
                razon_social_emisor=datos.get('razon_social_emisor', ''),
                ruc_comprador=datos.get('id_cliente', ''),
                razon_social_comprador=datos.get('razon_social_cliente', ''),
                fecha_emision=datetime.strptime(datos['fecha_emision'], '%d/%m/%Y').date()
                    if datos.get('fecha_emision') else None,
                numero_factura=datos.get('numero_factura', ''),
                importe_total=datos.get('importe_total', 0),
                base_ice=sum(p.get('base_ice', 0) for p in datos.get('productos', [])),
                valor_ice=sum(p.get('ice', 0) for p in datos.get('productos', [])),
                base_iva=sum(p.get('base_iva', 0) for p in datos.get('productos', [])),
                valor_iva=sum(p.get('iva', 0) for p in datos.get('productos', [])),
                xml_original='',
                tipo=tipo,
                descuento_total=descuento_total,
                tiene_descuento=descuento_total > 0,
            )
            db.session.add(factura)
            procesadas += 1
        except Exception as e:
            print(f"Error procesando {archivo.filename}: {e}")
            errores += 1
        finally:
            if os.path.exists(ruta_temp):
                os.remove(ruta_temp)

    db.session.commit()
    flash(f'{procesadas} factura(s) procesada(s). Duplicadas: {duplicadas}. Errores: {errores}.', 'success')

    if tipo == 'ingreso':
        return redirect(url_for('invoices.cargar_ingresos'))
    return redirect(url_for('invoices.pagina_carga'))


# ─── INGRESOS (facturas de venta) ────────────────────────────────────────────

@invoices.route('/ingresos')
@login_required
def cargar_ingresos():
    """Página para subir facturas de INGRESOS (ventas propias)."""
    if not _tiene_modulo('facturas_ingreso'):
        flash('Necesitas el módulo "Facturas de Ingreso" para subir facturas de ingreso.', 'warning')
        return redirect(url_for('payments.ver_planes'))
    facturas = Factura.query.filter_by(
        usuario_id=current_user.id, tipo='ingreso'
    ).order_by(Factura.fecha_procesamiento.desc()).limit(50).all()
    return render_template('invoices/cargar_ingresos.html', facturas=facturas, tipo='ingreso')


@invoices.route('/reporte_ingresos')
@login_required
def reporte_ingresos():
    """Reporte de facturas de ingreso con totales ICE/IVA."""
    if not _tiene_modulo('facturas_ingreso'):
        flash('Módulo no activo.', 'warning')
        return redirect(url_for('payments.ver_planes'))
    from sqlalchemy import func, extract
    facturas = Factura.query.filter_by(
        usuario_id=current_user.id, tipo='ingreso'
    ).order_by(Factura.fecha_emision.desc()).all()

    resumen = db.session.query(
        extract('year', Factura.fecha_emision).label('anio'),
        extract('month', Factura.fecha_emision).label('mes'),
        func.count(Factura.id).label('cantidad'),
        func.sum(Factura.importe_total).label('total'),
        func.sum(Factura.base_ice).label('base_ice'),
        func.sum(Factura.valor_ice).label('ice'),
        func.sum(Factura.base_iva).label('base_iva'),
        func.sum(Factura.valor_iva).label('iva'),
    ).filter_by(usuario_id=current_user.id, tipo='ingreso')\
     .group_by('anio', 'mes').order_by('anio', 'mes').all()

    tiene_anexos = _tiene_modulo('anexos')
    return render_template('invoices/reporte_ingresos.html',
                           facturas=facturas,
                           resumen=resumen,
                           tiene_anexos=tiene_anexos)


# ─── COMUNES ─────────────────────────────────────────────────────────────────

@invoices.route('/ver')
@login_required
def ver_facturas():
    tipo = request.args.get('tipo', '')
    q = Factura.query.filter_by(usuario_id=current_user.id)
    if tipo:
        q = q.filter_by(tipo=tipo)
    facturas = q.order_by(Factura.fecha_procesamiento.desc()).all()
    return render_template('invoices/ver.html', facturas=facturas, tipo=tipo)


@invoices.route('/resumen')
@login_required
def resumen():
    from sqlalchemy import func, extract
    resumen = db.session.query(
        extract('year', Factura.fecha_emision).label('anio'),
        extract('month', Factura.fecha_emision).label('mes'),
        func.count(Factura.id).label('cantidad'),
        func.sum(Factura.importe_total).label('total'),
        func.sum(Factura.base_ice).label('base_ice'),
        func.sum(Factura.valor_ice).label('ice'),
        func.sum(Factura.base_iva).label('base_iva'),
        func.sum(Factura.valor_iva).label('iva')
    ).filter(Factura.usuario_id == current_user.id)\
     .group_by('anio', 'mes').order_by('anio', 'mes').all()
    return render_template('invoices/resumen.html', resumen=resumen)
