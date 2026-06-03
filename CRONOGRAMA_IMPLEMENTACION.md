# 📅 CRONOGRAMA DE IMPLEMENTACIÓN - GESTOR SRI ICE

**Objetivo:** Pasar de BETA a PRODUCCIÓN en 4-6 semanas  
**Versión Target:** 1.0-Production  
**Fecha Estimada Release:** Mediados de Julio 2026

---

## ✅ COMPLETADO (HOY - 3 de Junio)

### Infraestructura Base
- [x] `.env` con variables sensibles
- [x] `.gitignore` actualizado
- [x] `config.py` con carga de `.env`
- [x] Módulo `validaciones_sri.py` (Validaciones tributarias)
- [x] Suite de tests `test_validaciones_sri.py` (40+ test cases)
- [x] `invoices.py` actualizado con validaciones
- [x] APIs configuradas (Mistral + Codestral)

### Security Fixes
- [x] Eliminar hardcoded credentials
- [x] Implementar RUC validation (módulo-11)
- [x] Periodo fiscal validation
- [x] XXE mitigation (defusedxml)
- [x] Path traversal fix (secure_filename)
- [x] Race condition fix (session isolation)

### Tributarias
- [x] Agrupar IVA por tarifa (0%, 5%, 12%, 15%)
- [x] Validación de gastos personales (USD 1,500)
- [x] Límites turismo/arte-cultura
- [x] Cálculo crédito tributario IVA

---

## 📅 SEMANA 1-2: CORRECCIONES CRÍTICAS (7-10 días)

### Día 1-2: IVA Por Tarifa (CRÍTICO)

**Módulos afectados:** invoices, facturas_ingreso, registro_completo

**Tasks:**
- [ ] Actualizar `xml_parser.py` para extraer tarifa de cada línea
- [ ] Actualizar `facturas_ingreso.py` para usar `agrupar_iva_por_tarifa()`
- [ ] Actualizar `registro_completo.py` procesar_ingresos()
- [ ] Agregar campo `notas_auditoria` a tabla Factura (para detalles IVA)
- [ ] Tests: `test_iva_tarifas_correcto.py` (20+ casos)

**Validación:**
```bash
pytest tests/test_iva_*.py -v
# Debe pasar: 20/20 tests
```

---

### Día 3-4: Filtro usuario_id (CRÍTICO)

**Módulos afectados:** facturas_ingreso, retenciones, registro_completo, empresas

**Tasks:**
- [ ] `facturas_ingreso.procesar()` - Agregar `usuario_id=current_user.id` filter
- [ ] `retenciones.procesar()` - Agregar filtro usuario_id
- [ ] `registro_completo.procesar_*()` - Agregar filtros en ALL queries
- [ ] `empresas.seleccionar_empresa()` - Validar propiedad
- [ ] Tests: `test_acceso_datos.py` (GDPR compliance)

**Validación:**
```bash
pytest tests/test_acceso_datos.py -v
# Resultado: Usuario A NO puede ver datos Usuario B
```

---

### Día 5: XXE + Gastos (CRÍTICO)

**Módulos afectados:** ats, retenciones, sri_processor, gastos

**Tasks:**
- [ ] Reemplazar `ET.parse()` → `defusedxml.ElementTree.parse()` en ats, retenciones, sri_processor
- [ ] `gastos.py` - Agregar validación USD 1,500 limite
- [ ] `gastos.py` - Validar 20% turismo
- [ ] `gastos.py` - Validar 10% arte/cultura
- [ ] Tests: `test_xxe_protection.py` (XXE injection tests)

**Validación:**
```bash
pytest tests/test_xxe_protection.py -v
# Resultado: XXE blocked, gastos limits enforced
```

---

## 📅 SEMANA 2-3: INTEGRACIONES (7-10 días)

### Día 6-8: Crédito Tributario IVA

**Tabla nueva:** `saldo_iva_mes` (usuario_id, anio, mes, saldo)

