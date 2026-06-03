# 👥 Guía del Usuario - Gestor SRI ICE

**Versión:** 1.0  
**Idioma:** Español  
**Última Actualización:** 3 Junio, 2026

---

## 📖 Tabla de Contenidos

1. [Introducción](#introducción)
2. [Primeros Pasos](#primeros-pasos)
3. [Gestión de Facturas](#gestión-de-facturas)
4. [Generación de Reportes](#generación-de-reportes)
5. [Auditoría y Cumplimiento](#auditoría-y-cumplimiento)
6. [Preguntas Frecuentes](#preguntas-frecuentes)
7. [Soporte](#soporte)

---

## 📚 Introducción

**Gestor SRI ICE** es una plataforma integral para gestionar facturas e impuestos según la normativa del SRI (Servicio de Rentas Internas) de Ecuador.

### Características Principales

✅ **Gestión Integral de Facturas**
- Cargar facturas de ingresos y gastos
- Validación automática según SRI
- Categorización inteligente

✅ **Reportes SRI Automáticos**
- Formulario 104 (IVA)
- Anexo ICE/PVP
- ATS (Archivo Técnico Tributario)
- Certificados de Retención

✅ **Cálculo de Crédito Tributario**
- Mes a mes
- Seguimiento año completo
- Proyecciones de IVA

✅ **Auditoría Completa**
- Historial de cambios
- Cumplimiento GDPR
- Trazabilidad total

---

## 🚀 Primeros Pasos

### Paso 1: Acceder a la Plataforma

```
1. Ir a https://gestor-sri-ice.com
2. Hacer clic en "Ingresar"
3. Usar tu email y contraseña
4. ¡Listo! Ya estás dentro
```

### Paso 2: Completar Perfil Empresa

```
Ir a: Perfil → Mi Empresa
├─ Nombre: Tu razón social
├─ RUC: 13 dígitos (ej: 0191234567001)
├─ Dirección: Domicilio fiscal
├─ Teléfono: Para contacto
└─ Guardar cambios
```

### Paso 3: Configurar Impuestos

```
Ir a: Configuración → Impuestos
├─ Tarifas IVA: 0%, 5%, 12%, 15%
├─ Número de cargas: (para gastos personales)
├─ Períodos: Año fiscal actual
└─ Guardar
```

---

## 📝 Gestión de Facturas

### Cargar Factura de Ingreso

```
1. Ir a: Facturas → Nuevas Facturas
2. Seleccionar: "Factura de Ingreso"
3. Completar datos:
   ├─ Número factura: 001-001-000000001
   ├─ Fecha emisión: DD/MM/YYYY
   ├─ RUC cliente: 13 dígitos
   ├─ Base IVA: Monto sin impuesto
   ├─ Tarifa: 0%, 5%, 12% o 15%
   └─ Guardar
4. ¡Automáticamente se calcula el IVA!
```

### Cargar Factura de Gasto

```
1. Ir a: Facturas → Nuevas Facturas
2. Seleccionar: "Factura de Gasto"
3. Completar datos:
   ├─ Número factura: 002-001-000000001
   ├─ Fecha emisión: DD/MM/YYYY
   ├─ RUC proveedor: 13 dígitos
   ├─ Descripción: ¿Qué es?
   ├─ Base IVA: Monto
   ├─ Tarifa: Seleccionar
   └─ Categoría: (personal, operativo, etc.)
4. Guardar
```

### Validación Automática

El sistema valida automáticamente:
- ✅ RUC formato 13 dígitos
- ✅ RUC checksum (módulo-11)
- ✅ Fecha no futuro
- ✅ Período fiscal (max 5 años atrás)
- ✅ Montos positivos
- ✅ Tarifas IVA válidas

---

## 📊 Generación de Reportes

### Formulario 104 (IVA)

```
Ir a: Reportes → Formulario 104
├─ Seleccionar periodo: Año/Mes
├─ Ver preview (JSON)
├─ Descargar opciones:
│  ├─ Excel (para editar)
│  ├─ XML (para SRI)
│  └─ JSON (para sistema)
└─ ✅ Listo para declaración
```

**¿Qué contiene?**
- Ventas por tarifa IVA
- Compras por tarifa IVA
- Crédito tributario calculado
- Saldo a pagar o a favor

### Anexo ICE/PVP

```
Ir a: Reportes → Anexo ICE
├─ Período: Año/Mes
├─ Formatos:
│  ├─ Excel (detallado)
│  ├─ JSON (preview)
│  └─ XML (SRI)
└─ Descargable
```

**¿Qué contiene?**
- Productos con ICE
- Por categoría (bebidas, combustibles, etc.)
- Tasa y monto de ICE
- Detalles transacción

### ATS (Archivo Técnico Tributario)

```
Ir a: Reportes → ATS
├─ Período: Año/Mes
├─ Formato archivo plano (TXT)
├─ Enviable directamente a SRI
└─ Con checksums validados
```

**¿Qué contiene?**
- Cabecera con datos empresa
- Cada transacción factura
- Checksums para validación
- Formato oficial SRI

### Certificado de Retenciones

```
Ir a: Reportes → Retenciones
├─ Período: Año/Mes
├─ Imprimible (HTML)
├─ Enviable a proveedores
└─ Con datos retención 30% IVA
```

**¿Qué contiene?**
- Facturas con retención
- Monto retenido
- RUC proveedor
- Total retenido periodo

### Paquete Completo (ZIP)

```
Ir a: Reportes → Descargar Todo
├─ Obtiene en ZIP:
│  ├─ Formulario 104 (Excel)
│  ├─ Anexo ICE (Excel)
│  ├─ ATS (Archivo plano)
│  └─ Retenciones (HTML)
└─ ¡Todo en un archivo!
```

---

## 🔒 Auditoría y Cumplimiento

### Ver Historial de Cambios

```
Ir a: Auditoría → Historial
├─ Listar todos los cambios
├─ Por tabla: factura, usuario, etc.
├─ Límite de registros: 1-200
└─ Ver detalles:
   ├─ Usuario que cambió
   ├─ Qué cambió
   ├─ Fecha/hora exacta
   ├─ IP del equipo
   └─ Navegador usado
```

### Filtrar por Rango de Fechas

```
Ir a: Auditoría → Por Fechas
├─ Desde: DD/MM/YYYY
├─ Hasta: DD/MM/YYYY
├─ Por tabla: (opcional)
└─ Búsqueda automática
```

### Ver por Tipo de Acción

```
Ir a: Auditoría → Por Acción
├─ CREATE: Nuevos registros
├─ UPDATE: Cambios
├─ DELETE: Eliminaciones
└─ READ: Consultas
```

### Resumen Mensual

```
Ir a: Auditoría → Resumen
├─ Últimos 30 días
├─ Total cambios
├─ Por acción: CREATE, UPDATE, DELETE
├─ Por tabla: factura, usuario, etc.
└─ Cambios más recientes
```

---

## ❓ Preguntas Frecuentes

### P: ¿Cuál es la tarifa IVA correcta?

**R:** Las tarifas en Ecuador son:
- **0%** - Productos de canasta básica, agua, energía
- **5%** - Servicios algunos, productos agropecuarios
- **12%** - Mayoría de productos y servicios
- **15%** - Algunas bebidas y servicios especiales

Si no estás seguro, es mejor usar 12% (tarifa general).

---

### P: ¿Qué es el Crédito Tributario?

**R:** Es el IVA que pagaste en compras que puedes restar del IVA que cobraste en ventas.

```
Ejemplo:
Ventas: $5,000 + IVA $600 = $5,600
Compras: $3,000 + IVA $360 = $3,360

IVA a pagar = $600 - $360 = $240

Si la diferencia es negativa, tienes CRÉDITO (SRI te devuelve).
```

---

### P: ¿Qué es el RUC?

**R:** Registro Único de Contribuyentes. Es el número único de identificación fiscal.
- Formato: 13 dígitos (ej: 0191234567001)
- Primeros 2: Código provincia
- Últimos 3: Dígitos de control

---

### P: ¿Cuánto puedo deducir en gastos personales?

**R:** Depende del número de dependientes (cargas):

| Cargas | Límite USD |
|--------|-----------|
| 0 | $1,035.47 |
| 1 | $1,331.32 |
| 2 | $1,627.16 |
| 3 | $2,070.94 |
| 4 | $2,514.71 |
| 6+ | $14,792.40 |

Turismo: Máximo 20% del deducible
Cultura/Arte: Máximo 10% del deducible

---

### P: ¿Cuándo vence la declaración del SRI?

**R:** Depende de tu RUC:
- Termina en 0-3: 11 de cada mes
- Termina en 4-7: 14 de cada mes
- Termina en 8-9: 17 de cada mes

Se presenta cada mes (IVA) y anualmente (IR).

---

### P: ¿Qué es el ATS?

**R:** Archivo Técnico Tributario. Documento que contiene detalle de todas tus transacciones. Es enviado electrónicamente al SRI.

---

### P: ¿Qué documentos debo guardar?

**R:** Obligatoriamente:
- ✅ Facturas originales
- ✅ Comprobantes retención
- ✅ Comprobantes IVA
- ✅ Comprobantes pago impuestos
- ✅ Documento crédito tributario

**Tiempo:** Mínimo 5 años (prescripción).

---

## 🆘 Soporte

### Contactos

**Email:** support@gestor-sri-ice.com  
**Teléfono:** +593 2 XXXX XXXX  
**WhatsApp:** +593 99 999 9999  
**Horario:** Lunes-Viernes, 9am-6pm ECT  

### Centro de Ayuda

Visita nuestra base de conocimiento:
```
https://gestor-sri-ice.com/ayuda
├─ Preguntas frecuentes
├─ Tutoriales en video
├─ Documentos descargables
└─ Contacto directo
```

### Reportar Problemas

Si encuentras un error:
```
1. Ir a: Perfil → Reportar Problema
2. Describir: Qué pasó, cuándo, cómo reproducir
3. Adjuntar: Capturas de pantalla
4. Enviar: Automáticamente recibimos
5. Esperar: Respuesta en máximo 24 horas
```

---

## 📱 Acceso Móvil

La plataforma es completamente responsive:
- ✅ Funciona en iPhone y Android
- ✅ Interfaz optimizada para móvil
- ✅ Descarga de reportes desde app
- ✅ Cargar facturas con cámara

---

## 🔐 Seguridad de Tu Cuenta

### Mejores Prácticas

```
✅ DO:
   - Usar contraseña fuerte (12+ caracteres)
   - Activar 2FA (autenticación doble factor)
   - Logout cuando termines
   - Cambiar contraseña cada 3 meses
   - Usar HTTPS siempre

❌ DON'T:
   - Compartir tu login con otros
   - Usar WiFi público para conectar
   - Guardar contraseña en navegador
   - Hacer screenshot de datos sensibles
   - Dejar sesión abierta en PC compartida
```

---

## 💡 Tips y Trucos

### Tip 1: Importación Masiva
Puedes subir múltiples facturas en un CSV:
```
numero_factura,ruc,descripcion,base_iva,tarifa,fecha
001-001-000000001,0192000000001,Venta,1000,12,2026-06-01
001-001-000000002,0192000000001,Venta,2000,12,2026-06-01
```

### Tip 2: Búsqueda Avanzada
Busca facturas por:
- Rango de fechas
- Rango de montos
- Tarifa IVA
- Tipo (ingreso/gasto)

### Tip 3: Exporta a Excel
Todos los reportes se abren en Excel para editar:
- Cambiar formatos
- Agregar columnas
- Hacer análisis adicional

---

## 📅 Calendario de Plazos

```
Cada Mes (por RUC):
├─ Día 11, 14 o 17: Declaración IVA
└─ Archivos: Descarga reportes en Gestor

Cada Año (Enero):
├─ Impuesto a la Renta (IR)
├─ Anexo Gastos Personales
└─ ATS completo año anterior

Aniversario RUC (Anual):
├─ Actualización datos
├─ Revisar cargas dependientes
└─ Confirmar actividad
```

---

**¡Gracias por usar Gestor SRI ICE!**

Para más información, visita nuestra web o contacta al soporte.

**Última Actualización:** 3 Junio, 2026  
**Próxima Actualización:** Cuando haya nuevas funciones
