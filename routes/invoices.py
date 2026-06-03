from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from models import db
from models.user import Factura, SaldoIVAMes
from services.xml_parser import parse_xml_factura
from services.validaciones_sri import ValidacionesSRI
from datetime import datetime
import os
import traceback

invoices = Blueprint('invoices', __name__)

UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)


def _tiene_modulo(modulo_id):
    from routes.payments import get_modulos_activos
    if current_user.is_admin:
        return True
    return modulo_id in get_modulos_activos(current_user.id)


# ─── GASTOS (facturas de compra) ─────────────────────────────────────────────

@invoices.route('/cargar')
@login_required
def pagina_carga():
    """Página para subir facturas de GASTOS (compras/proveedores)."""
    if not _tiene_modulo('facturas_gasto'):
        flash('Necesitas el módulo "Facturas de Gasto" para subir facturas de gasto.', 'warning')
        return redirect(url_for('payments.ver_planes'))
    facturas = Factura.query.filter_by(
        usuario_id=current_user.id, tipo='gasto'
    ).order_by(Factura.fecha_procesamiento.desc()).limit(50).all()
    return render_template('invoices/cargar.html', facturas=facturas, tipo='gasto')


def _parsear_fecha(fecha_str):
    """Intenta parsear fecha en múltiples formatos comunes del SRI."""
    if not fecha_str:
        return None
    formatos = ['%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y']
    for fmt in formatos:
        try:
            return datetime.strptime(fecha_str.strip(), fmt).date()
        except (ValueError, AttributeError):
            continue
    return None


def _actualizar_saldo_iva_mes(usuario_id, anio, mes):
    """Actualiza el saldo IVA mensual del usuario basado en sus facturas."""
    try:
        # Obtener todas las facturas del mes
        from sqlalchemy import and_, extract
        facturas_mes = Factura.query.filter(
            and_(
                Factura.usuario_id == usuario_id,
                extract('year', Factura.fecha_emision) == anio,
                extract('month', Factura.fecha_emision) == mes,
            )
        ).all()

        # Separar por tipo
        iva_cobrado = 0  # IVA de ingresos
        iva_pagado = 0   # IVA de gastos

        for factura in facturas_mes:
            iva = float(factura.valor_iva or 0)
            if factura.tipo == 'ingreso':
                iva_cobrado += iva
            else:  # gasto
                iva_pagado += iva

        # Obtener o crear registro de saldo
        saldo = SaldoIVAMes.query.filter_by(
            usuario_id=usuario_id, anio=anio, mes=mes
        ).first()

        if saldo:
            saldo.iva_cobrado = iva_cobrado
            saldo.iva_pagado = iva_pagado
            saldo.saldo_final = iva_cobrado - iva_pagado
            saldo.fecha_actualizacion = datetime.utcnow()
        else:
            saldo = SaldoIVAMes(
                usuario_id=usuario_id,
                anio=anio,
                mes=mes,
                iva_cobrado=iva_cobrado,
                iva_pagado=iva_pagado,
                saldo_anterior=0,
                saldo_final=iva_cobrado - iva_pagado,
            )
            db.session.add(saldo)

        db.session.commit()
    except Exception as e:
        print(f"Error actualizando saldo IVA: {e}")
        db.session.rollback()


