# 📚 API Reportes SRI - Documentación Completa

**Versión:** 1.0  
**Última Actualización:** 3 Junio, 2026  
**Endpoint Base:** `https://gestor-sri-ice.com/api`

---

## 🔐 Autenticación

Todos los endpoints requieren autenticación JWT o sesión Flask.

```bash
# Header requerido
Authorization: Bearer <jwt_token>

# O sesión activa (login)
```

---

## 📊 Endpoints Disponibles

### 1️⃣ Formulario 104 (IVA)

#### GET /reportes/formulario_104/{anio}/{mes}
Descarga el Formulario 104 en el formato especificado.

**Parámetros Path:**
```
anio: integer (2020-2026)
mes: integer (1-12)
```

**Parámetros Query:**
```
formato: string [excel, json, xml]
  Default: excel
```

**Respuestas:**

- **200 OK** - Archivo descargado
  ```
  Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet
  Content-Disposition: attachment; filename=Formulario_104_2026_06.xlsx
  ```

- **400 Bad Request** - Parámetros inválidos
  ```json
  {
    "error": "Mes debe estar entre 1 y 12"
  }
  ```

- **401 Unauthorized** - No autenticado
- **403 Forbidden** - Sin permisos
- **500 Internal Server Error** - Error del servidor

**Ejemplo cURL:**
```bash
curl -X GET \
  'https://gestor-sri-ice.com/api/reportes/formulario_104/2026/6?formato=excel' \
  -H 'Authorization: Bearer YOUR_TOKEN' \
  -o Formulario_104_2026_06.xlsx
```

---

#### GET /reportes/formulario_104/{anio}/{mes}/preview
Vista previa del Formulario 104 en JSON (sin descarga).

**Respuesta JSON:**
```json
{
  "status": "success",
  "formulario": {
    "periodo": {
      "anio": 2026,
      "mes": 6,
      "fecha_presentacion": "2026-06-03T15:45:30"
    },
    "ventas": {
      "base_iva": 5000.00,
      "iva_cobrado": 750.00
    },
    "compras": {
      "base_iva": 3000.00,
      "iva_pagado": 450.00
    },
    "credito": {
      "iva_cobrado": 750.00,
      "iva_pagado": 450.00,
      "saldo_anterior": 100.00,
      "saldo_final": 400.00
    },
    "resumen": {
      "iva_cobrado_periodo": 750.00,
      "iva_pagado_periodo": 450.00,
      "saldo_iva_mes": 400.00,
      "debe_pagar": false,
      "tiene_credito": true
    }
  }
}
```

---

### 2️⃣ Anexo ICE/PVP

#### GET /reportes/anexo_ice/{anio}/{mes}
Descarga el Anexo ICE/PVP.

**Parámetros Path:**
```
anio: integer (2020-2026)
mes: integer (1-12)
```

**Parámetros Query:**
```
formato: string [excel, json, xml]
  Default: excel
```

**Respuesta JSON (preview):**
```json
{
  "tipo": "Anexo ICE/PVP",
  "version": "1.0",
  "periodo": {
    "anio": 2026,
    "mes": 6
  },
  "resumen": {
    "total_registros": 5,
    "total_base_imponible": 2500.00,
    "total_ice": 125.00,
    "fecha_generacion": "2026-06-03T15:45:30"
  },
  "categorias": {
    "bebidas_alcoholicas": {
      "codigo": "01",
      "nombre": "Bebidas Alcohólicas",
      "cantidad": 2,
      "base_imponible": 1000.00,
      "tasa_promedio": 5.0,
      "valor_ice": 50.00
    }
  },
  "detalles": [
    {
      "factura_id": "001-001-000000001",
      "ruc_proveedor": "0192000000001",
      "descripcion": "Cerveza importada",
      "base_imponible": 500.00,
      "tasa_ice": 5.0,
      "valor_ice": 25.00,
      "tipo": "ingreso",
      "fecha": "2026-06-03"
    }
  ]
}
```

---

### 3️⃣ ATS (Archivo Técnico Tributario)

#### GET /reportes/ats/{anio}/{mes}
Descarga el ATS.

**Parámetros Query:**
```
formato: string [plano, json, xml]
  Default: plano
```

**Formato Plano (archivo .txt):**
```
0191234567001202606ATS0000000050000000000125000001
000000001030620260192000000001010000100000120000006000000000000120000000
...
```

