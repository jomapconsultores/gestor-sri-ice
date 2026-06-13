from flask import Blueprint, render_template, redirect, url_for, flash, request, session, g
from flask_login import login_required, current_user, login_user
from models import db
from models.user import Usuario, Pago, FacturaEmitida, ModuloSuscrito, SolicitudAcceso
from config import Config
from datetime import datetime
from sqlalchemy import func, extract, case
import json

admin_reports = Blueprint('admin_reports', __name__)

MESES = ['', 'Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun',
         'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']

ROLES_CLIENTE = {
    'cliente':   ('Cliente',    '#f1f5f9', '#475569'),
    'gerente':   ('Gerente',    '#eff6ff', '#1d4ed8'),
    'contador':  ('Contador',   '#f0fdf4', '#15803d'),
    'analista':  ('Analista',   '#fff7ed', '#c2410c'),
}

# Módulos disponibles en el espacio de trabajo del admin
# (endpoint, icono, color fondo, color texto, etiqueta corta)
MODULOS_TRABAJO = [
    ('ice.calculadora',           'bi-calculator',          '#dbeafe', '#1e40af', 'ICE Simple'),
    ('ice.multiple',              'bi-calculator-fill',     '#ede9fe', '#5b21b6', 'ICE Múltiple'),
    ('anexos_ice.index',          'bi-file-earmark-code',   '#e0f2fe', '#0369a1', 'Anexos ICE/PVP'),
    ('facturas_ingreso.index',    'bi-cloud-upload',        '#dcfce7', '#15803d', 'Facturas Ingreso'),
    ('invoices.pagina_carga',     'bi-receipt',             '#fef9c3', '#854d0e', 'Facturas Gasto'),
    ('registro_completo.index',   'bi-journal-check',       '#fce7f3', '#9d174d', 'Declaración Completa'),
    ('retenciones.index',         'bi-file-earmark-minus',  '#ffedd5', '#c2410c', 'Retenciones'),
    ('ats.index',                 'bi-table',               '#f0fdf4', '#166534', 'ATS'),
    ('gastos.index',              'bi-cash-stack',          '#fef2f2', '#991b1b', 'Gastos'),
    ('catalog.index',             'bi-box-seam',            '#f0f9ff', '#0c4a6e', 'Catálogo Productos'),
    ('empresas.index',            'bi-building',            '#f5f3ff', '#4c1d95', 'Empresas'),
]


def requiere_admin():
    """Valida que el usuario sea admin o esté impersonando."""
    if current_user.is_admin:
        return True
    if getattr(g, 'es_impersonacion', False):
        return True
    flash('Acceso denegado: Se requieren permisos de administrador.', 'danger')
    return False


def _puede_ver_usuario(uid):
    """Valida que pueda ver datos del usuario uid (admin o impersonación)."""
    if not requiere_admin():
        return False
    admin_id = getattr(g, 'admin_original_id', None)
    if admin_id and uid == admin_id:
        return True
    if current_user.is_admin:
        return True
    return False


