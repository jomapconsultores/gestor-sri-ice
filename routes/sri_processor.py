"""Gestor SRI Pro – Descarga masiva + clasificación + Excel (basado en SRI-XML.py)"""
import io, re, os, json
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import Counter
from flask import Blueprint, render_template, request, flash, redirect, url_for, Response, session
from flask_login import login_required, current_user
from routes.payments import usuario_tiene_modulo
try:
    from defusedxml import ElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET

sri_processor = Blueprint('sri_processor', __name__)

SRI_URLS = [
    "https://cel.sri.gob.ec/comprobantes-electronicos-ws/AutorizacionComprobantesOffline?wsdl",
    "https://celcer.sri.gob.ec/comprobantes-electronicos-ws/AutorizacionComprobantesOffline?wsdl"
]

GASTOS_PERSONALES = [
    "ALIMENTACIÓN", "ALIMENTACION", "EDUCACIÓN", "EDUCACION",
    "SALUD", "VESTIMENTA", "VIVIENDA", "VARIOS", "TURISMO", "ARTE Y CULTURA"
]


def _requiere_modulo():
    if current_user.is_admin:
        return None
    if not usuario_tiene_modulo('descarga_sri'):
        flash('Requieres el módulo Descarga Masiva SRI.', 'warning')
        return redirect(url_for('payments.ver_planes'))
    return None


# ── Helpers XML ─────────────────────────────────────────────────────────────

def find_text(parent, tag):
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
    if parent is None:
        return None
    for el in parent.iter():
        if el.tag.endswith(f'}}{tag}') or el.tag == tag:
            return el
    return None


def descargar_xml_sri(clave_acceso, carpeta):
    import requests, urllib3
    urllib3.disable_warnings()

    ruta = os.path.join(carpeta, f'{clave_acceso}.xml')
    if os.path.exists(ruta) and os.path.getsize(ruta) > 200:
        return ruta

    soap = (
        '<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"'
        ' xmlns:ec="http://ec.gob.sri.ws.autorizacion">'
        '<soapenv:Header/><soapenv:Body>'
        '<ec:autorizacionComprobante>'
        f'<claveAccesoComprobante>{clave_acceso}</claveAccesoComprobante>'
        '</ec:autorizacionComprobante>'
        '</soapenv:Body></soapenv:Envelope>'
    )
    headers = {'Content-Type': 'text/xml; charset=utf-8',
               'User-Agent': 'Mozilla/5.0'}

    for url in SRI_URLS:
        try:
            resp = requests.post(url, data=soap, headers=headers, timeout=10, verify=False)
            if resp.status_code == 200:
                root = ET.fromstring(resp.content)
                for node in root.iter():
                    if node.tag.endswith('comprobante') and node.text:
                        txt = node.text.replace('<![CDATA[', '').replace(']]>', '').strip()
                        if '<infoTributaria>' in txt:
                            with open(ruta, 'w', encoding='utf-8') as f:
                                f.write(txt)
                            return ruta
        except Exception:
            pass
    return None


