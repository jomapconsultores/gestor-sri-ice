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

    # ── Módulos ICE ────────────────────────────────────────────────────────────
    MODULOS = {
        'tarifas_ice': {
            'nombre': 'Tarifas ICE 2021–2026',
            'descripcion': (
                'Consulta completa de tarifas ICE vigentes desde 2021 hasta 2026. '
                'Incluye toda la reglamentación: artículos de la Ley de Régimen Tributario Interno, '
                'Reglamento LRTI, NAC y Resoluciones del SRI, con las tarifas y fórmulas de cálculo '
                'correspondientes a cada período.'
            ),
            'precio': 0.00,
            'precio_unico': False,
            'gratuito': True,
            'categoria': 'ice',
            'color': 'success',
            'icono': 'book',
            'tooltip': 'Consulta gratuita de tarifas y reglamentación ICE 2021–2026',
        },
        'ice_simple': {
            'nombre': 'Cálculo ICE Simple',
            'descripcion': (
                'Calcula el ICE de un producto individual ingresando grado alcohólico, capacidad '
                'y cantidad. Genera un reporte en Excel con las fórmulas de cálculo y la base legal '
                'correspondiente, listo para sustentar tu declaración mensual ante el SRI.'
            ),
            'precio': 10.00,
            'precio_unico': False,
            'gratuito': False,
            'categoria': 'ice',
            'color': 'primary',
            'icono': 'calculator',
            'tooltip': 'Cálculo ICE individual con reporte Excel + base legal',
        },
        'ice_multiple': {
            'nombre': 'ICE Múltiple',
            'descripcion': (
                'Calcula el ICE de múltiples productos (licores, cerveza artesanal e industrial) '
                'en una sola sesión. Ingresa costos totales, utilidad y precio ex fábrica; obtén '
                'ICE específico, ICE ad-valorem, IVA y PVP por unidad y por cantidad de botellas. '
                'Incluye cálculo de mezcla total. Los productos quedan guardados en la base de datos. '
                'Genera reporte Excel con resumen por producto y totales generales.'
            ),
            'precio': 15.00,
            'precio_unico': False,
            'gratuito': False,
            'categoria': 'ice',
            'color': 'warning',
            'icono': 'calculator-fill',
            'tooltip': 'ICE multi-producto con PVP, costos, utilidad y reporte Excel',
        },
        'anexos_ice': {
            'nombre': 'Anexos ICE / PVP',
            'descripcion': (
                'Genera y edita los Anexos ICE y PVP en formato XML oficial del SRI. '
                'Carga un XML existente desde la base de datos o arrastra uno desde tu computador, '
                'edita cada campo según tus necesidades, valida la estructura y descarga el XML '
                'listo para subir. Incluye conversión a ZIP para aquellos casos en que el SRI lo requiera.'
            ),
            'precio': 10.00,
            'precio_unico': False,
            'gratuito': False,
            'categoria': 'ice',
            'color': 'info',
            'icono': 'file-earmark-code',
            'tooltip': 'Editor visual de Anexos ICE/PVP + validación + ZIP',
        },
        'facturas_ice': {
            'nombre': 'Procesamiento Facturas ICE',
            'descripcion': (
                'Arrastra o importa tus facturas de ingresos en formato XML para generar '
                'automáticamente el Anexo ICE o PVP según la reglamentación vigente. '
                'Todos los datos quedan grabados en la base de datos de forma individual por usuario. '
                'El administrador puede acceder a los datos de cualquier usuario sin que se mezclen.'
            ),
            'precio': 15.00,
            'precio_unico': False,
            'gratuito': False,
            'categoria': 'ice',
            'color': 'danger',
            'icono': 'file-earmark-arrow-up',
            'tooltip': 'Procesa XMLs de ingresos y genera Anexo ICE/PVP automáticamente',
        },

        # ── Módulos Generales (próxima tanda) ──────────────────────────────────
        'facturas': {
            'nombre': 'Facturas Ilimitadas',
            'descripcion': (
                'Sube y procesa facturas XML ilimitadas de gastos e ingresos. '
                'Clasificación automática con catálogo personalizable. El catálogo de productos está '
                'incluido sin costo adicional.'
            ),
            'precio': 10.00,
            'precio_unico': False,
            'gratuito': False,
            'categoria': 'general',
            'color': 'secondary',
            'icono': 'receipt',
            'tooltip': 'Facturas ilimitadas de gastos e ingresos + catálogo incluido',
        },
        'exportacion': {
            'nombre': 'Exportación Excel',
            'descripcion': (
                'Exporta todos tus reportes a Excel con fórmulas, resúmenes por período y '
                'formato profesional. Compatible con todos los módulos del sistema.'
            ),
            'precio': 5.00,
            'precio_unico': False,
            'gratuito': False,
            'categoria': 'general',
            'color': 'success',
            'icono': 'file-earmark-excel',
            'tooltip': 'Exporta reportes de todos los módulos a Excel',
        },
        'descarga_sri': {
            'nombre': 'Descarga Masiva SRI',
            'descripcion': (
                'Descarga masivamente tus comprobantes del portal del SRI usando claves de acceso. '
                'Pago único con acceso permanente a la herramienta.'
            ),
            'precio': 15.00,
            'precio_unico': True,
            'gratuito': False,
            'categoria': 'general',
            'color': 'secondary',
            'icono': 'cloud-download',
            'tooltip': 'Descarga masiva desde el SRI — pago único $15',
        },
        'conciliacion': {
            'nombre': 'Conciliación Bancaria IA',
            'descripcion': (
                'Sube estados de cuenta en PDF y extrae transacciones automáticamente con IA. '
                'Exporta en formato Excel compatible con Odoo.'
            ),
            'precio': 10.00,
            'precio_unico': False,
            'gratuito': False,
            'categoria': 'general',
            'color': 'primary',
            'icono': 'bank',
            'tooltip': 'Extrae transacciones bancarias de PDFs con IA y exporta a Odoo',
        },
        'retenciones': {
            'nombre': 'Procesador de Retenciones',
            'descripcion': (
                'Procesa XMLs de comprobantes de retención. Detecta automáticamente Renta, IVA e ISD. '
                'Exporta a Excel con fórmulas y resumen por agente de retención.'
            ),
            'precio': 10.00,
            'precio_unico': False,
            'gratuito': False,
            'categoria': 'general',
            'color': 'info',
            'icono': 'file-earmark-minus',
            'tooltip': 'Procesa XMLs de retenciones y exporta a Excel',
        },
        'sri_pro': {
            'nombre': 'Gestor SRI Pro',
            'descripcion': (
                'Descarga XMLs del SRI desde un TXT de claves de acceso (hasta 10 en paralelo) '
                'o importa XMLs locales. Clasifica y exporta a Excel con SUMIF por categoría.'
            ),
            'precio': 15.00,
            'precio_unico': False,
            'gratuito': False,
            'categoria': 'general',
            'color': 'secondary',
            'icono': 'cloud-arrow-down',
            'tooltip': 'Descarga y clasifica XMLs del SRI masivamente',
        },
        'soporte': {
            'nombre': 'Soporte Prioritario',
            'descripcion': (
                'Atención preferencial por WhatsApp y correo electrónico. '
                'Respuesta en menos de 24 horas hábiles.'
            ),
            'precio': 5.00,
            'precio_unico': False,
            'gratuito': False,
            'categoria': 'general',
            'color': 'dark',
            'icono': 'headset',
            'tooltip': 'Soporte prioritario por WhatsApp y email',
        },
    }

    # Descuentos por duración
    DURACIONES = {
        1:  {'nombre': '1 mes',   'descuento': 0},
        3:  {'nombre': '3 meses', 'descuento': 5},
        6:  {'nombre': '6 meses', 'descuento': 10},
        12: {'nombre': '1 año',   'descuento': 15},
    }