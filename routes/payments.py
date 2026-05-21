from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from models import db
from models.user import Suscripcion
from config import Config
from services.payphone_service import PayPhoneService
from datetime import datetime, timedelta
import json

payments = Blueprint('payments', __name__)

PLANES = {
    'basico': {
        'nombre': 'Plan Básico',
        'precio': '$9.99',
        'precio_centavos': 999,
        'limite_facturas': '100/mes',
        'incluye_auditoria': False,
        'color': 'primary',
        'icono': 'star'
    },
    'profesional': {
        'nombre': 'Plan Profesional',
        'precio': '$19.99',
        'precio_centavos': 1999,
        'limite_facturas': 'Ilimitadas',
        'incluye_auditoria': True,
        'color': 'success',
        'icono': 'star-fill'
    },
    'empresarial': {
        'nombre': 'Plan Empresarial',
        'precio': '$39.99',
        'precio_centavos': 3999,
        'limite_facturas': 'Ilimitadas',
        'incluye_auditoria': True,
        'color': 'warning',
        'icono': 'building'
    }
}


@payments.route('/planes')
def ver_planes():
    return render_template('planes.html', planes=PLANES)


@payments.route('/pagar/<plan_id>')
@login_required
def pagar(plan_id):
    if plan_id not in PLANES:
        flash('Plan no válido.', 'danger')
        return redirect(url_for('payments.ver_planes'))
    
    # Si ya tiene este plan activo
    if current_user.tiene_suscripcion_activa():
        if current_user.suscripcion.plan_id == plan_id:
            flash('Ya tienes este plan activo.', 'info')
            return redirect(url_for('dashboard'))
    
    # Crear pago en PayPhone
    url_pago, error = PayPhoneService.crear_pago(
        plan_id=plan_id,
        usuario_email=current_user.email,
        usuario_nombre=current_user.nombre
    )
    
    if error:
        flash(f'Error al crear el pago: {error}', 'danger')
        return redirect(url_for('payments.ver_planes'))
    
    if url_pago:
        return redirect(url_pago)
    else:
        flash('No se pudo generar el link de pago.', 'danger')
        return redirect(url_for('payments.ver_planes'))


@payments.route('/respuesta')
@login_required
def respuesta_pago():
    """PayPhone redirige aquí después del pago"""
    transaction_id = request.args.get('clientTransactionId')
    status = request.args.get('status')
    
    if status == 'success' or status == 'approved':
        # Extraer plan_id del transactionId (formato: plan_id_email)
        try:
            plan_id = transaction_id.split('_')[0]
        except:
            plan_id = 'basico'
        
        # Activar suscripción
        suscripcion = Suscripcion.query.filter_by(usuario_id=current_user.id).first()
        
        if suscripcion:
            suscripcion.plan_id = plan_id
            suscripcion.estado = 'activa'
            suscripcion.fecha_inicio = datetime.utcnow()
            suscripcion.fecha_renovacion = datetime.utcnow() + timedelta(days=30)
            suscripcion.facturas_procesadas_mes = 0
        else:
            suscripcion = Suscripcion(
                usuario_id=current_user.id,
                plan_id=plan_id,
                estado='activa',
                fecha_inicio=datetime.utcnow(),
                fecha_renovacion=datetime.utcnow() + timedelta(days=30),
                facturas_procesadas_mes=0
            )
            db.session.add(suscripcion)
        
        db.session.commit()
        
        flash('¡Pago exitoso! Tu suscripción está activa.', 'success')
        return render_template('pago_exito.html', plan=plan_id)
    
    else:
        flash('El pago no se completó. Intenta de nuevo.', 'warning')
        return redirect(url_for('payments.ver_planes'))


@payments.route('/cancelar')
@login_required
def cancelar_suscripcion():
    suscripcion = Suscripcion.query.filter_by(usuario_id=current_user.id).first()
    
    if suscripcion and suscripcion.estado == 'activa':
        suscripcion.estado = 'cancelada'
        db.session.commit()
        flash('Suscripción cancelada. Puedes volver a activarla cuando quieras.', 'info')
    else:
        flash('No tienes una suscripción activa.', 'warning')
    
    return redirect(url_for('dashboard'))


@payments.route('/renovar')
@login_required
def renovar():
    """Redirige a pagar el mismo plan que ya tenía"""
    if current_user.suscripcion:
        return redirect(url_for('payments.pagar', 
                                plan_id=current_user.suscripcion.plan_id))
    return redirect(url_for('payments.ver_planes'))