def parsear_xml_factura(ruta, mapa_clasificacion):
    try:
        tree = ET.parse(ruta)
        root = tree.getroot()

        comp_node = find_node(root, 'comprobante')
        if comp_node is not None and comp_node.text:
            txt = comp_node.text.replace('<![CDATA[', '').replace(']]>', '').strip()
            try:
                root = ET.fromstring(txt)
            except Exception:
                pass

        info_trib = find_node(root, 'infoTributaria')
        info_fact = find_node(root, 'infoFactura')
        if info_trib is None and info_fact is None:
            return None

        clave = find_text(info_trib, 'claveAcceso')
        ruc = find_text(info_trib, 'ruc')
        estab = find_text(info_trib, 'estab')
        pto_emi = find_text(info_trib, 'ptoEmi')
        secuencial = find_text(info_trib, 'secuencial')
        num_factura = f'{estab}-{pto_emi}-{secuencial}'
        nombre = find_text(info_trib, 'razonSocial')
        ruc_comprador = find_text(info_fact, 'identificacionComprador')
        destinatario = find_text(info_fact, 'razonSocialComprador')
        fecha = find_text(info_fact, 'fechaEmision')
        clasificacion = mapa_clasificacion.get(ruc, 'SIN CLASIFICAR')

        base_0 = base_15 = iva_15 = base_5 = iva_5 = base_exento = base_no_objeto = 0.0
        total_con_imp = find_node(info_fact, 'totalConImpuestos')
        if total_con_imp is not None:
            for imp in total_con_imp:
                codigo = find_text(imp, 'codigo')
                if codigo == '2':
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

        try:
            total = float(find_text(info_fact, 'importeTotal') or 0)
        except ValueError:
            total = 0.0

        pagos_n = find_node(info_fact, 'pagos')
        forma_pago = 'Otros'
        if pagos_n is not None:
            pago = find_node(pagos_n, 'pago')
            if pago is not None:
                cod_p = find_text(pago, 'formaPago')
                if cod_p == '01':
                    forma_pago = 'Sin Uso Sistema Financiero'
                elif cod_p == '19':
                    forma_pago = 'Tarjeta de Crédito'
                elif cod_p == '20':
                    forma_pago = 'Otros con Sistema Financiero'

        detalles_n = find_node(root, 'detalles')
        concepto = 'VARIOS'
        if detalles_n is not None:
            lista = list(detalles_n)
            for det in lista:
                desc = find_text(det, 'descripcion')
                if desc:
                    concepto = desc + ('...' if len(lista) > 1 else '')
                    break

        return {
            'ID': clave or f'{ruc}-{num_factura}',
            'Estado': 'OK',
            'Fecha': fecha, 'RUC': ruc, 'Factura': num_factura,
            'Nombre': nombre, 'Clasificación': clasificacion,
            'Concepto': concepto, 'Forma Pago': forma_pago,
            'No Objeto IVA': round(base_no_objeto, 2),
            'Exento IVA': round(base_exento, 2),
            'Base 0%': round(base_0, 2),
            'Base 15%': round(base_15, 2), 'IVA 15%': round(iva_15, 2),
            'Base 5%': round(base_5, 2), 'IVA 5%': round(iva_5, 2),
            'Total': round(total, 2),
            'Destinatario': destinatario, 'RUC_Comprador': ruc_comprador,
        }
    except Exception as e:
        print(f'Error parseando {ruta}: {e}')
        return None


# ── Rutas ────────────────────────────────────────────────────────────────────

@sri_processor.route('/')
@login_required
def index():
    r = _requiere_modulo()
    if r:
        return r
    return render_template('sri_processor/index.html')


@sri_processor.route('/procesar_txt', methods=['POST'])
@login_required
def procesar_txt():
    r = _requiere_modulo()
    if r:
        return {'error': 'Sin acceso'}, 403

    archivos_txt = request.files.getlist('archivos_txt')
    archivo_mapa = request.files.get('mapa')

    if not archivos_txt:
        return {'error': 'Sube al menos un archivo TXT con claves de acceso'}, 400

    # Cargar mapa de clasificación si viene
    mapa = {}
    if archivo_mapa and archivo_mapa.filename:
        try:
            import pandas as pd
            df = pd.read_excel(io.BytesIO(archivo_mapa.read()), header=None)
            for _, row in df.iterrows():
                try:
                    ruc = str(row[0]).strip().replace("'", '').zfill(13)
                    cat = str(row[2]).strip().upper()
                    if ruc and cat:
                        mapa[ruc] = cat
                except Exception:
                    continue
        except Exception:
            pass

    # Extraer claves de acceso (49 dígitos)
    claves = set()
    for archivo in archivos_txt:
        for enc in ('utf-8', 'latin-1', 'cp1252'):
            try:
                contenido = archivo.read().decode(enc)
                claves.update(k for k in re.findall(r'\d{49}', contenido) if len(k) == 49)
                break
            except UnicodeDecodeError:
                archivo.seek(0)
                continue

    if not claves:
        return {'error': 'No se encontraron claves de acceso válidas en los TXT'}, 400

    # Carpeta temporal para XMLs
    carpeta = os.path.join(current_user.id.__str__(), 'xml_temp')
    carpeta_abs = os.path.join('uploads', carpeta)
    os.makedirs(carpeta_abs, exist_ok=True)

    # Descarga paralela
    rutas = []
    errores = 0
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(descargar_xml_sri, c, carpeta_abs): c for c in claves}
        for future in as_completed(futures):
            try:
                ruta = future.result()
                if ruta:
                    rutas.append(ruta)
                else:
                    errores += 1
            except Exception:
                errores += 1

    # Parsear XMLs
    filas = []
    ids_vistos = set()
    for ruta in rutas:
        row = parsear_xml_factura(ruta, mapa)
        if row:
            if row['ID'] in ids_vistos:
                row['Estado'] = 'DUPLICADO'
            else:
                ids_vistos.add(row['ID'])
            filas.append(row)

    return {
        'filas': filas,
        'claves_encontradas': len(claves),
        'xml_descargados': len(rutas),
        'errores_descarga': errores,
        'mapa_cargado': len(mapa)
    }


