import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'clave-super-secreta-cambiar-en-produccion')
    # Supabase/Render: postgres:// → postgresql+psycopg:// (psycopg 3)
    _db_url = os.getenv('DATABASE_URL', 'sqlite:///sistema_ice.db')
    if _db_url.startswith('postgres://'):
        _db_url = _db_url.replace('postgres://', 'postgresql+psycopg://', 1)
    elif _db_url.startswith('postgresql://'):
        _db_url = _db_url.replace('postgresql://', 'postgresql+psycopg://', 1)
    SQLALCHEMY_DATABASE_URI = _db_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {'pool_pre_ping': True, 'pool_recycle': 300}

    BASE_URL = os.getenv('BASE_URL', 'http://localhost:5000')

    # IVA Ecuador
    IVA_RATE = 0.12

    # Datos de pago por transferencia
    BANCO_NOMBRE = 'Produbanco - Cuenta Corriente'
    BANCO_TITULAR = 'CMAJ ASOCIADOS SAS'
    BANCO_CUENTA = '27059106889'
    BANCO_RUC = '0195146942001'
    BANCO_CORREO = 'jomapconsultores@outlook.com'
    BANCO_CELULAR = '0963511411'

    # Módulos disponibles con sus precios (sin IVA)
    MODULOS = {
        'ice_simple': {
            'nombre': 'Cálculo ICE Simple',
            'descripcion': 'Calcula el ICE de un producto individual: ingresa grado alcohólico, capacidad y cantidad para obtener el impuesto a pagar en tu declaración mensual.',
            'precio': 5.00,
            'precio_unico': False,
            'color': 'success',
            'icono': 'calculator',
            'tooltip': 'Cálculo ICE para un producto a la vez'
        },
        'ice_multiple': {
            'nombre': 'Cálculo ICE Múltiple + Mezcla',
            'descripcion': 'Calcula el ICE de varios productos simultáneamente y realiza cálculos de mezcla total. Ideal para distribuidores con múltiples líneas de producto.',
            'precio': 15.00,
            'precio_unico': False,
            'color': 'primary',
            'icono': 'calculator-fill',
            'tooltip': 'ICE multi-producto y mezcla total'
        },
        'anexos': {
            'nombre': 'Generación Anexos SRI',
            'descripcion': 'Genera automáticamente el Anexo PVP e ICE en formato XML para presentar al SRI cada mes. Incluye validación de datos y generación del archivo listo para subir.',
            'precio': 15.00,
            'precio_unico': False,
            'color': 'warning',
            'icono': 'file-earmark-zip',
            'tooltip': 'Genera los anexos XML para el SRI'
        },
        'exportacion': {
            'nombre': 'Exportación Excel',
            'descripcion': 'Exporta todos tus reportes a Excel: declaraciones, auditorías ICE, gastos personales clasificados, resúmenes por período y más. Compatible con todos los módulos.',
            'precio': 5.00,
            'precio_unico': False,
            'color': 'info',
            'icono': 'file-earmark-excel',
            'tooltip': 'Exporta reportes de todos los módulos a Excel'
        },
        'facturas': {
            'nombre': 'Facturas Ilimitadas',
            'descripcion': 'Sube y procesa facturas XML ilimitadas. Incluye GASTOS (facturas de compra → clasificación de gastos personales con catálogo) e INGRESOS (facturas de venta → reporte + anexo PVP/ICE). El catálogo de productos está incluido sin costo adicional.',
            'precio': 10.00,
            'precio_unico': False,
            'color': 'danger',
            'icono': 'receipt',
            'tooltip': 'Facturas ilimitadas de gastos e ingresos + catálogo incluido'
        },
        'descarga_sri': {
            'nombre': 'Descarga Masiva SRI',
            'descripcion': 'Herramienta para descargar masivamente tus facturas del portal del SRI. Pago único que te da acceso permanente a la herramienta de descarga.',
            'precio': 15.00,
            'precio_unico': True,
            'color': 'secondary',
            'icono': 'cloud-download',
            'tooltip': 'Descarga masiva desde el SRI - pago único $15'
        },
        'soporte': {
            'nombre': 'Soporte Prioritario',
            'descripcion': 'Atención preferencial por WhatsApp y correo electrónico. Respuesta en menos de 24 horas hábiles para resolver dudas técnicas y de uso del sistema.',
            'precio': 5.00,
            'precio_unico': False,
            'color': 'dark',
            'icono': 'headset',
            'tooltip': 'Soporte prioritario por WhatsApp y email'
        },
        'conciliacion': {
            'nombre': 'Conciliación Bancaria Odoo',
            'descripcion': 'Sube estados de cuenta en PDF y extrae automáticamente las transacciones con IA (Mistral). Exporta en formato Excel compatible con Odoo para importación directa.',
            'precio': 10.00,
            'precio_unico': False,
            'color': 'primary',
            'icono': 'bank',
            'tooltip': 'Extrae transacciones bancarias de PDFs con IA y exporta a Odoo'
        },
        'retenciones': {
            'nombre': 'Procesador de Retenciones',
            'descripcion': 'Procesa XMLs de comprobantes de retención del SRI. Detecta automáticamente Renta, IVA e ISD. Exporta a Excel con fórmulas, resumen por agente de retención y totales.',
            'precio': 10.00,
            'precio_unico': False,
            'color': 'info',
            'icono': 'file-earmark-minus',
            'tooltip': 'Procesa XMLs de retenciones y exporta a Excel con resumen'
        },
        'sri_pro': {
            'nombre': 'Gestor SRI Pro',
            'descripcion': 'Descarga XMLs del SRI desde un TXT de claves de acceso (hasta 10 en paralelo) o importa XMLs locales. Clasifica facturas por proveedor y exporta a Excel con SUMIF por categoría.',
            'precio': 15.00,
            'precio_unico': False,
            'color': 'secondary',
            'icono': 'cloud-download',
            'tooltip': 'Descarga y clasifica XMLs del SRI masivamente'
        },
        'ice_auditoria': {
            'nombre': 'Auditoría ICE Completa',
            'descripcion': 'Auditoría ICE con tarifas 2021–2026. Detecta packs y los descompone, calcula ICE específico y ad-valorem, genera el anexo XML para el SRI y exporta a Excel con 3 hojas de análisis.',
            'precio': 20.00,
            'precio_unico': False,
            'color': 'danger',
            'icono': 'fire',
            'tooltip': 'Auditoría ICE multi-año con generación de anexo XML'
        },
    }

    # Descuentos por duración
    DURACIONES = {
        1:  {'nombre': '1 mes',   'descuento': 0},
        3:  {'nombre': '3 meses', 'descuento': 5},
        6:  {'nombre': '6 meses', 'descuento': 10},
        12: {'nombre': '1 año',   'descuento': 15},
    }