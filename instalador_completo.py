import os, sys, shutil
from datetime import datetime
from pathlib import Path

USER_PY = '''from models import db, login_manager
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

class Usuario(UserMixin, db.Model):
    __tablename__ = 'usuario'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    nombre = db.Column(db.String(100), nullable=False)
    empresa = db.Column(db.String(200))
    ruc = db.Column(db.String(13))
    password_hash = db.Column(db.String(256), nullable=False)
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow)
    activo = db.Column(db.Boolean, default=True)
    is_admin = db.Column(db.Boolean, default=False)
    stripe_customer_id = db.Column(db.String(100))
    suscripcion = db.relationship("Suscripcion", backref="usuario", lazy=True, uselist=False)
    facturas = db.relationship("Factura", backref="usuario", lazy=True)
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    def tiene_suscripcion_activa(self):
        if self.suscripcion and self.suscripcion.estado == "activa":
            return self.suscripcion.fecha_renovacion > datetime.utcnow()
        return False

class Suscripcion(db.Model):
    __tablename__ = "suscripcion"
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuario.id"))
    plan_id = db.Column(db.String(50), nullable=False)
    estado = db.Column(db.String(20), default="activa")
    fecha_inicio = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_renovacion = db.Column(db.DateTime, nullable=False)
    stripe_subscription_id = db.Column(db.String(100))
    facturas_procesadas_mes = db.Column(db.Integer, default=0)
    empresa_actual_id = db.Column(db.Integer, db.ForeignKey("empresa.id"))

class Factura(db.Model):
    __tablename__ = "factura"
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuario.id"))
    clave_acceso = db.Column(db.String(49), unique=True, nullable=False)
    ruc_emisor = db.Column(db.String(13))
    razon_social_emisor = db.Column(db.String(300))
    ruc_comprador = db.Column(db.String(13))
    razon_social_comprador = db.Column(db.String(300))
    fecha_emision = db.Column(db.Date)
    numero_factura = db.Column(db.String(50))
    importe_total = db.Column(db.Numeric(12,2))
    base_ice = db.Column(db.Numeric(12,2))
    valor_ice = db.Column(db.Numeric(12,2))
    base_iva = db.Column(db.Numeric(12,2))
    valor_iva = db.Column(db.Numeric(12,2))
    xml_original = db.Column(db.Text)
    tipo = db.Column(db.String(20), default="ingreso")
    fecha_procesamiento = db.Column(db.DateTime, default=datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(Usuario, int(user_id))

class CatalogoProducto(db.Model):
    __tablename__ = "catalogo_producto"
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuario.id"))
    nombre = db.Column(db.String(300), nullable=False)
    cod_marca = db.Column(db.String(6), default="000000")
    cod_impuesto = db.Column(db.String(4), default="3031")
    cod_clasificacion = db.Column(db.String(3), default="057")
    presentacion = db.Column(db.String(3), default="013")
    capacidad = db.Column(db.String(6), default="000750")
    unidad = db.Column(db.String(2), default="66")
    grado_alcoholico = db.Column(db.String(6), default="000015")
    cod_pais = db.Column(db.String(3), default="593")
    es_pack = db.Column(db.Boolean, default=False)
    unidades_por_caja = db.Column(db.Integer, default=12)

class Pago(db.Model):
    __tablename__ = "pago"
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuario.id"))
    plan_id = db.Column(db.String(50))
    monto = db.Column(db.Numeric(10, 2))
    estado = db.Column(db.String(20), default="pendiente")
    fecha_pago = db.Column(db.DateTime, default=datetime.utcnow)
    transaction_id = db.Column(db.String(100))
    usuario = db.relationship("Usuario", backref="pagos", lazy=True)

class FacturaEmitida(db.Model):
    __tablename__ = "factura_emitida"
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuario.id"))
    monto = db.Column(db.Numeric(10, 2))
    estado = db.Column(db.String(20), default="pendiente")
    fecha_emision = db.Column(db.Date)
    fecha_pago = db.Column(db.DateTime)
    numero_factura = db.Column(db.String(50))
    usuario = db.relationship("Usuario", backref="facturas_emitidas", lazy=True)

class ClasificacionGasto(db.Model):
    __tablename__ = "clasificacion_gasto"
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuario.id"))
    factura_id = db.Column(db.Integer, db.ForeignKey("factura.id"))
    categoria = db.Column(db.String(100))
    monto = db.Column(db.Numeric(12, 2))
    fecha = db.Column(db.DateTime, default=datetime.utcnow)

class MapaClasificacion(db.Model):
    __tablename__ = "mapa_clasificacion"
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuario.id"))
    nombre = db.Column(db.String(200))
    activo = db.Column(db.Boolean, default=True)
    fecha_subida = db.Column(db.DateTime, default=datetime.utcnow)
    detalles = db.relationship("MapaClasificacionDetalle", backref="mapa", lazy=True, cascade="all, delete-orphan")

class MapaClasificacionDetalle(db.Model):
    __tablename__ = "mapa_clasificacion_detalle"
    id = db.Column(db.Integer, primary_key=True)
    mapa_id = db.Column(db.Integer, db.ForeignKey("mapa_clasificacion.id"))
    ruc = db.Column(db.String(13), index=True)
    nombre_proveedor = db.Column(db.String(300))
    categoria = db.Column(db.String(100))

class Empresa(db.Model):
    __tablename__ = "empresa"
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuario.id"))
    ruc = db.Column(db.String(13))
    nombre = db.Column(db.String(300))
    razon_social = db.Column(db.String(300))
    activa = db.Column(db.Boolean, default=True)
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow)
    usuario = db.relationship("Usuario", backref="empresas", lazy=True)

class IpAutorizada(db.Model):
    __tablename__ = "ip_autorizada"
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuario.id"))
    direccion_ip = db.Column(db.String(45), nullable=False)
    activa = db.Column(db.Boolean, default=True)
    fecha_autorizacion = db.Column(db.DateTime, default=datetime.utcnow)
    usuario = db.relationship("Usuario", backref="ips_autorizadas", lazy=True)

class SolicitudIp(db.Model):
    __tablename__ = "solicitud_ip"
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuario.id"))
    direccion_ip = db.Column(db.String(45), nullable=False)
    justificacion = db.Column(db.Text)
    estado = db.Column(db.String(20), default="pendiente")
    fecha_solicitud = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_respuesta = db.Column(db.DateTime)
    usuario = db.relationship("Usuario", backref="solicitudes_ip", lazy=True)

class ProductoLicor(db.Model):
    __tablename__ = "producto_licor"
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuario.id"))
    factura_id = db.Column(db.Integer, db.ForeignKey("factura.id"))
    codigo_producto = db.Column(db.String(100))
    descripcion = db.Column(db.String(500))
    cantidad = db.Column(db.Numeric(10, 2))
    precio_unitario = db.Column(db.Numeric(12, 2))
    subtotal = db.Column(db.Numeric(12, 2))
    ice = db.Column(db.Numeric(12, 2))
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow)
    usuario = db.relationship("Usuario", backref="productos_licor", lazy=True)
    factura = db.relationship("Factura", backref="productos_licor", lazy=True)

class Recaudacion(db.Model):
    __tablename__ = "recaudacion"
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuario.id"))
    factura_id = db.Column(db.Integer, db.ForeignKey("factura.id"))
    periodo = db.Column(db.String(7))
    total_ice = db.Column(db.Numeric(12, 2))
    total_iva = db.Column(db.Numeric(12, 2))
    total_facturas = db.Column(db.Integer)
    fecha_calculo = db.Column(db.DateTime, default=datetime.utcnow)
    usuario = db.relationship("Usuario", backref="recaudaciones", lazy=True)
'''

