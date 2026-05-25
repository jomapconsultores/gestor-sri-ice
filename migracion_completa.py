from app import create_app
from models import db

app = create_app()
with app.app_context():
    print('=== MIGRACIÓN COMPLETA BASE DE DATOS ===')

    with db.engine.connect() as conn:

        # ===== TABLA PLANES =====
        print('\n[1/5] Creando tabla PLANES...')
        conn.execute(db.text('''
            CREATE TABLE IF NOT EXISTS planes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                codigo VARCHAR(50) UNIQUE NOT NULL,
                nombre VARCHAR(100) NOT NULL,
                descripcion TEXT,
                precio_mensual NUMERIC(10,2),
                precio_unico NUMERIC(10,2),
                tipo VARCHAR(20) DEFAULT 'mensual',
                activo BOOLEAN DEFAULT 1,
                orden INTEGER DEFAULT 0
            )
        '''))
        conn.commit()
        print('  ✓ Tabla planes creada')

        # ===== TABLA SUSCRIPCION_DETALLE =====
        print('\n[2/5] Creando tabla SUSCRIPCION_DETALLE...')
        conn.execute(db.text('''
            CREATE TABLE IF NOT EXISTS suscripcion_detalle (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                suscripcion_id INTEGER NOT NULL,
                plan_codigo VARCHAR(50) NOT NULL,
                activo BOOLEAN DEFAULT 1,
                fecha_activacion DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (suscripcion_id) REFERENCES suscripcion(id)
            )
        '''))
        conn.commit()
        print('  ✓ Tabla suscripcion_detalle creada')

        # ===== MODIFICAR SUSCRIPCION =====
        print('\n[3/5] Modificando tabla SUSCRIPCION...')
        result = conn.execute(db.text("PRAGMA table_info(suscripcion)"))
        cols = [row[1] for row in result]

        if 'descarga_sri_activa' not in cols:
            conn.execute(db.text('ALTER TABLE suscripcion ADD COLUMN descarga_sri_activa BOOLEAN DEFAULT 0'))
            conn.commit()
            print('  ✓ Campo descarga_sri_activa agregado')

        # ===== MODIFICAR FACTURA_EMITIDA =====
        print('\n[4/5] Modificando tabla FACTURA_EMITIDA...')
        result = conn.execute(db.text("PRAGMA table_info(factura_emitida)"))
        cols = [row[1] for row in result]

        if 'fecha_emision_real' not in cols:
            conn.execute(db.text('ALTER TABLE factura_emitida ADD COLUMN fecha_emision_real DATE'))
            conn.commit()
            print('  ✓ Campo fecha_emision_real agregado')

        if 'emitida' not in cols:
            conn.execute(db.text('ALTER TABLE factura_emitida ADD COLUMN emitida BOOLEAN DEFAULT 0'))
            conn.commit()
            print('  ✓ Campo emitida agregado')

        # ===== INSERTAR PLANES INICIALES =====
        print('\n[5/5] Insertando catálogo de planes...')

        planes_data = [
            ('ICE_SIMPLE', 'Cálculo ICE Simple', 'Cálculo básico de ICE', 5.00, None, 'mensual', 1, 1),
            ('ICE_MULTIPLE', 'Cálculo ICE Múltiple y Mezcla', 'Cálculo avanzado con productos múltiples', 15.00, None, 'mensual', 1, 2),
            ('ANEXOS_SRI', 'Generación Anexos SRI', 'Anexos PVP e ICE', 15.00, None, 'mensual', 1, 3),
            ('FACTURAS_ILIMITADAS', 'Facturas Ilimitadas', 'Procesamiento XMLs ingresos y gastos', 10.00, None, 'mensual', 1, 4),
            ('EXPORTAR_REPORTES', 'Exportación Reportes Excel', 'Exportar todos los reportes de módulos', 5.00, None, 'mensual', 1, 5),
            ('DESCARGA_SRI', 'Descarga Masiva SRI', 'Instalador para descargar facturas', None, 15.00, 'unico', 1, 6),
            ('SOPORTE_PRIORITARIO', 'Soporte Prioritario', 'Atención prioritaria', 5.00, None, 'mensual', 1, 7),
        ]

        for plan in planes_data:
            try:
                conn.execute(db.text('''
                    INSERT OR IGNORE INTO planes
                    (codigo, nombre, descripcion, precio_mensual, precio_unico, tipo, activo, orden)
                    VALUES (:codigo, :nombre, :desc, :pm, :pu, :tipo, :activo, :orden)
                '''), {
                    'codigo': plan[0], 'nombre': plan[1], 'desc': plan[2],
                    'pm': plan[3], 'pu': plan[4], 'tipo': plan[5],
                    'activo': plan[6], 'orden': plan[7]
                })
            except Exception as e:
                print(f'  ! Error en plan {plan[0]}: {e}')

        conn.commit()
        print('  ✓ Planes insertados')

print('\n=== ✓ MIGRACIÓN COMPLETADA ===')