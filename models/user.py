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
    descuento_total = db.Column(db.Numeric(12, 2), default=0)
    tiene_descuento = db.Column(db.Boolean, default=False)

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


class ModuloSuscrito(db.Model):
    """Módulos individuales que cada usuario tiene activos."""
    __tablename__ = "modulo_suscrito"
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuario.id"), nullable=False)
    modulo_id = db.Column(db.String(50), nullable=False)
    estado = db.Column(db.String(20), default="activo")
    es_pago_unico = db.Column(db.Boolean, default=False)
    precio_pagado = db.Column(db.Numeric(10, 2))
    iva_pagado = db.Column(db.Numeric(10, 2))
    duracion_meses = db.Column(db.Integer, default=1)
    fecha_inicio = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_vencimiento = db.Column(db.DateTime)
    comprobante_path = db.Column(db.String(500))
    verificado = db.Column(db.Boolean, default=False)
    usuario = db.relationship("Usuario", backref="modulos_suscritos", lazy=True)

    def esta_activo(self):
        if self.estado != "activo" or not self.verificado:
            return False
        if self.es_pago_unico:
            return True
        return self.fecha_vencimiento and self.fecha_vencimiento > datetime.utcnow()


class ProductoSesionICE(db.Model):
    """Último lote de productos calculados en ICE Múltiple por usuario."""
    __tablename__ = "producto_sesion_ice"
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuario.id"), nullable=False)
    nombre = db.Column(db.String(300), nullable=False)
    tipo_producto = db.Column(db.String(50), default='Licor')
    volumen_cc = db.Column(db.Numeric(10, 2), default=750)
    grado_alcoholico = db.Column(db.Numeric(6, 2), default=35)
    precio_fabrica = db.Column(db.Numeric(12, 4))
    costos = db.Column(db.Numeric(12, 4), default=0)
    utilidad = db.Column(db.Numeric(12, 4), default=0)
    cantidad = db.Column(db.Integer, default=1)
    escala = db.Column(db.String(50))
    orden = db.Column(db.Integer, default=0)
    fecha_guardado = db.Column(db.DateTime, default=datetime.utcnow)
    usuario = db.relationship("Usuario", backref="sesiones_ice", lazy=True)


class AnexoICEGuardado(db.Model):
    """XMLs de Anexo ICE/PVP guardados por usuario para edición futura."""
    __tablename__ = "anexo_ice_guardado"
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuario.id"), nullable=False)
    nombre = db.Column(db.String(300))
    tipo = db.Column(db.String(10), default='ICE')
    xml_contenido = db.Column(db.Text)
    periodo_anio = db.Column(db.String(4))
    periodo_mes = db.Column(db.String(2))
    fecha_guardado = db.Column(db.DateTime, default=datetime.utcnow)
    usuario = db.relationship("Usuario", backref="anexos_guardados", lazy=True)


class FacturaICEProcesada(db.Model):
    """Registro de cada factura XML procesada en el módulo Facturas ICE."""
    __tablename__ = "factura_ice_procesada"
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuario.id"), nullable=False)
    nombre_archivo = db.Column(db.String(500))
    fecha_emision = db.Column(db.String(30))
    tipo_id_cliente = db.Column(db.String(10))
    id_cliente = db.Column(db.String(20))
    razon_social_cliente = db.Column(db.String(300))
    nombre_producto = db.Column(db.String(500))
    cod_marca = db.Column(db.String(20))
    cod_prod_sri = db.Column(db.String(50))
    capacidad = db.Column(db.String(10))
    grado_alcoholico = db.Column(db.String(10))
    cantidad_cajas = db.Column(db.Numeric(10, 2))
    unidades_botellas = db.Column(db.Integer)
    precio_por_caja = db.Column(db.Numeric(12, 4))
    precio_por_botella = db.Column(db.Numeric(12, 4))
    base_ice = db.Column(db.Numeric(12, 2))
    valor_ice = db.Column(db.Numeric(12, 2))
    base_iva = db.Column(db.Numeric(12, 2))
    valor_iva = db.Column(db.Numeric(12, 2))
    periodo_anio = db.Column(db.String(4))
    periodo_mes = db.Column(db.String(2))
    fecha_proceso = db.Column(db.DateTime, default=datetime.utcnow)
    usuario = db.relationship("Usuario", backref="facturas_ice_procesadas", lazy=True)


class SolicitudAcceso(db.Model):
    """Comprobante de pago subido por el usuario para que el admin apruebe."""
    __tablename__ = "solicitud_acceso"
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuario.id"), nullable=False)
    modulos = db.Column(db.Text)
    duracion_meses = db.Column(db.Integer, default=1)
    monto_total = db.Column(db.Numeric(10, 2))
    comprobante_path = db.Column(db.String(500))
    estado = db.Column(db.String(20), default="pendiente")
    nota_admin = db.Column(db.Text)
    fecha_solicitud = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_respuesta = db.Column(db.DateTime)
    usuario = db.relationship("Usuario", backref="solicitudes_acceso", lazy=True)
