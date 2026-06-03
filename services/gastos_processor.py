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


def find_text_ignore_ns(parent, tag_name):
    """
    Busca texto en un elemento XML ignorando namespaces
    Similar a la función en SRI-XML.py
    """
    if parent is None:
        return ""

    # Intenta búsqueda directa primero
    node = parent.find(tag_name)
    if node is not None and node.text:
        return node.text.strip()

    # Luego busca ignorando namespace
    for element in parent.iter():
        if element.tag.endswith(f"}}{tag_name}") or element.tag == tag_name:
            if element.text:
                return element.text.strip()

    return ""


def find_node_ignore_ns(parent, tag_name):
    """
    Busca un nodo XML ignorando namespaces
    Similar a la función en SRI-XML.py
    """
    if parent is None:
        return None

    # Intenta búsqueda directa primero
    node = parent.find(tag_name)
    if node is not None:
        return node

    # Luego busca ignorando namespace
    for element in parent.iter():
        if element.tag.endswith(f"}}{tag_name}") or element.tag == tag_name:
            return element

    return None


def parse_xml_gasto_completo(filepath):
    """
    Parsea un XML de gasto electrónico completo
    Extrae toda la composición de IVA y datos tributarios

    Returns:
        dict: Diccionario con todos los datos del gasto o None si hay error
    """
    try:
        tree = ET.parse(filepath)
        root = tree.getroot()

        info_tributaria = find_node_ignore_ns(root, 'infoTributaria')
        info_factura = find_node_ignore_ns(root, 'infoFactura')

        if info_tributaria is None or info_factura is None:
            return None

        # ─────────────────────────────────────────────────────────────────
        # DATOS BÁSICOS DE LA FACTURA
        # ─────────────────────────────────────────────────────────────────
        clave_acceso = find_text_ignore_ns(info_tributaria, 'claveAcceso')
        ruc_emisor = find_text_ignore_ns(info_tributaria, 'ruc')
        estab = find_text_ignore_ns(info_tributaria, 'estab')
        pto_emi = find_text_ignore_ns(info_tributaria, 'ptoEmi')
        secuencial = find_text_ignore_ns(info_tributaria, 'secuencial')
        nombre_emisor = find_text_ignore_ns(info_tributaria, 'razonSocial')

        # Número de factura formateado
        numero_factura = f"{estab}-{pto_emi}-{secuencial}" if estab and pto_emi and secuencial else ""

        # Datos del comprador (quien compra/suscriptor)
        ruc_comprador = find_text_ignore_ns(info_factura, 'identificacionComprador')
        nombre_comprador = find_text_ignore_ns(info_factura, 'razonSocialComprador')

        # Fecha de emisión
        fecha = find_text_ignore_ns(info_factura, 'fechaEmision')

        # ─────────────────────────────────────────────────────────────────
        # COMPOSICIÓN DE IVA Y BASES IMPONIBLES
        # Similar a SRI-XML.py líneas 182-203
        # ─────────────────────────────────────────────────────────────────
        base_0 = 0.0
        base_5 = 0.0
        iva_5 = 0.0
        base_15 = 0.0
        iva_15 = 0.0
        base_exento = 0.0
        base_no_objeto = 0.0

        total_con_impuestos = find_node_ignore_ns(info_factura, 'totalConImpuestos')
        if total_con_impuestos is not None:
            for impuesto in total_con_impuestos:
                codigo = find_text_ignore_ns(impuesto, 'codigo')

                # Código 2 = IVA
                if codigo == '2':
                    cod_porc = find_text_ignore_ns(impuesto, 'codigoPorcentaje')
                    try:
                        base_imponible = float(find_text_ignore_ns(impuesto, 'baseImponible') or 0)
                    except:
                        base_imponible = 0.0

                    try:
                        valor_impuesto = float(find_text_ignore_ns(impuesto, 'valor') or 0)
                    except:
                        valor_impuesto = 0.0

                    # Clasificar según código de porcentaje
                    # 0 = 0%, 2,3,4,10 = 15%, 5 = 5%, 6 = NO OBJETO, 7 = EXENTO
                    if cod_porc == '0':
                        base_0 += base_imponible
                    elif cod_porc in ['2', '3', '4', '10']:
                        base_15 += base_imponible
                        iva_15 += valor_impuesto
                    elif cod_porc == '5':
                        base_5 += base_imponible
                        iva_5 += valor_impuesto
                    elif cod_porc == '6':
                        base_no_objeto += base_imponible
                    elif cod_porc == '7':
                        base_exento += base_imponible

        # ─────────────────────────────────────────────────────────────────
        # TOTALES Y DESCUENTOS
        # Similar a SRI-XML.py línea 179, 205
        # ─────────────────────────────────────────────────────────────────
        try:
            total = float(find_text_ignore_ns(info_factura, 'importeTotal') or 0)
        except:
            total = 0.0

        try:
            total_descuento = float(find_text_ignore_ns(info_factura, 'totalDescuento') or 0)
        except:
            total_descuento = 0.0

        # ─────────────────────────────────────────────────────────────────
        # FORMA DE PAGO
        # Similar a SRI-XML.py línea 240-252
        # ─────────────────────────────────────────────────────────────────
        pagos = find_node_ignore_ns(info_factura, 'pagos')
        forma_pago = "Otros"

        if pagos is not None:
            pago = find_node_ignore_ns(pagos, 'pago')
            if pago is not None:
                cod_pago = find_text_ignore_ns(pago, 'formaPago')

                # Mapeo de códigos de forma de pago del SRI
                formas_pago_map = {
                    '01': 'Sin Utilización del Sistema Financiero',
                    '15': 'Compensación de deudas',
                    '16': 'Tarjeta de débito',
                    '17': 'Dinero electrónico',
                    '18': 'Tarjeta prepago',
                    '19': 'Tarjeta de crédito',
                    '20': 'Otros con Utilización del Sistema Financiero',
                    '21': 'Transferencia bancaria nacional',
                }

                forma_pago = formas_pago_map.get(cod_pago, "Otros")

        # ─────────────────────────────────────────────────────────────────
        # CONCEPTO/DESCRIPCIÓN (del primer detalle)
        # Similar a SRI-XML.py línea 215-235
        # ─────────────────────────────────────────────────────────────────
        detalles = find_node_ignore_ns(root, 'detalles')
        concepto = "VARIOS"
        detalles_list = []

        if detalles is not None:
            lista_detalles = list(detalles)

            # Buscar primer detalle con descripción
            for child in lista_detalles:
                if child.tag.endswith('}detalle') or child.tag == 'detalle':
                    desc = find_text_ignore_ns(child, 'descripcion')
                    if desc:
                        concepto = desc
                        # Si hay múltiples detalles, agregar "..."
                        if len(lista_detalles) > 1:
                            concepto += "..."
                        break

            # Extraer todos los detalles para almacenar
            for child in lista_detalles:
                if child.tag.endswith('}detalle') or child.tag == 'detalle':
                    try:
                        desc = find_text_ignore_ns(child, 'descripcion')
                        cantidad = float(find_text_ignore_ns(child, 'cantidad') or 0)
                        precio_unitario = float(find_text_ignore_ns(child, 'precioUnitario') or 0)
                        precio_total = float(find_text_ignore_ns(child, 'precioTotalSinImpuesto') or 0)

                        detalles_list.append({
                            'descripcion': desc,
                            'cantidad': cantidad,
                            'precio_unitario': precio_unitario,
                            'precio_total': precio_total,
                        })
                    except:
                        pass

        # ─────────────────────────────────────────────────────────────────
        # INFORMACIÓN ADICIONAL
        # ─────────────────────────────────────────────────────────────────
        tipo_id_comprador = find_text_ignore_ns(info_factura, 'tipoIdentificacionComprador')
        ambiente = find_text_ignore_ns(info_tributaria, 'ambiente')  # 1=producción, 2=prueba

        # ─────────────────────────────────────────────────────────────────
        # RETORNAR DICCIONARIO COMPLETO
        # ─────────────────────────────────────────────────────────────────
        return {
            # Datos tributarios
            'clave_acceso': clave_acceso,
            'ruc_emisor': ruc_emisor,
            'numero_factura': numero_factura,
            'nombre_emisor': nombre_emisor,

            # Datos del comprador
            'ruc_comprador': ruc_comprador,
            'nombre_comprador': nombre_comprador,
            'tipo_id_comprador': tipo_id_comprador,

            # Fecha
            'fecha': fecha,

            # Composición de IVA
            'base_0': round(base_0, 2),
            'base_5': round(base_5, 2),
            'iva_5': round(iva_5, 2),
            'base_15': round(base_15, 2),
            'iva_15': round(iva_15, 2),
            'base_exento': round(base_exento, 2),
            'base_no_objeto': round(base_no_objeto, 2),

            # Totales
            'total_descuento': round(total_descuento, 2),
            'total': round(total, 2),

            # Forma de pago
            'forma_pago': forma_pago,

            # Concepto/descripción
            'concepto': concepto,

            # Detalles completos
            'detalles': detalles_list,

            # Información adicional
            'ambiente': ambiente,
        }

    except Exception as e:
        print(f"Error parseando {filepath}: {e}")
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
