from app import create_app
from models import db

app = create_app()
with app.app_context():
    print('=== MIGRACIÓN COMPLETA ===')
    with db.engine.connect() as conn:
        # Usuario
        result = conn.execute(db.text("PRAGMA table_info(usuario)"))
        cols = [row[1] for row in result]
        if 'stripe_customer_id' not in cols:
            conn.execute(db.text('ALTER TABLE usuario ADD COLUMN stripe_customer_id VARCHAR(100)'))
            conn.commit()
            print('✓ stripe_customer_id agregado')
        
        # Suscripcion
        result = conn.execute(db.text("PRAGMA table_info(suscripcion)"))
        cols = [row[1] for row in result]
        if 'fecha_renovacion' not in cols:
            conn.execute(db.text('ALTER TABLE suscripcion ADD COLUMN fecha_renovacion DATETIME'))
            conn.commit()
            print('✓ fecha_renovacion agregado')
        if 'empresa_actual_id' not in cols:
            conn.execute(db.text('ALTER TABLE suscripcion ADD COLUMN empresa_actual_id INTEGER'))
            conn.commit()
            print('✓ empresa_actual_id agregado')
        
        # Empresa
        result = conn.execute(db.text("PRAGMA table_info(empresa)"))
        cols = [row[1] for row in result]
        if 'razon_social' not in cols:
            conn.execute(db.text('ALTER TABLE empresa ADD COLUMN razon_social VARCHAR(300)'))
            conn.commit()
            print('✓ razon_social agregado')
print('=== COMPLETADO ===')
