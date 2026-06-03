-- Migración: Crear tabla auditoria_cambios para rastrear TODOS los cambios
-- Propósito: Auditoría completa de cambios en el sistema (GDPR + SRI)
-- Cumplimiento: ISO 27001, RGPD, Normativas SRI

CREATE TABLE IF NOT EXISTS auditoria_cambios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER NOT NULL,
    modulo VARCHAR(50) NOT NULL,
    accion VARCHAR(20) NOT NULL,  -- CREATE, UPDATE, DELETE, READ
    tabla VARCHAR(50) NOT NULL,
    registro_id INTEGER,
    datos_anterior JSON,  -- Estado anterior (para UPDATE/DELETE)
    datos_nuevo JSON,     -- Estado nuevo (para CREATE/UPDATE)
    ip_address VARCHAR(45),
    user_agent TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,

    -- Restricciones
    FOREIGN KEY(usuario_id) REFERENCES usuario(id) ON DELETE CASCADE
);

-- Índices para consultas rápidas
CREATE INDEX IF NOT EXISTS idx_auditoria_usuario_timestamp
    ON auditoria_cambios(usuario_id, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_auditoria_tabla_registro
    ON auditoria_cambios(tabla, registro_id);

CREATE INDEX IF NOT EXISTS idx_auditoria_accion
    ON auditoria_cambios(accion);

CREATE INDEX IF NOT EXISTS idx_auditoria_timestamp
    ON auditoria_cambios(timestamp DESC);

-- Comentarios (documentación)
-- accion: CREATE (nuevo registro), UPDATE (modificación), DELETE (eliminación), READ (consulta)
-- datos_anterior: Estado antes del cambio (NULL para CREATE)
-- datos_nuevo: Estado después del cambio (NULL para DELETE)
-- Útil para: Trazabilidad, auditoría, cumplimiento normativo, recuperación
