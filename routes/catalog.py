from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from models import db
from models.user import CatalogoProducto

catalog = Blueprint('catalog', __name__)

CATALOGO_INICIAL = [
    {'nombre': 'LICOR ORO 15V 750 ML (12U)', 'cod_marca': '000001', 'cod_impuesto': '3031', 'cod_clasificacion': '057', 'presentacion': '013', 'capacidad': '000750', 'unidad': '66', 'grado_alcoholico': '000015', 'cod_pais': '593', 'es_pack': False, 'unidades_por_caja': 12},
    {'nombre': 'LICOR SECO BLANCO 15V 750 ML (12U)', 'cod_marca': '000002', 'cod_impuesto': '3031', 'cod_clasificacion': '057', 'presentacion': '013', 'capacidad': '000750', 'unidad': '66', 'grado_alcoholico': '000015', 'cod_pais': '593', 'es_pack': False, 'unidades_por_caja': 12},
    {'nombre': 'AGUARDIENTE DE CANA 15V 750 ML (12U)', 'cod_marca': '000003', 'cod_impuesto': '3031', 'cod_clasificacion': '057', 'presentacion': '013', 'capacidad': '000750', 'unidad': '66', 'grado_alcoholico': '000015', 'cod_pais': '593', 'es_pack': False, 'unidades_por_caja': 12},
    {'nombre': 'VODKA SECO GLACIAL 15V 750ML (12U)', 'cod_marca': '000004', 'cod_impuesto': '3031', 'cod_clasificacion': '057', 'presentacion': '013', 'capacidad': '000750', 'unidad': '66', 'grado_alcoholico': '000015', 'cod_pais': '593', 'es_pack': False, 'unidades_por_caja': 12},
    {'nombre': 'COCKTAIL MARACUYA 5V 800ML (12U)', 'cod_marca': '000005', 'cod_impuesto': '3031', 'cod_clasificacion': '057', 'presentacion': '013', 'capacidad': '000800', 'unidad': '66', 'grado_alcoholico': '000005', 'cod_pais': '593', 'es_pack': False, 'unidades_por_caja': 12},
    {'nombre': 'COCKTAIL DURAZNO 5V 800ML (12U)', 'cod_marca': '000006', 'cod_impuesto': '3031', 'cod_clasificacion': '057', 'presentacion': '013', 'capacidad': '000800', 'unidad': '66', 'grado_alcoholico': '000005', 'cod_pais': '593', 'es_pack': False, 'unidades_por_caja': 12},
    {'nombre': 'COCKTAIL GUARANA 5V 750ML (12U)', 'cod_marca': '000007', 'cod_impuesto': '3031', 'cod_clasificacion': '057', 'presentacion': '013', 'capacidad': '000750', 'unidad': '66', 'grado_alcoholico': '000005', 'cod_pais': '593', 'es_pack': False, 'unidades_por_caja': 12},
]


@catalog.route('/ver')
@login_required
def ver_catalogo():
    productos = CatalogoProducto.query.filter_by(usuario_id=current_user.id).order_by(CatalogoProducto.nombre).all()
    return render_template('catalog/ver.html', productos=productos)


@catalog.route('/inicializar', methods=['POST'])
@login_required
def inicializar_catalogo():
    existentes = CatalogoProducto.query.filter_by(usuario_id=current_user.id).count()
    if existentes > 0:
        flash('El catalogo ya tiene productos. Se omitio la inicializacion.', 'info')
        return redirect(url_for('catalog.ver_catalogo'))
    
    for prod in CATALOGO_INICIAL:
        p = CatalogoProducto(
            usuario_id=current_user.id,
            nombre=prod['nombre'],
            cod_marca=prod['cod_marca'],
            cod_impuesto=prod['cod_impuesto'],
            cod_clasificacion=prod['cod_clasificacion'],
            presentacion=prod['presentacion'],
            capacidad=prod['capacidad'],
            unidad=prod['unidad'],
            grado_alcoholico=prod['grado_alcoholico'],
            cod_pais=prod['cod_pais'],
            es_pack=prod['es_pack'],
            unidades_por_caja=prod['unidades_por_caja']
        )
        db.session.add(p)
    
    db.session.commit()
    flash('Catalogo inicializado con 7 productos.', 'success')
    return redirect(url_for('catalog.ver_catalogo'))


