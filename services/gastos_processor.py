"""
Servicio de procesamiento completo de facturas de gasto (XMLs)
Basado en la lógica de SRI-XML.py

Extrae:
- Datos básicos (RUC, nombre, fecha, etc.)
- Composición completa de IVA (bases y valores por porcentaje)
- Forma de pago
- Detalles de productos/servicios
- Descuentos
"""

import xml.etree.ElementTree as ET
from datetime import datetime
import json


def find_text(parent, tag):
    """Busca texto en elemento XML ignorando namespaces - funciona con cualquier formato"""
    if parent is None:
        return ''
    n = parent.find(tag)
    if n is not None and n.text:
        return n.text.strip()
    for el in parent.iter():
        if el.tag.endswith(f'}}{tag}') or el.tag == tag:
            if el.text:
                return el.text.strip()
    return ''


def find_node(parent, tag):
    """Busca nodo XML ignorando namespaces - funciona con cualquier formato"""
    if parent is None:
        return None
    for el in parent.iter():
        if el.tag.endswith(f'}}{tag}') or el.tag == tag:
            return el
    return None


def parse_xml_gasto_completo(filepath):
    """Parsea XML de gasto completo - extrae TODOS los datos incluida composición de IVA"""
    try:
        tree = ET.parse(filepath)
        root = tree.getroot()

        # Procesar si viene envuelto en nodo <comprobante>
        comp_node = find_node(root, 'comprobante')
        if comp_node is not None and comp_node.text:
            txt = comp_node.text.replace('<![CDATA[', '').replace(']]>', '').strip()
            try:
                root = ET.fromstring(txt)
            except:
                pass

        info_trib = find_node(root, 'infoTributaria')
        info_fact = find_node(root, 'infoFactura')
        if info_trib is None or info_fact is None:
            return None

        # ──────────────────────────────────────────────────────────────
        # DATOS BÁSICOS
        # ──────────────────────────────────────────────────────────────
        clave_acceso = find_text(info_trib, 'claveAcceso')
        ruc_emisor = find_text(info_trib, 'ruc')
        estab = find_text(info_trib, 'estab')
        pto_emi = find_text(info_trib, 'ptoEmi')
        secuencial = find_text(info_trib, 'secuencial')
        numero_factura = f'{estab}-{pto_emi}-{secuencial}'
        nombre_emisor = find_text(info_trib, 'razonSocial')

        ruc_comprador = find_text(info_fact, 'identificacionComprador')
        nombre_comprador = find_text(info_fact, 'razonSocialComprador')
        fecha = find_text(info_fact, 'fechaEmision')

        # ──────────────────────────────────────────────────────────────
        # COMPOSICIÓN IVA (CLAVE)
        # ──────────────────────────────────────────────────────────────
        base_0 = base_15 = iva_15 = base_5 = iva_5 = base_exento = base_no_objeto = 0.0
        total_con_imp = find_node(info_fact, 'totalConImpuestos')
        if total_con_imp is not None:
            for imp in total_con_imp:
                codigo = find_text(imp, 'codigo')
                if codigo == '2':  # IVA
                    cod_porc = find_text(imp, 'codigoPorcentaje')
                    try:
                        base_imp = float(find_text(imp, 'baseImponible') or 0)
                    except ValueError:
                        base_imp = 0.0
                    try:
                        val_imp = float(find_text(imp, 'valor') or 0)
                    except ValueError:
                        val_imp = 0.0

                    if cod_porc == '0':
                        base_0 += base_imp
                    elif cod_porc in ('2', '3', '4', '10'):
                        base_15 += base_imp
                        iva_15 += val_imp
                    elif cod_porc == '5':
                        base_5 += base_imp
                        iva_5 += val_imp
                    elif cod_porc == '6':
                        base_no_objeto += base_imp
                    elif cod_porc == '7':
                        base_exento += base_imp

        # ──────────────────────────────────────────────────────────────
        # TOTALES
        # ──────────────────────────────────────────────────────────────
        try:
            total = float(find_text(info_fact, 'importeTotal') or 0)
        except ValueError:
            total = 0.0

        try:
            total_descuento = float(find_text(info_fact, 'totalDescuento') or 0)
        except ValueError:
            total_descuento = 0.0

        # ──────────────────────────────────────────────────────────────
        # FORMA DE PAGO
        # ──────────────────────────────────────────────────────────────
        pagos_n = find_node(info_fact, 'pagos')
        forma_pago = 'Otros'
        if pagos_n is not None:
            pago = find_node(pagos_n, 'pago')
            if pago is not None:
                cod_p = find_text(pago, 'formaPago')
                formas_map = {
                    '01': 'Sin Uso Sistema Financiero',
                    '15': 'Compensación deudas',
                    '16': 'Tarjeta débito',
                    '17': 'Dinero electrónico',
                    '18': 'Tarjeta prepago',
                    '19': 'Tarjeta crédito',
                    '20': 'Otros con Sistema Financiero',
                    '21': 'Transferencia bancaria',
                }
                forma_pago = formas_map.get(cod_p, 'Otros')

        # ──────────────────────────────────────────────────────────────
        # DETALLES Y CONCEPTO
        # ──────────────────────────────────────────────────────────────
        detalles_n = find_node(root, 'detalles')
        concepto = 'VARIOS'
        detalles_list = []
        if detalles_n is not None:
            lista = list(detalles_n)
            for det in lista:
                desc = find_text(det, 'descripcion')
                if desc and not concepto.startswith(desc[:10]):
                    concepto = desc + ('...' if len(lista) > 1 else '')
                try:
                    detalles_list.append({
                        'descripcion': desc,
                        'cantidad': float(find_text(det, 'cantidad') or 0),
                        'precio_unitario': float(find_text(det, 'precioUnitario') or 0),
                        'precio_total': float(find_text(det, 'precioTotalSinImpuesto') or 0),
                    })
                except:
                    pass

        return {
            'clave_acceso': clave_acceso,
            'ruc_emisor': ruc_emisor,
            'numero_factura': numero_factura,
            'nombre_emisor': nombre_emisor,
            'ruc_comprador': ruc_comprador,
            'nombre_comprador': nombre_comprador,
            'fecha': fecha,
            'base_0': round(base_0, 2),
            'base_5': round(base_5, 2),
            'iva_5': round(iva_5, 2),
            'base_15': round(base_15, 2),
            'iva_15': round(iva_15, 2),
            'base_exento': round(base_exento, 2),
            'base_no_objeto': round(base_no_objeto, 2),
            'total_descuento': round(total_descuento, 2),
            'total': round(total, 2),
            'forma_pago': forma_pago,
            'concepto': concepto,
            'detalles': detalles_list,
        }

    except Exception as e:
        print(f'Error parseando {filepath}: {e}')
        return None