@sri_processor.route('/procesar_xmls', methods=['POST'])
@login_required
def procesar_xmls():
    r = _requiere_modulo()
    if r:
        return {'error': 'Sin acceso'}, 403

    archivos = request.files.getlist('archivos_xml')
    archivo_mapa = request.files.get('mapa')

    mapa = {}
    if archivo_mapa and archivo_mapa.filename:
        try:
            import pandas as pd
            df = pd.read_excel(io.BytesIO(archivo_mapa.read()), header=None)
            for _, row in df.iterrows():
                try:
                    ruc = str(row[0]).strip().replace("'", '').zfill(13)
                    cat = str(row[2]).strip().upper()
                    if ruc and cat:
                        mapa[ruc] = cat
                except Exception:
                    continue
        except Exception:
            pass

    # Guardar XMLs temporalmente
    carpeta_abs = os.path.join('uploads', str(current_user.id), 'xml_temp')
    os.makedirs(carpeta_abs, exist_ok=True)

    filas = []
    ids_vistos = set()
    for archivo in archivos:
        if not archivo.filename.lower().endswith('.xml'):
            continue
        ruta = os.path.join(carpeta_abs, archivo.filename)
        archivo.save(ruta)
        row = parsear_xml_factura(ruta, mapa)
        if row:
            if row['ID'] in ids_vistos:
                row['Estado'] = 'DUPLICADO'
            else:
                ids_vistos.add(row['ID'])
            filas.append(row)

    return {'filas': filas, 'mapa_cargado': len(mapa)}


