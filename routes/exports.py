from flask import Blueprint, render_template, request, flash, redirect, url_for, send_file
from flask_login import login_required, current_user
from models.user import Factura
from services.excel_exporter import ExcelExporter
from services.ice_calculator import TAX_DB
from datetime import datetime

exports = Blueprint('exports', __name__)


@exports.route('/declaracion')
@login_required
def exportar_declaracion():
    facturas = Factura.query.filter_by(usuario_id=current_user.id)\
                           .order_by(Factura.fecha_emision.desc()).all()
    
    if not facturas:
        flash('No hay facturas para exportar.', 'warning')
        return redirect(url_for('invoices.ver_facturas'))
    
    output = ExcelExporter.exportar_declaracion(facturas)
    
    if output:
        fecha = datetime.now().strftime('%Y%m%d_%H%M%S')
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f'Declaracion_{fecha}.xlsx'
        )
    
    flash('Error al generar Excel. Instala openpyxl.', 'danger')
    return redirect(url_for('invoices.ver_facturas'))


@exports.route('/auditoria', methods=['GET', 'POST'])
@login_required
def exportar_auditoria():
    if request.method == 'POST':
        try:
            precio = float(request.form.get('precio', 0))
            volumen = int(request.form.get('volumen', 750))
            grado = float(request.form.get('grado', 0))

            if precio <= 0:
                flash('El precio de fábrica debe ser mayor a 0.', 'warning')
                return redirect(url_for('exports.exportar_auditoria'))
            if volumen <= 0:
                flash('El volumen debe ser mayor a 0.', 'warning')
                return redirect(url_for('exports.exportar_auditoria'))
            if grado <= 0:
                flash('El grado alcohólico debe ser mayor a 0.', 'warning')
                return redirect(url_for('exports.exportar_auditoria'))

            datos = {
                'precio_fabrica': precio,
                'volumen_cc': volumen,
                'grado_alcoholico': grado,
                'tipo_producto': request.form.get('tipo', 'Licor'),
                'cantidad': int(request.form.get('cantidad', 1))
            }
            anios = request.form.getlist('anios')

            if not anios:
                flash('Selecciona al menos un ano.', 'warning')
                return redirect(url_for('exports.exportar_auditoria'))
            
            output = ExcelExporter.exportar_auditoria(datos, anios)
            
            if output:
                fecha = datetime.now().strftime('%Y%m%d_%H%M%S')
                return send_file(
                    output,
                    mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                    as_attachment=True,
                    download_name=f'Auditoria_ICE_{fecha}.xlsx'
                )
        except Exception as e:
            flash(f'Error: {str(e)}', 'danger')
    
    return render_template('exports/auditoria.html', tax_db=TAX_DB)