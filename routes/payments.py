from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from models import db
from models.user import ModuloSuscrito, SolicitudAcceso, Usuario
from config import Config
from datetime import datetime, timedelta
import json
import os

payments = Blueprint('payments', __name__)

MODULOS = Config.MODULOS
DURACIONES = Config.DURACIONES
IVA = Config.IVA_RATE
UPLOAD_COMPROBANTES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'uploads', 'comprobantes')
if not os.path.exists(UPLOAD_COMPROBANTES):
    os.makedirs(UPLOAD_COMPROBANTES)


def get_modulos_activos(usuario_id):
    """Retorna lista de modulo_id activos para un usuario."""
    modulos = ModuloSuscrito.query.filter_by(usuario_id=usuario_id, estado='activo', verificado=True).all()
    return [m.modulo_id for m in modulos if m.esta_activo()]


def usuario_tiene_modulo(modulo_id, usuario=None):
    u = usuario or current_user
    if u.is_admin:
        return True
    activos = get_modulos_activos(u.id)
    # Catálogo siempre incluido si tiene facturas
    if modulo_id == 'catalogo' and 'facturas' in activos:
        return True
    return modulo_id in activos


@payments.route('/planes')
def ver_planes():
    modulos_activos = []
    solicitudes_pendientes = []
    if current_user.is_authenticated:
        modulos_activos = get_modulos_activos(current_user.id)
        solicitudes_pendientes = [s.modulos for s in SolicitudAcceso.query.filter_by(
            usuario_id=current_user.id, estado='pendiente').all()]
    return render_template('payments/planes.html',
                           modulos=MODULOS,
                           duraciones=DURACIONES,
                           modulos_activos=modulos_activos,
                           solicitudes_pendientes=solicitudes_pendientes,
                           config=Config)


@payments.route('/calcular_precio', methods=['POST'])
def calcular_precio():
    data = request.get_json()
    modulos_sel = data.get('modulos', [])
    duracion = int(data.get('duracion', 1))
    if duracion not in DURACIONES:
        duracion = 1

    subtotal_mensual = 0.0
    subtotal_unico = 0.0

    for mid in modulos_sel:
        if mid not in MODULOS:
            continue
        m = MODULOS[mid]
        if m['precio_unico']:
            subtotal_unico += m['precio']
        else:
            subtotal_mensual += m['precio']

    base_mensual_total = subtotal_mensual * duracion
    subtotal_antes_desc = base_mensual_total + subtotal_unico

    descuento_pct = DURACIONES[duracion]['descuento']
    aplica_descuento = descuento_pct > 0 and len([m for m in modulos_sel if not MODULOS.get(m, {}).get('precio_unico')]) >= 1
    descuento_monto = round(base_mensual_total * descuento_pct / 100, 2) if aplica_descuento else 0.0

    subtotal_final = round(subtotal_antes_desc - descuento_monto, 2)
    iva = round(subtotal_final * IVA, 2)
    total = round(subtotal_final + iva, 2)

    return jsonify({
        'subtotal_mensual': round(subtotal_mensual, 2),
        'subtotal_unico': round(subtotal_unico, 2),
        'subtotal_final': subtotal_final,
        'aplica_descuento': aplica_descuento,
        'descuento_pct': descuento_pct,
        'descuento': descuento_monto,
        'iva': iva,
        'total': total,
    })


@payments.route('/pagar_transferencia', methods=['POST'])
@login_required
def pagar_transferencia():
    modulos_sel = request.form.getlist('modulos')
    duracion = int(request.form.get('duracion', 1))
    comprobante = request.files.get('comprobante')

    if not modulos_sel:
        flash('Selecciona al menos un módulo.', 'warning')
        return redirect(url_for('payments.ver_planes'))

    if not comprobante or comprobante.filename == '':
        flash('Debes subir el comprobante de pago.', 'warning')
        return redirect(url_for('payments.ver_planes'))

    ext = comprobante.filename.rsplit('.', 1)[-1].lower()
    if ext not in ('jpg', 'jpeg', 'png', 'pdf'):
        flash('Formato de comprobante no válido. Usa JPG, PNG o PDF.', 'warning')
        return redirect(url_for('payments.ver_planes'))

    nombre_archivo = f"comp_{current_user.id}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.{ext}"
    ruta = os.path.join(UPLOAD_COMPROBANTES, nombre_archivo)
    comprobante.save(ruta)

    # Calcular monto
    subtotal_mensual = sum(MODULOS[m]['precio'] for m in modulos_sel if m in MODULOS and not MODULOS[m]['precio_unico'])
    subtotal_unico = sum(MODULOS[m]['precio'] for m in modulos_sel if m in MODULOS and MODULOS[m]['precio_unico'])
    base = subtotal_mensual * duracion + subtotal_unico
    desc_pct = DURACIONES.get(duracion, {}).get('descuento', 0)
    descuento = round(subtotal_mensual * duracion * desc_pct / 100, 2)
    subtotal = round(base - descuento, 2)
    iva = round(subtotal * IVA, 2)
    total = round(subtotal + iva, 2)

    solicitud = SolicitudAcceso(
        usuario_id=current_user.id,
        modulos=json.dumps(modulos_sel),
        duracion_meses=duracion,
        monto_total=total,
        comprobante_path=nombre_archivo,
        estado='pendiente',
    )
    db.session.add(solicitud)
    db.session.commit()

    flash('¡Comprobante enviado! El administrador revisará tu pago y activará los módulos en breve.', 'success')
    return redirect(url_for('payments.mis_modulos'))


