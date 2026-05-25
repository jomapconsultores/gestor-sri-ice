"""Sistema Integrado ICE – Auditoría + Anexo SRI (basado en ICEcompleto.py)"""
import io, os, json
from collections import defaultdict
from flask import Blueprint, render_template, request, Response, redirect, url_for, flash
from flask_login import login_required, current_user
from routes.payments import usuario_tiene_modulo
import xml.etree.ElementTree as ET
import xml.dom.minidom as minidom

ice_auditoria = Blueprint('ice_auditoria', __name__)

# ── Base de datos tributaria ──────────────────────────────────────────────────
TAX_DB = {
    "2021": {"esp": 7.18, "art": 1.49, "ind": 13.08, "umb": 4.29, "iva": 0.12},
    "2022": {"esp": 10.00, "art": 1.50, "ind": 13.08, "umb": 4.37, "iva": 0.12},
    "2023": {"esp": 10.00, "art": 1.50, "ind": 13.08, "umb": 4.53, "iva": 0.12},
    "2024": {"esp": 10.15, "art": 1.52, "ind": 13.28, "umb": 4.60, "iva": "MIXTO"},
    "2025": {"esp": 10.30, "art": 1.54, "ind": 13.48, "umb": 4.67, "iva": 0.15},
    "2026": {"esp": 10.41, "art": 1.56, "ind": 13.62, "umb": 4.72, "iva": 0.15},
}