**Respuesta JSON (preview):**
```json
{
  "tipo": "ATS",
  "version": "1.0",
  "usuario": {
    "ruc": "0191234567001",
    "nombre": "Test User",
    "empresa": "Test Company"
  },
  "periodo": {
    "anio": 2026,
    "mes": "06",
    "fecha_generacion": "2026-06-03T15:45:30"
  },
  "resumen": {
    "total_ingresos": 5000.00,
    "total_gastos": 3000.00,
    "total_iva": 960.00,
    "total_registros": 8
  },
  "registros": [
    {
      "secuencial": 1,
      "fecha": "2026-06-03T10:30:00",
      "numero_factura": "001-001-000000001",
      "ruc_contraparte": "0192000000001",
      "tipo": "01",
      "base_imponible": 1000.00,
      "valor_iva": 120.00,
      "importe_total": 1120.00
    }
  ]
}
```

---

### 4️⃣ Certificado de Retenciones

#### GET /reportes/retenciones/{anio}/{mes}
Descarga el certificado de retención.

**Parámetros Query:**
```
formato: string [html, json, xml]
  Default: html
```

**Respuesta JSON (preview):**
```json
{
  "tipo": "Certificado de Retención",
  "version": "1.0",
  "usuario": {
    "ruc": "0191234567001",
    "nombre": "Test User",
    "empresa": "Test Company"
  },
  "periodo": {
    "anio": 2026,
    "mes": "06",
    "fecha_generacion": "2026-06-03T15:45:30"
  },
  "resumen": {
    "total_retenciones": 3,
    "total_retenido": 180.00,
    "total_pagado": 2820.00,
    "total_original": 3000.00
  },
  "retenciones": [
    {
      "secuencial": 1,
      "fecha": "2026-06-01",
      "numero_comprobante": "002-001-000000001",
      "ruc_proveedor": "0193000000001",
      "razon_social": "Proveedor ABC",
      "tipo_retencion": "iva",
      "base_imponible": 1000.00,
      "tasa_retencion": 30.0,
      "valor_retencion": 300.00,
      "importe_neto": 700.00
    }
  ]
}
```

---

### 5️⃣ Paquete Completo ZIP

#### GET /reportes/paquete_completo/{anio}/{mes}
Descarga todos los reportes en un archivo ZIP.

**Contenido del ZIP:**
```
Reportes_SRI_2026_06.zip
├── Formulario_104_2026_06.xlsx
├── Anexo_ICE_2026_06.xlsx
├── ATS_2026_06.txt
└── Retenciones_2026_06.html
```

---

### 6️⃣ Utilidades

#### GET /reportes/lista_periodos
Obtiene todos los períodos disponibles con datos.

**Respuesta:**
```json
{
  "usuario_id": 1,
  "periodos": [
    {
      "anio": 2026,
      "mes": 1,
      "label": "2026/01"
    },
    {
      "anio": 2026,
      "mes": 2,
      "label": "2026/02"
    },
    {
      "anio": 2026,
      "mes": 6,
      "label": "2026/06"
    }
  ],
  "total": 3
}
```

---

#### GET /reportes/resumen_anio/{anio}
Obtiene resumen IVA para un año completo.

**Parámetros Path:**
```
anio: integer (2020-2026)
```

**Respuesta:**
```json
{
  "status": "success",
  "resumen": {
    "enero": {
      "iva_cobrado": 1200.00,
      "iva_pagado": 800.00,
      "saldo": 400.00
    },
    "febrero": {
      "iva_cobrado": 1500.00,
      "iva_pagado": 900.00,
      "saldo": 600.00
    },
    ...
    "diciembre": {
      "iva_cobrado": 1100.00,
      "iva_pagado": 850.00,
      "saldo": 250.00
    },
    "total_anio": {
      "iva_cobrado": 15000.00,
      "iva_pagado": 10000.00,
      "saldo_final": 5000.00
    }
  }
}
```

---

## 📋 Auditoría - Endpoints

### GET /auditoria/historial
Obtiene historial de cambios del usuario.

**Parámetros Query:**
```
tabla: string (opcional)
  Filtrar por tabla (factura, usuario, etc.)

registro_id: integer (opcional)
  Filtrar por ID de registro

limite: integer (default: 50, max: 200)
  Cantidad de registros a retornar
```

**Respuesta:**
```json
{
  "total": 5,
  "cambios": [
    {
      "id": 1,
      "usuario_id": 1,
      "modulo": "facturas",
      "accion": "CREATE",
      "tabla": "factura",
      "registro_id": 123,
      "datos_anterior": null,
      "datos_nuevo": {
        "numero_factura": "001-001-000000001",
        "base_iva": 1000.00
      },
      "ip_address": "192.168.1.1",
      "user_agent": "Mozilla/5.0...",
      "timestamp": "2026-06-03T10:30:00"
    }
  ]
}
```

