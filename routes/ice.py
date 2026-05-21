from flask import Blueprint, render_template, request, flash
from flask_login import login_required, current_user
from services.ice_calculator import IceCalculator, TAX_DB

ice = Blueprint('ice', __name__)


@ice.route('/calculadora')
@login_required
def calculadora():
    return render_template('ice/calculadora.html', tax_db=TAX_DB)


@ice.route('/calcular', methods=['POST'])
@login_required
def calcular():
    try:
        precio = float(request.form.get('precio', 0))
        volumen = float(request.form.get('volumen', 750))
        grado = float(request.form.get('grado', 35))
        tipo = request.form.get('tipo', 'Licor')
        cantidad = int(request.form.get('cantidad', 1))
        escala = request.form.get('escala', '')
        anios = request.form.getlist('anios')
        
        if not anios:
            flash('Selecciona al menos un ano.', 'warning')
            return render_template('ice/calculadora.html', tax_db=TAX_DB)
        
        datos = {
            'precio_fabrica': precio,
            'volumen_cc': volumen,
            'grado_alcoholico': grado,
            'tipo_producto': tipo,
            'cantidad': cantidad
        }
        if escala:
            datos['escala'] = escala
        
        resultados = {}
        for anio in anios:
            if anio == '2024':
                # 2024 con ambos periodos
                res_12 = IceCalculator.calcular_liquidacion_completa(datos, '2024', iva_tasa=0.12)
                res_15 = IceCalculator.calcular_liquidacion_completa(datos, '2024', iva_tasa=0.15)
                resultados['2024 (12%)'] = res_12
                resultados['2024 (15%)'] = res_15
            else:
                res = IceCalculator.calcular_liquidacion_completa(datos, anio)
                resultados[anio] = res
        
        return render_template('ice/resultado.html', 
                             resultados=resultados,
                             datos={'precio': precio, 'volumen': volumen, 
                                   'grado': grado, 'tipo': tipo, 'cantidad': cantidad})
    
    except Exception as e:
        flash(f'Error: {str(e)}', 'danger')
        return render_template('ice/calculadora.html', tax_db=TAX_DB)


@ice.route('/multiple')
@login_required
def multiple():
    return render_template('ice/multiple.html', tax_db=TAX_DB)


@ice.route('/calcular_multiple', methods=['POST'])
@login_required
def calcular_multiple():
    try:
        anios = request.form.getlist('anios')
        if not anios:
            flash('Selecciona al menos un ano.', 'warning')
            return render_template('ice/multiple.html', tax_db=TAX_DB)
        
        # Obtener todos los productos del formulario
        productos = []
        indices = set()
        for key in request.form.keys():
            if key.startswith('precio_'):
                indices.add(key.replace('precio_', ''))
        
        for i in sorted(indices):
            precio = float(request.form.get(f'precio_{i}', 0))
            volumen = float(request.form.get(f'volumen_{i}', 750))
            grado = float(request.form.get(f'grado_{i}', 35))
            tipo = request.form.get(f'tipo_{i}', 'Licor')
            cantidad = int(request.form.get(f'cantidad_{i}', 1))
            nombre = request.form.get(f'nombre_{i}', f'Producto {i}')
            
            if precio > 0 and cantidad > 0:
                productos.append({
                    'nombre': nombre,
                    'datos': {
                        'precio_fabrica': precio,
                        'volumen_cc': volumen,
                        'grado_alcoholico': grado,
                        'tipo_producto': tipo,
                        'cantidad': cantidad
                    }
                })
        
        if not productos:
            flash('Agrega al menos un producto.', 'warning')
            return render_template('ice/multiple.html', tax_db=TAX_DB)
        
        # Calcular para cada producto y cada año
        resultados = {}
        for anio in anios:
            resultados[anio] = []
            for prod in productos:
                if anio == '2024':
                    res_12 = IceCalculator.calcular_liquidacion_completa(prod['datos'], '2024', iva_tasa=0.12)
                    res_15 = IceCalculator.calcular_liquidacion_completa(prod['datos'], '2024', iva_tasa=0.15)
                    resultados['2024 (12%)'] = resultados.get('2024 (12%)', [])
                    resultados['2024 (15%)'] = resultados.get('2024 (15%)', [])
                    res_12['nombre'] = prod['nombre']
                    res_15['nombre'] = prod['nombre']
                    resultados['2024 (12%)'].append(res_12)
                    resultados['2024 (15%)'].append(res_15)
                else:
                    res = IceCalculator.calcular_liquidacion_completa(prod['datos'], anio)
                    res['nombre'] = prod['nombre']
                    resultados[anio].append(res)
        
        # Calcular totales
        totales = {}
        for anio, items in resultados.items():
            totales[anio] = {
                'ice_total': sum(r['ice_total'] for r in items),
                'iva_total': sum(r['iva_total'] for r in items),
                'pvp': sum(r['pvp'] for r in items),
                'cantidad_productos': len(items)
            }
        
        return render_template('ice/resultado_multiple.html',
                             resultados=resultados,
                             totales=totales,
                             productos=productos)
    
    except Exception as e:
        flash(f'Error: {str(e)}', 'danger')
        return render_template('ice/multiple.html', tax_db=TAX_DB)


