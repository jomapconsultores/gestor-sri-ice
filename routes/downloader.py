from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify, session
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


def _obtener_progreso():
    """Obtiene el progreso de descarga del usuario actual desde sesión."""
    clave = f"progreso_descarga_{current_user.id}"
    return session.get(clave, {'total': 0, 'completadas': 0, 'errores': 0, 'activo': False})


def _guardar_progreso(progreso):
    """Guarda el progreso de descarga del usuario actual en sesión."""
    clave = f"progreso_descarga_{current_user.id}"
    session[clave] = progreso
    session.modified = True


@downloader.route('/descargar')
@login_required
def pagina_descarga():
    progreso = _obtener_progreso()
    return render_template('downloader/descargar.html', progreso=progreso)


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

    progreso = {'total': len(claves), 'completadas': 0, 'errores': 0, 'activo': True}
    _guardar_progreso(progreso)

    def actualizar_progreso(completadas, total):
        progreso['completadas'] = completadas
        _guardar_progreso(progreso)

    resultados = SRIDownloader.descargar_lote(claves, DOWNLOAD_FOLDER, actualizar_progreso)

    procesadas = 0
    duplicadas = 0

    for ruta in resultados['descargados']:
        try:
            datos = parse_xml_factura(ruta)
            if datos:
                existente = Factura.query.filter_by(
                    usuario_id=current_user.id,
                    clave_acceso=datos['clave_acceso']
                ).first()
                if not existente:
                    fecha = None
                    if datos.get('fecha_emision'):
                        try:
                            from datetime import datetime as dt
                            fecha = dt.strptime(datos['fecha_emision'], '%d/%m/%Y').date()
                        except ValueError:
                            pass
                    factura = Factura(
                        usuario_id=current_user.id,
                        clave_acceso=datos['clave_acceso'],
                        ruc_emisor=datos.get('ruc', ''),
                        razon_social_emisor=datos.get('razon_social_emisor', ''),
                        ruc_comprador=current_user.ruc or datos.get('id_cliente', ''),
                        razon_social_comprador=current_user.nombre or datos.get('razon_social_cliente', ''),
                        fecha_emision=fecha,
                        numero_factura=datos.get('numero_factura', ''),
                        importe_total=float(datos.get('importe_total', 0) or 0),
                        base_ice=sum(float(p.get('base_ice', 0) or 0) for p in datos.get('productos', [])),
                        valor_ice=sum(float(p.get('ice', 0) or 0) for p in datos.get('productos', [])),
                        base_iva=sum(float(p.get('base_iva', 0) or 0) for p in datos.get('productos', [])),
                        valor_iva=sum(float(p.get('iva', 0) or 0) for p in datos.get('productos', [])),
                        xml_original=''
                    )
                    db.session.add(factura)
                    procesadas += 1
                else:
                    duplicadas += 1
        except Exception as e:
            progreso['errores'] += 1
            _guardar_progreso(progreso)
            print(f"Error procesando {ruta}: {e}")

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        flash(f'Error al guardar facturas: {str(e)}', 'danger')
        progreso['activo'] = False
        _guardar_progreso(progreso)
        return redirect(url_for('downloader.pagina_descarga'))

    progreso['activo'] = False
    progreso['errores'] = len(resultados['errores'])
    _guardar_progreso(progreso)

    for ruta in resultados['descargados']:
        try:
            os.remove(ruta)
        except:
            pass

    flash(f'✅ Descarga: {procesadas} procesadas, {duplicadas} duplicadas, {len(resultados["errores"])} errores.', 'success')
    return redirect(url_for('downloader.pagina_descarga'))


@downloader.route('/progreso')
@login_required
def ver_progreso():
    progreso = _obtener_progreso()
    return jsonify(progreso)