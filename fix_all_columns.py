from app import create_app
from models import db

app = create_app()
with app.app_context():
    print('=== MIGRACIÓN COMPLETA DE TODAS LAS COLUMNAS ===')
    with db.engine.connect() as conn:
        
        # TABLA USUARIO
        print('\n[1/3] Tabla USUARIO')
        result = conn.execute(db.text("PRAGMA table_info(usuario)"))
        cols = [row[1] for row in result]
        if 'stripe_customer_id' not in cols:
            conn.execute(db.text('ALTER TABLE usuario ADD COLUMN stripe_customer_id VARCHAR(100)'))
            conn.commit()
            print('  ✓ stripe_customer_id agregado')
        else:
            print('  ✓ stripe_customer_id existe')
        
        # TABLA SUSCRIPCION - TODAS LAS COLUMNAS
        print('\n[2/3] Tabla SUSCRIPCION')
        result = conn.execute(db.text("PRAGMA table_info(suscripcion)"))
        cols = [row[1] for row in result]
        
        columnas_susc = [
            ('fecha_renovacion', 'DATETIME'),
            ('stripe_subscription_id', 'VARCHAR(100)'),
            ('facturas_procesadas_mes', 'INTEGER DEFAULT 0'),
            ('empresa_actual_id', 'INTEGER'),
        ]
        
        for col_name, col_type in columnas_susc:
            if col_name not in cols:
                conn.execute(db.text(f'ALTER TABLE suscripcion ADD COLUMN {col_name} {col_type}'))
                conn.commit()
                print(f'  ✓ {col_name} agregado')
            else:
                print(f'  ✓ {col_name} existe')
        
        # TABLA EMPRESA
        print('\n[3/3] Tabla EMPRESA')
        result = conn.execute(db.text("PRAGMA table_info(empresa)"))
        cols = [row[1] for row in result]
        if 'razon_social' not in cols:
            conn.execute(db.text('ALTER TABLE empresa ADD COLUMN razon_social VARCHAR(300)'))
            conn.commit()
            print('  ✓ razon_social agregado')
        else:
            print('  ✓ razon_social existe')

print('\n=== ✓ MIGRACIÓN COMPLETADA ===')
print('Ejecuta: python app.py')
