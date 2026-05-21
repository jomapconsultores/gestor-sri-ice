from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from models import db
from models.user import Factura, Suscripcion
from services.xml_parser import parse_xml_factura
from datetime import datetime
import os

invoices = Blueprint('invoices', __name__)

UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)


def verificar_limite_facturas():
    if not current_user.tiene_suscripcion_activa():
        return False, "No tienes una suscripcion activa"
    suscripcion = current_user.suscripcion
    if suscripcion.plan_id == 'basico':
        if suscripcion.facturas_procesadas_mes >= 100:
            return False, "Has alcanzado el limite de 100 facturas este mes"
    return True, "OK"


@invoices.route('/cargar')
@login_required
def pagina_carga():
    puede, mensaje = verificar_limite_facturas()
    if not puede:
        flash(mensaje, 'warning')
    facturas = Factura.query.filter_by(usuario_id=current_user.id).order_by(Factura.fecha_procesamiento.desc()).limit(50).all()
    return render_template('invoices/cargar.html', facturas=facturas)


@invoices.route('/subir', methods=['POST'])
@login_required
def subir_facturas():
    puede, mensaje = verificar_limite_facturas()
    if not puede:
        flash(mensaje, 'danger')
        return redirect(url_for('invoices.pagina_carga'))
    if 'archivos' not in request.files:
        flash('No se seleccionaron archivos.', 'warning')
        return redirect(url_for('invoices.pagina_carga'))
    archivos = request.files.getlist('archivos')
    if not archivos or archivos[0].filename == '':
        flash('No se seleccionaron archivos.', 'warning')
        return redirect(url_for('invoices.pagina_carga'))
    procesadas = 0
    errores = 0
    duplicadas = 0
    for archivo in archivos:
        if not archivo.filename.endswith('.xml'):
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
                os.remove(ruta_temp)
                continue
            factura = Factura(
                usuario_id=current_user.id,
                clave_acceso=datos['clave_acceso'],
                ruc_emisor=datos['ruc'],
                razon_social_emisor='',
                ruc_comprador=datos['id_cliente'],
                razon_social_comprador=datos['razon_social_cliente'],
                fecha_emision=datetime.strptime(datos['fecha_emision'], '%d/%m/%Y').date() if datos['fecha_emision'] else None,
                numero_factura=datos['numero_factura'],
                importe_total=datos['importe_total'],
                base_ice=sum(p['base_ice'] for p in datos['productos']),
                valor_ice=sum(p['ice'] for p in datos['productos']),
                base_iva=sum(p['base_iva'] for p in datos['productos']),
                valor_iva=sum(p['iva'] for p in datos['productos']),
                xml_original=''
            )
            db.session.add(factura)
            suscripcion = current_user.suscripcion
            if suscripcion:
                suscripcion.facturas_procesadas_mes += 1
            procesadas += 1
        except Exception as e:
            print(f"Error: {e}")
            errores += 1
        finally:
            if os.path.exists(ruta_temp):
                os.remove(ruta_temp)
    db.session.commit()
    flash(f'{procesadas} facturas procesadas. Errores: {errores}. Duplicadas: {duplicadas}.', 'success')
    return redirect(url_for('invoices.pagina_carga'))


@invoices.route('/ver')
@login_required
def ver_facturas():
    facturas = Factura.query.filter_by(usuario_id=current_user.id).order_by(Factura.fecha_procesamiento.desc()).all()
    return render_template('invoices/ver.html', facturas=facturas)


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
    ).filter(Factura.usuario_id == current_user.id).group_by('anio', 'mes').order_by('anio', 'mes').all()
    return render_template('invoices/resumen.html', resumen=resumen)