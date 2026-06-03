"""Procesador de Retenciones XML SRI (basado en Retenciones.py)"""
import io, os, re
from flask import Blueprint, render_template, request, Response, redirect, url_for, flash
from flask_login import login_required, current_user
from routes.payments import usuario_tiene_modulo
from werkzeug.utils import secure_filename
try:
    from defusedxml import ElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET

retenciones = Blueprint('retenciones', __name__)


def _requiere_modulo():
    if current_user.is_admin:
        return None
    if not usuario_tiene_modulo('retenciones'):
        flash('Requieres el módulo Procesador de Retenciones.', 'warning')
        return redirect(url_for('payments.ver_planes'))
    return None


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


def parsear_retencion(ruta):
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
        info_ret = find_node(root, 'infoCompRetencion')
        if info_trib is None:
            return None

        clave = find_text(info_trib, 'claveAcceso')
        ruc_emisor = find_text(info_trib, 'ruc')
        razon = find_text(info_trib, 'razonSocial')
        estab = find_text(info_trib, 'estab')
        pto_emi = find_text(info_trib, 'ptoEmi')
        secuencial = find_text(info_trib, 'secuencial')
        nro = f'{estab}-{pto_emi}-{secuencial}'
        fecha = find_text(info_ret, 'fechaEmision') if info_ret else ''
        periodo = find_text(info_ret, 'periodoFiscal') if info_ret else ''
        ruc_sujeto = find_text(info_ret, 'identificacionSujetoRetenido') if info_ret else ''

        base_renta = ret_renta = porc_renta = 0.0
        base_iva = ret_iva = porc_iva = 0.0
        ret_isd = total_retenido = 0.0

        def procesar_imp(nodo):
            nonlocal base_renta, ret_renta, porc_renta
            nonlocal base_iva, ret_iva, porc_iva
            nonlocal ret_isd, total_retenido
            try:
                codigo = find_text(nodo, 'codigo')
                base = float(find_text(nodo, 'baseImponible') or 0)
                try:
                    porc = float(find_text(nodo, 'porcentajeRetener') or 0)
                except (ValueError, TypeError):
                    porc = 0.0
                valor = float(find_text(nodo, 'valorRetenido') or 0)
                total_retenido += valor

                if codigo == '1':
                    base_renta += base
                    ret_renta += valor
                    if base > 0:
                        porc_renta = porc
                elif codigo == '2':
                    base_iva += base
                    ret_iva += valor
                    if base > 0:
                        porc_iva = porc
                elif codigo == '6':
                    ret_isd += valor
            except Exception:
                pass

        impuestos_n = find_node(root, 'impuestos')
        if impuestos_n is not None:
            for imp in impuestos_n.iter():
                if imp.tag.endswith('impuesto'):
                    procesar_imp(imp)

        docs_n = find_node(root, 'docsSustento')
        if docs_n is not None:
            for doc in docs_n:
                ret_group = find_node(doc, 'retenciones')
                if ret_group is not None:
                    for ret in ret_group:
                        if ret.tag.endswith('retencion'):
                            procesar_imp(ret)

        return {
            'ID': clave, 'Estado': 'OK', 'Fecha': fecha,
            'RUC Emisor': ruc_emisor, 'Agente Retención': razon,
            'Nro. Comprobante': nro, 'Periodo Fiscal': periodo,
            'Base Renta': round(base_renta, 2), '% Renta': porc_renta,
            'Ret. Renta': round(ret_renta, 2),
            'Base IVA': round(base_iva, 2), '% IVA': porc_iva,
            'Ret. IVA': round(ret_iva, 2),
            'Ret. ISD': round(ret_isd, 2),
            'Total Retenido': round(total_retenido, 2),
            'RUC_Sujeto': ruc_sujeto,
        }
    except Exception as e:
        print(f'Error parseando {ruta}: {e}')
        return None


@retenciones.route('/')
@login_required
def index():
    r = _requiere_modulo()
    if r:
        return r
    return render_template('retenciones/index.html')


