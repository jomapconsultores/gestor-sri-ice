from flask import Blueprint, render_template, redirect, url_for, flash, request, g
from flask_login import login_required, current_user
from models import db
from models.user import Usuario, OrdenTrabajo, ItemOrdenTrabajo
from datetime import datetime

ordenes = Blueprint('ordenes', __name__)

TIPOS_SERVICIO = [
    ('declaracion_iva',        'Declaración IVA',           'bi-file-earmark-text',    '#1e40af'),
    ('declaracion_ice',        'Declaración ICE',           'bi-fire',                  '#7c3aed'),
    ('anexo_ice',              'Anexo ICE',                  'bi-file-earmark-code',    '#0369a1'),
    ('anexo_pvp',              'Anexo PVP',                  'bi-file-earmark-code',    '#0891b2'),
    ('calculo_ice_simple',     'Cálculo ICE Simple',         'bi-calculator',           '#059669'),
    ('calculo_ice_multiple',   'Cálculo ICE Múltiple',       'bi-calculator-fill',      '#065f46'),
    ('retenciones',            'Retenciones',                'bi-file-earmark-minus',   '#b45309'),
    ('ats',                    'ATS',                        'bi-table',                '#166534'),
    ('conciliacion',           'Conciliación Bancaria',      'bi-bank',                 '#5b21b6'),
    ('otro',                   'Otro servicio',              'bi-wrench',               '#64748b'),
]
TIPOS_MAP = {t[0]: t for t in TIPOS_SERVICIO}


def solo_admin():
    if current_user.is_admin:
        return True
    if getattr(g, 'es_impersonacion', False) and getattr(g, 'admin_original', None):
        return True
    flash('Acceso exclusivo del administrador.', 'danger')
    return False


def _siguiente_numero():
    anio = datetime.utcnow().year
    ultimo = OrdenTrabajo.query.filter(
        OrdenTrabajo.numero.like(f'OT-{anio}-%')
    ).order_by(OrdenTrabajo.id.desc()).first()
    if ultimo and ultimo.numero:
        try:
            n = int(ultimo.numero.split('-')[-1]) + 1
        except ValueError:
            n = 1
    else:
        n = 1
    return f'OT-{anio}-{n:03d}'


# ── Lista de órdenes ──────────────────────────────────────────────────────────

@ordenes.route('/')
@login_required
def lista():
    if not solo_admin():
        return redirect(url_for('dashboard'))
    ords = OrdenTrabajo.query.order_by(OrdenTrabajo.fecha_creacion.desc()).all()
    # Totales resumen
    total_pendiente = sum(float(o.total or 0) for o in ords if o.estado in ('borrador', 'completada'))
    total_facturado = sum(float(o.total or 0) for o in ords if o.estado == 'facturada')
    total_cobrado   = sum(float(o.total or 0) for o in ords if o.estado == 'pagada')
    return render_template('admin/ordenes/lista.html',
                           ordenes=ords,
                           total_pendiente=total_pendiente,
                           total_facturado=total_facturado,
                           total_cobrado=total_cobrado,
                           TIPOS_MAP=TIPOS_MAP)


# ── Nueva orden ───────────────────────────────────────────────────────────────

@ordenes.route('/nueva', methods=['GET', 'POST'])
@login_required
def nueva():
    if not solo_admin():
        return redirect(url_for('dashboard'))

    clientes = Usuario.query.filter_by(is_admin=False, activo=True).order_by(Usuario.nombre).all()

    if request.method == 'POST':
        usuario_id_raw = request.form.get('usuario_id', '').strip()
        cliente_nombre = request.form.get('cliente_nombre', '').strip()
        cliente_ruc    = request.form.get('cliente_ruc', '').strip()
        cliente_email  = request.form.get('cliente_email', '').strip()
        cliente_empresa = request.form.get('cliente_empresa', '').strip()
        notas          = request.form.get('notas', '').strip() or None
        aplica_iva     = request.form.get('aplica_iva') == '1'

        # Si seleccionó un cliente del sistema, prellenar desde su perfil
        usuario_id = None
        if usuario_id_raw:
            try:
                usuario_id = int(usuario_id_raw)
                u = db.session.get(Usuario, usuario_id)
                if u:
                    if not cliente_nombre:
                        cliente_nombre = u.nombre
                    if not cliente_ruc:
                        cliente_ruc = u.ruc or ''
                    if not cliente_email:
                        cliente_email = u.email
                    if not cliente_empresa:
                        cliente_empresa = u.empresa or ''
            except (ValueError, TypeError):
                usuario_id = None

        if not cliente_nombre:
            flash('El nombre del cliente es obligatorio.', 'danger')
            return render_template('admin/ordenes/nueva.html', clientes=clientes,
                                   form=request.form)

        orden = OrdenTrabajo(
            usuario_id=usuario_id,
            cliente_nombre=cliente_nombre,
            cliente_ruc=cliente_ruc,
            cliente_email=cliente_email,
            cliente_empresa=cliente_empresa,
            numero=_siguiente_numero(),
            notas=notas,
            aplica_iva=aplica_iva,
            estado='borrador',
        )
        db.session.add(orden)
        db.session.commit()
        flash(f'Orden {orden.numero} creada. Ahora agrega los servicios realizados.', 'success')
        return redirect(url_for('ordenes.detalle', oid=orden.id))

    # Pre-llenar si viene de la ficha de un cliente
    uid_pre = request.args.get('uid')
    form_pre = {}
    if uid_pre:
        try:
            u = db.session.get(Usuario, int(uid_pre))
            if u:
                form_pre = {'usuario_id': u.id, 'cliente_nombre': u.nombre,
                            'cliente_ruc': u.ruc or '', 'cliente_email': u.email,
                            'cliente_empresa': u.empresa or ''}
        except (ValueError, TypeError):
            pass

    return render_template('admin/ordenes/nueva.html', clientes=clientes, form=form_pre)


