"""
Rutas para consultar historial de auditoría
Acceso: Solo el usuario propietario + admins
"""
from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from services.auditoria import ServicioAuditoria
from datetime import datetime, timedelta

auditoria = Blueprint('auditoria', __name__, url_prefix='/auditoria')


@auditoria.route('/historial')
@login_required
def obtener_historial():
    """Obtiene el historial de cambios del usuario actual

    Query params:
        - tabla: Filtrar por tabla (opcional)
        - registro_id: Filtrar por registro específico (opcional)
        - limite: Cantidad máxima (default: 50, max: 200)
    """
    tabla = request.args.get('tabla')
    registro_id = request.args.get('registro_id', type=int)
    limite = request.args.get('limite', 50, type=int)
    limite = min(limite, 200)  # Máximo 200 registros

    cambios = ServicioAuditoria.obtener_historial(
        usuario_id=current_user.id,
        tabla=tabla,
        registro_id=registro_id,
        limite=limite
    )

    return jsonify({
        'total': len(cambios),
        'cambios': [ServicioAuditoria.serializar_cambio(c) for c in cambios]
    })


@auditoria.route('/rango_fechas')
@login_required
def obtener_cambios_fecha():
    """Obtiene cambios en un rango de fechas

    Query params:
        - desde: Fecha inicio (YYYY-MM-DD)
        - hasta: Fecha fin (YYYY-MM-DD)
        - tabla: Filtrar por tabla (opcional)
    """
    desde_str = request.args.get('desde')
    hasta_str = request.args.get('hasta')
    tabla = request.args.get('tabla')

    if not desde_str or not hasta_str:
        return jsonify({'error': 'Se requieren parámetros "desde" y "hasta"'}), 400

    try:
        desde = datetime.strptime(desde_str, '%Y-%m-%d')
        hasta = datetime.strptime(hasta_str, '%Y-%m-%d') + timedelta(days=1)
    except ValueError:
        return jsonify({'error': 'Formato de fecha inválido (use YYYY-MM-DD)'}), 400

    cambios = ServicioAuditoria.obtener_cambios_fecha(
        usuario_id=current_user.id,
        desde=desde,
        hasta=hasta,
        tabla=tabla
    )

    return jsonify({
        'desde': desde_str,
        'hasta': hasta_str,
        'total': len(cambios),
        'cambios': [ServicioAuditoria.serializar_cambio(c) for c in cambios]
    })


@auditoria.route('/por_accion/<accion>')
@login_required
def obtener_por_accion(accion):
    """Obtiene cambios filtrados por acción

    Path params:
        - accion: CREATE, UPDATE, DELETE, READ

    Query params:
        - tabla: Filtrar por tabla (opcional)
        - limite: Cantidad máxima (default: 50, max: 200)
    """
    acciones_validas = ['CREATE', 'UPDATE', 'DELETE', 'READ']
    if accion.upper() not in acciones_validas:
        return jsonify({'error': f'Acción inválida. Válidas: {acciones_validas}'}), 400

    tabla = request.args.get('tabla')
    limite = request.args.get('limite', 50, type=int)
    limite = min(limite, 200)

    cambios = ServicioAuditoria.obtener_cambios_por_accion(
        usuario_id=current_user.id,
        accion=accion,
        tabla=tabla,
        limite=limite
    )

    return jsonify({
        'accion': accion.upper(),
        'total': len(cambios),
        'cambios': [ServicioAuditoria.serializar_cambio(c) for c in cambios]
    })


@auditoria.route('/resumen')
@login_required
def obtener_resumen():
    """Obtiene resumen de auditoría del usuario (últimos 30 días)"""
    hace_30_dias = datetime.utcnow() - timedelta(days=30)

    cambios = ServicioAuditoria.obtener_cambios_fecha(
        usuario_id=current_user.id,
        desde=hace_30_dias,
        hasta=datetime.utcnow()
    )

    # Contar por acción y tabla
    resumen_acciones = {}
    resumen_tablas = {}

    for cambio in cambios:
        # Por acción
        resumen_acciones[cambio.accion] = resumen_acciones.get(cambio.accion, 0) + 1
        # Por tabla
        resumen_tablas[cambio.tabla] = resumen_tablas.get(cambio.tabla, 0) + 1

    return jsonify({
        'periodo': '30 últimos días',
        'total_cambios': len(cambios),
        'por_accion': resumen_acciones,
        'por_tabla': resumen_tablas,
        'cambios_recientes': [ServicioAuditoria.serializar_cambio(c) for c in cambios[:10]]
    })
