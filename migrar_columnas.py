from app import create_app
from models import db

app = create_app()
with app.app_context():
    try:
        with db.engine.connect() as conn:
            # Verificar si la columna existe
            result = conn.execute(db.text("PRAGMA table_info(usuario)"))
            columns = [row[1] for row in result]

            if 'stripe_customer_id' not in columns:
                print('Agregando columna stripe_customer_id...')
                conn.execute(db.text('ALTER TABLE usuario ADD COLUMN stripe_customer_id VARCHAR(100)'))
                conn.commit()
                print('OK Columna stripe_customer_id agregada')
            else:
                print('OK Columna stripe_customer_id ya existe')

            # Verificar columnas de suscripcion
            result = conn.execute(db.text("PRAGMA table_info(suscripcion)"))
            columns = [row[1] for row in result]

            if 'empresa_actual_id' not in columns:
                print('Agregando columna empresa_actual_id a suscripcion...')
                conn.execute(db.text('ALTER TABLE suscripcion ADD COLUMN empresa_actual_id INTEGER REFERENCES empresa(id)'))
                conn.commit()
                print('OK Columna empresa_actual_id agregada')
            else:
                print('OK Columna empresa_actual_id ya existe')

            # Verificar columnas de empresa
            result = conn.execute(db.text("PRAGMA table_info(empresa)"))
            columns = [row[1] for row in result]

            if 'razon_social' not in columns:
                print('Agregando columna razon_social a empresa...')
                conn.execute(db.text('ALTER TABLE empresa ADD COLUMN razon_social VARCHAR(300)'))
                conn.commit()
                print('OK Columna razon_social agregada')
            else:
                print('OK Columna razon_social ya existe')

    except Exception as e:
        print(f'Error: {e}')

print('=== Migración completada ===')