@payments.route('/mis_modulos')
@login_required
def mis_modulos():
    modulos_db = ModuloSuscrito.query.filter_by(usuario_id=current_user.id).order_by(
        ModuloSuscrito.fecha_inicio.desc()).all()
    solicitudes = SolicitudAcceso.query.filter_by(usuario_id=current_user.id).order_by(
        SolicitudAcceso.fecha_solicitud.desc()).all()
    return render_template('payments/mis_modulos.html',
                           modulos_db=modulos_db,
                           solicitudes=solicitudes,
                           MODULOS=MODULOS)


# ─── Admin: aprobar solicitudes ──────────────────────────────────────────────

@payments.route('/admin/solicitudes')
@login_required
def admin_solicitudes():
    if not current_user.is_admin:
        flash('Acceso denegado.', 'danger')
        return redirect(url_for('dashboard'))
    solicitudes = SolicitudAcceso.query.order_by(SolicitudAcceso.fecha_solicitud.desc()).all()
    return render_template('payments/admin_solicitudes.html', solicitudes=solicitudes, MODULOS=MODULOS)


@payments.route('/admin/aprobar/<int:solicitud_id>', methods=['POST'])
@login_required
def admin_aprobar(solicitud_id):
    if not current_user.is_admin:
        flash('Acceso denegado.', 'danger')
        return redirect(url_for('dashboard'))

    solicitud = db.session.get(SolicitudAcceso, solicitud_id)
    if not solicitud or solicitud.estado != 'pendiente':
        flash('Solicitud no encontrada o ya procesada.', 'warning')
        return redirect(url_for('payments.admin_solicitudes'))

    modulos_lista = json.loads(solicitud.modulos or '[]')
    duracion = solicitud.duracion_meses or 1

    if not modulos_lista:
        flash('La solicitud no tiene módulos válidos.', 'danger')
        return redirect(url_for('payments.admin_solicitudes'))

    # VALIDAR TODOS los módulos ANTES de crear nada
    modulos_validos = []
    for mid in modulos_lista:
        if mid not in MODULOS:
            flash(f'⚠️ Módulo "{mid}" no existe en configuración. Solicitud cancelada.', 'danger')
            return redirect(url_for('payments.admin_solicitudes'))
        modulos_validos.append(mid)

    if len(modulos_validos) != len(modulos_lista):
        flash('Algunos módulos no son válidos.', 'danger')
        return redirect(url_for('payments.admin_solicitudes'))

    # Ahora sí, crear todos los módulos
    try:
        modulos_creados = 0
        for mid in modulos_validos:
            m_info = MODULOS[mid]
            es_unico = m_info.get('precio_unico', False)
            precio = float(m_info.get('precio', 0))
            iva = round(precio * IVA, 2)

            # Cancelar módulo anterior si existe y no es pago único
            if not es_unico:
                anterior = ModuloSuscrito.query.filter_by(
                    usuario_id=solicitud.usuario_id,
                    modulo_id=mid,
                    estado='activo'
                ).first()
                if anterior:
                    anterior.estado = 'cancelado'

            vencimiento = None if es_unico else datetime.utcnow() + timedelta(days=30 * duracion)
            nuevo = ModuloSuscrito(
                usuario_id=solicitud.usuario_id,
                modulo_id=mid,
                estado='activo',
                es_pago_unico=es_unico,
                precio_pagado=precio,
                iva_pagado=iva,
                duracion_meses=duracion,
                fecha_inicio=datetime.utcnow(),
                fecha_vencimiento=vencimiento,
                comprobante_path=solicitud.comprobante_path,
                verificado=True,
            )
            db.session.add(nuevo)
            modulos_creados += 1

        solicitud.estado = 'aprobado'
        solicitud.fecha_respuesta = datetime.utcnow()
        db.session.commit()
        flash(f'✅ Solicitud aprobada. Se activaron {modulos_creados} módulos.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'❌ Error al aprobar solicitud: {str(e)[:100]}', 'danger')
        print(f"Error aprobar solicitud {solicitud_id}: {e}")

    return redirect(url_for('payments.admin_solicitudes'))


@payments.route('/admin/rechazar/<int:solicitud_id>', methods=['POST'])
@login_required
def admin_rechazar(solicitud_id):
    if not current_user.is_admin:
        flash('Acceso denegado.', 'danger')
        return redirect(url_for('dashboard'))

    solicitud = db.session.get(SolicitudAcceso, solicitud_id)
    if solicitud:
        solicitud.estado = 'rechazado'
        solicitud.nota_admin = request.form.get('nota', '')
        solicitud.fecha_respuesta = datetime.utcnow()
        db.session.commit()
        flash('Solicitud rechazada.', 'info')
    return redirect(url_for('payments.admin_solicitudes'))


# ─── Compatibilidad hacia atrás ───────────────────────────────────────────────

@payments.route('/pagar/<plan_id>')
@login_required
def pagar(plan_id):
    flash('El sistema ahora usa módulos independientes. Selecciona los que necesitas.', 'info')
    return redirect(url_for('payments.ver_planes'))


@payments.route('/cancelar')
@login_required
def cancelar_suscripcion():
    flash('Para cancelar un módulo contacta al soporte.', 'info')
    return redirect(url_for('payments.mis_modulos'))


@payments.route('/renovar')
@login_required
def renovar():
    return redirect(url_for('payments.ver_planes'))
