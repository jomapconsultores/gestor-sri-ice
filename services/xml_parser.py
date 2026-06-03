"""
Servicio de parseo de XMLs de facturas electrónicas del SRI
Basado en tus códigos ICEcompleto.py e ICEingresos.py
"""
import xml.etree.ElementTree as ET
import os
from datetime import datetime


def find_text(parent, tag_name):
    """Busca texto en un elemento XML ignorando namespaces"""
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
    """Busca un nodo XML ignorando namespaces"""
    if parent is None:
        return None
    for element in parent.iter():
        if element.tag.endswith(f"}}{tag_name}") or element.tag == tag_name:
            return element
    return None


def extraer_impuestos(impuestos_node):
    """Extrae ICE e IVA del nodo de impuestos"""
    resultado = {
        'ice': 0.0,
        'base_ice': 0.0,
        'iva': 0.0,
        'base_iva': 0.0
    }
    
    if impuestos_node is None:
        return resultado
    
    for impuesto in impuestos_node.findall('impuesto'):
        codigo = find_text(impuesto, 'codigo')
        if codigo == '3':  # ICE
            try:
                resultado['ice'] = float(find_text(impuesto, 'valor'))
                resultado['base_ice'] = float(find_text(impuesto, 'baseImponible'))
            except:
                pass
        elif codigo == '2':  # IVA
            try:
                resultado['iva'] = float(find_text(impuesto, 'valor'))
                resultado['base_iva'] = float(find_text(impuesto, 'baseImponible'))
            except:
                pass
    
    return resultado


def parse_xml_factura(ruta_archivo):
    """
    Parsea un archivo XML de factura electrónica del SRI
    
    Retorna un diccionario con todos los datos de la factura
    o None si hay error.
    """
    try:
        # Intentar parsear el XML
        try:
            tree = ET.parse(ruta_archivo)
            root = tree.getroot()
        except:
            return None
        
        # Verificar que sea una factura
        info_tributaria = find_node(root, 'infoTributaria')
        info_factura = find_node(root, 'infoFactura')
        
        if info_tributaria is None and info_factura is None:
            return None
        
        # Datos tributarios
        clave_acceso = find_text(info_tributaria, 'claveAcceso')
        ruc = find_text(info_tributaria, 'ruc')
        estab = find_text(info_tributaria, 'estab')
        pto_emi = find_text(info_tributaria, 'ptoEmi')
        secuencial = find_text(info_tributaria, 'secuencial')
        numero_factura = f"{estab}-{pto_emi}-{secuencial}"
        razon_social_emisor = find_text(info_tributaria, 'razonSocial')

        # Datos de la factura
        fecha = find_text(info_factura, 'fechaEmision')
        importe_total = float(find_text(info_factura, 'importeTotal') or 0)

        # Comprador
        tipo_id = find_text(info_factura, 'tipoIdentificacionComprador')
        id_cliente = find_text(info_factura, 'identificacionComprador')
        razon_social = find_text(info_factura, 'razonSocialComprador') or 'CONSUMIDOR FINAL'
        
        # Procesar detalles
        detalles = find_node(root, 'detalles')
        productos = []
        total_descuentos = 0.0

        if detalles is not None:
            for detalle in detalles.findall('detalle'):
                codigo = find_text(detalle, 'codigoPrincipal')
                descripcion = find_text(detalle, 'descripcion')
                cantidad = float(find_text(detalle, 'cantidad') or 0)
                precio_unitario = float(find_text(detalle, 'precioUnitario') or 0)
                precio_total = float(find_text(detalle, 'precioTotalSinImpuesto') or 0)

                descuento_detalle = 0.0
                try:
                    descuento_detalle = float(find_text(detalle, 'descuento') or 0)
                except:
                    pass
                total_descuentos += descuento_detalle

                impuestos = extraer_impuestos(find_node(detalle, 'impuestos'))

                productos.append({
                    'codigo': codigo,
                    'descripcion': descripcion[:200] if descripcion else '',
                    'cantidad': cantidad,
                    'precio_unitario': precio_unitario,
                    'precio_total': precio_total,
                    'descuento': descuento_detalle,
                    'ice': impuestos['ice'],
                    'base_ice': impuestos['base_ice'],
                    'iva': impuestos['iva'],
                    'base_iva': impuestos['base_iva']
                })

        return {
            'clave_acceso': clave_acceso,
            'ruc': ruc,
            'razon_social_emisor': razon_social_emisor,
            'numero_factura': numero_factura,
            'fecha_emision': fecha,
            'importe_total': importe_total,
            'descuento_total': total_descuentos,
            'tipo_id_cliente': tipo_id,
            'id_cliente': id_cliente,
            'razon_social_cliente': razon_social,
            'productos': productos,
            'archivo': os.path.basename(ruta_archivo)
        }
    
    except Exception as e:
        print(f"Error parseando {ruta_archivo}: {e}")
        return None


def parse_xml_desde_texto(contenido_xml):
    """
    Parsea un XML desde un string (para cuando el XML viene dentro de otro XML del SRI)
    """
    try:
        root = ET.fromstring(contenido_xml)
        
        info_tributaria = find_node(root, 'infoTributaria')
        info_factura = find_node(root, 'infoFactura')
        
        if info_tributaria is None:
            return None
        
        clave_acceso = find_text(info_tributaria, 'claveAcceso')
        ruc = find_text(info_tributaria, 'ruc')
        fecha = find_text(info_factura, 'fechaEmision')
        importe_total = float(find_text(info_factura, 'importeTotal') or 0)
        
        return {
            'clave_acceso': clave_acceso,
            'ruc': ruc,
            'fecha_emision': fecha,
            'importe_total': importe_total,
            'xml_completo': contenido_xml
        }
    
    except:
        return None