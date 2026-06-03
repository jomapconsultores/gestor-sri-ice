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
    """Parsea XML de factura - extrae TODOS los datos incluyendo composición IVA completa"""
    try:
        tree = ET.parse(ruta_archivo)
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
        ruc = find_text(info_trib, 'ruc')
        estab = find_text(info_trib, 'estab')
        pto_emi = find_text(info_trib, 'ptoEmi')
        secuencial = find_text(info_trib, 'secuencial')
        numero_factura = f'{estab}-{pto_emi}-{secuencial}'
        razon_social_emisor = find_text(info_trib, 'razonSocial')

        fecha_emision = find_text(info_fact, 'fechaEmision')

        # Comprador
        tipo_id_cliente = find_text(info_fact, 'tipoIdentificacionComprador')
        id_cliente = find_text(info_fact, 'identificacionComprador')
        razon_social_cliente = find_text(info_fact, 'razonSocialComprador') or 'CONSUMIDOR FINAL'

        # ──────────────────────────────────────────────────────────────
        # COMPOSICIÓN IVA (CLAVE) - Separada por porcentajes
        # ──────────────────────────────────────────────────────────────
        base_0 = base_15 = valor_iva = base_5 = iva_5 = base_exento = base_no_objeto = 0.0
        total_con_imp = find_node(info_fact, 'totalConImpuestos')
        if total_con_imp is not None:
            for imp in total_con_imp:
                codigo = find_text(imp, 'codigo')
                if codigo == '2':  # IVA
                    cod_porc = find_text(imp, 'codigoPorcentaje')
                    try:
                        base_imp = float(find_text(imp, 'baseImponible') or 0)
                    except (ValueError, TypeError):
                        base_imp = 0.0
                    try:
                        val_imp = float(find_text(imp, 'valor') or 0)
                    except (ValueError, TypeError):
                        val_imp = 0.0

                    if cod_porc == '0':
                        base_0 += base_imp
                    elif cod_porc in ('2', '3', '4', '10'):
                        base_15 += base_imp
                        valor_iva += val_imp
                    elif cod_porc == '5':
                        base_5 += base_imp
                        iva_5 += val_imp
                    elif cod_porc == '6':
                        base_no_objeto += base_imp
                    elif cod_porc == '7':
                        base_exento += base_imp

        # ──────────────────────────────────────────────────────────────
        # TOTALES Y DESCUENTOS
        # ──────────────────────────────────────────────────────────────
        try:
            importe_total = float(find_text(info_fact, 'importeTotal') or 0)
        except (ValueError, TypeError):
            importe_total = 0.0

        try:
            descuento_total = float(find_text(info_fact, 'totalDescuento') or 0)
        except (ValueError, TypeError):
            descuento_total = 0.0

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
        # DETALLES
        # ──────────────────────────────────────────────────────────────
        detalles_n = find_node(root, 'detalles')
        productos = []
        if detalles_n is not None:
            for det in detalles_n:
                try:
                    desc = find_text(det, 'descripcion')
                    productos.append({
                        'codigo': find_text(det, 'codigoPrincipal'),
                        'descripcion': desc[:200] if desc else '',
                        'cantidad': float(find_text(det, 'cantidad') or 0),
                        'precio_unitario': float(find_text(det, 'precioUnitario') or 0),
                        'precio_total': float(find_text(det, 'precioTotalSinImpuesto') or 0),
                    })
                except:
                    pass

        return {
            'clave_acceso': clave_acceso,
            'ruc': ruc,
            'razon_social_emisor': razon_social_emisor,
            'numero_factura': numero_factura,
            'fecha_emision': fecha_emision,
            'importe_total': round(importe_total, 2),
            'descuento_total': round(descuento_total, 2),
            'tipo_id_cliente': tipo_id_cliente,
            'id_cliente': id_cliente,
            'razon_social_cliente': razon_social_cliente,
            # Composición IVA (la parte crítica)
            'base_iva': round(base_15, 2),
            'valor_iva': round(valor_iva, 2),
            'base_0': round(base_0, 2),
            'base_5': round(base_5, 2),
            'iva_5': round(iva_5, 2),
            'base_exento': round(base_exento, 2),
            'base_no_objeto': round(base_no_objeto, 2),
            'forma_pago': forma_pago,
            'productos': productos,
            'archivo': os.path.basename(ruta_archivo)
        }

    except Exception as e:
        print(f'Error parseando {ruta_archivo}: {e}')
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