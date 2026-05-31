from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from models import db
from models.user import Usuario, Pago, FacturaEmitida, ModuloSuscrito, SolicitudAcceso
from config import Config
from datetime import datetime
from sqlalchemy import func, extract
import json

admin_reports = Blueprint('admin_reports', __name__)

MESES = ['', 'Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun',
         'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']


def requiere_admin():
    if not current_user.is_admin:
        flash('Acceso denegado.', 'danger')
        return False
    return True


@admin_reports.route('/reportes')
@login_required
def reportes():
    if not requiere_admin():
        return redirect(url_for('dashboard'))

    # Recaudación por usuario (basada en ModuloSuscrito verificados)
    recaudacion_usuarios = db.session.query(
        Usuario.nombre,
        Usuario.email,
        func.sum(ModuloSuscrito.precio_pagado).label('subtotal'),
        func.sum(ModuloSuscrito.iva_pagado).label('iva_total'),
        func.count(ModuloSuscrito.id).label('cantidad')
    ).join(ModuloSuscrito, ModuloSuscrito.usuario_id == Usuario.id)\
     .filter(ModuloSuscrito.verificado == True, ModuloSuscrito.estado == 'activo')\
     .group_by(Usuario.id).all()

    # Recaudación por módulo/producto
    recaudacion_modulos = db.session.query(
        ModuloSuscrito.modulo_id,
        func.sum(ModuloSuscrito.precio_pagado).label('subtotal'),
        func.sum(ModuloSuscrito.iva_pagado).label('iva_total'),
        func.count(ModuloSuscrito.id).label('cantidad')
    ).filter(ModuloSuscrito.verificado == True, ModuloSuscrito.estado == 'activo')\
     .group_by(ModuloSuscrito.modulo_id).all()

    # Recaudación mensual (por fecha de inicio del módulo)
    recaudacion_mensual = db.session.query(
        extract('year', ModuloSuscrito.fecha_inicio).label('anio'),
        extract('month', ModuloSuscrito.fecha_inicio).label('mes'),
        func.sum(ModuloSuscrito.precio_pagado + ModuloSuscrito.iva_pagado).label('total'),
        func.count(ModuloSuscrito.id).label('cantidad')
    ).filter(ModuloSuscrito.verificado == True)\
     .group_by('anio', 'mes').order_by('anio', 'mes').all()

    # Recaudación por año
    recaudacion_anual = db.session.query(
        extract('year', ModuloSuscrito.fecha_inicio).label('anio'),
        func.sum(ModuloSuscrito.precio_pagado + ModuloSuscrito.iva_pagado).label('total'),
        func.count(ModuloSuscrito.id).label('cantidad')
    ).filter(ModuloSuscrito.verificado == True)\
     .group_by('anio').order_by('anio').all()

    # Facturas pendientes de emisión
    facturas_pendientes = FacturaEmitida.query\
        .filter_by(estado='pendiente')\
        .order_by(FacturaEmitida.fecha_emision).all()

    # Total recaudado (precio + IVA)
    total_recaudado = db.session.query(
        func.sum(ModuloSuscrito.precio_pagado + ModuloSuscrito.iva_pagado)
    ).filter(ModuloSuscrito.verificado == True).scalar() or 0

    # Solicitudes pendientes de comprobante
    solicitudes_pendientes = SolicitudAcceso.query\
        .filter_by(estado='pendiente')\
        .order_by(SolicitudAcceso.fecha_solicitud.desc()).all()

    usuarios = Usuario.query.order_by(Usuario.nombre).all()

    return render_template('admin/reportes.html',
                           recaudacion_usuarios=recaudacion_usuarios,
                           recaudacion_modulos=recaudacion_modulos,
                           recaudacion_mensual=recaudacion_mensual,
                           recaudacion_anual=recaudacion_anual,
                           facturas_pendientes=facturas_pendientes,
                           solicitudes_pendientes=solicitudes_pendientes,
                           total_recaudado=total_recaudado,
                           usuarios=usuarios,
                           MODULOS=Config.MODULOS,
                           MESES=MESES)


@admin_reports.route('/marcar_factura/<int:factura_id>', methods=['POST'])
@login_required
def marcar_factura(factura_id):
    if not requiere_admin():
        return redirect(url_for('dashboard'))
    factura = db.session.get(FacturaEmitida, factura_id)
    if factura:
        factura.estado = 'emitida'
        factura.fecha_pago = datetime.utcnow()
        db.session.commit()
        flash(f'Factura #{factura.numero_factura} marcada como emitida.', 'success')
    return redirect(url_for('admin_reports.reportes'))


@admin_reports.route('/generar_factura', methods=['POST'])
@login_required
def generar_factura():
    if not requiere_admin():
        return redirect(url_for('dashboard'))
    try:
        usuario_id = int(request.form.get('usuario_id'))
        monto = float(request.form.get('monto'))
        if monto <= 0:
            flash('El monto debe ser mayor a 0.', 'warning')
            return redirect(url_for('admin_reports.reportes'))
        numero = f"F-{datetime.utcnow().strftime('%Y%m%d')}-{usuario_id}"
        factura = FacturaEmitida(
            usuario_id=usuario_id,
            monto=monto,
            fecha_emision=datetime.utcnow().date(),
            estado='pendiente',
            numero_factura=numero
        )
        db.session.add(factura)
        db.session.commit()
        flash(f'Factura {numero} generada para emisión.', 'success')
    except (ValueError, TypeError):
        flash('Datos inválidos.', 'danger')
    return redirect(url_for('admin_reports.reportes'))


