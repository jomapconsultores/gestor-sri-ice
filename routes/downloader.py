from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user
from services.sri_downloader import SRIDownloader
from services.xml_parser import parse_xml_factura
from models import db
from models.user import Factura
from datetime import datetime
import os

downloader = Blueprint('downloader', __name__)

DOWNLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'sri_downloads')
if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

progreso_actual = {'total': 0, 'completadas': 0, 'errores': 0, 'activo': False}


@downloader.route('/descargar')
@login_required
def pagina_descarga():
    return render_template('downloader/descargar.html', progreso=progreso_actual)


@downloader.route('/bookmarklet')
@login_required
def bookmarklet():
    return render_template('downloader/bookmarklet.html')


@downloader.route('/procesar_txt', methods=['POST'])
@login_required
def procesar_txt():
    if 'archivo_txt' not in request.files:
        flash('Selecciona un archivo TXT.', 'warning')
        return redirect(url_for('downloader.pagina_descarga'))
    
    archivo = request.files['archivo_txt']
    
    if archivo.filename == '':
        flash('Selecciona un archivo.', 'warning')
        return redirect(url_for('downloader.pagina_descarga'))
    
    contenido = archivo.read().decode('utf-8', errors='ignore')
    claves = SRIDownloader.extraer_claves(contenido)
    
    if not claves:
        flash('No se encontraron claves de acceso en el archivo.', 'warning')
        return redirect(url_for('downloader.pagina_descarga'))
    
    global progreso_actual
    progreso_actual = {'total': len(claves), 'completadas': 0, 'errores': 0, 'activo': True}
    
    def actualizar_progreso(completadas, total):
        progreso_actual['completadas'] = completadas
    
    resultados = SRIDownloader.descargar_lote(claves, DOWNLOAD_FOLDER, actualizar_progreso)
    
    procesadas = 0
    duplicadas = 0
    
    for ruta in resultados['descargados']:
        try:
            datos = parse_xml_factura(ruta)
            if datos:
                existente = Factura.query.filter_by(clave_acceso=datos['clave_acceso']).first()
                if not existente:
                    fecha = None
                    if datos.get('fecha_emision'):
                        try:
                            fecha = datetime.strptime(datos['fecha_emision'], '%d/%m/%Y').date()
                        except ValueError:
                            pass
                    factura = Factura(
                        usuario_id=current_user.id,
                        clave_acceso=datos['clave_acceso'],
                        ruc_emisor=datos['ruc'],
                        razon_social_emisor='',
                        ruc_comprador=datos['id_cliente'],
                        razon_social_comprador=datos['razon_social_cliente'],
                        fecha_emision=fecha,
                        numero_factura=datos['numero_factura'],
                        importe_total=datos['importe_total'],
                        base_ice=sum(p['base_ice'] for p in datos['productos']),
                        valor_ice=sum(p['ice'] for p in datos['productos']),
                        base_iva=sum(p['base_iva'] for p in datos['productos']),
                        valor_iva=sum(p['iva'] for p in datos['productos']),
                        xml_original=''
                    )
                    db.session.add(factura)
                    procesadas += 1
                else:
                    duplicadas += 1
        except Exception as e:
            print(f"Error procesando {ruta}: {e}")
    
    db.session.commit()
    
    progreso_actual['activo'] = False
    progreso_actual['errores'] = len(resultados['errores'])
    
    for ruta in resultados['descargados']:
        try:
            os.remove(ruta)
        except:
            pass
    
    flash(f'Descarga completada: {procesadas} procesadas, {duplicadas} duplicadas, {len(resultados["errores"])} errores.', 'success')
    return redirect(url_for('downloader.pagina_descarga'))


@downloader.route('/progreso')
@login_required
def ver_progreso():
    return jsonify({
        'total': progreso_actual['total'],
        'completadas': progreso_actual['completadas'],
        'errores': progreso_actual['errores'],
        'activo': progreso_actual['activo']
    })