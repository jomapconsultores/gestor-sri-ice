-- Migración: Agregar columna notas_auditoria a tabla factura
-- Descripción: La columna notas_auditoria se usa para almacenar detalles de IVA y auditoría
-- Fecha: 2026-06-03

ALTER TABLE factura ADD COLUMN IF NOT EXISTS notas_auditoria TEXT;

-- Comentario para PostgreSQL
COMMENT ON COLUMN factura.notas_auditoria IS 'Notas de auditoría y detalles de procesamiento (ej: detalles IVA por tarifa)';