@catalog.route('/agregar', methods=['GET', 'POST'])
@login_required
def agregar_producto():
    if request.method == 'POST':
        try:
            producto = CatalogoProducto(
                usuario_id=current_user.id,
                nombre=request.form.get('nombre', '').upper(),
                cod_marca=request.form.get('cod_marca', '000000').zfill(6),
                cod_impuesto=request.form.get('cod_impuesto', '3031'),
                cod_clasificacion=request.form.get('cod_clasificacion', '057'),
                presentacion=request.form.get('presentacion', '013').zfill(3),
                capacidad=request.form.get('capacidad', '000750').zfill(6),
                unidad=request.form.get('unidad', '66'),
                grado_alcoholico=request.form.get('grado_alcoholico', '000015').zfill(6),
                cod_pais=request.form.get('cod_pais', '593'),
                es_pack=request.form.get('es_pack') == 'on',
                unidades_por_caja=int(request.form.get('unidades_por_caja', 12))
            )
            db.session.add(producto)
            db.session.commit()
            flash(f'Producto "{producto.nombre}" agregado.', 'success')
            return redirect(url_for('catalog.ver_catalogo'))
        except Exception as e:
            flash(f'Error: {str(e)}', 'danger')
    
    return render_template('catalog/agregar.html')


@catalog.route('/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_producto(id):
    producto = CatalogoProducto.query.filter_by(id=id, usuario_id=current_user.id).first()
    if not producto:
        flash('Producto no encontrado.', 'danger')
        return redirect(url_for('catalog.ver_catalogo'))
    
    if request.method == 'POST':
        try:
            producto.nombre = request.form.get('nombre', producto.nombre).upper()
            producto.cod_marca = request.form.get('cod_marca', producto.cod_marca).zfill(6)
            producto.cod_impuesto = request.form.get('cod_impuesto', producto.cod_impuesto)
            producto.cod_clasificacion = request.form.get('cod_clasificacion', producto.cod_clasificacion)
            producto.presentacion = request.form.get('presentacion', producto.presentacion).zfill(3)
            producto.capacidad = request.form.get('capacidad', producto.capacidad).zfill(6)
            producto.unidad = request.form.get('unidad', producto.unidad)
            producto.grado_alcoholico = request.form.get('grado_alcoholico', producto.grado_alcoholico).zfill(6)
            producto.cod_pais = request.form.get('cod_pais', producto.cod_pais)
            producto.es_pack = request.form.get('es_pack') == 'on'
            producto.unidades_por_caja = int(request.form.get('unidades_por_caja', producto.unidades_por_caja))
            db.session.commit()
            flash('Producto actualizado.', 'success')
            return redirect(url_for('catalog.ver_catalogo'))
        except Exception as e:
            flash(f'Error: {str(e)}', 'danger')
    
    return render_template('catalog/editar.html', producto=producto)


@catalog.route('/eliminar/<int:id>', methods=['POST'])
@login_required
def eliminar_producto(id):
    producto = CatalogoProducto.query.filter_by(id=id, usuario_id=current_user.id).first()
    if producto:
        nombre = producto.nombre
        db.session.delete(producto)
        db.session.commit()
        flash(f'Producto "{nombre}" eliminado.', 'success')
    return redirect(url_for('catalog.ver_catalogo'))


@catalog.route('/codigo/<int:id>')
@login_required
def ver_codigo(id):
    producto = CatalogoProducto.query.filter_by(id=id, usuario_id=current_user.id).first()
    if not producto:
        flash('Producto no encontrado.', 'danger')
        return redirect(url_for('catalog.ver_catalogo'))
    
    codigo = f"{producto.cod_impuesto}-{producto.cod_clasificacion}-{producto.cod_marca}-{producto.presentacion}-{producto.capacidad}-{producto.unidad}-{producto.cod_pais}-{producto.grado_alcoholico}"
    
    return render_template('catalog/codigo.html', producto=producto, codigo=codigo)