@invoices.route('/subir', methods=['POST'])
@login_required
def subir_facturas():
    tipo = request.form.get('tipo', 'gasto')
    modulo_requerido = 'facturas_gasto' if tipo == 'gasto' else 'facturas_ingreso'
    if not _tiene_modulo(modulo_requerido):
        flash('Módulo no activo.', 'danger')
        return redirect(url_for('invoices.pagina_carga' if tipo == 'gasto' else 'invoices.cargar_ingresos'))

    archivos = request.files.getlist('archivos')
    if not archivos or archivos[0].filename == '':
        flash('No se seleccionaron archivos.', 'warning')
        return redirect(url_for('invoices.pagina_carga' if tipo == 'gasto' else 'invoices.cargar_ingresos'))

    procesadas = errores = duplicadas = 0
    mensajes_error = []

    for archivo in archivos:
        if not archivo.filename.lower().endswith('.xml'):
            continue
        ruta_temp = os.path.join(UPLOAD_FOLDER, archivo.filename)
        contenido_xml = None

        try:
            archivo.save(ruta_temp)

            with open(ruta_temp, 'r', encoding='utf-8') as f:
                contenido_xml = f.read()

            datos = parse_xml_factura(ruta_temp)
            if datos is None:
                errores += 1
                mensajes_error.append(f"❌ {archivo.filename}: No se pudo parsear XML (estructura inválida)")
                continue

            # VALIDACIONES CRÍTICAS
            clave_acceso = datos.get('clave_acceso', '').strip()
            if not clave_acceso or len(clave_acceso) != 49:
                errores += 1
                mensajes_error.append(f"❌ {archivo.filename}: Clave de acceso inválida")
                continue

            # Validar RUC emisor
            try:
                ValidacionesSRI.validar_ruc(datos.get('ruc', ''))
            except ValueError as e:
                errores += 1
                mensajes_error.append(f"❌ {archivo.filename}: {str(e)}")
                continue

            existente = Factura.query.filter_by(
                usuario_id=current_user.id,
                clave_acceso=clave_acceso
            ).first()
            if existente:
                duplicadas += 1
                mensajes_error.append(f"⚠️ {archivo.filename}: Factura duplicada (ya existe)")
                continue

            fecha_emision = _parsear_fecha(datos.get('fecha_emision', ''))
            if not fecha_emision:
                errores += 1
                mensajes_error.append(f"❌ {archivo.filename}: Fecha inválida ({datos.get('fecha_emision')})")
                continue

            # Validar período fiscal
            try:
                ValidacionesSRI.validar_periodo_fiscal(fecha_emision)
            except ValueError as e:
                errores += 1
                mensajes_error.append(f"❌ {archivo.filename}: {str(e)}")
                continue

            descuento_total = float(datos.get('descuento_total', 0) or 0)
            importe_total = float(datos.get('importe_total', 0) or 0)

            # Validar importe
            try:
                ValidacionesSRI.validar_importe(importe_total, minimo=0.01)
            except ValueError as e:
                errores += 1
                mensajes_error.append(f"❌ {archivo.filename}: {str(e)}")
                continue

            # AGRUPAR IVA POR TARIFA (CRÍTICO para SRI)
            productos = datos.get('productos', [])
            iva_por_tarifa = ValidacionesSRI.agrupar_iva_por_tarifa(productos)

            # Almacenar información de tarifa en JSON para auditoría
            detalles_iva = {
                '0%': {'base': iva_por_tarifa['0']['base'], 'iva': iva_por_tarifa['0']['iva']},
                '5%': {'base': iva_por_tarifa['5']['base'], 'iva': iva_por_tarifa['5']['iva']},
                '12%': {'base': iva_por_tarifa['12']['base'], 'iva': iva_por_tarifa['12']['iva']},
                '15%': {'base': iva_por_tarifa['15']['base'], 'iva': iva_por_tarifa['15']['iva']},
            }

            factura = Factura(
                usuario_id=current_user.id,
                clave_acceso=clave_acceso,
                ruc_emisor=datos.get('ruc', '').strip(),
                razon_social_emisor=datos.get('razon_social_emisor', '').strip(),
                ruc_comprador=current_user.ruc or datos.get('id_cliente', '').strip(),
                razon_social_comprador=current_user.nombre or datos.get('razon_social_cliente', '').strip(),
                fecha_emision=fecha_emision,
                numero_factura=datos.get('numero_factura', '').strip(),
                importe_total=importe_total,
                base_ice=sum(float(p.get('base_ice', 0) or 0) for p in productos),
                valor_ice=sum(float(p.get('ice', 0) or 0) for p in productos),
                # ✅ IVA AGRUPADO POR TARIFA (no suma simple)
                base_iva=sum(iva_por_tarifa[t]['base'] for t in iva_por_tarifa),
                valor_iva=sum(iva_por_tarifa[t]['iva'] for t in iva_por_tarifa),
                xml_original=contenido_xml[:65535] if contenido_xml else '',
                tipo=tipo,
                descuento_total=descuento_total,
                tiene_descuento=descuento_total > 0,
            )
            # Guardar detalles de tarifa como comentario (para auditoría)
            factura.notas_auditoria = f"Detalles IVA: {detalles_iva}"
            db.session.add(factura)
            procesadas += 1
        except Exception as e:
            errores += 1
            mensajes_error.append(f"❌ {archivo.filename}: {str(e)[:80]}")
            import traceback
            print(f"Error procesando {archivo.filename}: {traceback.format_exc()}")
        finally:
            if os.path.exists(ruta_temp):
                os.remove(ruta_temp)

    try:
        db.session.commit()
        msg = f'✅ {procesadas} factura(s) procesada(s)'
        if duplicadas:
            msg += f' | ⚠️ {duplicadas} duplicada(s)'
        if errores:
            msg += f' | ❌ {errores} error(es)'
        flash(msg, 'success' if procesadas > 0 else 'warning')

        if mensajes_error and procesadas == 0:
            for err in mensajes_error[:5]:
                flash(err, 'danger')

        # ACTUALIZAR SALDO IVA POR MES después de procesar
        if procesadas > 0:
            facturas_nuevas = Factura.query.filter_by(usuario_id=current_user.id).order_by(
                Factura.fecha_procesamiento.desc()).limit(procesadas).all()
            meses_actualizados = set()
            for factura in facturas_nuevas:
                if factura.fecha_emision:
                    mes_key = (factura.fecha_emision.year, factura.fecha_emision.month)
                    if mes_key not in meses_actualizados:
                        # Recalcular saldo IVA para este mes
                        _actualizar_saldo_iva_mes(current_user.id, factura.fecha_emision.year, factura.fecha_emision.month)
                        meses_actualizados.add(mes_key)
    except Exception as e:
        db.session.rollback()
        flash(f'Error al guardar en base de datos: {str(e)}', 'danger')
        print(f"DB Error: {e}")

    if tipo == 'ingreso':
        return redirect(url_for('invoices.cargar_ingresos'))
    return redirect(url_for('invoices.pagina_carga'))