SECURITY_PY = '''from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from models import db
from models.user import IpAutorizada, SolicitudIp, Usuario
from datetime import datetime

security = Blueprint("security", __name__)

def obtener_ip():
    if request.headers.get("X-Forwarded-For"):
        return request.headers.get("X-Forwarded-For").split(",")[0].strip()
    return request.remote_addr or "127.0.0.1"

@security.route("/solicitar_ip", methods=["GET", "POST"])
@login_required
def solicitar_ip():
    if request.method == "POST":
        ip = obtener_ip()
        justificacion = request.form.get("justificacion", "")
        if not justificacion:
            flash("Debes escribir una justificacion.", "warning")
            return render_template("security/solicitar_ip.html", ip=ip)
        existente = SolicitudIp.query.filter_by(usuario_id=current_user.id, direccion_ip=ip, estado="pendiente").first()
        if existente:
            flash("Ya tienes una solicitud pendiente para esta IP.", "warning")
            return redirect(url_for("dashboard"))
        solicitud = SolicitudIp(usuario_id=current_user.id, direccion_ip=ip, justificacion=justificacion)
        db.session.add(solicitud)
        db.session.commit()
        flash("Solicitud enviada. Un administrador la revisara.", "success")
        return redirect(url_for("dashboard"))
    return render_template("security/solicitar_ip.html", ip=obtener_ip())

@security.route("/admin/ips")
@login_required
def admin_ips():
    if not current_user.is_admin:
        flash("Acceso denegado.", "danger")
        return redirect(url_for("dashboard"))
    solicitudes = SolicitudIp.query.filter_by(estado="pendiente").order_by(SolicitudIp.fecha_solicitud.desc()).all()
    usuarios = Usuario.query.all()
    return render_template("security/admin_ips.html", solicitudes=solicitudes, usuarios=usuarios)

@security.route("/admin/aprobar_ip/<int:solicitud_id>")
@login_required
def aprobar_ip(solicitud_id):
    if not current_user.is_admin:
        flash("Acceso denegado.", "danger")
        return redirect(url_for("dashboard"))
    solicitud = db.session.get(SolicitudIp, solicitud_id)
    if solicitud and solicitud.estado == "pendiente":
        ips_activas = IpAutorizada.query.filter_by(usuario_id=solicitud.usuario_id, activa=True).count()
        if ips_activas >= 3:
            flash(f"El usuario ya tiene {ips_activas} IPs autorizadas.", "warning")
        else:
            nueva_ip = IpAutorizada(usuario_id=solicitud.usuario_id, direccion_ip=solicitud.direccion_ip)
            db.session.add(nueva_ip)
            solicitud.estado = "aprobada"
            solicitud.fecha_respuesta = datetime.utcnow()
            db.session.commit()
            flash("IP autorizada correctamente.", "success")
    return redirect(url_for("security.admin_ips"))

@security.route("/admin/rechazar_ip/<int:solicitud_id>")
@login_required
def rechazar_ip(solicitud_id):
    if not current_user.is_admin:
        flash("Acceso denegado.", "danger")
        return redirect(url_for("dashboard"))
    solicitud = db.session.get(SolicitudIp, solicitud_id)
    if solicitud:
        solicitud.estado = "rechazada"
        solicitud.fecha_respuesta = datetime.utcnow()
        db.session.commit()
        flash("Solicitud de IP rechazada.", "info")
    return redirect(url_for("security.admin_ips"))
'''

