from app import app, db
from models.user import Usuario, Suscripcion
from datetime import datetime, timedelta
import json

with app.app_context():
    db.create_all()
    
    admin = Usuario(email='admin@test.com', nombre='Administrador')
    admin.set_password('admin123')
    db.session.add(admin)
    
    u1 = Usuario(email='test1@test.com', nombre='Usuario Basico')
    u1.set_password('test123')
    db.session.add(u1)
    db.session.flush()
    s1 = Suscripcion(usuario_id=u1.id, estado='activa', fecha_vencimiento=datetime.utcnow() + timedelta(days=30),
                     modulos_activos=json.dumps(['facturas_ilimitadas']))
    db.session.add(s1)
    
    u2 = Usuario(email='test2@test.com', nombre='Contador Intermedio')
    u2.set_password('test123')
    db.session.add(u2)
    db.session.flush()
    s2 = Suscripcion(usuario_id=u2.id, estado='activa', fecha_vencimiento=datetime.utcnow() + timedelta(days=30),
                     modulos_activos=json.dumps(['facturas_ilimitadas', 'calculo_ice_simple', 'anexos_sri']))
    db.session.add(s2)
    
    u3 = Usuario(email='test3@test.com', nombre='Empresa Completa')
    u3.set_password('test123')
    db.session.add(u3)
    db.session.flush()
    s3 = Suscripcion(usuario_id=u3.id, estado='activa', fecha_vencimiento=datetime.utcnow() + timedelta(days=90),
                     modulos_activos=json.dumps(['facturas_ilimitadas', 'calculo_ice_simple', 'calculo_ice_avanzado',
                                                'anexos_sri', 'exportar_excel', 'descarga_sri', 'soporte',
                                                'clasificacion_gastos']))
    db.session.add(s3)
    
    db.session.commit()
    print("4 usuarios creados!")