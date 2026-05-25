from flask import Blueprint, render_template, request, flash, redirect, url_for, Response
from flask_login import login_required, current_user
from models import db
from models.user import Factura, CatalogoProducto
from services.annex_generator import AnnexGenerator
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
        
        from sqlalchemy import extract
        facturas = Factura.query.filter_by(usuario_id=current_user.id)\
                               .filter(Factura.valor_ice > 0)\
                               .filter(extract('year', Factura.fecha_emision) == int(anio))\
                               .filter(extract('month', Factura.fecha_emision) == int(mes))\
                               .order_by(Factura.fecha_emision.asc())\
                               .all()

        if not facturas:
            flash(f'No hay facturas con ICE para {mes}/{anio}.', 'warning')
            return redirect(url_for('annexes.pagina_generar'))

        producto = CatalogoProducto.query.filter_by(usuario_id=current_user.id).first()

        xml_content = AnnexGenerator.generar_anexo(
            tipo=tipo, ruc=ruc, razon_social=razon,
            anio=anio, mes=mes, facturas=facturas, producto=producto
        )
        
        xml_formateado = minidom.parseString(xml_content).toprettyxml(indent='  ', encoding='UTF-8')
        
        return Response(
            xml_formateado,
            mimetype='application/xml',
            headers={'Content-Disposition': f'attachment; filename=Anexo_{tipo}_{ruc}_{anio}{mes}.xml'}
        )
    
    except Exception as e:
        flash(f'Error al generar el anexo: {str(e)}', 'danger')
        return redirect(url_for('annexes.pagina_generar'))


@annexes.route('/historial')
@login_required
def historial():
    from sqlalchemy import func, extract
    resumen = db.session.query(
        extract('year', Factura.fecha_emision).label('anio'),
        extract('month', Factura.fecha_emision).label('mes'),
        func.count(Factura.id).label('cantidad'),
        func.sum(Factura.valor_ice).label('total_ice')
    ).filter(
        Factura.usuario_id == current_user.id,
        Factura.valor_ice > 0
    ).group_by('anio', 'mes').order_by('anio', 'mes').all()
    return render_template('annexes/historial.html', resumen=resumen)