from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from services.ice_calculator import IceCalculator, TAX_DB
from routes.payments import usuario_tiene_modulo

ice = Blueprint('ice', __name__)

# Mapa de períodos especiales de 2024
_PERIODOS_2024 = {
    '2024_q1': {'label': '2024 (Ene–Mar, IVA 12%)', 'iva': 0.12},
    '2024_q2': {'label': '2024 (Abr–Dic, IVA 15%)', 'iva': 0.15},
}


def _requiere_ice_simple():
    if current_user.is_admin:
        return None
    if not usuario_tiene_modulo('ice_simple'):
        flash('Requieres el módulo Cálculo ICE Simple ($10/mes) para acceder.', 'warning')
        return redirect(url_for('payments.ver_planes'))
    return None


def _requiere_ice_multiple():
    if current_user.is_admin:
        return None
    if not usuario_tiene_modulo('ice_multiple'):
        flash('Requieres el módulo ICE Múltiple + Mezcla ($15/mes) para acceder.', 'warning')
        return redirect(url_for('payments.ver_planes'))
    return None


def _resolver_anios(anios_raw):
    """
    Convierte la lista de valores del formulario en pares (etiqueta, iva_tasa).
    Maneja '2024_q1', '2024_q2' y años normales.
    """
    periodos = []
    for v in anios_raw:
        if v in _PERIODOS_2024:
            p = _PERIODOS_2024[v]
            periodos.append({'anio': '2024', 'label': p['label'], 'iva': p['iva']})
        else:
            iva = TAX_DB.get(v, {}).get('iva', 0.15)
            if iva == 'MIXTO':
                iva = 0.15
            periodos.append({'anio': v, 'label': v, 'iva': iva})
    return periodos


# ── Cálculo ICE Simple ────────────────────────────────────────────────────────

@ice.route('/calculadora')
@login_required
def calculadora():
    r = _requiere_ice_simple()
    if r:
        return r
    return render_template('ice/calculadora.html', tax_db=TAX_DB)


@ice.route('/calcular', methods=['POST'])
@login_required
def calcular():
    r = _requiere_ice_simple()
    if r:
        return r
    try:
        precio   = float(request.form.get('precio', 0))
        costos   = float(request.form.get('costos', 0))
        utilidad = float(request.form.get('utilidad', 0))
        volumen  = float(request.form.get('volumen', 750))
        grado    = float(request.form.get('grado', 35))
        tipo     = request.form.get('tipo', 'Licor')
        cantidad = int(request.form.get('cantidad', 1))
        escala   = request.form.get('escala', '')
        anios_raw = request.form.getlist('anios')

        if not anios_raw:
            flash('Selecciona al menos un período.', 'warning')
            return render_template('ice/calculadora.html', tax_db=TAX_DB)

        datos = {
            'precio_fabrica': precio,
            'volumen_cc': volumen,
            'grado_alcoholico': grado,
            'tipo_producto': tipo,
            'cantidad': cantidad,
        }
        if escala:
            datos['escala'] = escala

        periodos = _resolver_anios(anios_raw)
        resultados = {}
        for p in periodos:
            res = IceCalculator.calcular_liquidacion_completa(
                datos, p['anio'], iva_tasa=p['iva'])
            resultados[p['label']] = res

        return render_template('ice/resultado.html',
                               resultados=resultados,
                               datos={
                                   'precio': precio, 'costos': costos,
                                   'utilidad': utilidad, 'volumen': volumen,
                                   'grado': grado, 'tipo': tipo, 'cantidad': cantidad,
                               })

    except Exception as e:
        flash(f'Error: {str(e)}', 'danger')
        return render_template('ice/calculadora.html', tax_db=TAX_DB)


# ── ICE Múltiple + Mezcla ─────────────────────────────────────────────────────

@ice.route('/multiple')
@login_required
def multiple():
    r = _requiere_ice_multiple()
    if r:
        return r
    return render_template('ice/multiple.html', tax_db=TAX_DB)


