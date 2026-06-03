# Integración Completa de Lógica SRI-XML al Sistema Web

**Fecha:** 2024-06-03
**Versión:** 1.0
**Estado:** Completada

---

## 📋 Resumen Ejecutivo

Se ha integrado completamente la lógica de parseo y procesamiento de facturas de gasto desde SRI-XML.py al sistema web. El sistema ahora puede:

1. **Procesar XMLs de gasto** con extracción completa de composición de IVA
2. **Guardar toda la información tributaria** en la base de datos
3. **Auto-clasificar gastos** según mapas de usuario
4. **Exportar datos completos** a Excel con múltiples hojas analíticas

---

## 🔧 Componentes Implementados

### 1. Servicio de Procesamiento: `services/gastos_processor.py`

**Funciones principales:**

#### `parse_xml_gasto_completo(filepath)`
Parsea un XML de factura electrónica del SRI extrayendo:

- **Datos Básicos:**
  - Clave de acceso
  - RUC del emisor y comprador
  - Nombres de empresa
  - Fecha de emisión
  - Número de factura (formato: ESTAB-PTOEMIT-SECUENCIAL)

- **Composición de IVA (todas las bases y valores):**
  - Base 0% (exento)
  - Base 5% e IVA 5%
  - Base 15% e IVA 15%
  - Base no objeto de IVA
  - Base exenta

- **Información Adicional:**
  - Forma de pago (mapeo de códigos SRI)
  - Concepto/descripción del gasto
  - Detalles completos de productos/servicios
  - Total descuentos
  - Total general

**Ejemplo de salida:**
```json
{
  "clave_acceso": "1111111111111111111111111111111111111111111111111",
  "ruc_emisor": "0191234567001",
  "nombre_emisor": "PROVEEDOR EJEMPLO S.A.",
  "ruc_comprador": "0193456789001",
  "nombre_comprador": "CLIENTE EJEMPLO S.A.",
  "fecha": "01/06/2024",
  "numero_factura": "001-001-000000001",
  "base_0": 0.0,
  "base_5": 0.0,
  "iva_5": 0.0,
  "base_15": 869.57,
  "iva_15": 130.44,
  "base_exento": 0.0,
  "base_no_objeto": 0.0,
  "total_descuento": 0.0,
  "total": 1000.01,
  "forma_pago": "Tarjeta de crédito",
  "concepto": "Servicio de consultoría en impuestos",
  "detalles": [
    {
      "descripcion": "Servicio de consultoría en impuestos",
      "cantidad": 1.0,
      "precio_unitario": 869.57,
      "precio_total": 869.57
    }
  ]
}
```

#### `serializar_datos_gasto(datos_gasto)`
Convierte el diccionario de datos a JSON para almacenamiento en `notas_auditoria`.

#### `clasificar_gasto_automatico(ruc_emisor, nombre_emisor, mapa_detalles)`
Clasifica un gasto según el mapa de clasificación del usuario (RUC → Categoría).

### 2. Rutas Nuevas: `routes/gastos.py`

#### `POST /gastos/procesar_gasto_xml`
Procesa un archivo XML de gasto cargado.

**Parámetros:**
- `archivo`: Archivo XML (multipart/form-data)

**Retorna (JSON):**
```json
{
  "success": true,
  "factura_id": 123,
  "clasificacion": "SERVICIOS PROFESIONALES",
  "datos": {
    "numero_factura": "001-001-000000001",
    "fecha": "01/06/2024",
    "nombre_emisor": "PROVEEDOR EJEMPLO S.A.",
    "nombre_comprador": "CLIENTE EJEMPLO S.A.",
    "total": 1000.01,
    "concepto": "Servicio de consultoría en impuestos",
    "base_15": 869.57,
    "iva_15": 130.44
  }
}
```

#### `GET /gastos/detalle_factura/<factura_id>`
Retorna los detalles completos de una factura de gasto.

**Retorna (JSON):**
```json
{
  "factura": {
    "id": 123,
    "fecha": "01/06/2024",
    "numero": "001-001-000000001",
    "ruc_emisor": "0191234567001",
    "nombre_emisor": "PROVEEDOR EJEMPLO S.A.",
    "ruc_comprador": "0193456789001",
    "nombre_comprador": "CLIENTE EJEMPLO S.A.",
    "total": 1000.01
  },
  "composicion_iva": {
    "base_0": 0.0,
    "base_5": 0.0,
    "iva_5": 0.0,
    "base_15": 869.57,
    "iva_15": 130.44,
    "base_exento": 0.0,
    "base_no_objeto": 0.0,
    "total_descuento": 0.0
  },
  "detalles": [
    {
      "descripcion": "Servicio de consultoría en impuestos",
      "cantidad": 1.0,
      "precio_unitario": 869.57,
      "precio_total": 869.57
    }
  ],
  "concepto": "Servicio de consultoría en impuestos",
  "forma_pago": "Tarjeta de crédito",
  "clasificacion": {
    "categoria": "SERVICIOS PROFESIONALES",
    "fecha": "01/06/2024 14:30"
  }
}
```

#### `GET /gastos/exportar_excel`
Exporta todos los gastos clasificados a Excel con múltiples hojas.

**Hojas incluidas:**
1. **DATOS** - Detalle de cada factura (fecha, número, proveedor, RUC, categoría, monto, tipo)
2. **COMPOSICIÓN IVA** - Desglose completo de bases y valores de IVA
3. **GASTOS PERSONALES** - Resumen por categoría de gastos personales
4. **GASTOS EJERCICIO** - Resumen por categoría de gastos deducibles del ejercicio
5. **RESUMEN GENERAL** - Totales por tipo y total general

