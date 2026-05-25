from flask import Blueprint, render_template, redirect, url_for, flash, request, send_file
from flask_login import login_required, current_user
from models import db
from models.user import Factura, ClasificacionGasto, MapaClasificacion, MapaClasificacionDetalle
from datetime import datetime
from sqlalchemy import func
import pandas as pd
import io
import os

gastos = Blueprint('gastos', __name__)

GASTOS_PERSONALES = ['ALIMENTACION', 'EDUCACION', 'SALUD', 'VESTIMENTA', 'VIVIENDA', 'TURISMO', 'ARTE Y CULTURA', 'VARIOS']
UPLOAD_MAPAS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'uploads', 'mapas')
if not os.path.exists(UPLOAD_MAPAS):
    os.makedirs(UPLOAD_MAPAS)


@gastos.route('/panel')
@login_required
def panel():
    facturas = Factura.query.filter_by(usuario_id=current_user.id, tipo='gasto')\
                           .order_by(Factura.fecha_emision.desc()).limit(50).all()
    
    clasificaciones = ClasificacionGasto.query.filter_by(usuario_id=current_user.id)\
                                             .order_by(ClasificacionGasto.fecha.desc()).all()
    
    resumen = db.session.query(
        ClasificacionGasto.categoria,
        func.sum(ClasificacionGasto.monto).label('total'),
        func.count(ClasificacionGasto.id).label('cantidad')
    ).filter_by(usuario_id=current_user.id).group_by(ClasificacionGasto.categoria).all()
    
    gastos_personales_total = sum(r.total for r in resumen if r.categoria in GASTOS_PERSONALES)
    gastos_ejercicio_total = sum(r.total for r in resumen if r.categoria not in GASTOS_PERSONALES)
    
    mapas = MapaClasificacion.query.filter_by(usuario_id=current_user.id, activo=True)\
                                  .order_by(MapaClasificacion.fecha_subida.desc()).all()
    
    return render_template('gastos/panel.html',
                         facturas=facturas, clasificaciones=clasificaciones,
                         resumen=resumen,
                         gastos_personales_total=gastos_personales_total or 0,
                         gastos_ejercicio_total=gastos_ejercicio_total or 0,
                         mapas=mapas, categorias=GASTOS_PERSONALES)


@gastos.route('/subir_mapa', methods=['POST'])
@login_required
def subir_mapa():
    if 'archivo_mapa' not in request.files:
        flash('Selecciona un archivo Excel.', 'warning')
        return redirect(url_for('gastos.panel'))
    
    archivo = request.files['archivo_mapa']
    
    if archivo.filename == '':
        flash('Selecciona un archivo.', 'warning')
        return redirect(url_for('gastos.panel'))
    
    try:
        df = pd.read_excel(archivo, header=None)
        
        mapa = MapaClasificacion(usuario_id=current_user.id, nombre=archivo.filename, activo=True)
        db.session.add(mapa)
        db.session.flush()
        
        count = 0
        for _, row in df.iterrows():
            try:
                ruc = str(row[0]).strip().replace("'", "").zfill(13)
                nombre = str(row[1]).strip() if len(row) > 1 else ''
                categoria = str(row[2]).strip().upper() if len(row) > 2 else 'VARIOS'
                
                if ruc and len(ruc) == 13:
                    detalle = MapaClasificacionDetalle(mapa_id=mapa.id, ruc=ruc, nombre_proveedor=nombre, categoria=categoria)
                    db.session.add(detalle)
                    count += 1
            except:
                continue
        
        db.session.commit()
        flash(f'Mapa subido correctamente con {count} proveedores.', 'success')
    except Exception as e:
        flash(f'Error al procesar: {str(e)}', 'danger')
    
    return redirect(url_for('gastos.panel'))


@gastos.route('/eliminar_mapa/<int:mapa_id>', methods=['POST'])
@login_required
def eliminar_mapa(mapa_id):
    mapa = MapaClasificacion.query.filter_by(id=mapa_id, usuario_id=current_user.id).first()
    if mapa:
        mapa.activo = False
        db.session.commit()
        flash('Mapa eliminado.', 'info')
    return redirect(url_for('gastos.panel'))


