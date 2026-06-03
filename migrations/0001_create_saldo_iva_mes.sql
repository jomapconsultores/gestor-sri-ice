-- Migración: Crear tabla saldo_iva_mes para rastrear crédito tributario IVA
-- Propósito: Almacenar el saldo de IVA del mes (cobrado - pagado + saldo anterior)
-- Uso: Cálculo del Formulario 104 y ATS

CREATE TABLE IF NOT EXISTS saldo_iva_mes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER NOT NULL,
    anio INTEGER NOT NULL,
    mes INTEGER NOT NULL,
    iva_cobrado NUMERIC(12, 2) DEFAULT 0,
    iva_pagado NUMERIC(12, 2) DEFAULT 0,
    saldo_anterior NUMERIC(12, 2) DEFAULT 0,
    saldo_final NUMERIC(12, 2) DEFAULT 0,
    nota TEXT,
    fecha_calculo DATETIME DEFAULT CURRENT_TIMESTAMP,
    fecha_actualizacion DATETIME DEFAULT CURRENT_TIMESTAMP,

    -- Restricciones
    UNIQUE(usuario_id, anio, mes),
    FOREIGN KEY(usuario_id) REFERENCES usuario(id) ON DELETE CASCADE
);

-- Índices para consultas rápidas
CREATE INDEX IF NOT EXISTS idx_saldo_iva_mes_usuario_anio
    ON saldo_iva_mes(usuario_id, anio);

CREATE INDEX IF NOT EXISTS idx_saldo_iva_mes_usuario_anio_mes
    ON saldo_iva_mes(usuario_id, anio, mes);

-- Comentarios (para documentación)
-- saldo_final = iva_cobrado - iva_pagado + saldo_anterior
-- Si saldo_final > 0: Usuario puede solicitar devolución o usar como crédito
-- Si saldo_final < 0: Usuario debe pagar la diferencia al SRI
-- Arrastre: saldo_final de mes N es saldo_anterior del mes N+1
