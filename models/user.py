from models import db, login_manager
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
    stripe_customer_id = db.Column(db.String(100))
    
    suscripcion = db.relationship('Suscripcion', backref='usuario', lazy=True, uselist=False)
    facturas = db.relationship('Factura', backref='usuario', lazy=True)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def tiene_suscripcion_activa(self):
        if self.suscripcion and self.suscripcion.estado == 'activa':
            return self.suscripcion.fecha_renovacion > datetime.utcnow()
        return False


class Suscripcion(db.Model):
    __tablename__ = 'suscripcion'
    
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'))
    plan_id = db.Column(db.String(50), nullable=False)
    estado = db.Column(db.String(20), default='activa')
    fecha_inicio = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_renovacion = db.Column(db.DateTime, nullable=False)
    stripe_subscription_id = db.Column(db.String(100))
    facturas_procesadas_mes = db.Column(db.Integer, default=0)


class Factura(db.Model):
    __tablename__ = 'factura'
    
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'))
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
    fecha_procesamiento = db.Column(db.DateTime, default=datetime.utcnow)


@login_manager.user_loader
def load_user(user_id):
    return Usuario.query.get(int(user_id))

class CatalogoProducto(db.Model):
    __tablename__ = 'catalogo_producto'
    
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'))
    nombre = db.Column(db.String(300), nullable=False)
    cod_marca = db.Column(db.String(6), default='000000')
    cod_impuesto = db.Column(db.String(4), default='3031')
    cod_clasificacion = db.Column(db.String(3), default='057')
    presentacion = db.Column(db.String(3), default='013')
    capacidad = db.Column(db.String(6), default='000750')
    unidad = db.Column(db.String(2), default='66')
    grado_alcoholico = db.Column(db.String(6), default='000015')
    cod_pais = db.Column(db.String(3), default='593')
    es_pack = db.Column(db.Boolean, default=False)
    unidades_por_caja = db.Column(db.Integer, default=12)
    
    def __repr__(self):
        return f'<CatalogoProducto {self.nombre}>'