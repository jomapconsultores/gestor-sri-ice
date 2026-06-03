"""Módulo: Anexos ICE/PVP - Editor visual y generador de XMLs para el SRI"""

from flask import Blueprint, render_template, request, Response, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from routes.payments import usuario_tiene_modulo
from models import db
from models.user import AnexoICEGuardado
from services.ice_xml import construir_xml_ice
import json
import io
import zipfile
from datetime import datetime

try:
    from defusedxml.ElementTree import fromstring as ET_fromstring, parse as ET_parse, Element as ET_Element, SubElement as ET_SubElement, tostring as ET_tostring
    from defusedxml import ElementTree as ET
    DEFUSEDXML_AVAILABLE = True
except ImportError:
    from xml.etree.ElementTree import fromstring as ET_fromstring, parse as ET_parse, Element as ET_Element, SubElement as ET_SubElement, tostring as ET_tostring
    import xml.etree.ElementTree as ET
    DEFUSEDXML_AVAILABLE = False

anexos_ice = Blueprint('anexos_ice', __name__)

# Constantes para el editor ATS/Anexos (originalmente de ats.py)
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


def _requiere():
    """Verifica si el usuario tiene el módulo Anexos ICE."""
    if current_user.is_admin:
        return None
    if not usuario_tiene_modulo('anexos_ice'):
        flash('Requieres el módulo Anexos ICE / PVP ($10/mes) para acceder.', 'warning')
        return redirect(url_for('payments.ver_planes'))
    return None


@anexos_ice.route('/')
@login_required
def index():
    """Página principal del editor de Anexos ICE/PVP."""
    r = _requiere()
    if r:
        return r

    anexos_guardados = AnexoICEGuardado.query.filter_by(
        usuario_id=current_user.id
    ).order_by(AnexoICEGuardado.fecha_guardado.desc()).all()

    return render_template('anexos_ice/index.html',
                           anexos_guardados=anexos_guardados)


@anexos_ice.route('/parsear_xml', methods=['POST'])
@login_required
def parsear_xml():
    """Parsea un XML subido y devuelve los campos editables."""
    r = _requiere()
    if r:
        return jsonify({'error': 'Sin acceso'}), 403

    try:
        if 'archivo' not in request.files:
            return jsonify({'error': 'No se envió archivo'}), 400

        archivo = request.files['archivo']
        contenido = archivo.read()

        if not contenido:
            return jsonify({'error': 'Archivo vacío'}), 400

        if not DEFUSEDXML_AVAILABLE:
            flash('⚠️ Advertencia: defusedxml no instalado, usando XML estándar', 'warning')

        try:
            root = ET_fromstring(contenido)
        except Exception as e:
            return jsonify({'error': f'XML inválido: {str(e)[:100]}'}), 400

        resultado = {
            'ruc': root.findtext('.//ruc', ''),
            'razonSocial': root.findtext('.//razonSocial', ''),
            'periodo': root.findtext('.//periodo', ''),
            'tipo': root.get('tipo', 'ICE'),
            'registros': []
        }

        registros = root.findall('.//registro')
        for reg in registros[:100]:  # Limitar a 100 registros
            resultado['registros'].append({
                'codigoProducto': reg.findtext('codigoProducto', ''),
                'cantidadBotella': reg.findtext('cantidadBotella', '0'),
                'valor': reg.findtext('valor', '0'),
            })

        return jsonify(resultado)

    except Exception as e:
        return jsonify({'error': str(e)}), 400


@anexos_ice.route('/guardar_xml', methods=['POST'])
@login_required
def guardar_xml():
    """Guarda un XML en la base de datos del usuario."""
    r = _requiere()
    if r:
        return jsonify({'error': 'Sin acceso'}), 403

    try:
        datos = request.get_json()
        nombre = datos.get('nombre', f'Anexo_{datetime.now().strftime("%Y%m%d_%H%M%S")}')
        tipo = datos.get('tipo', 'ICE')
        xml_contenido = datos.get('xml_contenido', '')
        periodo_anio = datos.get('periodo_anio', '')
        periodo_mes = datos.get('periodo_mes', '')

        anexo = AnexoICEGuardado(
            usuario_id=current_user.id,
            nombre=nombre,
            tipo=tipo,
            xml_contenido=xml_contenido,
            periodo_anio=periodo_anio,
            periodo_mes=periodo_mes,
        )
        db.session.add(anexo)
        db.session.commit()

        return jsonify({'success': True, 'id': anexo.id})

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400


@anexos_ice.route('/cargar/<int:anexo_id>')
@login_required
def cargar_guardado(anexo_id):
    """Carga un XML guardado anteriormente."""
    r = _requiere()
    if r:
        return r

    anexo = AnexoICEGuardado.query.filter_by(
        id=anexo_id, usuario_id=current_user.id
    ).first_or_404()

    return jsonify({
        'id': anexo.id,
        'nombre': anexo.nombre,
        'tipo': anexo.tipo,
        'xml_contenido': anexo.xml_contenido,
        'periodo_anio': anexo.periodo_anio,
        'periodo_mes': anexo.periodo_mes,
    })