**Tasks:**
- [ ] Crear migración BD para `saldo_iva_mes`
- [ ] Implementar `calcular_saldo_iva_mes(usuario_id, anio, mes)`
- [ ] Integrar en formulario 104
- [ ] Validar arrastre 5 años máximo
- [ ] Tests: `test_credito_tributario.py` (15+ casos)

**SQL:**
```sql
CREATE TABLE saldo_iva_mes (
    id INTEGER PRIMARY KEY,
    usuario_id INTEGER NOT NULL,
    anio INTEGER NOT NULL,
    mes INTEGER NOT NULL,
    iva_cobrado NUMERIC(12,2),
    iva_pagado NUMERIC(12,2),
    saldo_anterior NUMERIC(12,2),
    saldo_final NUMERIC(12,2),
    fecha_calculo DATETIME,
    UNIQUE(usuario_id, anio, mes),
    FOREIGN KEY(usuario_id) REFERENCES usuario(id)
)
```

---

### Día 9-10: Auditoría Global

**Tabla nueva:** `auditoria_cambios` (log de TODOS los cambios)

**Tasks:**
- [ ] Crear migración BD para `auditoria_cambios`
- [ ] Crear decorador `@registrar_auditoria`
- [ ] Aplicar a: gastos, facturas, pagos, módulos, usuarios
- [ ] Tests: `test_auditoria.py` (10+ casos)

**SQL:**
```sql
CREATE TABLE auditoria_cambios (
    id INTEGER PRIMARY KEY,
    usuario_id INTEGER,
    modulo VARCHAR(50),
    accion VARCHAR(20),  -- CREATE, UPDATE, DELETE
    tabla VARCHAR(50),
    registro_id INTEGER,
    datos_anterior JSON,
    datos_nuevo JSON,
    ip_address VARCHAR(45),
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(usuario_id) REFERENCES usuario(id)
)
```

---

## 📅 SEMANA 3-4: VALIDACIONES SRI (7-10 días)

### Día 11-13: RUC + Período + Importes

**Tasks:**
- [ ] Tests: `test_ruc_validation.py` (20+ RUCs reales/inválidos)
- [ ] Tests: `test_periodo_fiscal.py` (límites, prescripción)
- [ ] Tests: `test_importes.py` (negativos, redondeo, máximos)
- [ ] Integrar validaciones en TODOS los endpoints

**Validación:**
```bash
pytest tests/test_ruc_*.py tests/test_periodo_*.py tests/test_importes.py -v
# Resultado: 50+ tests passing
```

---

### Día 14-15: Generación de Reportes SRI

**Reportes a generar:**
1. Formulario 104 (IVA) - XML/PDF
2. Anexo ICE/PVP - XML/JSON
3. ATS - TXT/XML
4. Retenciones - XML
5. Certificado de pagos

**Tasks:**
- [ ] Crear `servicios/generador_formulario_104.py`
- [ ] Crear `servicios/generador_anexo_ice.py`
- [ ] Crear `servicios/generador_ats.py`
- [ ] Tests: `test_generacion_reportes.py`

---

## 📅 SEMANA 4: TESTING + DOCUMENTATION (7 días)

### Día 16-18: Testing Exhaustivo

**Tipo de tests:**
- [x] Unit tests (validaciones) ✅
- [ ] Integration tests (flujos completos)
- [ ] E2E tests (usuario completo desde carga a reporte)
- [ ] Security tests (OWASP Top 10)
- [ ] Performance tests (1,000+ facturas)

**Coverage target:** 85%+

```bash
pytest tests/ --cov=services --cov=routes --cov-report=html
# Generar HTML coverage report
```

---

### Día 19-20: Documentación + Capacitación

**Documentos:**
- [ ] API Reference (Swagger/OpenAPI)
- [ ] User Manual (paso a paso)
- [ ] Admin Guide (configuración, mantenimiento)
- [ ] Compliance Checklist (requisitos SRI)
- [ ] Troubleshooting Guide

**Capacitación:**
- [ ] Video: Cómo cargar facturas
- [ ] Video: Interpretación de reportes
- [ ] Q&A webinar

---

## 📅 SEMANA 4-5: BETA TESTING (7-10 días)

### Fase Beta Controlada

**Participantes:** 10-20 usuarios de prueba + equipo interno

