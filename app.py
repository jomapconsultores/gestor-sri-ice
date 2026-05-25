from flask import Flask, render_template, redirect, url_for, request, flash
from config import Config
from models import db, login_manager
import json as _json
from routes.auth import auth
from routes.payments import payments, get_modulos_activos
from routes.invoices import invoices
from routes.ice import ice
from routes.catalog import catalog
from routes.annexes import annexes
from routes.exports import exports
from routes.downloader import downloader
from routes.admin_reports import admin_reports
from routes.gastos import gastos
from routes.empresas import empresas
from routes.security import security, obtener_ip
from routes.ats import ats
from routes.conciliacion import conciliacion
from routes.sri_processor import sri_processor
from routes.ice_auditoria import ice_auditoria
from routes.retenciones import retenciones
from flask_login import login_required, current_user

RUTAS_LIBRES = {
    '/auth/login', '/auth/register', '/auth/logout',
    '/bienvenido', '/payments/planes', '/payments/calcular_precio',
    '/security/solicitar_ip', '/static',
}

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

    db.init_app(app)
    login_manager.init_app(app)

    app.register_blueprint(auth, url_prefix='/auth')
    app.register_blueprint(payments, url_prefix='/payments')
    app.register_blueprint(invoices, url_prefix='/invoices')
    app.register_blueprint(ice, url_prefix='/ice')
    app.register_blueprint(catalog, url_prefix='/catalog')
    app.register_blueprint(annexes, url_prefix='/annexes')
    app.register_blueprint(exports, url_prefix='/exports')
    app.register_blueprint(downloader, url_prefix='/downloader')
    app.register_blueprint(admin_reports, url_prefix='/admin')
    app.register_blueprint(gastos, url_prefix='/gastos')
    app.register_blueprint(empresas, url_prefix='/empresas')
    app.register_blueprint(security, url_prefix='/security')
    app.register_blueprint(ats, url_prefix='/ats')
    app.register_blueprint(conciliacion, url_prefix='/conciliacion')
    app.register_blueprint(sri_processor, url_prefix='/sri_processor')
    app.register_blueprint(ice_auditoria, url_prefix='/ice_auditoria')
    app.register_blueprint(retenciones, url_prefix='/retenciones')

    # Filtros Jinja2 personalizados
    @app.template_filter('from_json')
    def from_json_filter(value):
        try:
            return _json.loads(value)
        except Exception:
            return []

    with app.app_context():
        db.create_all()

    # ── Middleware de validación de IP ────────────────────────────────────────
    @app.before_request
    def verificar_ip():
        from models.user import IpAutorizada, SolicitudIp
        # Solo aplica a usuarios autenticados
        if not current_user.is_authenticated:
            return
        # Excluir rutas públicas y estáticas
        path = request.path
        if any(path.startswith(r) for r in RUTAS_LIBRES):
            return
        # Admin nunca bloqueado
        if current_user.is_admin:
            return

        ip_actual = obtener_ip()
        ips_autorizadas = IpAutorizada.query.filter_by(
            usuario_id=current_user.id, activa=True).all()

        # Si no tiene IPs registradas, registrar la primera automáticamente
        if not ips_autorizadas:
            nueva = IpAutorizada(usuario_id=current_user.id, direccion_ip=ip_actual)
            db.session.add(nueva)
            db.session.commit()
            return

        ips_lista = [i.direccion_ip for i in ips_autorizadas]
        if ip_actual in ips_lista:
            return

        # IP no autorizada: redirigir a solicitar acceso
        pendiente = SolicitudIp.query.filter_by(
            usuario_id=current_user.id,
            direccion_ip=ip_actual,
            estado='pendiente').first()

        if pendiente:
            flash(f'Tu IP {ip_actual} está pendiente de autorización por el administrador.', 'warning')
        else:
            flash(f'Estás accediendo desde una IP no autorizada ({ip_actual}). '
                  f'Ya tienes {len(ips_lista)} IP(s) registrada(s). '
                  f'Envía una solicitud al administrador para agregar esta IP.', 'warning')

        return redirect(url_for('security.solicitar_ip'))

    return app


app = create_app()


@app.route('/')
@app.route('/dashboard')
@login_required
def dashboard():
    from models.user import Factura
    total_facturas = Factura.query.filter_by(usuario_id=current_user.id).count()
    modulos_activos = get_modulos_activos(current_user.id) if not current_user.is_admin else list(Config.MODULOS.keys())
    return render_template('dashboard.html',
                           total_facturas=total_facturas,
                           modulos_activos=modulos_activos)


@app.route('/bienvenido')
def bienvenido():
    return render_template('bienvenido.html')


if __name__ == '__main__':
    app.run(debug=True, port=5000)