@admin_reports.route('/reportes')
@login_required
def reportes():
    if not requiere_admin():
        return redirect(url_for('dashboard'))

    # IVA efectivo: usa iva_pagado si fue registrado, sino calcula 15% sobre el precio
    iva_efectivo = case(
        (func.coalesce(ModuloSuscrito.iva_pagado, 0) == 0,
         ModuloSuscrito.precio_pagado * 0.15),
        else_=func.coalesce(ModuloSuscrito.iva_pagado, 0)
    )

    # Recaudación por usuario (basada en ModuloSuscrito verificados)
    recaudacion_usuarios = db.session.query(
        Usuario.nombre,
        Usuario.email,
        func.sum(ModuloSuscrito.precio_pagado).label('subtotal'),
        func.sum(iva_efectivo).label('iva_total'),
        func.count(ModuloSuscrito.id).label('cantidad')
    ).join(ModuloSuscrito, ModuloSuscrito.usuario_id == Usuario.id)\
     .filter(ModuloSuscrito.verificado == True, ModuloSuscrito.estado == 'activo')\
     .group_by(Usuario.id).all()

    # Recaudación por módulo/producto
    recaudacion_modulos = db.session.query(
        ModuloSuscrito.modulo_id,
        func.sum(ModuloSuscrito.precio_pagado).label('subtotal'),
        func.sum(iva_efectivo).label('iva_total'),
        func.count(ModuloSuscrito.id).label('cantidad')
    ).filter(ModuloSuscrito.verificado == True, ModuloSuscrito.estado == 'activo')\
     .group_by(ModuloSuscrito.modulo_id).all()

    # Recaudación mensual (por fecha de inicio del módulo)
    recaudacion_mensual = db.session.query(
        extract('year', ModuloSuscrito.fecha_inicio).label('anio'),
        extract('month', ModuloSuscrito.fecha_inicio).label('mes'),
        func.sum(ModuloSuscrito.precio_pagado + iva_efectivo).label('total'),
        func.count(ModuloSuscrito.id).label('cantidad')
    ).filter(ModuloSuscrito.verificado == True)\
     .group_by('anio', 'mes').order_by('anio', 'mes').all()

    # Recaudación por año
    recaudacion_anual = db.session.query(
        extract('year', ModuloSuscrito.fecha_inicio).label('anio'),
        func.sum(ModuloSuscrito.precio_pagado + iva_efectivo).label('total'),
        func.count(ModuloSuscrito.id).label('cantidad')
    ).filter(ModuloSuscrito.verificado == True)\
     .group_by('anio').order_by('anio').all()

    # Facturas pendientes de emisión
    facturas_pendientes = FacturaEmitida.query\
        .filter_by(estado='pendiente')\
        .order_by(FacturaEmitida.fecha_emision).all()

    # Total recaudado (precio + IVA, usando IVA calculado cuando no fue registrado)
    total_recaudado = db.session.query(
        func.sum(ModuloSuscrito.precio_pagado + iva_efectivo)
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
        valores_incluyen_iva = request.form.get('valores_incluyen_iva') == '1'
        if not valores_incluyen_iva:
            monto = round(monto * 1.15, 2)
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
        flash(f'Factura {numero} generada — Total c/IVA: ${monto:.2f}', 'success')
    except (ValueError, TypeError):
        flash('Datos inválidos.', 'danger')
    return redirect(url_for('admin_reports.reportes'))


@admin_reports.route('/ver_usuario/<int:usuario_id>')
@login_required
def ver_usuario(usuario_id):
    """Admin puede ver los datos detallados de cualquier usuario."""
    if not _puede_ver_usuario(usuario_id):
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
    if not _puede_ver_usuario(uid):
        return redirect(url_for('dashboard'))
    from models.user import Factura, AnexoICEGuardado, ProductoSesionICE, Empresa
    usuario = db.session.get(Usuario, uid)
    if not usuario:
        flash('Usuario no encontrado', 'danger')
        return redirect(url_for('admin_reports.clientes'))
    modulos = ModuloSuscrito.query.filter_by(usuario_id=uid).order_by(
        ModuloSuscrito.fecha_inicio.desc()).all()
    facturas = Factura.query.filter_by(usuario_id=uid).order_by(
        Factura.fecha_procesamiento.desc()).limit(30).all()
    solicitudes = SolicitudAcceso.query.filter_by(usuario_id=uid).order_by(
        SolicitudAcceso.fecha_solicitud.desc()).all()
    anexos = AnexoICEGuardado.query.filter_by(usuario_id=uid).order_by(
        AnexoICEGuardado.fecha_guardado.desc()).all()
    sesiones_ice = ProductoSesionICE.query.filter_by(usuario_id=uid).order_by(
        ProductoSesionICE.fecha_guardado.desc()).limit(50).all()
    empresas = Empresa.query.filter_by(usuario_id=uid).order_by(
        Empresa.fecha_registro.desc()).all()
    return render_template('admin/ver_cliente.html',
                           usuario=usuario, modulos=modulos,
                           facturas=facturas, solicitudes=solicitudes,
                           anexos=anexos, sesiones_ice=sesiones_ice,
                           empresas=empresas,
                           MODULOS=Config.MODULOS,
                           ROLES_CLIENTE=ROLES_CLIENTE)


@admin_reports.route('/cliente/<int:uid>/editar', methods=['POST'])
@login_required
def editar_cliente(uid):
    if not _puede_ver_usuario(uid):
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
    rol = request.form.get('rol', '').strip()
    if rol in ROLES_CLIENTE:
        usuario.rol = rol
    usuario.notas_admin = request.form.get('notas_admin', '').strip() or None
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

    # Precio personalizado o precio del módulo por defecto
    precio_raw = request.form.get('precio_personalizado', '').strip()
    try:
        precio_base = float(precio_raw) if precio_raw else float(m['precio'])
    except (ValueError, TypeError):
        precio_base = float(m['precio'])

    valores_incluyen_iva = request.form.get('valores_incluyen_iva') == '1'
    if valores_incluyen_iva:
        # El precio ingresado ya incluye IVA → descomponer
        precio_pagado = round(precio_base / 1.15, 2)
        iva_pagado = round(precio_base - precio_pagado, 2)
    else:
        # El precio ingresado es base → calcular IVA encima
        precio_pagado = round(precio_base, 2)
        iva_pagado = round(precio_base * 0.15, 2)

    nuevo = ModuloSuscrito(
        usuario_id=uid, modulo_id=modulo_id, estado='activo',
        es_pago_unico=es_unico, precio_pagado=precio_pagado,
        iva_pagado=iva_pagado,
        duracion_meses=duracion, fecha_inicio=datetime.utcnow(),
        fecha_vencimiento=vencimiento, verificado=True
    )
    db.session.add(nuevo)
    db.session.commit()
    total = precio_pagado + iva_pagado
    flash(f'Módulo {m["nombre"]} activado — Base: ${precio_pagado:.2f} | IVA: ${iva_pagado:.2f} | Total: ${total:.2f}', 'success')
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


# ── Impersonación ─────────────────────────────────────────────────────────────

@admin_reports.route('/impersonar/<int:uid>')
@login_required
def impersonar(uid):
    """Admin entra a trabajar como un cliente específico.
    Acepta ?next=/ruta para redirigir directo al módulo deseado."""
    is_admin_real = current_user.is_admin
    has_backup = bool(session.get('admin_original_id'))
    if not (is_admin_real or has_backup):
        flash('Acceso denegado.', 'danger')
        return redirect(url_for('dashboard'))

    admin_id = current_user.id if is_admin_real else session.get('admin_original_id')
    usuario = db.session.get(Usuario, uid)
    if not usuario or usuario.is_admin:
        flash('Usuario no válido para impersonar.', 'danger')
        return redirect(url_for('admin_reports.espacio'))

    session['admin_original_id'] = admin_id
    # Guardamos el uid para poder volver al espacio en la misma tarjeta
    session['impersonando_uid'] = uid
    login_user(usuario)

    next_url = request.args.get('next') or url_for('dashboard')
    # Validar que next_url sea una ruta interna (empieza con /)
    if not next_url.startswith('/'):
        next_url = url_for('dashboard')

    flash(f'Trabajando como <strong>{usuario.nombre}</strong>. '
          f'Usa el botón naranja "Volver" para regresar al espacio de trabajo.', 'warning')
    return redirect(next_url)


@admin_reports.route('/terminar_impersonacion')
@login_required
def terminar_impersonacion():
    """Regresa a la sesión de administrador y vuelve al espacio de trabajo."""
    admin_id = session.pop('admin_original_id', None)
    session.pop('impersonando_uid', None)
    if not admin_id:
        return redirect(url_for('dashboard'))
    admin = db.session.get(Usuario, int(admin_id))
    if not admin or not admin.is_admin:
        flash('Sesión de administrador inválida.', 'danger')
        return redirect(url_for('auth.login'))
    login_user(admin)
    return redirect(url_for('admin_reports.espacio'))


# ── Crear usuario desde admin ─────────────────────────────────────────────────

@admin_reports.route('/crear_usuario', methods=['GET', 'POST'])
@login_required
def crear_usuario():
    if not requiere_admin():
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        nombre = request.form.get('nombre', '').strip()
        empresa = request.form.get('empresa', '').strip()
        ruc = request.form.get('ruc', '').strip()
        password = request.form.get('password', '').strip()
        rol = request.form.get('rol', 'cliente')
        notas_admin = request.form.get('notas_admin', '').strip() or None

        if not email or not nombre or not password:
            flash('Email, nombre y contraseña son obligatorios.', 'danger')
            return render_template('admin/crear_usuario.html', ROLES_CLIENTE=ROLES_CLIENTE,
                                   form=request.form)
        if len(password) < 6:
            flash('La contraseña debe tener mínimo 6 caracteres.', 'danger')
            return render_template('admin/crear_usuario.html', ROLES_CLIENTE=ROLES_CLIENTE,
                                   form=request.form)
        if Usuario.query.filter_by(email=email).first():
            flash(f'Ya existe un usuario con el email {email}.', 'danger')
            return render_template('admin/crear_usuario.html', ROLES_CLIENTE=ROLES_CLIENTE,
                                   form=request.form)

        usuario = Usuario(
            email=email, nombre=nombre, empresa=empresa, ruc=ruc,
            activo=True, is_admin=False,
            rol=rol if rol in ROLES_CLIENTE else 'cliente',
            notas_admin=notas_admin,
        )
        usuario.set_password(password)
        db.session.add(usuario)
        db.session.commit()

        # Activar módulos seleccionados opcionalmente
        from datetime import timedelta
        modulos_sel = request.form.getlist('modulos_iniciales')
        duracion = int(request.form.get('duracion_inicial', 1))
        for mid in modulos_sel:
            if mid in Config.MODULOS:
                m = Config.MODULOS[mid]
                es_unico = m['precio_unico']
                venc = None if es_unico else datetime.utcnow() + timedelta(days=30 * duracion)
                ms = ModuloSuscrito(
                    usuario_id=usuario.id, modulo_id=mid, estado='activo',
                    es_pago_unico=es_unico, precio_pagado=0, iva_pagado=0,
                    duracion_meses=duracion, fecha_inicio=datetime.utcnow(),
                    fecha_vencimiento=venc, verificado=True,
                )
                db.session.add(ms)
        db.session.commit()

        flash(f'Usuario {nombre} creado exitosamente.', 'success')
        return redirect(url_for('admin_reports.ver_cliente', uid=usuario.id))

    return render_template('admin/crear_usuario.html', ROLES_CLIENTE=ROLES_CLIENTE,
                           MODULOS=Config.MODULOS, form={})


# ── Espacio de trabajo exclusivo del administrador ────────────────────────────

@admin_reports.route('/espacio')
@login_required
def espacio():
    """Panel privado del administrador: acceso directo a módulos por cliente."""
    if not current_user.is_admin:
        flash('Acceso exclusivo del administrador.', 'danger')
        return redirect(url_for('dashboard'))

    clientes = Usuario.query.filter_by(is_admin=False, activo=True)\
        .order_by(Usuario.nombre).all()

    # Para cada cliente calculamos sus módulos activos
    from werkzeug.routing import BuildError
    modulos_trabajo_validos = []
    for endpoint, icono, bg, color, etiqueta in MODULOS_TRABAJO:
        try:
            from flask import current_app
            with current_app.test_request_context():
                url_for(endpoint)
            modulos_trabajo_validos.append((endpoint, icono, bg, color, etiqueta))
        except (BuildError, Exception):
            pass

    return render_template('admin/espacio.html',
                           clientes=clientes,
                           modulos_trabajo=MODULOS_TRABAJO,
                           ROLES_CLIENTE=ROLES_CLIENTE,
                           MODULOS=Config.MODULOS)
