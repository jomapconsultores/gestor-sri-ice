"""Servicios de procesamiento XML ICE/PVP - Extraído de ice_auditoria.py"""

import xml.etree.ElementTree as ET
import xml.dom.minidom as minidom
from collections import defaultdict

# ── Catálogo con códigos SRI reales ──────────────────────────────────────────
CATALOGO = {
    'LICOR ORO': {
        'codMarca': '019167', 'codProdSRI': '19167', 'presentacion': '13',
        'capacidad': '750', 'unidad': '66', 'grado': '15',
        'codImpuesto': '3031', 'tipo': 'Licor', 'botellas_por_caja': 12
    },
    'LICOR SECO BLANCO': {
        'codMarca': '039919', 'codProdSRI': '39919', 'presentacion': '13',
        'capacidad': '750', 'unidad': '66', 'grado': '15',
        'codImpuesto': '3031', 'tipo': 'Licor', 'botellas_por_caja': 12
    },
    'AGUARDIENTE DE CAÑA': {
        'codMarca': '036886', 'codProdSRI': '36886', 'presentacion': '13',
        'capacidad': '750', 'unidad': '66', 'grado': '15',
        'codImpuesto': '3031', 'tipo': 'Licor', 'botellas_por_caja': 12
    },
    'VODKA SECO GLACIAL': {
        'codMarca': '027298', 'codProdSRI': '27298', 'presentacion': '13',
        'capacidad': '750', 'unidad': '66', 'grado': '15',
        'codImpuesto': '3031', 'tipo': 'Licor', 'botellas_por_caja': 12
    },
    'COCKTAIL CON VODKA SABOR A MARACUYA': {
        'codMarca': '022744', 'codProdSRI': '22744', 'presentacion': '13',
        'capacidad': '800', 'unidad': '66', 'grado': '5',
        'codImpuesto': '3031', 'tipo': 'Cocktail', 'botellas_por_caja': 12
    },
    'COCKTAIL CON BAJO GRADO ALCOHOLICO SABOR A DURAZNO': {
        'codMarca': '006868', 'codProdSRI': '6868', 'presentacion': '13',
        'capacidad': '800', 'unidad': '66', 'grado': '5',
        'codImpuesto': '3031', 'tipo': 'Cocktail', 'botellas_por_caja': 12
    },
    'COCKTAIL CON VODKA SABOR A GUARANA': {
        'codMarca': '039912', 'codProdSRI': '39912', 'presentacion': '13',
        'capacidad': '750', 'unidad': '66', 'grado': '5',
        'codImpuesto': '3031', 'tipo': 'Cocktail', 'botellas_por_caja': 12
    },
}

PALABRAS_CLAVE = {
    'LICOR ORO': ['LICOR ORO'],
    'LICOR SECO BLANCO': ['LICOR SECO BLANCO'],
    'AGUARDIENTE DE CAÑA': ['AGUARDIENTE DE CAÑA', 'AGUARDIENTE'],
    'VODKA SECO GLACIAL': ['VODKA SECO GLACIAL', 'VODKA SECO'],
    'COCKTAIL CON VODKA SABOR A MARACUYA': ['MARACUYA', 'MARACUYÁ'],
    'COCKTAIL CON BAJO GRADO ALCOHOLICO SABOR A DURAZNO': ['DURAZNO'],
    'COCKTAIL CON VODKA SABOR A GUARANA': ['GUARANA', 'GUARANÁ'],
}

CATALOGO_DEFAULT = {
    'codMarca': '000000', 'codProdSRI': '', 'presentacion': '13',
    'capacidad': '750', 'unidad': '66', 'grado': '15',
    'codImpuesto': '3031', 'tipo': 'Licor', 'botellas_por_caja': 12
}

_TIPO_ID_ICE = {
    '04': 'R',
    '05': 'C',
    '06': 'P',
    '07': 'F',
    '08': 'F',
}


def buscar_catalogo(descripcion):
    """Busca producto en catálogo por palabras clave."""
    desc_u = descripcion.upper()
    for nombre, claves in PALABRAS_CLAVE.items():
        if any(c in desc_u for c in claves) and nombre in CATALOGO:
            return CATALOGO[nombre].copy()
    return CATALOGO_DEFAULT.copy()


def _construir_cod_prod_ice(info_cat):
    """Construye el código completo codProdICE para el anexo XML del SRI."""
    cod_sri = info_cat.get('codProdSRI', '').strip()
    if not cod_sri:
        return info_cat.get('codImpuesto', '3031')
    if '-' in cod_sri:
        return cod_sri
    pres = info_cat.get('presentacion', '13').zfill(3)
    cap = info_cat.get('capacidad', '750').zfill(6)
    und = info_cat.get('unidad', '66')
    grad = info_cat.get('grado', '15').zfill(6)
    cimp = info_cat.get('codImpuesto', '3031')
    return f"{cimp}-057-{cod_sri.zfill(6)}-{pres}-{cap}-{und}-593-{grad}"