CATALOGO = {
    'LICOR ORO': {'codMarca': '000001', 'presentacion': '13', 'capacidad': '750', 'unidad': '66', 'grado': '15', 'codImpuesto': '3031', 'tipo': 'Licor', 'botellas_por_caja': 12},
    'LICOR SECO BLANCO': {'codMarca': '000002', 'presentacion': '13', 'capacidad': '750', 'unidad': '66', 'grado': '15', 'codImpuesto': '3031', 'tipo': 'Licor', 'botellas_por_caja': 12},
    'AGUARDIENTE DE CAÑA': {'codMarca': '000003', 'presentacion': '13', 'capacidad': '750', 'unidad': '66', 'grado': '15', 'codImpuesto': '3031', 'tipo': 'Licor', 'botellas_por_caja': 12},
    'VODKA SECO GLACIAL': {'codMarca': '000004', 'presentacion': '13', 'capacidad': '750', 'unidad': '66', 'grado': '15', 'codImpuesto': '3031', 'tipo': 'Licor', 'botellas_por_caja': 12},
    'COCKTAIL CON VODKA SABOR A MARACUYA': {'codMarca': '000005', 'presentacion': '13', 'capacidad': '800', 'unidad': '66', 'grado': '5', 'codImpuesto': '3031', 'tipo': 'Cocktail', 'botellas_por_caja': 12},
    'COCKTAIL CON BAJO GRADO ALCOHOLICO SABOR A DURAZNO': {'codMarca': '000006', 'presentacion': '13', 'capacidad': '800', 'unidad': '66', 'grado': '5', 'codImpuesto': '3031', 'tipo': 'Cocktail', 'botellas_por_caja': 12},
    'COCKTAIL CON VODKA SABOR A GUARANA': {'codMarca': '000007', 'presentacion': '13', 'capacidad': '750', 'unidad': '66', 'grado': '5', 'codImpuesto': '3031', 'tipo': 'Cocktail', 'botellas_por_caja': 12},
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
CATALOGO_DEFAULT = {'codMarca': '000000', 'presentacion': '13', 'capacidad': '750',
                    'unidad': '66', 'grado': '15', 'codImpuesto': '3031',
                    'tipo': 'Licor', 'botellas_por_caja': 12}


def buscar_catalogo(descripcion):
    desc_u = descripcion.upper()
    for nombre, claves in PALABRAS_CLAVE.items():
        if any(c in desc_u for c in claves) and nombre in CATALOGO:
            return CATALOGO[nombre].copy()
    return CATALOGO_DEFAULT.copy()


def es_pack(desc):
    d = desc.upper()
    if 'PACK' in d:
        return True
    if '+' in desc and any(p in d for p in ['AGUARDIENTE', 'VODKA', 'LICOR']):
        return True
    return False


def descomponer_pack(desc):
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
    return t_esp * (grado / 100.0) * (vol_cc / 1000.0)


def ice_advalorem(precio_bot, vol_cc, umbral):
    p_litro = (precio_bot * 1000.0) / vol_cc if vol_cc > 0 else 0
    if p_litro > umbral:
        return (p_litro - umbral) * 0.75 * (vol_cc / 1000.0)
    return 0.0


def _requiere_modulo():
    if current_user.is_admin:
        return None
    if not usuario_tiene_modulo('ice_multiple'):
        flash('Requieres el módulo Cálculo ICE Múltiple para usar la Auditoría ICE.', 'warning')
        return redirect(url_for('payments.ver_planes'))
    return None


# ── Parseo XML de facturas ICE ───────────────────────────────────────────────

def parsear_xml_ice(ruta):
    try:
        tree = ET.parse(ruta)
        root = tree.getroot()
        if root.tag != 'factura':
            return [], []

        fact = root.find('infoFactura')
        if fact is None:
            return [], []

        fecha = (fact.find('fechaEmision').text or '') if fact.find('fechaEmision') is not None else ''
        tipo_id = (fact.find('tipoIdentificacionComprador').text or '') if fact.find('tipoIdentificacionComprador') is not None else ''
        id_cli = (fact.find('identificacionComprador').text or '') if fact.find('identificacionComprador') is not None else ''
        razon_el = fact.find('razonSocialComprador')
        razon = razon_el.text if razon_el is not None else 'CONSUMIDOR FINAL'
        importe_total = float((fact.find('importeTotal').text or '0') if fact.find('importeTotal') is not None else '0')

        registros_ice = []
        registros_pvp = []
        detalles = root.find('detalles')
        if detalles is None:
            return [], []

        for det in detalles.findall('detalle'):
            cod = (det.find('codigoPrincipal').text or '') if det.find('codigoPrincipal') is not None else ''
            desc = (det.find('descripcion').text or '') if det.find('descripcion') is not None else ''
            try:
                cant = float(det.find('cantidad').text or 0)
            except (ValueError, AttributeError):
                cant = 0.0
            try:
                p_unit = float(det.find('precioUnitario').text or 0)
            except (ValueError, AttributeError):
                p_unit = 0.0
            try:
                p_total = float(det.find('precioTotalSinImpuesto').text or 0)
            except (ValueError, AttributeError):
                p_total = 0.0

            ice_val = iva_val = base_ice = base_iva = 0.0
            impuestos = det.find('impuestos')
            if impuestos is not None:
                for imp in impuestos.findall('impuesto'):
                    try:
                        codigo = imp.find('codigo').text
                        if codigo == '3':
                            ice_val = float(imp.find('valor').text or 0)
                            base_ice = float(imp.find('baseImponible').text or 0)
                        elif codigo == '2':
                            iva_val = float(imp.find('valor').text or 0)
                            base_iva = float(imp.find('baseImponible').text or 0)
                    except Exception:
                        pass

            bot_caja = 2 if es_pack(desc) else (12 if '12U' in desc.upper() else 12)
            unidades = int(cant * bot_caja)
            info_cat = buscar_catalogo(desc)
            precio_caja = p_total / cant if cant > 0 else p_unit
            precio_bot = precio_caja / bot_caja if bot_caja > 0 else precio_caja

            reg = {
                'fecha_emision': fecha,
                'tipo_id_cliente': tipo_id, 'id_cliente': id_cli,
                'razon_social_cliente': razon,
                'codigo_producto': cod, 'nombre_producto': desc[:80],
                'codMarca': info_cat['codMarca'], 'presentacion': info_cat['presentacion'],
                'capacidad': info_cat['capacidad'], 'unidad': info_cat['unidad'],
                'grado_alcoholico': info_cat['grado'], 'codImpuesto': info_cat['codImpuesto'],
                'tipo_producto': info_cat['tipo'],
                'es_pack': es_pack(desc), 'botellas_por_caja': bot_caja,
                'cantidad_cajas': cant, 'unidades_botellas': unidades,
                'precio_unitario': p_unit, 'precio_total_sin_impuesto': p_total,
                'precio_por_caja': precio_caja, 'precio_por_botella': precio_bot,
                'base_ice': base_ice, 'valor_ice': ice_val,
                'base_iva': base_iva, 'valor_iva': iva_val,
                'importe_total': importe_total,
                'archivo': os.path.basename(ruta)
            }

            if ice_val > 0:
                registros_ice.append(reg.copy())
            if p_unit > 0:
                registros_pvp.append(reg.copy())

        return registros_ice, registros_pvp
    except Exception as e:
        print(f'Error parseando {ruta}: {e}')
        return [], []


# ── Rutas ────────────────────────────────────────────────────────────────────

@ice_auditoria.route('/')
@login_required
def index():
    r = _requiere_modulo()
    if r:
        return r
    return render_template('ice_auditoria/index.html', anios=list(TAX_DB.keys()))


@ice_auditoria.route('/procesar', methods=['POST'])
@login_required
def procesar():
    r = _requiere_modulo()
    if r:
        return {'error': 'Sin acceso'}, 403

    archivos = request.files.getlist('archivos_xml')
    if not archivos:
        return {'error': 'Sube archivos XML de facturas'}, 400

    carpeta = os.path.join('uploads', str(current_user.id), 'ice_audit')
    os.makedirs(carpeta, exist_ok=True)

    datos_ice = []
    datos_pvp = []
    archivos_proc = set()

    for arch in archivos:
        if not arch.filename.lower().endswith('.xml'):
            continue
        ruta = os.path.join(carpeta, arch.filename)
        if ruta in archivos_proc:
            continue
        arch.save(ruta)
        archivos_proc.add(ruta)
        ice, pvp = parsear_xml_ice(ruta)
        datos_ice.extend(ice)
        datos_pvp.extend(pvp)

    return {
        'datos_ice': datos_ice,
        'datos_pvp': datos_pvp,
        'total_ice': len(datos_ice),
        'total_pvp': len(datos_pvp),
        'archivos': len(archivos_proc)
    }


@ice_auditoria.route('/generar_xml_anexo', methods=['POST'])
@login_required
def generar_xml_anexo():
    r = _requiere_modulo()
    if r:
        return {'error': 'Sin acceso'}, 403

    data = request.get_json(force=True)
    tipo = data.get('tipo', 'ICE').upper()
    ruc = data.get('ruc', '')
    razon = data.get('razon', '')
    anio = data.get('anio', '')
    mes = data.get('mes', '')
    datos = data.get('datos', [])

    root = ET.Element(tipo.lower())
    ET.SubElement(root, 'TipoIDInformante').text = 'R'
    ET.SubElement(root, 'IdInformante').text = ruc
    ET.SubElement(root, 'razonSocial').text = razon
    ET.SubElement(root, 'Anio').text = anio
    ET.SubElement(root, 'Mes').text = mes
    ET.SubElement(root, 'codigoOperativo').text = tipo
    if tipo == 'ICE':
        ET.SubElement(root, 'actImport').text = '0'

    ventas = ET.SubElement(root, 'ventas')
    ag = defaultdict(lambda: defaultdict(lambda: {'bot': 0, 'datos': {}}))
    for reg in datos:
        ag[reg['id_cliente']][reg['codigo_producto']]['bot'] += reg['unidades_botellas']
        ag[reg['id_cliente']][reg['codigo_producto']]['datos'] = reg

    for id_cli, prods in sorted(ag.items()):
        for cod_p, vals in sorted(prods.items()):
            reg = vals['datos']
            vta = ET.SubElement(ventas, 'vta')
            if tipo == 'ICE':
                campos = [
                    ('codProdICE', reg.get('codImpuesto', '3031')),
                    ('gramoAzucar', '0.00'),
                    ('tipoIdCliente', reg.get('tipo_id_cliente', '04')),
                    ('idCliente', id_cli),
                    ('tipoVentaICE', '1'),
                    ('ventaICE', f"{vals['bot']:.2f}"),
                    ('devICE', '0'),
                    ('cantProdBajaICE', str(vals['bot'])),
                ]
            else:
                campos = [
                    ('codProdPVP', reg.get('codMarca', '000001')),
                    ('gramoAzucar', '0.00'),
                    ('precioExPVP', f"{reg.get('precio_por_botella', 0):.2f}"),
                    ('precioPVP', f"{reg.get('precio_por_botella', 0):.2f}"),
                    ('fechaInPVP', f"01/{mes}/{anio}"),
                    ('fechaFinPVP', f"31/{mes}/{anio}"),
                ]
            for campo, valor in campos:
                ET.SubElement(vta, campo).text = str(valor)

    xml_str = minidom.parseString(ET.tostring(root, encoding='utf-8')).toprettyxml(indent='  ')

    return Response(
        xml_str.encode('utf-8'),
        mimetype='application/xml',
        headers={'Content-Disposition': f'attachment; filename=Anexo_{tipo}_{ruc}_{anio}{mes}.xml'}
    )


@ice_auditoria.route('/exportar_auditoria', methods=['POST'])
@login_required
def exportar_auditoria():
    r = _requiere_modulo()
    if r:
        return {'error': 'Sin acceso'}, 403

    data = request.get_json(force=True)
    datos = data.get('datos_ice', [])
    anio = data.get('anio', '2026')
    iva_tasa_override = data.get('iva_tasa', None)

    if not datos:
        return {'error': 'No hay datos ICE para exportar'}, 400

    info_tax = TAX_DB.get(anio, TAX_DB['2026'])
    iva_tasa = iva_tasa_override if iva_tasa_override else (
        info_tax['iva'] if isinstance(info_tax['iva'], float) else 0.15
    )

    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
        from openpyxl.utils import get_column_letter

        def estyle(h_color='FF1a5276', font_color='FFFFFFFF', bold=True):
            return {
                'fill': PatternFill(start_color=h_color, end_color=h_color, fill_type='solid'),
                'font': Font(name='Arial', size=9, bold=bold, color=font_color),
                'border': Border(
                    left=Side(style='thin'), right=Side(style='thin'),
                    top=Side(style='thin'), bottom=Side(style='thin')
                )
            }

        def cel(ws, row, col, val, style=None, fmt=None):
            c = ws.cell(row=row, column=col, value=val)
            if style:
                c.fill = style['fill']
                c.font = style['font']
                c.border = style['border']
            if fmt:
                c.number_format = fmt
            return c

        wb = Workbook()
        s_head = estyle()
        s_norm = estyle('FFFFFFFF', 'FF000000', False)
        s_norm['fill'] = PatternFill(fill_type=None)
        s_total = estyle('FF27ae60')
        brd = s_head['border']

        def write_headers(ws, row, headers):
            for j, h in enumerate(headers, 1):
                c = ws.cell(row=row, column=j, value=h)
                c.fill = s_head['fill']
                c.font = s_head['font']
                c.border = brd
                c.alignment = Alignment(horizontal='center', wrap_text=True)

        # ── Hoja 1: Detalle Completo ──────────────────────────────────────────
        ws = wb.active
        ws.title = 'Detalle Completo'

        enc = ['Fecha', 'Archivo', 'Tipo ID', 'ID Cliente', 'Razón Social',
               'Cód. Prod.', 'Nombre Producto', 'Cód. Marca', 'Es Pack',
               'Presentación', 'Capacidad', 'Unidad', 'Grado Alc.',
               'Bot/Caja', 'Cajas', 'Botellas',
               'Precio/Caja', 'Precio/Botella', 'Subtotal',
               'Base ICE', 'ICE', 'Base IVA', f'IVA {int(iva_tasa*100)}%', 'Importe Total']

        write_headers(ws, 1, enc)

        fila = 2
        for reg in datos:
            fijos = [
                reg.get('fecha_emision', ''), reg.get('archivo', ''),
                reg.get('tipo_id_cliente', ''), reg.get('id_cliente', ''),
                reg.get('razon_social_cliente', '')[:40],
                reg.get('codigo_producto', ''), reg.get('nombre_producto', '')[:40],
                reg.get('codMarca', ''), 'SÍ' if reg.get('es_pack') else 'NO',
                reg.get('presentacion', ''), reg.get('capacidad', ''),
                reg.get('unidad', ''), reg.get('grado_alcoholico', ''),
                reg.get('botellas_por_caja', 12), reg.get('cantidad_cajas', 0),
                reg.get('unidades_botellas', 0)
            ]
            for j, val in enumerate(fijos, 1):
                c = ws.cell(row=fila, column=j, value=val)
                c.border = brd
            for j, val in enumerate([
                reg.get('precio_por_caja', 0), reg.get('precio_por_botella', 0),
                reg.get('precio_total_sin_impuesto', 0),
                reg.get('base_ice', 0), reg.get('valor_ice', 0),
                reg.get('base_iva', 0), reg.get('valor_iva', 0),
                reg.get('importe_total', 0)
            ], 17):
                c = ws.cell(row=fila, column=j, value=val)
                c.number_format = '#,##0.00'
                c.border = brd
            fila += 1

        tot_row = fila
        ws.cell(row=tot_row, column=1, value='TOTALES').fill = s_total['fill']
        ws.cell(row=tot_row, column=1).font = s_total['font']
        for col in [15, 16, 17, 18, 19, 20, 21, 22, 23, 24]:
            letra = get_column_letter(col)
            c = ws.cell(row=tot_row, column=col, value=f'=SUM({letra}2:{letra}{tot_row-1})')
            c.fill = s_total['fill']
            c.font = s_total['font']
            c.number_format = '#,##0.00'
            c.border = brd

        # ── Hoja 2: Resumen ICE por Producto ─────────────────────────────────
        ws2 = wb.create_sheet('Resumen ICE')
        enc2 = ['Producto', 'Botellas', 'Precio Total', 'ICE Específico',
                'ICE Ad-Valorem', 'Total ICE', 'Aplica AdV?']
        write_headers(ws2, 1, enc2)

        prod_ag = defaultdict(lambda: {'bot': 0, 'precio': 0.0, 'ice_esp': 0.0, 'ice_adv': 0.0, 'aplica': False})
        for reg in datos:
            vol = float(reg.get('capacidad', 750))
            grado = float(reg.get('grado_alcoholico', 15))
            cajas = float(reg.get('cantidad_cajas', 0))
            precio_bot = float(reg.get('precio_por_botella', 0))

            if reg.get('es_pack'):
                prods = descomponer_pack(reg.get('nombre_producto', ''))
                num_p = len(prods)
                for pnom, pcap in prods:
                    cat = buscar_catalogo(pnom)
                    pbot = float(reg.get('precio_total_sin_impuesto', 0)) / (num_p * cajas) if cajas > 0 else 0
                    grado_p = float(cat.get('grado', 15))
                    vol_p = float(pcap)
                    i_esp = ice_especifico(info_tax['esp'], grado_p, vol_p) * cajas
                    i_adv = ice_advalorem(pbot, vol_p, info_tax['umb']) * cajas
                    k = f"{pnom} {pcap}ml (PACK)"
                    prod_ag[k]['bot'] += cajas
                    prod_ag[k]['precio'] += pbot * cajas
                    prod_ag[k]['ice_esp'] += i_esp
                    prod_ag[k]['ice_adv'] += i_adv
                    p_litro = (pbot * 1000.0) / vol_p if vol_p > 0 else 0
                    prod_ag[k]['aplica'] = p_litro > info_tax['umb']
            else:
                i_esp = ice_especifico(info_tax['esp'], grado, vol) * cajas
                i_adv = ice_advalorem(precio_bot, vol, info_tax['umb']) * cajas
                k = reg.get('nombre_producto', '')[:50]
                p_litro = (precio_bot * 1000.0) / vol if vol > 0 else 0
                prod_ag[k]['bot'] += int(reg.get('unidades_botellas', 0))
                prod_ag[k]['precio'] += float(reg.get('precio_total_sin_impuesto', 0))
                prod_ag[k]['ice_esp'] += i_esp
                prod_ag[k]['ice_adv'] += i_adv
                prod_ag[k]['aplica'] = p_litro > info_tax['umb']

        fila2 = 2
        for nombre, vals in sorted(prod_ag.items()):
            ice_tot = vals['ice_esp'] + vals['ice_adv']
            datos_fila = [nombre, vals['bot'], vals['precio'],
                          vals['ice_esp'], vals['ice_adv'], ice_tot,
                          'SÍ' if vals['aplica'] else 'NO']
            for j, val in enumerate(datos_fila, 1):
                c = ws2.cell(row=fila2, column=j, value=val)
                c.border = brd
                if j in (2, 3, 4, 5, 6):
                    c.number_format = '#,##0.00'
            fila2 += 1

        tot2 = fila2
        ws2.cell(row=tot2, column=1, value='TOTAL GENERAL').fill = s_total['fill']
        ws2.cell(row=tot2, column=1).font = s_total['font']
        for col in (2, 3, 4, 5, 6):
            letra = get_column_letter(col)
            c = ws2.cell(row=tot2, column=col, value=f'=SUM({letra}2:{letra}{tot2-1})')
            c.fill = s_total['fill']
            c.font = s_total['font']
            c.number_format = '#,##0.00'

        # ── Hoja 3: Resumen General ───────────────────────────────────────────
        ws3 = wb.create_sheet('Resumen General')
        enc3 = ['Concepto', 'Subtotal', 'ICE Específico', 'ICE Ad-Valorem',
                'Total ICE', 'Base IVA', f'IVA {int(iva_tasa*100)}%', 'Total General']
        write_headers(ws3, 1, enc3)

        t_sub = sum(float(r.get('precio_total_sin_impuesto', 0)) for r in datos)
        t_ice_esp = sum(v['ice_esp'] for v in prod_ag.values())
        t_ice_adv = sum(v['ice_adv'] for v in prod_ag.values())
        t_ice = t_ice_esp + t_ice_adv
        base_iva = t_sub + t_ice
        iva = base_iva * iva_tasa
        total_gen = base_iva + iva

        for j, val in enumerate([
            'TOTAL VENTAS BEBIDAS ALCOHÓLICAS', t_sub, t_ice_esp,
            t_ice_adv, t_ice, base_iva, iva, total_gen
        ], 1):
            c = ws3.cell(row=2, column=j, value=val)
            c.border = brd
            if j >= 2:
                c.number_format = '#,##0.00'

        # Ajustar anchos
        for j, w in enumerate([8, 12, 22, 30, 10, 30, 8, 8, 12, 12, 10,
                                10, 12, 8, 10, 12, 12, 12, 12, 12, 12, 12, 10, 12], 1):
            ws.column_dimensions[get_column_letter(j)].width = w
        ws2.column_dimensions['A'].width = 40
        ws3.column_dimensions['A'].width = 40
        for j in range(2, 9):
            ws2.column_dimensions[get_column_letter(j)].width = 16
            ws3.column_dimensions[get_column_letter(j)].width = 16

        output = io.BytesIO()
        wb.save(output)
        output.seek(0)

        return Response(
            output.getvalue(),
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            headers={'Content-Disposition': f'attachment; filename=Auditoria_ICE_{anio}.xlsx'}
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {'error': str(e)}, 500
