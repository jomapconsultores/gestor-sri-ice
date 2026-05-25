from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from models import db
from models.user import IpAutorizada, SolicitudIp, Usuario
from datetime import datetime

security = Blueprint("security", __name__)

def obtener_ip():
    if request.headers.get("X-Forwarded-For"):
        return request.headers.get("X-Forwarded-For").split(",")[0].strip()
    return request.remote_addr or "127.0.0.1"

@security.route("/solicitar_ip", methods=["GET", "POST"])
@login_required
def solicitar_ip():
    if request.method == "POST":
        ip = obtener_ip()
        justificacion = request.form.get("justificacion", "")
        if not justificacion:
            flash("Debes escribir una justificacion.", "warning")
            return render_template("security/solicitar_ip.html", ip=ip)
        existente = SolicitudIp.query.filter_by(usuario_id=current_user.id, direccion_ip=ip, estado="pendiente").first()
        if existente:
            flash("Ya tienes una solicitud pendiente para esta IP.", "warning")
            return redirect(url_for("dashboard"))
        solicitud = SolicitudIp(usuario_id=current_user.id, direccion_ip=ip, justificacion=justificacion)
        db.session.add(solicitud)
        db.session.commit()
        flash("Solicitud enviada. Un administrador la revisara.", "success")
        return redirect(url_for("dashboard"))
    return render_template("security/solicitar_ip.html", ip=obtener_ip())

@security.route("/admin/ips")
@login_required
def admin_ips():
    if not current_user.is_admin:
        flash("Acceso denegado.", "danger")
        return redirect(url_for("dashboard"))
    solicitudes = SolicitudIp.query.filter_by(estado="pendiente").order_by(SolicitudIp.fecha_solicitud.desc()).all()
    usuarios = Usuario.query.all()
    return render_template("security/admin_ips.html", solicitudes=solicitudes, usuarios=usuarios)

@security.route("/admin/aprobar_ip/<int:solicitud_id>", methods=["POST"])
@login_required
def aprobar_ip(solicitud_id):
    if not current_user.is_admin:
        flash("Acceso denegado.", "danger")
        return redirect(url_for("dashboard"))
    solicitud = db.session.get(SolicitudIp, solicitud_id)
    if solicitud and solicitud.estado == "pendiente":
        ips_activas = IpAutorizada.query.filter_by(usuario_id=solicitud.usuario_id, activa=True).count()
        if ips_activas >= 3:
            flash(f"El usuario ya tiene {ips_activas} IPs autorizadas.", "warning")
        else:
            nueva_ip = IpAutorizada(usuario_id=solicitud.usuario_id, direccion_ip=solicitud.direccion_ip)
            db.session.add(nueva_ip)
            solicitud.estado = "aprobada"
            solicitud.fecha_respuesta = datetime.utcnow()
            db.session.commit()
            flash("IP autorizada correctamente.", "success")
    return redirect(url_for("security.admin_ips"))

@security.route("/admin/rechazar_ip/<int:solicitud_id>", methods=["POST"])
@login_required
def rechazar_ip(solicitud_id):
    if not current_user.is_admin:
        flash("Acceso denegado.", "danger")
        return redirect(url_for("dashboard"))
    solicitud = db.session.get(SolicitudIp, solicitud_id)
    if solicitud:
        solicitud.estado = "rechazada"
        solicitud.fecha_respuesta = datetime.utcnow()
        db.session.commit()
        flash("Solicitud de IP rechazada.", "info")
    return redirect(url_for("security.admin_ips"))