### 3. Mejoras en BD (Model: `models/user.py`)

La tabla `factura` ya contiene los campos necesarios:

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `base_iva` | NUMERIC(12,2) | Base imponible del IVA 15% |
| `valor_iva` | NUMERIC(12,2) | Valor del IVA 15% |
| `descuento_total` | NUMERIC(12,2) | Total de descuentos |
| `tiene_descuento` | BOOLEAN | Indicador de descuentos |
| `notas_auditoria` | TEXT | JSON con composición completa de IVA |
| `xml_original` | TEXT | XML original de la factura |

---

## 📊 Flujo de Procesamiento

```
1. Usuario carga XML de gasto
   ↓
2. Sistema valida formato XML
   ↓
3. Servicio gastos_processor.py parsea:
   - Datos tributarios
   - Composición de IVA (todos los porcentajes)
   - Forma de pago
   - Concepto
   - Detalles
   ↓
4. Se verifica si factura ya existe (por clave_acceso)
   ↓
5. Se crea registro en tabla factura con:
   - Datos básicos
   - Totales
   - XML serializado en notas_auditoria
   ↓
6. Si existe mapa de clasificación activo:
   - Búsqueda automática por RUC del emisor
   - Clasificación automática del gasto
   ↓
7. Se retorna JSON con confirmación
   ↓
8. Usuario puede exportar a Excel o ver detalles
```

---

## 🧪 Pruebas Realizadas

Se han ejecutado pruebas completas en `test_gastos_processor.py`:

### ✅ Prueba 1: Parseo Básico
- Extrae correctamente datos de factura simple
- Identifica porcentaje de IVA 15%
- Mapea forma de pago a texto legible
- Identifica concepto del primer detalle

### ✅ Prueba 2: Composición Múltiple de IVA
- Extrae correctamente base 0% = $500
- Extrae correctamente base 5% = $200, IVA 5% = $10
- Extrae correctamente base 15% = $300, IVA 15% = $45
- Total correcto = $1055

### ✅ Prueba 3: Serialización JSON
- Datos se serializan correctamente a JSON
- Se pueden deserializar sin errores
- Compatible con almacenamiento en campo TEXT

---

## 🚀 Ejemplos de Uso

### Procesar un XML desde JavaScript/Frontend:

```javascript
const formData = new FormData();
formData.append('archivo', fileInput.files[0]);

fetch('/gastos/procesar_gasto_xml', {
  method: 'POST',
  body: formData
})
.then(response => response.json())
.then(data => {
  if (data.success) {
    console.log('Factura creada:', data.factura_id);
    console.log('Clasificación:', data.clasificacion);
    console.log('Datos:', data.datos);
  } else {
    console.error('Error:', data.error);
  }
});
```

### Obtener detalles de una factura:

```javascript
fetch('/gastos/detalle_factura/123')
  .then(response => response.json())
  .then(data => {
    console.log('Composición de IVA:');
    console.log(`Base 15%: ${data.composicion_iva.base_15}`);
    console.log(`IVA 15%: ${data.composicion_iva.iva_15}`);
  });
```

### Exportar a Excel:

```javascript
// Simplemente navegar a la URL
window.location.href = '/gastos/exportar_excel';
```

---

## 📋 Mapeo de Códigos SRI

### Formas de Pago

| Código | Descripción |
|--------|-------------|
| 01 | Sin Utilización del Sistema Financiero |
| 15 | Compensación de deudas |
| 16 | Tarjeta de débito |
| 17 | Dinero electrónico |
| 18 | Tarjeta prepago |
| 19 | Tarjeta de crédito |
| 20 | Otros con Utilización del Sistema Financiero |
| 21 | Transferencia bancaria nacional |

### Códigos de Porcentaje de IVA

| Código | Porcentaje |
|--------|-----------|
| 0 | 0% (Gravado) |
| 2, 3, 4, 10 | 15% (Tarifa general) |
| 5 | 5% (Tarifa reducida) |
| 6 | No objeto de IVA |
| 7 | Exento |

---

## 🔒 Seguridad

- ✅ Validación de tipo de archivo (solo .xml)
- ✅ Validación de usuario propietario (usuario_id)
- ✅ Revisión de módulos activos (requiere 'facturas_gasto')
- ✅ Prevención de duplicados (clave_acceso única)
- ✅ Límpieza de archivos temporales
- ✅ Manejo seguro de excepciones (sin exponer detalles internos)

---

## 📈 Próximas Mejoras (Opcional)

1. **Validación de firma digital** del XML (si SRI lo requiere)
2. **Importación masiva** desde ZIP con múltiples XMLs
3. **Gráficos analíticos** de composición de IVA por período
4. **Integración con SRI** para obtener estado de validación
5. **Histórico de cambios** en clasificación de gastos

---

## 📞 Soporte

- Revisa el archivo `test_gastos_processor.py` para ejemplos de uso
- Consulta `services/gastos_processor.py` para documentación completa de funciones
- Revisa `routes/gastos.py` para endpoints disponibles

---

## ✨ Conclusión

La integración SRI-XML es **100% funcional** y lista para producción. Todos los datos tributarios se extraen correctamente, incluyendo la composición completa de IVA, y se almacenan de forma segura en la base de datos para auditoría y análisis posterior.
