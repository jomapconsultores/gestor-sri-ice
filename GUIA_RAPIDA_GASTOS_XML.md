# Guía Rápida: Sistema de Procesamiento de Gastos XML

## 🎯 ¿Qué es esta integración?

Has integrado la lógica completa de **SRI-XML.py** directamente en tu sistema web. Ahora puedes:

1. **Cargar XMLs de facturas** de gasto desde la interfaz web
2. **Extraer automáticamente** toda la información tributaria
3. **Clasificar gastos** según tus propios mapas
4. **Exportar a Excel** con desglose completo de IVA

---

## 📦 Archivos Nuevos Creados

```
services/gastos_processor.py
│
├─ parse_xml_gasto_completo(filepath)
│   └─ Extrae todos los datos del XML
│
├─ serializar_datos_gasto(datos)
│   └─ Convierte datos a JSON para BD
│
└─ clasificar_gasto_automatico(ruc, nombre, mapa)
    └─ Auto-clasifica según RUC
```

---

## 🔌 Nuevas Rutas de API

### 1. Procesar XML de Gasto
```http
POST /gastos/procesar_gasto_xml
Content-Type: multipart/form-data

archivo: <file.xml>
```

**Respuesta exitosa (201):**
```json
{
  "success": true,
  "factura_id": 123,
  "clasificacion": "SERVICIOS PROFESIONALES",
  "datos": {
    "numero_factura": "001-001-000000001",
    "fecha": "01/06/2024",
    "nombre_emisor": "PROVEEDOR EJEMPLO S.A.",
    "total": 1000.01,
    "base_15": 869.57,
    "iva_15": 130.44
  }
}
```

### 2. Ver Detalles de Factura
```http
GET /gastos/detalle_factura/123
```

**Respuesta:**
```json
{
  "factura": {
    "id": 123,
    "fecha": "01/06/2024",
    "numero": "001-001-000000001",
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
  "detalles": [...],
  "forma_pago": "Tarjeta de crédito"
}
```

### 3. Exportar a Excel
```http
GET /gastos/exportar_excel
```

**Retorna:** Excel con 5 hojas

---

## 📊 Estructura del Excel Exportado

### Hoja 1: DATOS
Detalle de cada factura cargada
| Fecha | N Factura | Proveedor | RUC | Categoria | Total | Tipo |
|-------|-----------|-----------|-----|-----------|-------|------|

### Hoja 2: COMPOSICIÓN IVA
Desglose completo de bases y valores por porcentaje
| Fecha | N Factura | Base 0% | Base 5% | IVA 5% | Base 15% | IVA 15% | ... |
|-------|-----------|---------|---------|--------|----------|---------|-----|

### Hoja 3: GASTOS PERSONALES
Resumen por categoría (Alimentación, Educación, Salud, etc.)
| Categoria | Total | Cantidad |
|-----------|-------|----------|

### Hoja 4: GASTOS EJERCICIO
Resumen de gastos deducibles
| Categoria | Total | Cantidad |
|-----------|-------|----------|

### Hoja 5: RESUMEN GENERAL
Totales de todo
| Tipo | Cantidad | Total |
|------|----------|-------|

---

## 🔄 Flujo de Uso

```
1. Panel de Gastos (/gastos/panel)
   ├─ Ves gastos sin clasificar
   ├─ Puedes subir mapa RUC → Categoría
   └─ Tienes botón "Cargar XML"

2. Cargar XML
   ├─ Sistema parsea y extrae datos
   ├─ Crea registro en BD
   └─ Auto-clasifica si hay mapa activo

3. Ver Detalles
   ├─ Composición completa de IVA
   ├─ Detalles de productos/servicios
   └─ Forma de pago

4. Exportar
   └─ Excel con 5 hojas de análisis
```

---

## 💾 ¿Dónde se guardan los datos?

| Campo BD | Contenido |
|----------|-----------|
| `factura.base_iva` | Base del IVA 15% |
| `factura.valor_iva` | Valor del IVA 15% |
| `factura.descuento_total` | Total descuentos |
| `factura.notas_auditoria` | **JSON completo** con: base_0, base_5, iva_5, base_15, iva_15, base_exento, base_no_objeto, concepto, forma_pago, detalles |
| `factura.xml_original` | XML completo guardado |

---

## 🧪 Pruebas Incluidas

```bash
python test_gastos_processor.py
```

Valida:
- ✅ Parseo básico de facturas
- ✅ Extracción correcta de composición IVA múltiple
- ✅ Serialización a JSON
- ✅ Mapeo de formas de pago SRI

---

## 📋 Ejemplo Completo: Desde XML a Excel

### Paso 1: Cargar XML
```javascript
const formData = new FormData();
formData.append('archivo', xmlFile);

const response = await fetch('/gastos/procesar_gasto_xml', {
  method: 'POST',
  body: formData
});

const resultado = await response.json();
console.log(`Factura ${resultado.factura_id} creada!`);
console.log(`Clasificación automática: ${resultado.clasificacion}`);
```

### Paso 2: Ver Detalles
```javascript
const detalles = await fetch(`/gastos/detalle_factura/${resultado.factura_id}`)
  .then(r => r.json());

console.log(`Base 15%: $${detalles.composicion_iva.base_15}`);
console.log(`IVA 15%: $${detalles.composicion_iva.iva_15}`);
```

### Paso 3: Exportar
```javascript
// Simplemente descargar Excel
window.location.href = '/gastos/exportar_excel';
```

---

## 🔍 Mappeo de Códigos SRI

### Formas de Pago
| Código | Texto |
|--------|-------|
| 01 | Sin Utilización del Sistema Financiero |
| 19 | Tarjeta de crédito |
| 20 | Otros con Utilización del Sistema Financiero |
| ... | (completo en INTEGRACION_SRI_XML_COMPLETA.md) |

### Porcentajes de IVA
| Código | % |
|--------|---|
| 0 | 0% |
| 2,3,4,10 | 15% |
| 5 | 5% |
| 6 | No objeto |
| 7 | Exento |

---

## ⚠️ Consideraciones Importantes

1. **Duplicados**: El sistema previene facturas duplicadas usando `clave_acceso`
2. **Módulo requerido**: Necesitas tener activo el módulo "facturas_gasto"
3. **Archivos temporales**: Se limpian automáticamente
4. **Encoding**: Soporta UTF-8 y Latin-1
5. **Límites**: El campo `notas_auditoria` es TEXT (hasta 65535 caracteres en MySQL)

---

## 🚀 Próximos Pasos (Opcional)

1. **Frontend**: Crear interfaz de drag-drop para cargar XMLs
2. **Importación masiva**: Cargar ZIP con múltiples XMLs
3. **Validación SRI**: Verificar estado de factura con SRI
4. **Gráficos**: Dashboard con análisis de IVA
5. **API Externa**: Integrar con sistemas contables

---

## 📞 Troubleshooting

### Error: "No se pudo parsear el XML"
- Verifica que sea un XML válido del SRI
- Comprueba que tenga `<infoTributaria>` e `<infoFactura>`
- Intenta abrirlo en navegador para ver errores

### Error: "Factura ya registrada"
- Ya existe esa clave de acceso en tu BD
- Verifica el ID de la factura existente

### Error: "No tienes acceso"
- Necesitas el módulo "facturas_gasto" activo
- Ve a Planes y actívalo

---

## 📚 Documentación Completa

Ver: `INTEGRACION_SRI_XML_COMPLETA.md`

---

**¡Listo para usar!** 🎉
