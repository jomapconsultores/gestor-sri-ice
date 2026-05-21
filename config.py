import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'clave-super-secreta-cambiar-en-produccion')
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///sistema_ice.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # PAYPHONE - REEMPLAZA CON TUS DATOS CUANDO LOS TENGAS
    PAYPHONE_CLIENT_ID = os.getenv('PAYPHONE_CLIENT_ID', 'TU_CLIENT_ID')
    PAYPHONE_CLIENT_SECRET = os.getenv('PAYPHONE_CLIENT_SECRET', 'TU_CLIENT_SECRET')
    PAYPHONE_MERCHANT_ID = os.getenv('PAYPHONE_MERCHANT_ID', 'TU_MERCHANT_ID')
    
    # URL de tu sistema (cámbiala cuando esté en Render)
    BASE_URL = os.getenv('BASE_URL', 'http://localhost:5000')
    
    # Planes
    PLAN_BASICO = {
        'id': 'basico',
        'nombre': 'Plan Básico',
        'precio': 9.99,
        'precio_centavos': 999,
        'limite_facturas': 100,
        'incluye_auditoria': False
    }
    PLAN_PROFESIONAL = {
        'id': 'profesional',
        'nombre': 'Plan Profesional',
        'precio': 19.99,
        'precio_centavos': 1999,
        'limite_facturas': float('inf'),
        'incluye_auditoria': True
    }
    PLAN_EMPRESARIAL = {
        'id': 'empresarial',
        'nombre': 'Plan Empresarial',
        'precio': 39.99,
        'precio_centavos': 3999,
        'limite_facturas': float('inf'),
        'incluye_auditoria': True
    }