# ─── INGRESOS (facturas de venta) ────────────────────────────────────────────

@invoices.route('/ingresos')
@login_required
def cargar_ingresos():
    """Página para subir facturas de INGRESOS (ventas propias)."""
    if not _tiene_modulo('facturas_ingreso'):
        flash('Necesitas el módulo "Facturas de Ingreso" para subir facturas de ingreso.', 'warning')
        return redirect(url_for('payments.ver_planes'))
    facturas = Factura.query.filter_by(
        usuario_id=current_user.id, tipo='ingreso'
    ).order_by(Factura.fecha_procesamiento.desc()).limit(50).all()
    return render_template('invoices/cargar_ingresos.html', facturas=facturas, tipo='ingreso')


@invoices.route('/reporte_ingresos')
@login_required
def reporte_ingresos():
    """Reporte de facturas de ingreso con totales ICE/IVA."""
    if not _tiene_modulo('facturas_ingreso'):
        flash('Módulo no activo.', 'warning')
        return redirect(url_for('payments.ver_planes'))
    from sqlalchemy import func, extract
    facturas = Factura.query.filter_by(
        usuario_id=current_user.id, tipo='ingreso'
    ).order_by(Factura.fecha_emision.desc()).all()

    resumen = db.session.query(
        extract('year', Factura.fecha_emision).label('anio'),
        extract('month', Factura.fecha_emision).label('mes'),
        func.count(Factura.id).label('cantidad'),
        func.sum(Factura.importe_total).label('total'),
        func.sum(Factura.base_ice).label('base_ice'),
        func.sum(Factura.valor_ice).label('ice'),
        func.sum(Factura.base_iva).label('base_iva'),
        func.sum(Factura.valor_iva).label('iva'),
    ).filter_by(usuario_id=current_user.id, tipo='ingreso')\
     .group_by('anio', 'mes').order_by('anio', 'mes').all()

    tiene_anexos = _tiene_modulo('anexos')
    return render_template('invoices/reporte_ingresos.html',
                           facturas=facturas,
                           resumen=resumen,
                           tiene_anexos=tiene_anexos)


# ─── COMUNES ─────────────────────────────────────────────────────────────────

@invoices.route('/ver')
@login_required
def ver_facturas():
    tipo = request.args.get('tipo', '')
    q = Factura.query.filter_by(usuario_id=current_user.id)
    if tipo:
        q = q.filter_by(tipo=tipo)
    facturas = q.order_by(Factura.fecha_procesamiento.desc()).all()
    return render_template('invoices/ver.html', facturas=facturas, tipo=tipo)


@invoices.route('/resumen')
@login_required
def resumen():
    from sqlalchemy import func, extract
    resumen = db.session.query(
        extract('year', Factura.fecha_emision).label('anio'),
        extract('month', Factura.fecha_emision).label('mes'),
        func.count(Factura.id).label('cantidad'),
        func.sum(Factura.importe_total).label('total'),
        func.sum(Factura.base_ice).label('base_ice'),
        func.sum(Factura.valor_ice).label('ice'),
        func.sum(Factura.base_iva).label('base_iva'),
        func.sum(Factura.valor_iva).label('iva')
    ).filter(Factura.usuario_id == current_user.id)\
     .group_by('anio', 'mes').order_by('anio', 'mes').all()
    return render_template('invoices/resumen.html', resumen=resumen)