@anexos_ice.route('/generar_xml', methods=['POST'])
@login_required
def generar_xml():
    """Genera un XML validado a partir de los datos editados."""
    r = _requiere()
    if r:
        return jsonify({'error': 'Sin acceso'}), 403

    try:
        datos = request.get_json()
        tipo = datos.get('tipo', 'ICE')
        ruc = datos.get('ruc', '')
        razon = datos.get('razon', '')
        anio = datos.get('anio', '')
        mes = datos.get('mes', '')
        registros = datos.get('registros', [])

        xml_str = construir_xml_ice(
            tipo=tipo,
            ruc=ruc,
            razon=razon,
            anio=anio,
            mes=mes,
            act_import=False,
            datos=registros
        )

        return jsonify({
            'success': True,
            'xml': xml_str,
            'nombre': f'Anexo{tipo}_{anio}{mes}.xml'
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 400


@anexos_ice.route('/descargar_xml', methods=['POST'])
@login_required
def descargar_xml():
    """Descarga el XML generado."""
    r = _requiere()
    if r:
        return r, 403

    try:
        datos = request.get_json()
        xml_contenido = datos.get('xml', '')
        nombre = datos.get('nombre', 'anexo.xml')

        return Response(
            xml_contenido.encode('utf-8'),
            mimetype='application/xml',
            headers={'Content-Disposition': f'attachment; filename={nombre}'}
        )

    except Exception as e:
        return {'error': str(e)}, 400


# ── Editor ATS (Anexos - originalmente de ats.py) ─────────────────────────────

@anexos_ice.route('/editor')
@login_required
def editor():
    """Editor web para Anexos ICE/PVP (compatible con ats.py)."""
    r = _requiere()
    if r:
        return r
    return render_template('ats/editor.html',
                           campos_ice=CAMPOS_ICE, campos_pvp=CAMPOS_PVP,
                           campos_cab=CAMPOS_CAB_BASE)


@anexos_ice.route('/cargar_xml_ats', methods=['POST'])
@login_required
def cargar_xml_ats():
    """Carga un XML en formato ATS (compatible con ats.py)."""
    r = _requiere()
    if r:
        return jsonify({'error': 'Sin acceso'}), 403
    archivo = request.files.get('archivo_xml')
    if not archivo or not archivo.filename.lower().endswith('.xml'):
        return jsonify({'error': 'Sube un archivo .xml válido'}), 400
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

        return jsonify({'tipo': tipo, 'cabecera': cabecera, 'ventas': ventas,
                'campos': campos_det, 'campo_extra': campo_extra})
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@anexos_ice.route('/generar_xml_ats', methods=['POST'])
@login_required
def generar_xml_ats():
    """Genera un XML en formato ATS (compatible con ats.py)."""
    r = _requiere()
    if r:
        return jsonify({'error': 'Sin acceso'}), 403
    data = request.get_json(force=True)
    tipo = (data.get('tipo') or 'ICE').lower()
    cabecera = data.get('cabecera', {})
    ventas = data.get('ventas', [])

    root = ET_Element(tipo)
    for campo, valor in cabecera.items():
        ET_SubElement(root, campo).text = str(valor).strip()

    ventas_node = ET_SubElement(root, 'ventas')
    for fila in ventas:
        vta = ET_SubElement(ventas_node, 'vta')
        for campo, valor in fila.items():
            ET_SubElement(vta, campo).text = str(valor).strip()

    xml_body = ET_tostring(root, encoding='unicode')
    xml_content = f'<?xml version="1.0" encoding="UTF-8" standalone="no"?>\n{xml_body}'

    return Response(
        xml_content.encode('utf-8'),
        mimetype='application/xml',
        headers={'Content-Disposition': f'attachment; filename=Anexo_{tipo.upper()}.xml'}
    )


@anexos_ice.route('/descargar_zip', methods=['POST'])
@login_required
def descargar_zip():
    """Descarga el XML empaquetado en ZIP."""
    r = _requiere()
    if r:
        return r, 403

    try:
        datos = request.get_json()
        xml_contenido = datos.get('xml', '')
        nombre_xml = datos.get('nombre', 'anexo.xml')
        nombre_zip = nombre_xml.replace('.xml', '.zip')

        output = io.BytesIO()
        with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.writestr(nombre_xml, xml_contenido.encode('utf-8'))
        output.seek(0)

        return Response(
            output.getvalue(),
            mimetype='application/zip',
            headers={'Content-Disposition': f'attachment; filename={nombre_zip}'}
        )

    except Exception as e:
        return {'error': str(e)}, 400
