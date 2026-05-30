"""Editor Web de Anexos SRI – ICE / PVP (basado en ICEanexos.py)"""
from flask import Blueprint, render_template, request, flash, redirect, url_for, Response
from flask_login import login_required, current_user
from routes.payments import usuario_tiene_modulo
import xml.etree.ElementTree as ET
import json

ats = Blueprint('ats', __name__)

CAMPOS_ICE = ['codProdICE', 'gramoAzucar', 'tipoIdCliente', 'idCliente',
              'tipoVentaICE', 'ventaICE', 'devICE', 'cantProdBajaICE']
CAMPOS_PVP = ['codProdPVP', 'gramoAzucar', 'precioExPVP', 'precioPVP',
              'fechaInPVP', 'fechaFinPVP']
CAMPOS_CAB_BASE = ['TipoIDInformante', 'IdInformante', 'razonSocial',
                   'Anio', 'Mes', 'codigoOperativo']
DEFAULTS_NUMERICOS = {
    'devICE': '0', 'cantProdBajaICE': '0', 'ventaICE': '0.00',
    'precioExPVP': '0.00', 'precioPVP': '0.00', 'gramoAzucar': '0.00',
}


def _requiere_modulo():
    if current_user.is_admin:
        return None
    if not usuario_tiene_modulo('anexos_ice'):
        flash('Requieres el módulo Anexos ICE / PVP para usar el editor XML.', 'warning')
        return redirect(url_for('payments.ver_planes'))
    return None


@ats.route('/editor')
@login_required
def editor():
    r = _requiere_modulo()
    if r:
        return r
    return render_template('ats/editor.html',
                           campos_ice=CAMPOS_ICE, campos_pvp=CAMPOS_PVP,
                           campos_cab=CAMPOS_CAB_BASE)


@ats.route('/cargar_xml', methods=['POST'])
@login_required
def cargar_xml():
    r = _requiere_modulo()
    if r:
        return {'error': 'Sin acceso'}, 403
    archivo = request.files.get('archivo_xml')
    if not archivo or not archivo.filename.lower().endswith('.xml'):
        return {'error': 'Sube un archivo .xml válido'}, 400
    try:
        tree = ET.parse(archivo)
        root = tree.getroot()
        tipo = root.tag.upper()

        campo_extra = 'actImport' if tipo == 'ICE' else 'tipoCarga'
        campos_cab = CAMPOS_CAB_BASE + [campo_extra]
        cabecera = {}
        for c in campos_cab:
            n = root.find(c)
            cabecera[c] = (n.text or '') if n is not None else ''

        campos_det = CAMPOS_ICE if tipo == 'ICE' else CAMPOS_PVP
        ventas = []
        ventas_node = root.find('ventas')
        if ventas_node is not None:
            for vta in ventas_node.findall('vta'):
                row = {}
                for c in campos_det:
                    n = vta.find(c)
                    val = (n.text or '') if n is not None else ''
                    if not val:
                        val = DEFAULTS_NUMERICOS.get(c, '')
                    row[c] = val
                ventas.append(row)

        return {'tipo': tipo, 'cabecera': cabecera, 'ventas': ventas,
                'campos': campos_det, 'campo_extra': campo_extra}
    except Exception as e:
        return {'error': str(e)}, 400


@ats.route('/generar_xml', methods=['POST'])
@login_required
def generar_xml():
    r = _requiere_modulo()
    if r:
        return {'error': 'Sin acceso'}, 403
    data = request.get_json(force=True)
    tipo = (data.get('tipo') or 'ICE').lower()
    cabecera = data.get('cabecera', {})
    ventas = data.get('ventas', [])

    root = ET.Element(tipo)
    for campo, valor in cabecera.items():
        ET.SubElement(root, campo).text = str(valor).strip()

    ventas_node = ET.SubElement(root, 'ventas')
    for fila in ventas:
        vta = ET.SubElement(ventas_node, 'vta')
        for campo, valor in fila.items():
            ET.SubElement(vta, campo).text = str(valor).strip()

    xml_body = ET.tostring(root, encoding='unicode')
    xml_content = f'<?xml version="1.0" encoding="UTF-8" standalone="no"?>\n{xml_body}'

    return Response(
        xml_content.encode('utf-8'),
        mimetype='application/xml',
        headers={'Content-Disposition': f'attachment; filename=Anexo_{tipo.upper()}.xml'}
    )