# ── Detalle / edición de orden ────────────────────────────────────────────────

@ordenes.route('/<int:oid>')
@login_required
def detalle(oid):
    if not solo_admin():
        return redirect(url_for('dashboard'))
    orden = db.session.get(OrdenTrabajo, oid)
    if not orden:
        flash('Orden no encontrada.', 'danger')
        return redirect(url_for('ordenes.lista'))
    return render_template('admin/ordenes/detalle.html',
                           orden=orden,
                           TIPOS_SERVICIO=TIPOS_SERVICIO,
                           TIPOS_MAP=TIPOS_MAP)


# ── Agregar ítem ──────────────────────────────────────────────────────────────

@ordenes.route('/<int:oid>/agregar_item', methods=['POST'])
@login_required
def agregar_item(oid):
    if not solo_admin():
        return redirect(url_for('dashboard'))
    orden = db.session.get(OrdenTrabajo, oid)
    if not orden:
        flash('Orden no encontrada.', 'danger')
        return redirect(url_for('ordenes.lista'))
    if orden.estado == 'pagada':
        flash('No se puede editar una orden ya pagada.', 'warning')
        return redirect(url_for('ordenes.detalle', oid=oid))

    descripcion     = request.form.get('descripcion', '').strip()
    tipo_servicio   = request.form.get('tipo_servicio', 'otro')
    periodo_mes     = request.form.get('periodo_mes', '').strip() or None
    periodo_anio    = request.form.get('periodo_anio', '').strip() or None
    notas_item      = request.form.get('notas_item', '').strip() or None
    try:
        cantidad        = float(request.form.get('cantidad', 1))
        precio_unitario = float(request.form.get('precio_unitario', 0))
    except (ValueError, TypeError):
        cantidad, precio_unitario = 1, 0

    if not descripcion:
        flash('La descripción del servicio es obligatoria.', 'danger')
        return redirect(url_for('ordenes.detalle', oid=oid))

    subtotal = round(cantidad * precio_unitario, 2)
    item = ItemOrdenTrabajo(
        orden_id=oid,
        descripcion=descripcion,
        tipo_servicio=tipo_servicio if tipo_servicio in TIPOS_MAP else 'otro',
        periodo_mes=periodo_mes,
        periodo_anio=periodo_anio,
        cantidad=cantidad,
        precio_unitario=precio_unitario,
        subtotal=subtotal,
        notas=notas_item,
    )
    db.session.add(item)
    orden.recalcular_totales()
    db.session.commit()
    flash(f'Servicio "{descripcion}" agregado.', 'success')
    return redirect(url_for('ordenes.detalle', oid=oid))


# ── Eliminar ítem ─────────────────────────────────────────────────────────────

@ordenes.route('/<int:oid>/eliminar_item/<int:iid>', methods=['POST'])
@login_required
def eliminar_item(oid, iid):
    if not solo_admin():
        return redirect(url_for('dashboard'))
    item = db.session.get(ItemOrdenTrabajo, iid)
    if item and item.orden_id == oid:
        db.session.delete(item)
        orden = db.session.get(OrdenTrabajo, oid)
        if orden:
            orden.recalcular_totales()
        db.session.commit()
        flash('Servicio eliminado.', 'info')
    return redirect(url_for('ordenes.detalle', oid=oid))


# ── Cambiar estado ────────────────────────────────────────────────────────────

@ordenes.route('/<int:oid>/estado', methods=['POST'])
@login_required
def cambiar_estado(oid):
    if not solo_admin():
        return redirect(url_for('dashboard'))
    orden = db.session.get(OrdenTrabajo, oid)
    if not orden:
        return redirect(url_for('ordenes.lista'))
    nuevo = request.form.get('estado')
    estados_validos = ('borrador', 'completada', 'facturada', 'pagada')
    if nuevo in estados_validos:
        orden.estado = nuevo
        if nuevo == 'completada' and not orden.fecha_completada:
            orden.fecha_completada = datetime.utcnow()
        db.session.commit()
        flash(f'Orden actualizada a "{nuevo}".', 'success')
    return redirect(url_for('ordenes.detalle', oid=oid))


# ── Eliminar orden (solo borrador) ────────────────────────────────────────────

@ordenes.route('/<int:oid>/eliminar', methods=['POST'])
@login_required
def eliminar_orden(oid):
    if not solo_admin():
        return redirect(url_for('dashboard'))
    orden = db.session.get(OrdenTrabajo, oid)
    if orden and orden.estado == 'borrador':
        db.session.delete(orden)
        db.session.commit()
        flash('Orden eliminada.', 'info')
    else:
        flash('Solo se pueden eliminar órdenes en estado Borrador.', 'warning')
    return redirect(url_for('ordenes.lista'))


# ── Reporte / Factura imprimible ──────────────────────────────────────────────

@ordenes.route('/<int:oid>/reporte')
@login_required
def reporte(oid):
    if not solo_admin():
        return redirect(url_for('dashboard'))
    orden = db.session.get(OrdenTrabajo, oid)
    if not orden:
        flash('Orden no encontrada.', 'danger')
        return redirect(url_for('ordenes.lista'))
    return render_template('admin/ordenes/reporte.html',
                           orden=orden,
                           TIPOS_MAP=TIPOS_MAP,
                           ahora=datetime.utcnow())