@ice.route('/mezcla')
@login_required
def mezcla():
    return render_template('ice/mezcla.html', tax_db=TAX_DB)


@ice.route('/calcular_mezcla', methods=['POST'])
@login_required
def calcular_mezcla():
    try:
        anios = request.form.getlist('anios')
        if not anios:
            flash('Selecciona al menos un ano.', 'warning')
            return render_template('ice/mezcla.html', tax_db=TAX_DB)
        
        productos = []
        indices = set()
        for key in request.form.keys():
            if key.startswith('precio_'):
                indices.add(key.replace('precio_', ''))
        
        for i in sorted(indices):
            precio = float(request.form.get(f'precio_{i}', 0))
            volumen = float(request.form.get(f'volumen_{i}', 750))
            grado = float(request.form.get(f'grado_{i}', 35))
            tipo = request.form.get(f'tipo_{i}', 'Licor')
            cantidad = int(request.form.get(f'cantidad_{i}', 1))
            nombre = request.form.get(f'nombre_{i}', f'Producto {i}')
            
            if precio > 0 and cantidad > 0:
                productos.append({
                    'nombre': nombre,
                    'datos': {
                        'precio_fabrica': precio,
                        'volumen_cc': volumen,
                        'grado_alcoholico': grado,
                        'tipo_producto': tipo,
                        'cantidad': cantidad
                    }
                })
        
        if not productos:
            flash('Agrega al menos un producto.', 'warning')
            return render_template('ice/mezcla.html', tax_db=TAX_DB)
        
        # Calcular combinado
        resultados = {}
        for anio in anios:
            if anio == '2024':
                for tasa, etiqueta in [(0.12, '2024 (12%)'), (0.15, '2024 (15%)')]:
                    items = []
                    gran_total = {'ice_total': 0, 'iva_total': 0, 'pvp': 0}
                    for prod in productos:
                        res = IceCalculator.calcular_liquidacion_completa(prod['datos'], '2024', iva_tasa=tasa)
                        res['nombre'] = prod['nombre']
                        items.append(res)
                        gran_total['ice_total'] += res['ice_total']
                        gran_total['iva_total'] += res['iva_total']
                        gran_total['pvp'] += res['pvp']
                    resultados[etiqueta] = {'items': items, 'total': gran_total}
            else:
                items = []
                gran_total = {'ice_total': 0, 'iva_total': 0, 'pvp': 0}
                for prod in productos:
                    res = IceCalculator.calcular_liquidacion_completa(prod['datos'], anio)
                    res['nombre'] = prod['nombre']
                    items.append(res)
                    gran_total['ice_total'] += res['ice_total']
                    gran_total['iva_total'] += res['iva_total']
                    gran_total['pvp'] += res['pvp']
                resultados[anio] = {'items': items, 'total': gran_total}
        
        return render_template('ice/resultado_mezcla.html',
                             resultados=resultados,
                             productos=productos)
    
    except Exception as e:
        flash(f'Error: {str(e)}', 'danger')
        return render_template('ice/mezcla.html', tax_db=TAX_DB)


@ice.route('/comparativa')
@login_required
def comparativa():
    return render_template('ice/comparativa.html', tax_db=TAX_DB)


@ice.route('/tarifas')
@login_required
def ver_tarifas():
    return render_template('ice/tarifas.html', tax_db=TAX_DB)