@retenciones.route('/procesar', methods=['POST'])
@login_required
def procesar():
    r = _requiere_modulo()
    if r:
        return {'error': 'Sin acceso'}, 403

    archivos = request.files.getlist('archivos_xml')
    if not archivos:
        return {'error': 'Sube archivos XML de retenciones'}, 400

    carpeta = os.path.join('uploads', str(current_user.id), 'retenciones')
    os.makedirs(carpeta, exist_ok=True)

    filas = []
    ids_vistos = set()
    duplicados = 0

    for arch in archivos:
        if not arch.filename.lower().endswith('.xml'):
            continue
        nombre_seguro = secure_filename(arch.filename)
        if not nombre_seguro:
            continue
        ruta = os.path.join(carpeta, nombre_seguro)
        try:
            arch.save(ruta)
            row = parsear_retencion(ruta)
            if row:
                if row['ID'] and row['ID'] in ids_vistos:
                    row['Estado'] = 'DUPLICADO'
                    duplicados += 1
                else:
                    if row['ID']:
                        ids_vistos.add(row['ID'])
                filas.append(row)
        except Exception as e:
            print(f"Error procesando {nombre_seguro}: {e}")
            filas.append({
                'ID': '',
                'Estado': f'ERROR: {str(e)[:50]}',
                'Fecha': '', 'RUC Emisor': '', 'Agente Retención': '',
                'Nro. Comprobante': '', 'Periodo Fiscal': ''
            })

    return {
        'filas': filas,
        'total': len(filas),
        'duplicados': duplicados
    }