@gastos.route('/clasificar/<int:factura_id>', methods=['POST'])
@login_required
def clasificar_gasto(factura_id):
    factura = Factura.query.filter_by(id=factura_id, usuario_id=current_user.id).first()
    if not factura:
        flash('Factura no encontrada.', 'danger')
        return redirect(url_for('gastos.panel'))
    
    categoria = request.form.get('categoria', 'VARIOS')
    existente = ClasificacionGasto.query.filter_by(factura_id=factura_id).first()
    if existente:
        existente.categoria = categoria
    else:
        clasificacion = ClasificacionGasto(usuario_id=current_user.id, factura_id=factura_id,
                                          categoria=categoria, monto=factura.importe_total, fecha=datetime.utcnow())
        db.session.add(clasificacion)
    
    db.session.commit()
    flash(f'Clasificado como {categoria}.', 'success')
    return redirect(url_for('gastos.panel'))


@gastos.route('/auto_clasificar')
@login_required
def auto_clasificar():
    mapa = MapaClasificacion.query.filter_by(usuario_id=current_user.id, activo=True).first()
    if not mapa:
        flash('No tienes un mapa activo. Sube uno primero.', 'warning')
        return redirect(url_for('gastos.panel'))
    
    facturas_sin = Factura.query.filter_by(usuario_id=current_user.id, tipo='gasto').all()
    clasificadas_ids = [c.factura_id for c in ClasificacionGasto.query.filter_by(usuario_id=current_user.id).all()]
    
    count = 0
    for factura in facturas_sin:
        if factura.id in clasificadas_ids:
            continue
        ruc_emisor = factura.ruc_emisor or ''
        detalle = MapaClasificacionDetalle.query.filter_by(mapa_id=mapa.id, ruc=ruc_emisor).first()
        if detalle:
            clasificacion = ClasificacionGasto(usuario_id=current_user.id, factura_id=factura.id,
                                              categoria=detalle.categoria, monto=factura.importe_total, fecha=datetime.utcnow())
            db.session.add(clasificacion)
            count += 1
    
    db.session.commit()
    flash(f'{count} facturas auto-clasificadas.', 'success')
    return redirect(url_for('gastos.panel'))


@gastos.route('/exportar_excel')
@login_required
def exportar_excel():
    try:
        clasificaciones = ClasificacionGasto.query.filter_by(usuario_id=current_user.id).all()
        if not clasificaciones:
            flash('No hay gastos clasificados.', 'warning')
            return redirect(url_for('gastos.panel'))
        
        data = []
        for c in clasificaciones:
            factura = db.session.get(Factura, c.factura_id)
            data.append({
                'Fecha': factura.fecha_emision.strftime('%d/%m/%Y') if factura and factura.fecha_emision else '',
                'N Factura': factura.numero_factura if factura else '',
                'Proveedor': factura.razon_social_emisor if factura else '',
                'RUC': factura.ruc_emisor if factura else '',
                'Categoria': c.categoria,
                'Monto': float(c.monto or 0),
                'Tipo': 'GASTO PERSONAL' if c.categoria in GASTOS_PERSONALES else 'GASTO EJERCICIO'
            })
        
        df = pd.DataFrame(data)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='DETALLE')
            resumen_personal = df[df['Tipo'] == 'GASTO PERSONAL'].groupby('Categoria').agg({'Monto': 'sum', 'N Factura': 'count'}).reset_index()
            resumen_personal.columns = ['Categoria', 'Total', 'Cantidad']
            resumen_ejercicio = df[df['Tipo'] == 'GASTO EJERCICIO'].groupby('Categoria').agg({'Monto': 'sum', 'N Factura': 'count'}).reset_index()
            resumen_ejercicio.columns = ['Categoria', 'Total', 'Cantidad']
            resumen_personal.to_excel(writer, index=False, sheet_name='GASTOS PERSONALES')
            resumen_ejercicio.to_excel(writer, index=False, sheet_name='GASTOS EJERCICIO')
        
        output.seek(0)
        return send_file(output, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                        as_attachment=True, download_name=f'Clasificacion_Gastos_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx')
    except Exception as e:
        flash(f'Error: {str(e)}', 'danger')
        return redirect(url_for('gastos.panel'))