**Criterios Beta:**
1. ✅ Todos los tests pasan
2. ✅ 85%+ code coverage
3. ✅ Validaciones SRI completas
4. ✅ Documentación lista
5. ✅ Sin bugs críticos

**Monitoreo Beta:**
- [ ] Logs en tiempo real
- [ ] Error tracking (Sentry/New Relic)
- [ ] User feedback form
- [ ] Performance monitoring

**Salida Beta:**
- [ ] 0 bugs CRÍTICOS
- [ ] < 5 bugs ALTOS
- [ ] Feedback positivo 80%+

---

## 📅 SEMANA 5-6: RELEASE A PRODUCCIÓN

### Preparación Release (Día 26-28)

**Checklist:**
- [ ] `CHANGELOG.md` actualizado
- [ ] Versión en `__about__.py` = "1.0.0"
- [ ] Tag git: `v1.0.0-production`
- [ ] README.md actualizado
- [ ] Backup BD producción
- [ ] Plan rollback documentado

---

### Deployment (Día 29-30)

**Timeline:**
```
07:00 - Pre-deploy checks
08:00 - Deploy a staging
09:00 - Smoke tests en staging
10:00 - Deploy a producción (primero 10% tráfico)
11:00 - Monitor 100% tráfico (1 hora)
12:00 - Anunciar a usuarios
```

**Post-Deploy Monitoring:**
- [ ] 24/7 monitoring primeras 48 horas
- [ ] Team on-call
- [ ] Runbook de rollback listo
- [ ] Comunicación canal #deploy

---

## 🎯 CHECKLIST DE RELEASE

### Antes de Deploy

- [ ] Todos los tests pasan (100%)
- [ ] Code review aprobado
- [ ] Security review completado
- [ ] Performance tests OK (< 2s response time)
- [ ] Database migration tested
- [ ] Backups creados
- [ ] Rollback plan documentado
- [ ] Team notificado

### Después de Deploy

- [ ] Monitoreo en vivo primeras 2 horas
- [ ] Logs sin errores CRÍTICOS
- [ ] Usuarios pueden cargar facturas
- [ ] Reportes SRI se generan correctamente
- [ ] Email notificaciones funcionando
- [ ] Métricas dentro de rangos esperados

---

## 📊 MÉTRICAS DE ÉXITO

| Métrica | Target | Actual |
|---------|--------|--------|
| Tests Pasando | 100% | ? |
| Code Coverage | 85%+ | ? |
| Performance (facturas/seg) | 100+ | ? |
| Uptime | 99.9%+ | ? |
| Bugs CRÍTICOS | 0 | ? |
| Bugs ALTOS | < 5 | ? |
| User Satisfaction | 80%+ | ? |
| SRI Compliance | 100% | ? |

---

## 🚨 RIESGOS + MITIGACIÓN

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|--------------|--------|-----------|
| IVA incorrecto en producción | MEDIA | CRÍTICO | Tests + SRI lawyer review |
| Datos usuario expuestos | BAJA | CRÍTICO | Security audit + penetration test |
| Performance issue con 1000+ facturas | BAJA | ALTO | Load tests + optimize DB indices |
| SRI API no disponible | BAJA | ALTO | Caché + offline mode |
| Rollback fallar | BAJA | CRÍTICO | Dry-run rollback antes de deploy |

---

## 📞 CONTACTOS CRÍTICOS

| Rol | Nombre | Email | Teléfono |
|-----|--------|-------|----------|
| Product Manager | Marco Antonio | jomapconsultores@gmail.com | +593-963511411 |
| SRI Compliance | [Contador] | - | - |
| DevOps | [Equipo] | - | - |
| Support | [Equipo] | - | - |

---

## 📝 NOTAS

- **Deadline ideal:** Mediados de Julio 2026
- **Buffer:** +2 semanas para imprevistos
- **Critical path:** IVA → Acceso datos → Tests → Deploy
- **Go/No-Go decision:** Viernes semana 4 (Beta review)

---

**Estado Actual:** 🟢 **ON TRACK**

Última actualización: 3 de Junio, 2026
