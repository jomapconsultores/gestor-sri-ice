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

    # ═══ CONFIGURACIÓN TRIBUTARIA SRI ECUADOR ═══════════════════════════════════

    # IVA - Tasas actualizadas 2024-2026
    IVA_RATE = float(os.getenv('IVA_RATE', '0.15'))  # 2024+
    IVA_TASA_CERO = float(os.getenv('IVA_TASA_CERO', '0.00'))
    IVA_TASA_CINCO = float(os.getenv('IVA_TASA_CINCO', '0.05'))
    IVA_TASA_DOCE = float(os.getenv('IVA_TASA_DOCE', '0.12'))
    IVA_TASA_QUINCE = float(os.getenv('IVA_TASA_QUINCE', '0.15'))

    # Límites de gastos según SRI 2026
    CANASTA_BASICA_ENERO_2026 = float(os.getenv('CANASTA_BASICA_ENERO_2026', '821.8'))

    # Rebaja Máxima de Impuestos según número de cargas
    GASTO_REBAJA_POR_CARGAS = {
        0: float(os.getenv('GASTO_REBAJA_0_CARGAS', '1035.47')),
        1: float(os.getenv('GASTO_REBAJA_1_CARGA', '1331.32')),
        2: float(os.getenv('GASTO_REBAJA_2_CARGAS', '1627.16')),
        3: float(os.getenv('GASTO_REBAJA_3_CARGAS', '2070.94')),
        4: float(os.getenv('GASTO_REBAJA_4_CARGAS', '2514.71')),
        6: float(os.getenv('GASTO_REBAJA_6_MAS_CARGAS', '14792.40')),
    }

    GASTO_TURISMO_LIMITE_PCT = float(os.getenv('GASTO_TURISMO_LIMITE_PCT', '0.20'))  # 20%
    GASTO_ARTE_CULTURA_LIMITE_PCT = float(os.getenv('GASTO_ARTE_CULTURA_LIMITE_PCT', '0.10'))  # 10%
    PRESCRIPCION_ANOS = int(os.getenv('PRESCRIPCION_ANOS', '5'))

    # APIs Externas (opcionales - solo para conciliación IA)
    MISTRAL_API_KEY = os.getenv('MISTRAL_API_KEY')
    CODESTRAL_API_KEY = os.getenv('CODESTRAL_API_KEY')

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

        # ── Módulos Tributaria — INGRESOS ───────────────────────────────────────────
        'facturas_ingreso': {
            'nombre': 'Facturas de Ingreso',
            'descripcion': 'Sube o arrastra facturas XML de ingreso (ventas). Obtén detalle completo: cliente, totales, ICE, IVA por factura. Exporta a Excel con valores reales. Datos guardados por usuario.',
            'precio': 15.00, 'precio_unico': False, 'gratuito': False,
            'categoria': 'tributaria', 'subcategoria': 'ingresos',
            'color': 'primary', 'icono': 'cloud-upload',
            'tooltip': 'Sube facturas de ingreso XML y exporta a Excel',
        },
        'retenciones': {
            'nombre': 'Retenciones',
            'descripcion': 'Sube o arrastra comprobantes de retención XML. Detecta automáticamente Renta, IVA e ISD. Exporta a Excel (solo valores) con resumen por agente retenedor.',
            'precio': 5.00, 'precio_unico': False, 'gratuito': False,
            'categoria': 'tributaria', 'subcategoria': 'ingresos',
            'color': 'info', 'icono': 'file-earmark-minus',
            'tooltip': 'Procesa retenciones XML y exporta a Excel',
        },
        # ── Módulos Tributaria — GASTOS ─────────────────────────────────────────────
        'descarga_sri': {
            'nombre': 'Descarga Masiva SRI',
            'descripcion': 'Bookmarklet que se arrastra al navegador para descargar masivamente facturas de gastos del portal SRI. Pago único, acceso permanente.',
            'precio': 15.00, 'precio_unico': True, 'gratuito': False,
            'categoria': 'tributaria', 'subcategoria': 'gastos',
            'color': 'secondary', 'icono': 'cloud-download',
            'tooltip': 'Descarga masiva desde el SRI — pago único $15',
        },
        'facturas_gasto': {
            'nombre': 'Facturas de Gasto',
            'descripcion': 'Sube o arrastra facturas XML de gasto. Clasifica en gastos generales o gastos personales. Descuentos Yanbal se aplican automáticamente; otros descuentos se marcan en color para que el usuario decida. Exporta a Excel (solo valores).',
            'precio': 15.00, 'precio_unico': False, 'gratuito': False,
            'categoria': 'tributaria', 'subcategoria': 'gastos',
            'color': 'danger', 'icono': 'receipt',
            'tooltip': 'Sube facturas de gasto, clasifica y exporta a Excel',
        },
        # ── Módulo Declaración Completa ───────────────────────────────────────────────
        'registro_completo': {
            'nombre': 'Declaración ICE + IVA',
            'descripcion': (
                'Todo en un solo lugar: Tarifas ICE, Cálculo ICE Simple y Múltiple, '
                'Generación de Anexos ICE/PVP, Procesamiento de Facturas ICE, '
                'Facturas de Ingreso, Retenciones, Facturas de Gasto con clasificación, '
                'Liquidación IVA (a pagar o crédito tributario) e ICE específico + '
                'ad valorem para declaración. Reporte Excel con todas las hojas.'
            ),
            'precio': 120.00, 'precio_unico': False, 'gratuito': False,
            'categoria': 'tributaria', 'subcategoria': 'completo',
            'color': 'dark', 'icono': 'journal-richtext',
            'tooltip': 'Todo en uno: ICE + Tributaria + Liquidación + Excel completo',
            'incluye': ['tarifas_ice', 'ice_simple', 'ice_multiple', 'anexos_ice', 'facturas_ice', 'facturas_ingreso', 'retenciones', 'facturas_gasto', 'conciliacion'],
        },
        # ── Módulos Odoo ─────────────────────────────────────────────────────────────
        'conciliacion': {
            'nombre': 'Conciliación Bancaria IA',
            'descripcion': 'Sube estados de cuenta bancarios en PDF. La IA extrae automáticamente las transacciones y genera Excel compatible con Odoo para importación directa.',
            'precio': 10.00, 'precio_unico': False, 'gratuito': False,
            'categoria': 'odoo', 'subcategoria': None,
            'color': 'primary', 'icono': 'bank',
            'tooltip': 'Extrae transacciones de PDFs con IA y exporta a Odoo',
        },
    }

    # Descuentos por duración
    DURACIONES = {
        1:  {'nombre': '1 mes',   'descuento': 0},
        3:  {'nombre': '3 meses', 'descuento': 5},
        6:  {'nombre': '6 meses', 'descuento': 10},
        12: {'nombre': '1 año',   'descuento': 15},
    }
