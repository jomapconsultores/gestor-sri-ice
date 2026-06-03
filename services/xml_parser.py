"""
Servicio de parseo de XMLs de facturas electrónicas del SRI
Basado en SRI-XML.py - código probado y funcional
"""
import xml.etree.ElementTree as ET
import os
from datetime import datetime


def find_text_ignore_ns(parent, tag_name):
    """Busca texto en un elemento XML ignorando namespaces - IDÉNTICO A SRI-XML.py"""
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


def find_node_ignore_ns(parent, tag_name):
    """Busca un nodo XML ignorando namespaces - IDÉNTICO A SRI-XML.py"""
    if parent is None:
        return None
    for element in parent.iter():
        if element.tag.endswith(f"}}{tag_name}") or element.tag == tag_name:
            return element
    return None


def parse_xml_factura(filepath, classification_map=None):
    """
    Parsea un archivo XML de factura electrónica del SRI
    IDÉNTICO AL CÓDIGO PROBADO EN SRI-XML.py

    Retorna un diccionario con todos los datos de la factura o None si hay error.
    """
    if classification_map is None:
        classification_map = {}

    try:
        try:
            tree = ET.parse(filepath)
            root = tree.getroot()
        except:
            return None

        comprobante_node = find_node_ignore_ns(root, 'comprobante')
        if comprobante_node is not None and comprobante_node.text:
            inner_xml = comprobante_node.text.strip()
            inner_xml = inner_xml.replace("<![CDATA[", "").replace("]]>", "").strip()
            try:
                root = ET.fromstring(inner_xml)
            except:
                pass

        info_tributaria = find_node_ignore_ns(root, 'infoTributaria')
        info_factura = find_node_ignore_ns(root, 'infoFactura')
        if info_tributaria is None and info_factura is None:
            return None

        clave_acceso = find_text_ignore_ns(info_tributaria, 'claveAcceso')
        ruc = find_text_ignore_ns(info_tributaria, 'ruc')
        ruc_comprador = find_text_ignore_ns(info_factura, 'identificacionComprador')

        estab = find_text_ignore_ns(info_tributaria, 'estab')
        pto_emi = find_text_ignore_ns(info_tributaria, 'ptoEmi')
        secuencial = find_text_ignore_ns(info_tributaria, 'secuencial')
        factura_numero = f"{estab}-{pto_emi}-{secuencial}"
        unique_id = clave_acceso if clave_acceso else f"{ruc}-{factura_numero}"

        fecha = find_text_ignore_ns(info_factura, 'fechaEmision')
        nombre = find_text_ignore_ns(info_tributaria, 'razonSocial')
        destinatario = find_text_ignore_ns(info_factura, 'razonSocialComprador')

        clasificacion = classification_map.get(ruc, "SIN CLASIFICAR")

        pagos = find_node_ignore_ns(info_factura, 'pagos')
        forma_pago = "Otros"
        if pagos is not None:
            pago = find_node_ignore_ns(pagos, 'pago')
            if pago is not None:
                cod_pago = find_text_ignore_ns(pago, 'formaPago')
                if cod_pago == '01':
                    forma_pago = "Sin Utilización del Sistema Financiero"
                elif cod_pago == '19':
                    forma_pago = "Tarjeta de Crédito"
                elif cod_pago == '20':
                    forma_pago = "Otros con Utilización del Sistema Financiero"
                else:
                    forma_pago = f"Código {cod_pago}"

        detalles = find_node_ignore_ns(root, 'detalles')
        concepto_str = "VARIOS"
        if detalles is not None:
            lista_detalles = list(detalles)
            for child in lista_detalles:
                if child.tag.endswith('detalle'):
                    desc = find_text_ignore_ns(child, 'descripcion')
                    if desc:
                        concepto_str = desc
                        if len(lista_detalles) > 1:
                            concepto_str += "..."
                        break

        try:
            total_descuento_xml = float(find_text_ignore_ns(info_factura, 'totalDescuento') or 0)
        except:
            total_descuento_xml = 0.0

        base_0, base_15, iva_15, base_5, iva_5, base_exento, base_no_objeto = 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0
        total_con_impuestos = find_node_ignore_ns(info_factura, 'totalConImpuestos')

        if total_con_impuestos is not None:
            for impuesto in total_con_impuestos:
                codigo = find_text_ignore_ns(impuesto, 'codigo')
                if codigo == '2':  # IVA
                    cod_porc = find_text_ignore_ns(impuesto, 'codigoPorcentaje')
                    try:
                        base_imponible = float(find_text_ignore_ns(impuesto, 'baseImponible') or 0)
                    except:
                        base_imponible = 0.0
                    try:
                        valor_impuesto = float(find_text_ignore_ns(impuesto, 'valor') or 0)
                    except:
                        valor_impuesto = 0.0

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

        try:
            total = float(find_text_ignore_ns(info_factura, 'importeTotal') or 0)
        except:
            total = 0.0

        return {
            "ID": unique_id,
            "Estado": "OK",
            "Fecha": fecha,
            "RUC": ruc,
            "Factura": factura_numero,
            "Nombre": nombre,
            "Clasificación": clasificacion,
            "Concepto": concepto_str,
            "Forma Pago": forma_pago,
            "No Objeto IVA": round(base_no_objeto, 2),
            "Exento IVA": round(base_exento, 2),
            "Base 0%": round(base_0, 2),
            "Base 15%": round(base_15, 2),
            "IVA 15%": round(iva_15, 2),
            "Base 5%": round(base_5, 2),
            "IVA 5%": round(iva_5, 2),
            "Desc. Info": round(total_descuento_xml, 2),
            "Total": round(total, 2),
            "Destinatario": destinatario,
            "RUC_Comprador": ruc_comprador,
            # Para compatibilidad con registro_completo
            'base_iva': round(base_15, 2),
            'valor_iva': round(iva_15, 2),
            'descuento_total': round(total_descuento_xml, 2),
            'importe_total': round(total, 2),
            'numero_factura': factura_numero,
            'fecha_emision': fecha,
            'razon_social_emisor': nombre,
            'tipo_id_cliente': find_text_ignore_ns(info_factura, 'tipoIdentificacionComprador'),
            'id_cliente': ruc_comprador,
            'razon_social_cliente': destinatario or 'CONSUMIDOR FINAL'
        }
    except Exception as e:
        print(f"Error parseando {filepath}: {e}")
        return None


def parse_xml_desde_texto(contenido_xml):
    """Parsea un XML desde un string (para cuando el XML viene dentro de otro XML del SRI)"""
    try:
        root = ET.fromstring(contenido_xml)

        info_tributaria = find_node_ignore_ns(root, 'infoTributaria')
        info_factura = find_node_ignore_ns(root, 'infoFactura')

        if info_tributaria is None:
            return None

        clave_acceso = find_text_ignore_ns(info_tributaria, 'claveAcceso')
        ruc = find_text_ignore_ns(info_tributaria, 'ruc')
        fecha = find_text_ignore_ns(info_factura, 'fechaEmision')
        importe_total = float(find_text_ignore_ns(info_factura, 'importeTotal') or 0)

        return {
            'clave_acceso': clave_acceso,
            'ruc': ruc,
            'fecha_emision': fecha,
            'importe_total': importe_total,
            'xml_completo': contenido_xml
        }

    except:
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