---

### GET /auditoria/rango_fechas
Obtiene cambios en un rango de fechas.

**Parámetros Query:**
```
desde: string (YYYY-MM-DD) - REQUERIDO
hasta: string (YYYY-MM-DD) - REQUERIDO
tabla: string (opcional)
```

---

### GET /auditoria/por_accion/{accion}
Obtiene cambios filtrados por acción.

**Parámetros Path:**
```
accion: string [CREATE, UPDATE, DELETE, READ]
```

---

### GET /auditoria/resumen
Obtiene resumen de auditoría (últimos 30 días).

**Respuesta:**
```json
{
  "periodo": "30 últimos días",
  "total_cambios": 45,
  "por_accion": {
    "CREATE": 10,
    "UPDATE": 30,
    "DELETE": 5,
    "READ": 0
  },
  "por_tabla": {
    "factura": 25,
    "usuario": 15,
    "saldo_iva_mes": 5
  },
  "cambios_recientes": [...]
}
```

---

## 🔍 Códigos de Error

| Código | Descripción | Solución |
|--------|-------------|----------|
| 400 | Bad Request | Verificar parámetros |
| 401 | Unauthorized | Autenticarse primero |
| 403 | Forbidden | Sin permisos suficientes |
| 404 | Not Found | Recurso no encontrado |
| 405 | Method Not Allowed | Usar método HTTP correcto |
| 500 | Internal Server Error | Contactar administrador |
| 503 | Service Unavailable | Servidor en mantenimiento |

---

## 📈 Ejemplos Prácticos

### Ejemplo 1: Descargar Formulario 104 en Excel
```bash
curl -X GET \
  'https://gestor-sri-ice.com/api/reportes/formulario_104/2026/6?formato=excel' \
  -H 'Authorization: Bearer YOUR_TOKEN' \
  -H 'Accept: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' \
  -o formulario_104.xlsx
```

### Ejemplo 2: Obtener Preview JSON
```javascript
fetch('/reportes/formulario_104/2026/6/preview', {
  method: 'GET',
  headers: {
    'Authorization': 'Bearer YOUR_TOKEN'
  }
})
.then(response => response.json())
.then(data => console.log(data));
```

### Ejemplo 3: Descargar Paquete ZIP
```python
import requests

url = 'https://gestor-sri-ice.com/api/reportes/paquete_completo/2026/6'
headers = {'Authorization': 'Bearer YOUR_TOKEN'}

response = requests.get(url, headers=headers)
with open('reportes.zip', 'wb') as f:
    f.write(response.content)
```

### Ejemplo 4: Obtener Historial de Auditoría
```bash
curl -X GET \
  'https://gestor-sri-ice.com/api/auditoria/historial?tabla=factura&limite=50' \
  -H 'Authorization: Bearer YOUR_TOKEN' \
  | jq '.'
```

---

## 🔒 Seguridad

### Autenticación Requerida
- ✅ JWT Bearer token
- ✅ Sesión Flask
- ✅ 2FA opcional

### Datos Encriptados
- ✅ HTTPS obligatorio
- ✅ Datos sensibles en BD encriptados
- ✅ Credenciales en .env

### Límites de Tasa (Rate Limiting)
- 100 requests/minuto por usuario
- 1000 requests/hora por IP
- Documentación completa en `/api/rate-limits`

---

## 📚 Modelos de Datos

### Formulario 104
```python
{
  "tipo": "Formulario 104",
  "periodo": {"anio": int, "mes": int},
  "ventas": {"base_iva": float, "iva_cobrado": float},
  "compras": {"base_iva": float, "iva_pagado": float},
  "credito": {
    "iva_cobrado": float,
    "iva_pagado": float,
    "saldo_anterior": float,
    "saldo_final": float
  }
}
```

### ATS
```python
{
  "tipo": "ATS",
  "usuario": {"ruc": str, "nombre": str},
  "periodo": {"anio": int, "mes": str},
  "registros": [
    {
      "secuencial": int,
      "fecha": str,
      "numero_factura": str,
      "ruc_contraparte": str,
      "base_imponible": float,
      "valor_iva": float
    }
  ]
}
```

---

## 🆘 Soporte

**Email:** support@gestor-sri-ice.com  
**Teléfono:** +593 2 XXXX XXXX  
**Horario:** Lunes-Viernes, 9am-6pm ECT

---

**Última Actualización:** 3 Junio, 2026  
**Próxima Revisión:** 10 Junio, 2026
