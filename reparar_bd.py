from app import create_app
from models import db

app = create_app()
with app.app_context():
    print('=== REPARANDO BASE DE DATOS ===')
    
    with db.engine.connect() as conn:
        # Ver estructura actual
        print('\n--- Verificando SUSCRIPCION ---')
        result = conn.execute(db.text("PRAGMA table_info(suscripcion)"))
        cols_actuales = [row[1] for row in result]
        print(f'Columnas actuales: {cols_actuales}')
        
        # Columnas que DEBEN existir
        columnas_requeridas = {
            'stripe_subscription_id': 'VARCHAR(100)',
            'facturas_procesadas_mes': 'INTEGER DEFAULT 0',
            'fecha_renovacion': 'DATETIME',
            'empresa_actual_id': 'INTEGER'
        }
        
        # Agregar las que faltan
        for col_name, col_type in columnas_requeridas.items():
            if col_name not in cols_actuales:
                print(f'  + Agregando {col_name}...')
                conn.execute(db.text(f'ALTER TABLE suscripcion ADD COLUMN {col_name} {col_type}'))
                conn.commit()
            else:
                print(f'  ✓ {col_name} ya existe')
        
        # Verificar resultado
        print('\n--- Verificación final ---')
        result = conn.execute(db.text("PRAGMA table_info(suscripcion)"))
        cols_finales = [row[1] for row in result]
        print(f'Columnas después: {cols_finales}')
        
        # Verificar otras tablas
        print('\n--- Verificando USUARIO ---')
        result = conn.execute(db.text("PRAGMA table_info(usuario)"))
        cols = [row[1] for row in result]
        if 'stripe_customer_id' not in cols:
            print('  + Agregando stripe_customer_id...')
            conn.execute(db.text('ALTER TABLE usuario ADD COLUMN stripe_customer_id VARCHAR(100)'))
            conn.commit()
        else:
            print('  ✓ stripe_customer_id existe')
        
        print('\n--- Verificando EMPRESA ---')
        result = conn.execute(db.text("PRAGMA table_info(empresa)"))
        cols = [row[1] for row in result]
        if 'razon_social' not in cols:
            print('  + Agregando razon_social...')
            conn.execute(db.text('ALTER TABLE empresa ADD COLUMN razon_social VARCHAR(300)'))
            conn.commit()
        else:
            print('  ✓ razon_social existe')

print('\n=== ✓ BASE DE DATOS REPARADA ===')
print('\nAhora ejecuta: python app.py')
