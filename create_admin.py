"""
Script para crear el usuario administrador en producción.
Ejecutar desde Render Shell:
  python create_admin.py
"""
from app import create_app
from models import db
from models.user import Usuario

app = create_app()

with app.app_context():
    email = 'jomapconsultores@outlook.com'
    admin = Usuario.query.filter_by(email=email).first()

    if admin:
        if not admin.is_admin:
            admin.is_admin = True
            db.session.commit()
            print(f'✅ Usuario {email} actualizado a administrador.')
        else:
            print(f'ℹ️  {email} ya es administrador.')
    else:
        admin = Usuario(
            email=email,
            nombre='Admin CMAJ',
            empresa='CMAJ ASOCIADOS SAS',
            ruc='0195146942001',
            is_admin=True,
            activo=True,
        )
        admin.set_password('Admin2024!')
        db.session.add(admin)
        db.session.commit()
        print(f'✅ Admin creado: {email} / Admin2024!')
        print('⚠️  Cambia la contraseña después del primer login.')
