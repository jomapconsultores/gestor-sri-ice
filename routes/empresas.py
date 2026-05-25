from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from models import db
from models.user import Empresa

empresas = Blueprint('empresas', __name__)


def _requiere_plan_empresarial():
    """Retorna True si el usuario tiene plan empresarial activo, False + flash si no."""
    if not current_user.tiene_suscripcion_activa():
        flash('Necesitas una suscripcion activa.', 'warning')
        return False
    if current_user.suscripcion.plan_id != 'empresarial':
        flash('El plan multi-empresa es exclusivo del Plan Empresarial.', 'warning')
        return False
    return True


@empresas.route('/mis_empresas')
@login_required
def mis_empresas():
    if not _requiere_plan_empresarial():
        return redirect(url_for('payments.ver_planes'))

    lista = Empresa.query.filter_by(usuario_id=current_user.id, activa=True).all()
    return render_template('empresas/mis_empresas.html', empresas=lista)


@empresas.route('/agregar', methods=['GET', 'POST'])
@login_required
def agregar_empresa():
    if not _requiere_plan_empresarial():
        return redirect(url_for('payments.ver_planes'))

    if request.method == 'POST':
        nombre = request.form.get('nombre', '').strip()
        ruc = request.form.get('ruc', '').strip()
        razon_social = request.form.get('razon_social', '').strip()

        if not nombre or not ruc:
            flash('Nombre y RUC son obligatorios.', 'warning')
            return render_template('empresas/agregar.html')

        if len(ruc) != 13 or not ruc.isdigit():
            flash('El RUC debe tener exactamente 13 dígitos.', 'warning')
            return render_template('empresas/agregar.html')

        existente = Empresa.query.filter_by(usuario_id=current_user.id, ruc=ruc).first()
        if existente:
            flash('Ya tienes registrada una empresa con ese RUC.', 'warning')
            return render_template('empresas/agregar.html')

        empresa = Empresa(
            usuario_id=current_user.id,
            nombre=nombre,
            ruc=ruc,
            razon_social=razon_social
        )
        db.session.add(empresa)

        if current_user.suscripcion.empresa_actual_id is None:
            db.session.flush()
            current_user.suscripcion.empresa_actual_id = empresa.id

        db.session.commit()
        flash(f'Empresa "{nombre}" agregada correctamente.', 'success')
        return redirect(url_for('empresas.mis_empresas'))

    return render_template('empresas/agregar.html')


@empresas.route('/seleccionar/<int:empresa_id>')
@login_required
def seleccionar_empresa(empresa_id):
    if not current_user.suscripcion:
        flash('Necesitas una suscripcion activa.', 'warning')
        return redirect(url_for('payments.ver_planes'))

    empresa = Empresa.query.filter_by(id=empresa_id, usuario_id=current_user.id, activa=True).first()
    if not empresa:
        flash('Empresa no encontrada.', 'danger')
        return redirect(url_for('empresas.mis_empresas'))

    current_user.suscripcion.empresa_actual_id = empresa_id
    db.session.commit()
    flash(f'Empresa actual: {empresa.nombre}', 'success')
    return redirect(url_for('dashboard'))


@empresas.route('/editar/<int:empresa_id>', methods=['GET', 'POST'])
@login_required
def editar_empresa(empresa_id):
    empresa = Empresa.query.filter_by(id=empresa_id, usuario_id=current_user.id).first()
    if not empresa:
        flash('Empresa no encontrada.', 'danger')
        return redirect(url_for('empresas.mis_empresas'))

    if request.method == 'POST':
        nombre = request.form.get('nombre', '').strip()
        ruc = request.form.get('ruc', '').strip()

        if not nombre or not ruc:
            flash('Nombre y RUC son obligatorios.', 'warning')
            return render_template('empresas/editar.html', empresa=empresa)

        if len(ruc) != 13 or not ruc.isdigit():
            flash('El RUC debe tener exactamente 13 dígitos.', 'warning')
            return render_template('empresas/editar.html', empresa=empresa)

        empresa.nombre = nombre
        empresa.ruc = ruc
        empresa.razon_social = request.form.get('razon_social', empresa.razon_social or '').strip()
        db.session.commit()
        flash('Empresa actualizada.', 'success')
        return redirect(url_for('empresas.mis_empresas'))

    return render_template('empresas/editar.html', empresa=empresa)


@empresas.route('/desactivar/<int:empresa_id>', methods=['POST'])
@login_required
def desactivar_empresa(empresa_id):
    empresa = Empresa.query.filter_by(id=empresa_id, usuario_id=current_user.id).first()
    if not empresa:
        flash('Empresa no encontrada.', 'danger')
        return redirect(url_for('empresas.mis_empresas'))

    empresa.activa = False
    if current_user.suscripcion and current_user.suscripcion.empresa_actual_id == empresa_id:
        current_user.suscripcion.empresa_actual_id = None
    db.session.commit()
    flash(f'Empresa "{empresa.nombre}" desactivada.', 'info')
    return redirect(url_for('empresas.mis_empresas'))
