from flask import Blueprint, render_template, request, flash, redirect, url_for, Response
from flask_login import login_required, current_user
from models import db
from models.user import Factura
from services.annex_generator import AnnexGenerator
from datetime import datetime
import xml.dom.minidom as minidom

annexes = Blueprint('annexes', __name__)


@annexes.route('/generar')
@login_required
def pagina_generar():
    facturas = Factura.query.filter_by(usuario_id=current_user.id)\
                           .filter(Factura.valor_ice > 0)\
                           .order_by(Factura.fecha_emision.desc())\
                           .limit(100).all()
    return render_template('annexes/generar.html', facturas=facturas)


@annexes.route('/generar_xml', methods=['POST'])
@login_required
def generar_xml():
    try:
        tipo = request.form.get('tipo', 'ICE')
        ruc = request.form.get('ruc', '').strip()
        razon = request.form.get('razon', '').strip()
        anio = request.form.get('anio', '').strip()
        mes = request.form.get('mes', '').strip()
        
        if not ruc or not razon or not anio or not mes:
            flash('Todos los campos son obligatorios.', 'warning')
            return redirect(url_for('annexes.pagina_generar'))
        
        # Obtener facturas del periodo
        facturas = Factura.query.filter_by(usuario_id=current_user.id)\
                               .filter(Factura.valor_ice > 0)\
                               .order_by(Factura.fecha_emision.desc())\
                               .limit(200).all()
        
        if not facturas:
            flash('No hay facturas con ICE para generar el anexo.', 'warning')
            return redirect(url_for('annexes.pagina_generar'))
        
        # Generar XML
        xml_content = AnnexGenerator.generar_anexo(
            tipo=tipo,
            ruc=ruc,
            razon_social=razon,
            anio=anio,
            mes=mes,
            facturas=facturas
        )
        
        # Formatear XML
        xml_formateado = minidom.parseString(xml_content).toprettyxml(indent='  ', encoding='UTF-8')
        
        return Response(
            xml_formateado,
            mimetype='application/xml',
            headers={
                'Content-Disposition': f'attachment; filename=Anexo_{tipo}_{ruc}_{anio}{mes}.xml'
            }
        )
    
    except Exception as e:
        flash(f'Error al generar el anexo: {str(e)}', 'danger')
        return redirect(url_for('annexes.pagina_generar'))


@annexes.route('/historial')
@login_required
def historial():
    return render_template('annexes/historial.html')