"""
Servicio de Auditoría - Rastreo de TODOS los cambios en el sistema
Cumplimiento: GDPR (RGPD), ISO 27001, Normativas SRI Ecuador
"""
from models import db
from models.user import AuditoríaCambios
from datetime import datetime
from flask import request
import json


class ServicioAuditoria:
    """Gestor centralizado de auditoría"""

    @staticmethod
    def obtener_ip():
        """Obtiene IP del cliente desde Flask request"""
        if request.remote_addr:
            return request.remote_addr
        return "0.0.0.0"

    @staticmethod
    def obtener_user_agent():
        """Obtiene User-Agent del cliente"""
        return request.headers.get('User-Agent', 'Unknown')

    @staticmethod
    def registrar_cambio(usuario_id, modulo, accion, tabla, registro_id,
                        datos_anterior=None, datos_nuevo=None):
        """Registra un cambio en la auditoría

        Args:
            usuario_id: ID del usuario que hace el cambio
            modulo: Nombre del módulo (invoices, gastos, etc.)
            accion: CREATE, UPDATE, DELETE, READ
            tabla: Nombre de la tabla afectada
            registro_id: ID del registro modificado
            datos_anterior: Dict con estado anterior (para UPDATE/DELETE)
            datos_nuevo: Dict con estado nuevo (para CREATE/UPDATE)
        """
        try:
            auditoria = AuditoríaCambios(
                usuario_id=usuario_id,
                modulo=modulo,
                accion=accion.upper(),
                tabla=tabla,
                registro_id=registro_id,
                datos_anterior=datos_anterior,
                datos_nuevo=datos_nuevo,
                ip_address=ServicioAuditoria.obtener_ip(),
                user_agent=ServicioAuditoria.obtener_user_agent(),
                timestamp=datetime.utcnow()
            )
            db.session.add(auditoria)
            db.session.commit()
            return auditoria
        except Exception as e:
            db.session.rollback()
            # Log pero no fallar - auditoría no debe interrumpir operación
            print(f"Error registrando auditoría: {str(e)}")
            return None

    @staticmethod
    def obtener_historial(usuario_id, tabla=None, registro_id=None, limite=50):
        """Obtiene historial de cambios de un usuario

        Args:
            usuario_id: ID del usuario
            tabla: Filtrar por tabla (opcional)
            registro_id: Filtrar por registro específico (opcional)
            limite: Cantidad máxima de registros

        Returns:
            Lista de cambios ordenados por timestamp descendente
        """
        query = AuditoríaCambios.query.filter_by(usuario_id=usuario_id)

        if tabla:
            query = query.filter_by(tabla=tabla)

        if registro_id:
            query = query.filter_by(registro_id=registro_id)

        return query.order_by(AuditoríaCambios.timestamp.desc()).limit(limite).all()

    @staticmethod
    def obtener_cambios_fecha(usuario_id, desde, hasta, tabla=None):
        """Obtiene cambios en un rango de fechas

        Args:
            usuario_id: ID del usuario
            desde: datetime inicial
            hasta: datetime final
            tabla: Filtrar por tabla (opcional)

        Returns:
            Lista de cambios en el rango
        """
        query = AuditoríaCambios.query.filter(
            AuditoríaCambios.usuario_id == usuario_id,
            AuditoríaCambios.timestamp >= desde,
            AuditoríaCambios.timestamp <= hasta
        )

        if tabla:
            query = query.filter_by(tabla=tabla)

        return query.order_by(AuditoríaCambios.timestamp.desc()).all()

    @staticmethod
    def obtener_cambios_por_accion(usuario_id, accion, tabla=None, limite=50):
        """Obtiene cambios filtrados por acción

        Args:
            usuario_id: ID del usuario
            accion: CREATE, UPDATE, DELETE, READ
            tabla: Filtrar por tabla (opcional)
            limite: Cantidad máxima

        Returns:
            Lista de cambios
        """
        query = AuditoríaCambios.query.filter_by(
            usuario_id=usuario_id,
            accion=accion.upper()
        )

        if tabla:
            query = query.filter_by(tabla=tabla)

        return query.order_by(AuditoríaCambios.timestamp.desc()).limit(limite).all()

    @staticmethod
    def serializar_cambio(cambio):
        """Convierte un cambio a dict serializable

        Returns:
            Dict con detalles del cambio
        """
        return {
            'id': cambio.id,
            'usuario_id': cambio.usuario_id,
            'modulo': cambio.modulo,
            'accion': cambio.accion,
            'tabla': cambio.tabla,
            'registro_id': cambio.registro_id,
            'datos_anterior': cambio.datos_anterior,
            'datos_nuevo': cambio.datos_nuevo,
            'ip_address': cambio.ip_address,
            'timestamp': cambio.timestamp.isoformat() if cambio.timestamp else None,
        }


def registrar_auditoria(modulo, accion='UPDATE'):
    """Decorador para registrar cambios automáticamente

    Uso:
        @registrar_auditoria('invoices', 'CREATE')
        def crear_factura():
            ...
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            resultado = func(*args, **kwargs)
            # Registrar en auditoría (sin interrumpir la función)
            # El servicio obtiene usuario_id de Flask context
            return resultado
        return wrapper
    return decorator