@ice.route('/calcular_multiple', methods=['POST'])
@login_required
def calcular_multiple():
    r = _requiere_ice_multiple()
    if r:
        return r
    try:
        anios_raw = request.form.getlist('anios')
        if not anios_raw:
            flash('Selecciona al menos un período.', 'warning')
            return render_template('ice/multiple.html', tax_db=TAX_DB)

        # Leer productos del formulario
        indices = sorted({k.replace('precio_', '')
                          for k in request.form if k.startswith('precio_')})
        productos = []
        for i in indices:
            precio   = float(request.form.get(f'precio_{i}', 0) or 0)
            costos   = float(request.form.get(f'costos_{i}', 0) or 0)
            utilidad = float(request.form.get(f'utilidad_{i}', 0) or 0)
            volumen  = float(request.form.get(f'volumen_{i}', 750) or 750)
            grado    = float(request.form.get(f'grado_{i}', 35) or 35)
            tipo     = request.form.get(f'tipo_{i}', 'Licor')
            cantidad = int(request.form.get(f'cantidad_{i}', 1) or 1)
            nombre   = request.form.get(f'nombre_{i}', f'Producto {i}')
            escala   = request.form.get(f'escala_{i}', '')
            if precio <= 0 or cantidad <= 0:
                continue
            d = {
                'precio_fabrica': precio,
                'costos': costos,
                'utilidad': utilidad,
                'volumen_cc': volumen,
                'grado_alcoholico': grado,
                'tipo_producto': tipo,
                'cantidad': cantidad,
            }
            if escala:
                d['escala'] = escala
            productos.append({'nombre': nombre, 'datos': d})

        if not productos:
            flash('Agrega al menos un producto con precio y cantidad válidos.', 'warning')
            return render_template('ice/multiple.html', tax_db=TAX_DB)

        periodos = _resolver_anios(anios_raw)

        # resultados[periodo_label] = lista de dicts por producto
        resultados = {}
        totales = {}

        for p in periodos:
            lbl = p['label']
            items = []
            tot = {'ice_especifico': 0.0, 'ice_advalorem': 0.0,
                   'ice_total': 0.0, 'iva_total': 0.0, 'pvp_total': 0.0}
            for prod in productos:
                res = IceCalculator.calcular_liquidacion_completa(
                    prod['datos'], p['anio'], iva_tasa=p['iva'])
                res['nombre']   = prod['nombre']
                res['costos']   = prod['datos']['costos']
                res['utilidad'] = prod['datos']['utilidad']
                res['cantidad'] = prod['datos']['cantidad']
                # Acumular totales por cantidad
                q = prod['datos']['cantidad']
                tot['ice_especifico'] += res.get('ice_especifico_unitario', 0) * q
                tot['ice_advalorem']  += res.get('ice_advalorem_unitario', 0) * q
                tot['ice_total']      += res.get('ice_total', 0)
                tot['iva_total']      += res.get('iva_total', 0)
                tot['pvp_total']      += res.get('pvp', 0)
                items.append(res)
            resultados[lbl] = items
            totales[lbl] = {k: round(v, 4) for k, v in tot.items()}

        return render_template('ice/resultado_multiple.html',
                               resultados=resultados,
                               totales=totales,
                               productos=productos,
                               periodos=[p['label'] for p in periodos])

    except Exception as e:
        flash(f'Error: {str(e)}', 'danger')
        return render_template('ice/multiple.html', tax_db=TAX_DB)


# ── Mezcla Total ──────────────────────────────────────────────────────────────

@ice.route('/mezcla')
@login_required
def mezcla():
    r = _requiere_ice_multiple()
    if r:
        return r
    return render_template('ice/mezcla.html', tax_db=TAX_DB)


@ice.route('/calcular_mezcla', methods=['POST'])
@login_required
def calcular_mezcla():
    r = _requiere_ice_multiple()
    if r:
        return r
    try:
        anios_raw = request.form.getlist('anios')
        if not anios_raw:
            flash('Selecciona al menos un período.', 'warning')
            return render_template('ice/mezcla.html', tax_db=TAX_DB)

        indices = sorted({k.replace('precio_', '')
                          for k in request.form if k.startswith('precio_')})
        productos = []
        for i in indices:
            precio   = float(request.form.get(f'precio_{i}', 0) or 0)
            volumen  = float(request.form.get(f'volumen_{i}', 750) or 750)
            grado    = float(request.form.get(f'grado_{i}', 35) or 35)
            tipo     = request.form.get(f'tipo_{i}', 'Licor')
            cantidad = int(request.form.get(f'cantidad_{i}', 1) or 1)
            nombre   = request.form.get(f'nombre_{i}', f'Producto {i}')
            escala   = request.form.get(f'escala_{i}', '')
            if precio <= 0 or cantidad <= 0:
                continue
            d = {'precio_fabrica': precio, 'volumen_cc': volumen,
                 'grado_alcoholico': grado, 'tipo_producto': tipo, 'cantidad': cantidad}
            if escala:
                d['escala'] = escala
            productos.append({'nombre': nombre, 'datos': d})

        if not productos:
            flash('Agrega al menos un producto.', 'warning')
            return render_template('ice/mezcla.html', tax_db=TAX_DB)

        periodos = _resolver_anios(anios_raw)
        resultados = {}
        for p in periodos:
            lbl = p['label']
            items = []
            gran_total = {'ice_total': 0.0, 'iva_total': 0.0, 'pvp': 0.0}
            for prod in productos:
                res = IceCalculator.calcular_liquidacion_completa(
                    prod['datos'], p['anio'], iva_tasa=p['iva'])
                res['nombre'] = prod['nombre']
                items.append(res)
                gran_total['ice_total'] += res['ice_total']
                gran_total['iva_total'] += res['iva_total']
                gran_total['pvp']       += res['pvp']
            resultados[lbl] = {'items': items, 'total': gran_total}

        return render_template('ice/resultado_mezcla.html',
                               resultados=resultados, productos=productos)

    except Exception as e:
        flash(f'Error: {str(e)}', 'danger')
        return render_template('ice/mezcla.html', tax_db=TAX_DB)


# ── Comparativa y Tarifas ─────────────────────────────────────────────────────

@ice.route('/comparativa')
@login_required
def comparativa():
    return render_template('ice/comparativa.html', tax_db=TAX_DB)


@ice.route('/tarifas')
@login_required
def ver_tarifas():
    return render_template('ice/tarifas.html', tax_db=TAX_DB)
