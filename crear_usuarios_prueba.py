"""
Script para crear usuarios de prueba con diferentes combinaciones de módulos.
Ejecutar: python crear_usuarios_prueba.py

Usuarios creados:
  admin@test.com       / Admin2024!   → Administrador (acceso total)
  ice_simple@test.com  / Test1234!    → Solo Cálculo ICE Simple
  ice_pro@test.com     / Test1234!    → ICE Simple + ICE Múltiple + Mezcla
  facturas@test.com    / Test1234!    → Facturas Ilimitadas (incl. catálogo)
  completo@test.com    / Test1234!    → Todos los módulos
  descarga@test.com    / Test1234!    → Solo Descarga Masiva SRI (pago único)
  anexos@test.com      / Test1234!    → Facturas + Anexos SRI + Exportación
  sin_modulos@test.com / Test1234!    → Sin módulos (usuario nuevo)
"""

import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime, timedelta
from app import app
from models import db
from models.user import Usuario, ModuloSuscrito

USUARIOS_PRUEBA = [
    {
        'email': 'admin@test.com',
        'password': 'Admin2024!',
        'nombre': 'Administrador Sistema',
        'empresa': 'CMAJ Asociados SAS',
        'ruc': '0195146942001',
        'is_admin': True,
        'modulos': [],  # Admin tiene acceso total sin módulos
    },
    {
        'email': 'ice_simple@test.com',
        'password': 'Test1234!',
        'nombre': 'Usuario ICE Simple',
        'empresa': 'Empresa Test 1',
        'ruc': '1790012345001',
        'is_admin': False,
        'modulos': ['ice_simple'],
    },
    {
        'email': 'ice_pro@test.com',
        'password': 'Test1234!',
        'nombre': 'Usuario ICE Profesional',
        'empresa': 'Empresa Test 2',
        'ruc': '1790012346001',
        'is_admin': False,
        'modulos': ['ice_simple', 'ice_multiple'],
    },
    {
        'email': 'facturas@test.com',
        'password': 'Test1234!',
        'nombre': 'Usuario Facturas',
        'empresa': 'Empresa Test 3',
        'ruc': '1790012347001',
        'is_admin': False,
        'modulos': ['facturas'],  # incluye catálogo gratis
    },
    {
        'email': 'anexos@test.com',
        'password': 'Test1234!',
        'nombre': 'Usuario Anexos SRI',
        'empresa': 'Empresa Test 4',
        'ruc': '1790012348001',
        'is_admin': False,
        'modulos': ['facturas', 'anexos', 'exportacion'],
    },
    {
        'email': 'descarga@test.com',
        'password': 'Test1234!',
        'nombre': 'Usuario Descarga SRI',
        'empresa': 'Empresa Test 5',
        'ruc': '1790012349001',
        'is_admin': False,
        'modulos': ['descarga_sri'],  # pago único
    },
    {
        'email': 'completo@test.com',
        'password': 'Test1234!',
        'nombre': 'Usuario Plan Completo',
        'empresa': 'Empresa Test 6',
        'ruc': '1790012350001',
        'is_admin': False,
        'modulos': ['ice_simple', 'ice_multiple', 'anexos', 'exportacion',
                    'facturas', 'descarga_sri', 'soporte'],
    },
    {
        'email': 'sin_modulos@test.com',
        'password': 'Test1234!',
        'nombre': 'Usuario Sin Módulos',
        'empresa': 'Empresa Test 7',
        'ruc': '1790012351001',
        'is_admin': False,
        'modulos': [],
    },
]

PRECIOS_MODULOS = {
    'ice_simple': {'precio': 5.00, 'unico': False},
    'ice_multiple': {'precio': 15.00, 'unico': False},
    'anexos': {'precio': 15.00, 'unico': False},
    'exportacion': {'precio': 5.00, 'unico': False},
    'facturas': {'precio': 10.00, 'unico': False},
    'descarga_sri': {'precio': 15.00, 'unico': True},
    'soporte': {'precio': 5.00, 'unico': False},
}


def crear_usuarios():
    with app.app_context():
        creados = 0
        actualizados = 0

        for datos in USUARIOS_PRUEBA:
            usuario = Usuario.query.filter_by(email=datos['email']).first()

            if not usuario:
                usuario = Usuario(
                    email=datos['email'],
                    nombre=datos['nombre'],
                    empresa=datos.get('empresa', ''),
                    ruc=datos.get('ruc', ''),
                    activo=True,
                    is_admin=datos['is_admin'],
                    fecha_registro=datetime.utcnow(),
                )
                usuario.set_password(datos['password'])
                db.session.add(usuario)
                db.session.flush()
                creados += 1
                print(f"  [NUEVO] {datos['email']}")
            else:
                usuario.nombre = datos['nombre']
                usuario.is_admin = datos['is_admin']
                usuario.set_password(datos['password'])
                actualizados += 1
                print(f"  [ACTUALIZADO] {datos['email']}")

            # Crear módulos activos (eliminando los anteriores de prueba)
            ModuloSuscrito.query.filter_by(usuario_id=usuario.id).delete()

            for modulo_id in datos['modulos']:
                info = PRECIOS_MODULOS.get(modulo_id, {})
                precio = info.get('precio', 0)
                es_unico = info.get('unico', False)
                iva = round(precio * 0.12, 2)

                modulo = ModuloSuscrito(
                    usuario_id=usuario.id,
                    modulo_id=modulo_id,
                    estado='activo',
                    es_pago_unico=es_unico,
                    precio_pagado=precio,
                    iva_pagado=iva,
                    duracion_meses=1,
                    fecha_inicio=datetime.utcnow(),
                    fecha_vencimiento=None if es_unico else datetime.utcnow() + timedelta(days=365),
                    verificado=True,
                )
                db.session.add(modulo)

        db.session.commit()
        print(f"\nResumen: {creados} usuario(s) creado(s), {actualizados} actualizado(s).")
        print("\nCredenciales de acceso:")
        print("-" * 60)
        for u in USUARIOS_PRUEBA:
            modulos_str = ', '.join(u['modulos']) if u['modulos'] else '(ninguno - usuario nuevo)'
            admin_str = ' [ADMIN]' if u['is_admin'] else ''
            print(f"  {u['email']}{admin_str}")
            print(f"    Contraseña : {u['password']}")
            print(f"    Módulos    : {modulos_str}")
            print()


if __name__ == '__main__':
    print("Creando usuarios de prueba...\n")
    crear_usuarios()
    print("Listo.")