def _mapear_tipo_id(tipo_id_factura):
    """Mapea tipoIdentificacion factura a letra ICE."""
    return _TIPO_ID_ICE.get(str(tipo_id_factura).strip(), 'F')


def es_pack(desc):
    """Detecta si la descripción es un pack."""
    d = desc.upper()
    if 'PACK' in d:
        return True
    if '+' in desc and any(p in d for p in ['AGUARDIENTE', 'VODKA', 'LICOR']):
        return True
    return False


def descomponer_pack(desc):
    """Descompone un pack en productos individuales."""
    d = desc.upper()
    productos = []
    if 'VODKA SECO GLACIAL' in d or 'VODKA SECO' in d or 'VODKA' in d:
        productos.append(('VODKA SECO GLACIAL', '750'))
    if 'LICOR ORO' in d:
        productos.append(('LICOR ORO', '750'))
    if 'AGUARDIENTE' in d:
        cap = '375' if '375' in desc else '750'
        productos.append(('AGUARDIENTE DE CAÑA', cap))
    return productos or [('LICOR ORO', '750')]


def ice_especifico(t_esp, grado, vol_cc):
    """Calcula ICE específico unitario."""
    return t_esp * (grado / 100.0) * (vol_cc / 1000.0)


def ice_advalorem(precio_bot, vol_cc, umbral):
    """Calcula ICE ad valorem unitario."""
    p_litro = (precio_bot * 1000.0) / vol_cc if vol_cc > 0 else 0
    if p_litro > umbral:
        return (p_litro - umbral) * 0.75 * (vol_cc / 1000.0)
    return 0.0


def parsear_xml_ice_bytes(contenido_bytes):
    """
    Parsea un XML de factura electrónica y extrae datos ICE/PVP.

    Args:
        contenido_bytes: contenido del XML como bytes

    Returns:
        tupla (registros_ice, registros_pvp)
    """
    try:
        root = ET.fromstring(contenido_bytes)
        ns = {
            'ac': 'http://www.sri.gob.ec/COMPROBANTES',
            'xsi': 'http://www.w3.org/2001/XMLSchema-instance',
        }

        registros_ice = []
        registros_pvp = []

        # Parsear datos cabecera
        ruc_emisor = root.findtext('.//ac:rucEmisor', '', ns) or root.findtext('.//rucEmisor', '')
        razon_social = root.findtext('.//ac:razonSocialEmisor', '', ns) or root.findtext('.//razonSocialEmisor', '')
        fecha = root.findtext('.//ac:fechaEmision', '', ns) or root.findtext('.//fechaEmision', '')

        # Parsear detalles (productos con ICE)
        detalles = root.findall('.//ac:detalle', ns) or root.findall('.//detalle')

        for det in detalles:
            impuestos = det.findall('.//ac:impuesto', ns) or det.findall('.//impuesto', [])
            for imp in impuestos:
                codigo = imp.findtext('ac:codigo', '', ns) or imp.findtext('codigo', '')

                # Código 3 = ICE, Código 2 = IVA
                if codigo == '3':
                    valor = float(imp.findtext('ac:valor', 0, ns) or imp.findtext('valor', 0) or 0)
                    registros_ice.append({'valor': valor, 'tipo': 'ICE'})
                elif codigo == '2':
                    valor = float(imp.findtext('ac:valor', 0, ns) or imp.findtext('valor', 0) or 0)
                    registros_pvp.append({'valor': valor, 'tipo': 'IVA'})

        return (registros_ice, registros_pvp)

    except Exception as e:
        print(f'Error parsear_xml_ice_bytes: {e}')
        return ([], [])


def construir_xml_ice(tipo, ruc, razon, anio, mes, act_import, datos):
    """
    Construye un XML de Anexo ICE/PVP válido para el SRI.

    Args:
        tipo: 'ICE' o 'PVP'
        ruc: RUC del contribuyente
        razon: razón social
        anio: año del anexo (ej: '2024')
        mes: mes del anexo (ej: '01')
        act_import: actividad de importación
        datos: dict con detalles de productos

    Returns:
        string XML formateado
    """
    try:
        root = ET.Element('anexoIce')
        root.set('tipo', tipo)
        root.set('periodo', f'{anio}{mes}')

        info = ET.SubElement(root, 'informacionAgenteRetencion')
        ET.SubElement(info, 'ruc').text = ruc
        ET.SubElement(info, 'razonSocial').text = razon
        ET.SubElement(info, 'actividadImportacion').text = str(act_import).lower()

        registros = ET.SubElement(root, 'registros')
        for d in (datos or []):
            reg = ET.SubElement(registros, 'registro')
            ET.SubElement(reg, 'codigoProducto').text = d.get('codProdICE', '')
            ET.SubElement(reg, 'cantidadBotella').text = str(d.get('cantidad', 0))
            ET.SubElement(reg, 'valor').text = f"{d.get('valor', 0):.2f}"

        xml_str = minidom.parseString(ET.tostring(root)).toprettyxml(indent='  ')
        return '\n'.join(xml_str.split('\n')[1:])

    except Exception as e:
        print(f'Error construir_xml_ice: {e}')
        return ''