def deserializar_notas_auditoria(notas_json_str):
    """
    Convierte la cadena JSON de notas_auditoria de vuelta a diccionario
    """
    if not notas_json_str:
        return {}

    try:
        return json.loads(notas_json_str)
    except:
        return {}


def serializar_datos_gasto(datos_gasto):
    """
    Serializa los datos de composición de IVA para guardar en notas_auditoria
    """
    if not datos_gasto:
        return "{}"

    datos_auditoria = {
        'base_0': datos_gasto.get('base_0', 0),
        'base_5': datos_gasto.get('base_5', 0),
        'iva_5': datos_gasto.get('iva_5', 0),
        'base_15': datos_gasto.get('base_15', 0),
        'iva_15': datos_gasto.get('iva_15', 0),
        'base_exento': datos_gasto.get('base_exento', 0),
        'base_no_objeto': datos_gasto.get('base_no_objeto', 0),
        'concepto': datos_gasto.get('concepto', ''),
        'forma_pago': datos_gasto.get('forma_pago', ''),
        'detalles': datos_gasto.get('detalles', []),
        'total_descuento': datos_gasto.get('total_descuento', 0),
    }

    return json.dumps(datos_auditoria, ensure_ascii=False)


def clasificar_gasto_automatico(ruc_emisor, nombre_emisor, mapa_clasificacion_detalles):
    """
    Clasifica automáticamente un gasto según RUC del proveedor

    Args:
        ruc_emisor: RUC del proveedor/emisor
        nombre_emisor: Nombre del proveedor/emisor
        mapa_clasificacion_detalles: Lista de MapaClasificacionDetalle o queryset

    Returns:
        str: Categoría de clasificación o "SIN CLASIFICAR"
    """
    if not ruc_emisor:
        return "SIN CLASIFICAR"

    # Buscar en el mapa por RUC
    for detalle in mapa_clasificacion_detalles:
        if detalle.ruc == ruc_emisor:
            return detalle.categoria

    return "SIN CLASIFICAR"