print('=== INSTALADOR INICIADO ===')
if not os.path.exists('app.py'):
    print('ERROR: Ejecuta desde C:\\Users\\mapos\\gestor_sri_ice')
    sys.exit(1)

ts = datetime.now().strftime('%Y%m%d_%H%M%S')
bak = Path(f'backups/consolidacion_{ts}')
bak.mkdir(parents=True, exist_ok=True)

if os.path.exists('models/user.py'):
    shutil.copy2('models/user.py', bak / 'user.py.backup')
    print(f'Respaldo: models/user.py')
if os.path.exists('routes/security.py'):
    shutil.copy2('routes/security.py', bak / 'security.py.backup')
    print(f'Respaldo: routes/security.py')
print(f'Respaldos en: {bak}')

with open('models/user.py', 'w', encoding='utf-8') as f:
    f.write(USER_PY)
print('models/user.py actualizado')

with open('routes/security.py', 'w', encoding='utf-8') as f:
    f.write(SECURITY_PY)
print('routes/security.py actualizado')

sys.path.insert(0, os.getcwd())
from models.user import IpAutorizada, SolicitudIp, ProductoLicor, Recaudacion
print('Imports verificados')

from app import create_app
from models import db
app = create_app()
with app.app_context():
    db.create_all()
    print('Tablas nuevas creadas')

    # Migrar columnas nuevas en tablas existentes (SQLite no soporta IF NOT EXISTS en ALTER TABLE)
    migraciones = [
        ("ALTER TABLE usuario ADD COLUMN is_admin BOOLEAN DEFAULT 0",      "usuario.is_admin"),
        ("ALTER TABLE factura ADD COLUMN tipo VARCHAR(20) DEFAULT 'ingreso'", "factura.tipo"),
        ("ALTER TABLE suscripcion ADD COLUMN empresa_actual_id INTEGER REFERENCES empresa(id)", "suscripcion.empresa_actual_id"),
        ("ALTER TABLE empresa ADD COLUMN razon_social VARCHAR(300)",         "empresa.razon_social"),
        ("ALTER TABLE empresa ADD COLUMN activa BOOLEAN DEFAULT 1",          "empresa.activa"),
    ]
    conn = db.engine.raw_connection()
    cursor = conn.cursor()
    for sql, desc in migraciones:
        try:
            cursor.execute(sql)
            conn.commit()
            print(f'  + Columna agregada: {desc}')
        except Exception as ex:
            if 'duplicate column' in str(ex).lower() or 'already exists' in str(ex).lower():
                print(f'  = Ya existia: {desc}')
            else:
                print(f'  ! Error en {desc}: {ex}')
    cursor.close()
    conn.close()

    from models.user import Usuario
    from sqlalchemy import text
    # Marcar admin directamente con SQL para evitar el ORM que ya carga is_admin
    result = db.session.execute(text("SELECT id FROM usuario WHERE email='admin@test.com'")).fetchone()
    if result:
        db.session.execute(text(f"UPDATE usuario SET is_admin=1 WHERE id={result[0]}"))
        db.session.commit()
        print(f'Admin configurado: admin@test.com')
    else:
        print('No existe admin@test.com - creando...')
        nuevo_admin = Usuario(email='admin@test.com', nombre='Administrador', is_admin=True)
        nuevo_admin.set_password('admin123')
        db.session.add(nuevo_admin)
        db.session.commit()
        print('Admin creado: admin@test.com / admin123')

print('=== COMPLETADO ===')
print('Ejecuta: .\\venv\\Scripts\\python.exe app.py')
