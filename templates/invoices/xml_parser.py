import xml.etree.ElementTree as ET
import os
from datetime import datetime


def find_text(parent, tag_name):
    if parent is None:
        return ""
    node = parent.find(tag_name)
    if node is not None and node.text:
        return node.text.strip()
    for element in parent.iter():
        if element.tag.endswith(f"}}{tag_name}") or element.tag == tag_name:
            if element.text:
                return element.text.strip()
    return ""


def find_node(parent, tag_name):
    if parent is None:
        return None
    for element in parent.iter():
        if element.tag.endswith(f"}}{tag_name}") or element.tag == tag_name:
            return element
    return None


def extraer_impuestos(impuestos_node):
    resultado = {'ice': 0.0, 'base_ice': 0.0, 'iva': 0.0, 'base_iva': 0.0}
    if impuestos_node is None:
        return resultado
    for impuesto in impuestos_node.findall('impuesto'):
        codigo = find_text(impuesto, 'codigo')
        if codigo == '3':
            try:
                resultado['ice'] = float(find_text(impuesto, 'valor'))
                resultado['base_ice'] = float(find_text(impuesto, 'baseImponible'))
            except:
                pass
        elif codigo == '2':
            try:
                resultado['iva'] = float(find_text(impuesto, 'valor'))
                resultado['base_iva'] = float(find_text(impuesto, 'baseImponible'))
            except:
                pass
    return resultado


def parse_xml_factura(ruta_archivo):
    try:
        try:
            tree = ET.parse(ruta_archivo)
            root = tree.getroot()
        except:
            return None
        info_tributaria = find_node(root, 'infoTributaria')
        info_factura = find_node(root, 'infoFactura')
        if info_tributaria is None and info_factura is None:
            return None
        clave_acceso = find_text(info_tributaria, 'claveAcceso')
        ruc = find_text(info_tributaria, 'ruc')
        estab = find_text(info_tributaria, 'estab')
        pto_emi = find_text(info_tributaria, 'ptoEmi')
        secuencial = find_text(info_tributaria, 'secuencial')
        numero_factura = f"{estab}-{pto_emi}-{secuencial}"
        fecha = find_text(info_factura, 'fechaEmision')
        importe_total = float(find_text(info_factura, 'importeTotal') or 0)
        tipo_id = find_text(info_factura, 'tipoIdentificacionComprador')
        id_cliente = find_text(info_factura, 'identificacionComprador')
        razon_social = find_text(info_factura, 'razonSocialComprador') or 'CONSUMIDOR FINAL'
        detalles = find_node(root, 'detalles')
        productos = []
        if detalles is not None:
            for detalle in detalles.findall('detalle'):
                codigo = find_text(detalle, 'codigoPrincipal')
                descripcion = find_text(detalle, 'descripcion')
                cantidad = float(find_text(detalle, 'cantidad') or 0)
                precio_unitario = float(find_text(detalle, 'precioUnitario') or 0)
                precio_total = float(find_text(detalle, 'precioTotalSinImpuesto') or 0)
                impuestos = extraer_impuestos(find_node(detalle, 'impuestos'))
                productos.append({
                    'codigo': codigo,
                    'descripcion': descripcion[:200] if descripcion else '',
                    'cantidad': cantidad,
                    'precio_unitario': precio_unitario,
                    'precio_total': precio_total,
                    'ice': impuestos['ice'],
                    'base_ice': impuestos['base_ice'],
                    'iva': impuestos['iva'],
                    'base_iva': impuestos['base_iva']
                })
        return {
            'clave_acceso': clave_acceso,
            'ruc': ruc,
            'numero_factura': numero_factura,
            'fecha_emision': fecha,
            'importe_total': importe_total,
            'tipo_id_cliente': tipo_id,
            'id_cliente': id_cliente,
            'razon_social_cliente': razon_social,
            'productos': productos,
            'archivo': os.path.basename(ruta_archivo)
        }
    except Exception as e:
        print(f"Error parseando {ruta_archivo}: {e}")
        return None