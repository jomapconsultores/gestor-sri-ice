from flask import Blueprint, render_template, redirect, url_for, flash, request, send_file, jsonify
from flask_login import login_required, current_user
from models import db
from models.user import Factura, ClasificacionGasto, MapaClasificacion, MapaClasificacionDetalle
from services.validaciones_sri import ValidacionesSRI
from services.gastos_processor import parse_xml_gasto_completo, serializar_datos_gasto, clasificar_gasto_automatico
from datetime import datetime
from sqlalchemy import func, extract
import pandas as pd
import io
import os
import tempfile
import json

gastos = Blueprint('gastos', __name__)

GASTOS_PERSONALES = ['ALIMENTACION', 'EDUCACION', 'SALUD', 'VESTIMENTA', 'VIVIENDA', 'TURISMO', 'ARTE Y CULTURA', 'VARIOS']

YANBAL_RUC = '1791246600001'
YANBAL_NOMBRE = 'YANBAL'


def es_yanbal(ruc_emisor, razon_social):
    ruc = (ruc_emisor or '').strip()
    nombre = (razon_social or '').upper()
    return ruc == YANBAL_RUC or YANBAL_NOMBRE in nombre


def _tiene_modulo(modulo_id):
    from routes.payments import get_modulos_activos
    if current_user.is_admin:
        return True
    return modulo_id in get_modulos_activos(current_user.id)
UPLOAD_MAPAS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'uploads', 'mapas')
if not os.path.exists(UPLOAD_MAPAS):
    os.makedirs(UPLOAD_MAPAS)