@sri_processor.route('/exportar_excel', methods=['POST'])
@login_required
def exportar_excel():
    r = _requiere_modulo()
    if r:
        return {'error': 'Sin acceso'}, 403

    data = request.get_json(force=True)
    filas = data.get('filas', [])
    if not filas:
        return {'error': 'No hay datos para exportar'}, 400

    COLUMNAS = [
        'Estado', 'Fecha', 'RUC', 'Factura', 'Nombre', 'Clasificación',
        'Concepto', 'Forma Pago', 'No Objeto IVA', 'Exento IVA',
        'Base 0%', 'Base 15%', 'IVA 15%', 'Base 5%', 'IVA 5%', 'Total'
    ]
    GASTOS_PERS = ['ALIMENTACION', 'ALIMENTACIÓN', 'EDUCACION', 'EDUCACIÓN',
                   'SALUD', 'VESTIMENTA', 'VIVIENDA', 'VARIOS', 'TURISMO', 'ARTE Y CULTURA']

    try:
        import xlsxwriter
        output = io.BytesIO()
        wb = xlsxwriter.Workbook(output)
        ws = wb.add_worksheet('DATOS')

        fmt_head = wb.add_format({'bold': True, 'bg_color': '#007bff', 'font_color': 'white', 'border': 1, 'align': 'center'})
        fmt_curr = wb.add_format({'num_format': '$#,##0.00', 'border': 1})
        fmt_cell = wb.add_format({'border': 1})

        for i, col in enumerate(COLUMNAS):
            ws.write(0, i, col, fmt_head)

        filas_ok = [f for f in filas if f.get('Estado') == 'OK']
        for row_i, fila in enumerate(filas_ok, 1):
            for col_i, col in enumerate(COLUMNAS):
                val = fila.get(col, '')
                if col in ('No Objeto IVA', 'Exento IVA', 'Base 0%', 'Base 15%',
                           'IVA 15%', 'Base 5%', 'IVA 5%', 'Total'):
                    try:
                        ws.write(row_i, col_i, float(val), fmt_curr)
                    except (ValueError, TypeError):
                        ws.write(row_i, col_i, 0.0, fmt_curr)
                else:
                    ws.write(row_i, col_i, str(val), fmt_cell)

        # Hoja RESUMEN con SUMIF
        ws_res = wb.add_worksheet('RESUMEN')
        fmt_rh = wb.add_format({'bold': True, 'bg_color': '#28a745', 'font_color': 'white', 'border': 1, 'align': 'center'})
        fmt_total = wb.add_format({'num_format': '$#,##0.00', 'bold': True, 'border': 1, 'bg_color': '#d4edda'})
        fmt_num = wb.add_format({'num_format': '$#,##0.00', 'border': 1})
        fmt_lbl = wb.add_format({'border': 1})

        categorias = sorted(list(set(f.get('Clasificación', 'SIN CLASIFICAR') for f in filas_ok)))
        headers_res = ['Clasificación', 'Facturas', 'Base 0%', 'Base 15%', 'IVA 15%',
                       'Base 5%', 'IVA 5%', 'No Objeto IVA', 'Exento IVA', 'Total']
        col_map = {
            'Base 0%': 'K', 'Base 15%': 'L', 'IVA 15%': 'M',
            'Base 5%': 'N', 'IVA 5%': 'O',
            'No Objeto IVA': 'I', 'Exento IVA': 'J', 'Total': 'P'
        }
        for i, h in enumerate(headers_res):
            ws_res.write(0, i, h, fmt_rh)

        # Precompute aggregates per category
        cat_data = {c: {'count': 0, **{k: 0.0 for k in col_map}} for c in categorias}
        for f in filas_ok:
            c = f.get('Clasificación', 'SIN CLASIFICAR')
            if c in cat_data:
                cat_data[c]['count'] += 1
                for k in col_map:
                    try:
                        cat_data[c][k] += float(f.get(k, 0) or 0)
                    except (ValueError, TypeError):
                        pass

        for row_i, cat in enumerate(categorias, 1):
            ws_res.write(row_i, 0, cat, fmt_lbl)
            ws_res.write(row_i, 1, cat_data[cat]['count'], fmt_num)
            for col_i, k in enumerate(col_map.keys(), 2):
                ws_res.write(row_i, col_i, round(cat_data[cat][k], 2), fmt_num)

        tot_row = len(categorias) + 1
        ws_res.write(tot_row, 0, 'TOTAL GENERAL', fmt_total)
        ws_res.write(tot_row, 1, sum(d['count'] for d in cat_data.values()), fmt_total)
        for col_i, k in enumerate(col_map.keys(), 2):
            ws_res.write(tot_row, col_i, round(sum(d[k] for d in cat_data.values()), 2), fmt_total)

        ws.set_column(0, 0, 10)
        ws.set_column(1, 1, 12)
        ws.set_column(4, 4, 30)
        ws.set_column(5, 5, 18)
        ws.set_column(8, 15, 13)
        ws_res.set_column(0, 0, 28)
        ws_res.set_column(1, 9, 14)

        wb.close()
        output.seek(0)
        return Response(
            output.getvalue(),
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            headers={'Content-Disposition': 'attachment; filename=Reporte_SRI.xlsx'}
        )
    except Exception as e:
        return {'error': str(e)}, 500