@retenciones.route('/exportar_excel', methods=['POST'])
@login_required
def exportar_excel():
    r = _requiere_modulo()
    if r:
        return {'error': 'Sin acceso'}, 403

    data = request.get_json(force=True)
    filas = [f for f in data.get('filas', []) if f.get('Estado') != 'DUPLICADO']

    if not filas:
        return {'error': 'No hay datos para exportar'}, 400

    COLS = ['Fecha', 'RUC Emisor', 'Agente Retención', 'Nro. Comprobante',
            'Periodo Fiscal', 'Base Renta', '% Renta', 'Ret. Renta',
            'Base IVA', '% IVA', 'Ret. IVA', 'Ret. ISD', 'Total Retenido']
    NUMS = {'Base Renta', '% Renta', 'Ret. Renta', 'Base IVA', '% IVA',
            'Ret. IVA', 'Ret. ISD', 'Total Retenido'}

    try:
        import xlsxwriter
        output = io.BytesIO()
        wb = xlsxwriter.Workbook(output)
        ws = wb.add_worksheet('DETALLE')

        fmt_head = wb.add_format({'bold': True, 'bg_color': '#007bff', 'font_color': 'white', 'border': 1, 'align': 'center'})
        fmt_curr = wb.add_format({'num_format': '$#,##0.00', 'border': 1})
        fmt_cell = wb.add_format({'border': 1})
        fmt_total = wb.add_format({'num_format': '$#,##0.00', 'bold': True, 'bg_color': '#28a745',
                                   'font_color': 'white', 'border': 1})

        for i, col in enumerate(COLS):
            ws.write(0, i, col, fmt_head)

        # Índices para fórmulas
        idx_base_renta = COLS.index('Base Renta')
        idx_porc_renta = COLS.index('% Renta')
        idx_ret_renta = COLS.index('Ret. Renta')
        idx_base_iva = COLS.index('Base IVA')
        idx_porc_iva = COLS.index('% IVA')
        idx_ret_iva = COLS.index('Ret. IVA')
        idx_ret_isd = COLS.index('Ret. ISD')
        idx_total = COLS.index('Total Retenido')

        for row_i, fila in enumerate(filas, 1):
            excel_row = row_i + 1
            for col_i, col in enumerate(COLS):
                val = fila.get(col, '')
                if col == 'Ret. Renta':
                    base = float(fila.get('Base Renta', 0) or 0)
                    porc = float(fila.get('% Renta', 0) or 0)
                    ws.write(row_i, col_i, round(base * porc / 100, 2), fmt_curr)
                elif col == 'Ret. IVA':
                    base = float(fila.get('Base IVA', 0) or 0)
                    porc = float(fila.get('% IVA', 0) or 0)
                    ws.write(row_i, col_i, round(base * porc / 100, 2), fmt_curr)
                elif col == 'Total Retenido':
                    base_r = float(fila.get('Base Renta', 0) or 0)
                    porc_r = float(fila.get('% Renta', 0) or 0)
                    base_v = float(fila.get('Base IVA', 0) or 0)
                    porc_v = float(fila.get('% IVA', 0) or 0)
                    isd = float(fila.get('Ret. ISD', 0) or 0)
                    total = round(base_r * porc_r / 100 + base_v * porc_v / 100 + isd, 2)
                    ws.write(row_i, col_i, total, fmt_curr)
                elif col in NUMS:
                    try:
                        ws.write(row_i, col_i, float(val), fmt_curr)
                    except (ValueError, TypeError):
                        ws.write(row_i, col_i, 0.0, fmt_curr)
                else:
                    ws.write(row_i, col_i, str(val), fmt_cell)

        # Totales
        last = len(filas) + 1
        ws.write(last, 0, 'TOTALES GENERALES', fmt_total)
        col_keys = {
            idx_base_renta: 'Base Renta', idx_ret_renta: 'Ret. Renta',
            idx_base_iva: 'Base IVA', idx_ret_iva: 'Ret. IVA',
            idx_ret_isd: 'Ret. ISD', idx_total: 'Total Retenido',
        }
        for ci, key in col_keys.items():
            total_val = round(sum(float(f.get(key, 0) or 0) for f in filas), 2)
            ws.write(last, ci, total_val, fmt_total)

        ws.set_column(2, 2, 35)
        ws.set_column(3, 3, 20)
        ws.set_column(idx_base_renta, idx_total, 13)

        # Hoja resumen por agente
        ws_res = wb.add_worksheet('RESUMEN_POR_AGENTE')
        fmt_rh = wb.add_format({'bold': True, 'bg_color': '#343a40', 'font_color': 'white', 'border': 1})
        fmt_rcurr = wb.add_format({'num_format': '$#,##0.00', 'border': 1})
        fmt_rtotal = wb.add_format({'num_format': '$#,##0.00', 'bold': True, 'border': 1, 'bg_color': '#28a745', 'font_color': 'white'})

        hdrs = ['Agente de Retención', 'Cant.', 'Ret. Renta', 'Ret. IVA', 'Ret. ISD', 'Total Retenido']
        for i, h in enumerate(hdrs):
            ws_res.write(0, i, h, fmt_rh)

        agentes = {}
        for f in filas:
            ag = f.get('Agente Retención', 'DESCONOCIDO')
            if ag not in agentes:
                agentes[ag] = {'cant': 0, 'renta': 0.0, 'iva': 0.0, 'isd': 0.0, 'total': 0.0}
            agentes[ag]['cant'] += 1
            agentes[ag]['renta'] += float(f.get('Ret. Renta', 0) or 0)
            agentes[ag]['iva'] += float(f.get('Ret. IVA', 0) or 0)
            agentes[ag]['isd'] += float(f.get('Ret. ISD', 0) or 0)
            agentes[ag]['total'] += float(f.get('Total Retenido', 0) or 0)

        res_row = 1
        for ag, vals in sorted(agentes.items()):
            ws_res.write(res_row, 0, ag)
            ws_res.write(res_row, 1, vals['cant'])
            ws_res.write(res_row, 2, round(vals['renta'], 2), fmt_rcurr)
            ws_res.write(res_row, 3, round(vals['iva'], 2), fmt_rcurr)
            ws_res.write(res_row, 4, round(vals['isd'], 2), fmt_rcurr)
            ws_res.write(res_row, 5, round(vals['total'], 2), fmt_rcurr)
            res_row += 1

        ws_res.write(res_row, 0, 'TOTAL FINAL', fmt_rtotal)
        totals_ag = {'renta': 0.0, 'iva': 0.0, 'isd': 0.0, 'total': 0.0}
        for vals in agentes.values():
            totals_ag['renta'] += vals['renta']
            totals_ag['iva'] += vals['iva']
            totals_ag['isd'] += vals['isd']
            totals_ag['total'] += vals['total']
        for ci, key in enumerate(('renta', 'iva', 'isd', 'total'), 2):
            ws_res.write(res_row, ci, round(totals_ag[key], 2), fmt_rtotal)

        ws_res.set_column(0, 0, 35)
        ws_res.set_column(1, 5, 15)

        wb.close()
        output.seek(0)
        return Response(
            output.getvalue(),
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            headers={'Content-Disposition': 'attachment; filename=Retenciones.xlsx'}
        )
    except Exception as e:
        return {'error': str(e)}, 500