@gastos.route('/panel')
@login_required
def panel():
    if not _tiene_modulo('facturas_gasto'):
        flash('Necesitas el módulo "Facturas de Gasto" para acceder a este panel.', 'warning')
        return redirect(url_for('payments.ver_planes'))

    # OBTENER GASTOS SIN CLASIFICAR
    factura_ids_clasificadas = db.session.query(ClasificacionGasto.factura_id).filter_by(
        usuario_id=current_user.id
    ).all()
    ids_clasificadas = {f[0] for f in factura_ids_clasificadas}

    gastos_sin_clasificar = Factura.query.filter_by(usuario_id=current_user.id, tipo='gasto')\
                                        .order_by(Factura.fecha_emision.desc()).all()
    gastos_sin_clasificar = [f for f in gastos_sin_clasificar if f.id not in ids_clasificadas]

    # TODAS LAS FACTURAS (para historial)
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
                         gastos_sin_clasificar=gastos_sin_clasificar,
                         resumen=resumen,
                         gastos_personales_total=gastos_personales_total or 0,
                         gastos_ejercicio_total=gastos_ejercicio_total or 0,
                         mapas=mapas, categorias=GASTOS_PERSONALES,
                         es_yanbal_fn=es_yanbal)


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

    if factura.tipo != 'gasto':
        flash('Solo se pueden clasificar facturas de gasto.', 'danger')
        return redirect(url_for('gastos.panel'))

    categoria = request.form.get('categoria', 'VARIOS').strip().upper()
    if not categoria:
        flash('Categoría vacía.', 'danger')
        return redirect(url_for('gastos.panel'))

    existente = ClasificacionGasto.query.filter_by(
        usuario_id=current_user.id,
        factura_id=factura_id
    ).first()

    try:
        # ✅ VALIDACIÓN SRI: Si es gasto personal, validar límites
        es_personal = categoria in GASTOS_PERSONALES

        if es_personal:
            # Obtener año actual
            anio = datetime.now().year

            # Obtener todos los gastos personales de este año
            gastos_personales = db.session.query(
                ClasificacionGasto.categoria,
                func.sum(ClasificacionGasto.monto).label('total')
            ).filter(
                ClasificacionGasto.usuario_id == current_user.id,
                ClasificacionGasto.categoria.in_(GASTOS_PERSONALES),
                extract('year', ClasificacionGasto.fecha) == anio
            ).group_by(ClasificacionGasto.categoria).all()

            # Preparar lista para validación
            gastos_list = [{'categoria': g[0], 'monto': float(g[1] or 0)} for g in gastos_personales]

            # Agregar el gasto actual si es nueva clasificación
            if not existente:
                gastos_list.append({'categoria': categoria, 'monto': factura.importe_total})
            else:
                # Si actualiza, restar el monto anterior y agregar el nuevo
                for g in gastos_list:
                    if g['categoria'] == existente.categoria:
                        g['monto'] -= existente.monto
                gastos_list.append({'categoria': categoria, 'monto': factura.importe_total})

            # Calcular deducibilidad según SRI (solo informativo, no restrictivo)
            validacion = ValidacionesSRI.validar_gasto_personal(gastos_list, anio)

            # Mostrar información de deducibilidad
            for adv in validacion['advertencias']:
                flash(adv, 'info')

            # Si hay errores, mostrarlos (aunque rara vez ocurran)
            for error in validacion['errores']:
                flash(f'❌ {error}', 'warning')

        # Guardar clasificación
        if existente:
            existente.categoria = categoria
            existente.fecha = datetime.utcnow()
        else:
            clasificacion = ClasificacionGasto(
                usuario_id=current_user.id,
                factura_id=factura_id,
                categoria=categoria,
                monto=factura.importe_total,
                fecha=datetime.utcnow()
            )
            db.session.add(clasificacion)

        db.session.commit()
        flash(f'✅ Clasificado como {categoria}.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'❌ Error al clasificar: {str(e)[:80]}', 'danger')

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


@gastos.route('/procesar_gasto_xml', methods=['POST'])
@login_required
def procesar_gasto_xml():
    """
    Procesa un XML de gasto completo (como SRI-XML.py)
    Extrae toda la composición de IVA y crea la factura en la BD

    Returns JSON con:
    - success: bool
    - factura_id: ID de la factura creada
    - datos: Diccionario con datos parseados
    - error: Mensaje de error (si aplica)
    """
    if not _tiene_modulo('facturas_gasto'):
        return jsonify({"error": "No tienes acceso al módulo de gastos"}), 403

    if 'archivo' not in request.files:
        return jsonify({"error": "No archivo proporcionado"}), 400

    file = request.files['archivo']
    if file.filename == '':
        return jsonify({"error": "Archivo vacío"}), 400

    if not file.filename.lower().endswith('.xml'):
        return jsonify({"error": "Solo se aceptan archivos XML"}), 400

    try:
        # Guardar temporalmente el archivo
        with tempfile.NamedTemporaryFile(delete=False, suffix='.xml') as tmp:
            file.save(tmp.name)
            tmp_path = tmp.name

        # Leer el contenido del XML antes de parsearlo
        xml_content = None
        for encoding in ('utf-8', 'latin-1', 'iso-8859-1', 'cp1252'):
            try:
                with open(tmp_path, 'r', encoding=encoding) as f:
                    xml_content = f.read()
                break
            except:
                continue

        # Parsear como SRI-XML.py
        datos = parse_xml_gasto_completo(tmp_path)

        # Limpiar archivo temporal
        try:
            os.remove(tmp_path)
        except:
            pass

        if not datos:
            return jsonify({
                "error": "No se pudo parsear el XML. Asegúrate de que: "
                         "1) Sea una factura electrónica válida del SRI, "
                         "2) Contenga infoTributaria e infoFactura, "
                         "3) El archivo no esté corrupto"
            }), 400

        # Verificar si la factura ya existe
        existente = Factura.query.filter_by(
            usuario_id=current_user.id,
            clave_acceso=datos['clave_acceso']
        ).first()

        if existente:
            return jsonify({
                "error": "Esta factura ya está registrada",
                "factura_id": existente.id
            }), 409

        # Crear factura en BD
        try:
            fecha_emision = datetime.strptime(datos['fecha'], '%d/%m/%Y').date() if datos['fecha'] else datetime.now().date()
        except:
            fecha_emision = datetime.now().date()

        factura = Factura(
            usuario_id=current_user.id,
            tipo='gasto',
            clave_acceso=datos['clave_acceso'],
            ruc_emisor=datos['ruc_emisor'],
            razon_social_emisor=datos['nombre_emisor'],
            ruc_comprador=datos['ruc_comprador'],
            razon_social_comprador=datos['nombre_comprador'],
            fecha_emision=fecha_emision,
            numero_factura=datos['numero_factura'],
            base_iva=datos['base_15'],  # La base principal del IVA es 15%
            valor_iva=datos['iva_15'],   # El valor del IVA
            importe_total=datos['total'],
            descuento_total=datos['total_descuento'],
            tiene_descuento=datos['total_descuento'] > 0,
            # Guardar toda la composición de IVA en notas_auditoria
            notas_auditoria=serializar_datos_gasto(datos),
            xml_original=xml_content,
        )

        db.session.add(factura)
        db.session.flush()  # Para obtener el ID sin hacer commit

        # Auto-clasificar si hay mapa activo
        mapa_activo = MapaClasificacion.query.filter_by(
            usuario_id=current_user.id,
            activo=True
        ).first()

        clasificacion_cat = "SIN CLASIFICAR"

        if mapa_activo:
            detalles_mapa = MapaClasificacionDetalle.query.filter_by(
                mapa_id=mapa_activo.id
            ).all()

            clasificacion_cat = clasificar_gasto_automatico(
                datos['ruc_emisor'],
                datos['nombre_emisor'],
                detalles_mapa
            )

        # Crear clasificación automática
        if clasificacion_cat != "SIN CLASIFICAR":
            clasificacion = ClasificacionGasto(
                usuario_id=current_user.id,
                factura_id=factura.id,
                categoria=clasificacion_cat,
                monto=factura.importe_total,
                fecha=datetime.utcnow()
            )
            db.session.add(clasificacion)

        db.session.commit()

        return jsonify({
            "success": True,
            "factura_id": factura.id,
            "clasificacion": clasificacion_cat,
            "datos": {
                "numero_factura": datos['numero_factura'],
                "fecha": datos['fecha'],
                "nombre_emisor": datos['nombre_emisor'],
                "nombre_comprador": datos['nombre_comprador'],
                "total": datos['total'],
                "concepto": datos['concepto'],
                "base_15": datos['base_15'],
                "iva_15": datos['iva_15'],
            }
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({
            "error": f"Error al procesar: {str(e)[:100]}"
        }), 500


@gastos.route('/detalle_factura/<int:factura_id>')
@login_required
def detalle_factura(factura_id):
    """
    Retorna los detalles completos de una factura de gasto,
    incluyendo la composición de IVA almacenada en notas_auditoria
    """
    factura = Factura.query.filter_by(
        id=factura_id,
        usuario_id=current_user.id,
        tipo='gasto'
    ).first()

    if not factura:
        return jsonify({"error": "Factura no encontrada"}), 404

    # Deserializar notas de auditoria
    notas = {}
    if factura.notas_auditoria:
        try:
            notas = json.loads(factura.notas_auditoria)
        except:
            notas = {}

    # Obtener clasificación si existe
    clasificacion = ClasificacionGasto.query.filter_by(
        factura_id=factura_id,
        usuario_id=current_user.id
    ).first()

    return jsonify({
        "factura": {
            "id": factura.id,
            "fecha": factura.fecha_emision.strftime('%d/%m/%Y') if factura.fecha_emision else '',
            "numero": factura.numero_factura,
            "ruc_emisor": factura.ruc_emisor,
            "nombre_emisor": factura.razon_social_emisor,
            "ruc_comprador": factura.ruc_comprador,
            "nombre_comprador": factura.razon_social_comprador,
            "total": float(factura.importe_total or 0),
        },
        "composicion_iva": {
            "base_0": float(notas.get('base_0', 0)),
            "base_5": float(notas.get('base_5', 0)),
            "iva_5": float(notas.get('iva_5', 0)),
            "base_15": float(notas.get('base_15', 0)),
            "iva_15": float(notas.get('iva_15', 0)),
            "base_exento": float(notas.get('base_exento', 0)),
            "base_no_objeto": float(notas.get('base_no_objeto', 0)),
            "total_descuento": float(notas.get('total_descuento', 0)),
        },
        "detalles": notas.get('detalles', []),
        "concepto": notas.get('concepto', ''),
        "forma_pago": notas.get('forma_pago', ''),
        "clasificacion": {
            "categoria": clasificacion.categoria if clasificacion else "SIN CLASIFICAR",
            "fecha": clasificacion.fecha.strftime('%d/%m/%Y %H:%M') if clasificacion and clasificacion.fecha else '',
        } if clasificacion else None,
    })


@gastos.route('/exportar_excel')
@login_required
def exportar_excel():
    """
    Exporta gastos a Excel con múltiples hojas:
    - DATOS: Detalle completo de cada gasto
    - COMPOSICIÓN IVA: Desglose de bases y valores por porcentaje
    - RESUMEN PERSONAL: Totales de gastos personales
    - RESUMEN EJERCICIO: Totales de gastos deducibles del ejercicio
    """
    try:
        clasificaciones = ClasificacionGasto.query.filter_by(usuario_id=current_user.id).all()
        if not clasificaciones:
            flash('No hay gastos clasificados.', 'warning')
            return redirect(url_for('gastos.panel'))

        # Preparar datos detallados
        datos_detalle = []
        composicion_iva_data = []

        for c in clasificaciones:
            factura = db.session.get(Factura, c.factura_id)
            if not factura:
                continue

            # Desserializar notas de auditoria para obtener composición de IVA
            notas = {}
            if factura.notas_auditoria:
                try:
                    notas = json.loads(factura.notas_auditoria)
                except:
                    notas = {}

            datos_detalle.append({
                'Fecha': factura.fecha_emision.strftime('%d/%m/%Y') if factura.fecha_emision else '',
                'N Factura': factura.numero_factura if factura else '',
                'Proveedor': factura.razon_social_emisor if factura else '',
                'RUC': factura.ruc_emisor if factura else '',
                'Categoria': c.categoria,
                'Total': float(c.monto or 0),
                'Tipo': 'GASTO PERSONAL' if c.categoria in GASTOS_PERSONALES else 'GASTO EJERCICIO'
            })

            # Agregar datos de composición de IVA
            composicion_iva_data.append({
                'Fecha': factura.fecha_emision.strftime('%d/%m/%Y') if factura.fecha_emision else '',
                'N Factura': factura.numero_factura if factura else '',
                'Proveedor': factura.razon_social_emisor if factura else '',
                'Base 0%': float(notas.get('base_0', 0)),
                'Base 5%': float(notas.get('base_5', 0)),
                'IVA 5%': float(notas.get('iva_5', 0)),
                'Base 15%': float(notas.get('base_15', 0)),
                'IVA 15%': float(notas.get('iva_15', 0)),
                'Base Exento': float(notas.get('base_exento', 0)),
                'Base No Objeto': float(notas.get('base_no_objeto', 0)),
                'Descuento': float(notas.get('total_descuento', 0)),
                'Total': float(c.monto or 0),
            })

        # Crear DataFrame
        df_detalle = pd.DataFrame(datos_detalle)
        df_composicion = pd.DataFrame(composicion_iva_data)

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # Hoja 1: DATOS - Detalle de cada factura
            df_detalle.to_excel(writer, index=False, sheet_name='DATOS')

            # Hoja 2: COMPOSICIÓN IVA - Desglose detallado
            df_composicion.to_excel(writer, index=False, sheet_name='COMPOSICIÓN IVA')

            # Hoja 3: RESUMEN PERSONAL
            resumen_personal = df_detalle[df_detalle['Tipo'] == 'GASTO PERSONAL'].groupby('Categoria').agg(
                {'Total': 'sum', 'N Factura': 'count'}
            ).reset_index()
            resumen_personal.columns = ['Categoria', 'Total', 'Cantidad']
            resumen_personal.to_excel(writer, index=False, sheet_name='GASTOS PERSONALES')

            # Hoja 4: RESUMEN EJERCICIO
            resumen_ejercicio = df_detalle[df_detalle['Tipo'] == 'GASTO EJERCICIO'].groupby('Categoria').agg(
                {'Total': 'sum', 'N Factura': 'count'}
            ).reset_index()
            resumen_ejercicio.columns = ['Categoria', 'Total', 'Cantidad']
            resumen_ejercicio.to_excel(writer, index=False, sheet_name='GASTOS EJERCICIO')

            # Hoja 5: RESUMEN GENERAL (totales por tipo)
            resumen_general = pd.DataFrame([
                {
                    'Tipo': 'GASTOS PERSONALES',
                    'Cantidad': len(df_detalle[df_detalle['Tipo'] == 'GASTO PERSONAL']),
                    'Total': float(df_detalle[df_detalle['Tipo'] == 'GASTO PERSONAL']['Total'].sum())
                },
                {
                    'Tipo': 'GASTOS EJERCICIO',
                    'Cantidad': len(df_detalle[df_detalle['Tipo'] == 'GASTO EJERCICIO']),
                    'Total': float(df_detalle[df_detalle['Tipo'] == 'GASTO EJERCICIO']['Total'].sum())
                },
                {
                    'Tipo': 'TOTAL GENERAL',
                    'Cantidad': len(df_detalle),
                    'Total': float(df_detalle['Total'].sum())
                }
            ])
            resumen_general.to_excel(writer, index=False, sheet_name='RESUMEN GENERAL')

        output.seek(0)
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f'Gastos_Completo_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        )

    except Exception as e:
        flash(f'Error: {str(e)}', 'danger')
        return redirect(url_for('gastos.panel'))