"""Servicios para guardar y cargar sesiones de ICE Múltiple."""

from models import db
from models.user import ProductoSesionICE


def guardar_sesion_multiple(usuario_id, productos):
    """
    Guarda el último lote de productos calculados en ICE Múltiple.

    Args:
        usuario_id: ID del usuario
        productos: lista de dicts con los datos del producto
    """
    try:
        ProductoSesionICE.query.filter_by(usuario_id=usuario_id).delete()

        for i, p in enumerate(productos):
            prod = ProductoSesionICE(
                usuario_id=usuario_id,
                nombre=p.get('nombre', f'Producto {i+1}'),
                tipo_producto=p.get('tipo_producto', 'Licor'),
                volumen_cc=p.get('volumen_cc', 750),
                grado_alcoholico=p.get('grado_alcoholico', 35),
                precio_fabrica=p.get('precio_fabrica', 0),
                costos=p.get('costos', 0),
                utilidad=p.get('utilidad', 0),
                cantidad=p.get('cantidad', 1),
                escala=p.get('escala', ''),
                orden=i,
            )
            db.session.add(prod)

        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f'Error guardar_sesion_multiple: {e}')


def cargar_sesion_multiple(usuario_id):
    """
    Carga la última sesión de ICE Múltiple del usuario.

    Args:
        usuario_id: ID del usuario

    Returns:
        lista de dicts con los datos de los productos
    """
    try:
        registros = ProductoSesionICE.query.filter_by(
            usuario_id=usuario_id
        ).order_by(ProductoSesionICE.orden).all()

        return [
            {
                'nombre': r.nombre or f'Producto {r.orden+1}',
                'tipo_producto': r.tipo_producto or 'Licor',
                'volumen_cc': float(r.volumen_cc or 750),
                'grado_alcoholico': float(r.grado_alcoholico or 35),
                'precio_fabrica': float(r.precio_fabrica or 0),
                'costos': float(r.costos or 0),
                'utilidad': float(r.utilidad or 0),
                'cantidad': r.cantidad or 1,
                'escala': r.escala or '',
            }
            for r in registros
        ]
    except Exception as e:
        print(f'Error cargar_sesion_multiple: {e}')
        return []
