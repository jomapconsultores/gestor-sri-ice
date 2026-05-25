from app import create_app
from models import db
from sqlalchemy import inspect, text

app = create_app()
with app.app_context():
    inspector = inspect(db.engine)
    cols_usuario = [c['name'] for c in inspector.get_columns('usuario')]
    print('Columnas usuario:', cols_usuario)

    r = db.session.execute(text("SELECT email, is_admin FROM usuario WHERE email='admin@test.com'")).fetchone()
    if r:
        print(f'Admin: {r[0]} | is_admin={r[1]}')
    else:
        print('Admin no encontrado')

    tablas = sorted(inspector.get_table_names())
    print(f'Total tablas: {len(tablas)} -> {tablas}')
    print('App OK')