@admin_reports.route('/ver_usuario/<int:usuario_id>')
@login_required
def ver_usuario(usuario_id):
    """Admin puede ver los datos detallados de cualquier usuario."""
    if not requiere_admin():
        return redirect(url_for('dashboard'))
    usuario = db.session.get(Usuario, usuario_id)
    if not usuario:
        flash('Usuario no encontrado.', 'danger')
        return redirect(url_for('admin_reports.reportes'))
    modulos = ModuloSuscrito.query.filter_by(usuario_id=usuario_id).order_by(
        ModuloSuscrito.fecha_inicio.desc()).all()
    solicitudes = SolicitudAcceso.query.filter_by(usuario_id=usuario_id).order_by(
        SolicitudAcceso.fecha_solicitud.desc()).all()
    return render_template('admin/ver_usuario.html',
                           usuario=usuario,
                           modulos=modulos,
                           solicitudes=solicitudes,
                           MODULOS=Config.MODULOS)


# ── Gestión de clientes ────────────────────────────────────────────────────

@admin_reports.route('/clientes')
@login_required
def clientes():
    if not requiere_admin():
        return redirect(url_for('dashboard'))
    usuarios = Usuario.query.filter_by(is_admin=False).order_by(Usuario.nombre).all()
    return render_template('admin/clientes.html', usuarios=usuarios, MODULOS=Config.MODULOS)


@admin_reports.route('/cliente/<int:uid>')
@login_required
def ver_cliente(uid):
    if not requiere_admin():
        return redirect(url_for('dashboard'))
    from models.user import Factura
    usuario = db.session.get(Usuario, uid)
    if not usuario:
        flash('Usuario no encontrado', 'danger')
        return redirect(url_for('admin_reports.clientes'))
    modulos = ModuloSuscrito.query.filter_by(usuario_id=uid).order_by(
        ModuloSuscrito.fecha_inicio.desc()).all()
    facturas = Factura.query.filter_by(usuario_id=uid).order_by(
        Factura.fecha_procesamiento.desc()).limit(20).all()
    solicitudes = SolicitudAcceso.query.filter_by(usuario_id=uid).order_by(
        SolicitudAcceso.fecha_solicitud.desc()).all()
    return render_template('admin/ver_cliente.html',
                           usuario=usuario, modulos=modulos,
                           facturas=facturas, solicitudes=solicitudes,
                           MODULOS=Config.MODULOS)


@admin_reports.route('/cliente/<int:uid>/editar', methods=['POST'])
@login_required
def editar_cliente(uid):
    if not requiere_admin():
        return redirect(url_for('dashboard'))
    usuario = db.session.get(Usuario, uid)
    if not usuario:
        flash('No encontrado', 'danger')
        return redirect(url_for('admin_reports.clientes'))
    usuario.nombre = request.form.get('nombre', usuario.nombre)
    usuario.email = request.form.get('email', usuario.email)
    usuario.empresa = request.form.get('empresa', usuario.empresa)
    usuario.ruc = request.form.get('ruc', usuario.ruc)
    activo = request.form.get('activo')
    usuario.activo = activo == '1'
    nueva_pass = request.form.get('nueva_password', '').strip()
    if nueva_pass:
        usuario.set_password(nueva_pass)
    db.session.commit()
    flash(f'Cliente {usuario.nombre} actualizado.', 'success')
    return redirect(url_for('admin_reports.ver_cliente', uid=uid))


@admin_reports.route('/cliente/<int:uid>/agregar_modulo', methods=['POST'])
@login_required
def agregar_modulo_cliente(uid):
    if not requiere_admin():
        return redirect(url_for('dashboard'))
    from datetime import timedelta
    modulo_id = request.form.get('modulo_id')
    duracion = int(request.form.get('duracion', 1))
    if modulo_id not in Config.MODULOS:
        flash('Módulo inválido', 'danger')
        return redirect(url_for('admin_reports.ver_cliente', uid=uid))
    m = Config.MODULOS[modulo_id]
    es_unico = m['precio_unico']
    vencimiento = None if es_unico else datetime.utcnow() + timedelta(days=30 * duracion)
    nuevo = ModuloSuscrito(
        usuario_id=uid, modulo_id=modulo_id, estado='activo',
        es_pago_unico=es_unico, precio_pagado=m['precio'],
        iva_pagado=round(m['precio'] * 0.15, 2),
        duracion_meses=duracion, fecha_inicio=datetime.utcnow(),
        fecha_vencimiento=vencimiento, verificado=True
    )
    db.session.add(nuevo)
    db.session.commit()
    flash(f'Módulo {m["nombre"]} activado para el cliente.', 'success')
    return redirect(url_for('admin_reports.ver_cliente', uid=uid))


@admin_reports.route('/cliente/<int:uid>/revocar_modulo/<int:mid>', methods=['POST'])
@login_required
def revocar_modulo_cliente(uid, mid):
    if not requiere_admin():
        return redirect(url_for('dashboard'))
    m = db.session.get(ModuloSuscrito, mid)
    if m and m.usuario_id == uid:
        m.estado = 'cancelado'
        db.session.commit()
        flash('Módulo revocado.', 'info')
    return redirect(url_for('admin_reports.ver_cliente', uid=uid))
