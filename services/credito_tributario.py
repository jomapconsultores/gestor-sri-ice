"""
Servicio para calcular y rastrear crédito tributario IVA (Formulario 104 SRI)
Cálculo: Saldo = IVA Cobrado (de ventas) - IVA Pagado (de compras) + Saldo Anterior
"""
from models import db
from models.user import Factura, SaldoIVAMes
from services.validaciones_sri import ValidacionesSRI
from datetime import datetime
from sqlalchemy import func, extract


class CreditoTributario:
    """Gestor de crédito tributario IVA mensual"""

    @staticmethod
    def calcular_iva_mes(usuario_id, anio, mes):
        """Calcula IVA cobrado (ventas) y pagado (compras) para un mes específico"""
        # IVA Cobrado (facturas de INGRESO)
        iva_cobrado = db.session.query(
            func.sum(Factura.valor_iva)
        ).filter(
            Factura.usuario_id == usuario_id,
            Factura.tipo == 'ingreso',
            extract('year', Factura.fecha_emision) == anio,
            extract('month', Factura.fecha_emision) == mes
        ).scalar() or 0

        # IVA Pagado (facturas de GASTO)
        iva_pagado = db.session.query(
            func.sum(Factura.valor_iva)
        ).filter(
            Factura.usuario_id == usuario_id,
            Factura.tipo == 'gasto',
            extract('year', Factura.fecha_emision) == anio,
            extract('month', Factura.fecha_emision) == mes
        ).scalar() or 0

        return float(iva_cobrado), float(iva_pagado)

    @staticmethod
    def obtener_saldo_anterior(usuario_id, anio, mes):
        """Obtiene el saldo_final del mes anterior (que es saldo_anterior del mes actual)"""
        if mes == 1:
            # Enero: buscar diciembre del año anterior
            saldo = SaldoIVAMes.query.filter_by(
                usuario_id=usuario_id,
                anio=anio - 1,
                mes=12
            ).first()
        else:
            # Otros meses: buscar mes anterior del mismo año
            saldo = SaldoIVAMes.query.filter_by(
                usuario_id=usuario_id,
                anio=anio,
                mes=mes - 1
            ).first()

        if saldo:
            return float(saldo.saldo_final)
        return 0.0

    @staticmethod
    def calcular_saldo_iva_mes(usuario_id, anio, mes):
        """Calcula el saldo IVA para un mes, actualiza BD y retorna el saldo"""
        # Obtener IVA del mes
        iva_cobrado, iva_pagado = CreditoTributario.calcular_iva_mes(usuario_id, anio, mes)

        # Obtener saldo anterior
        saldo_anterior = CreditoTributario.obtener_saldo_anterior(usuario_id, anio, mes)

        # Calcular saldo final
        saldo_final = ValidacionesSRI.calcular_credito_tributario_iva(
            iva_pagado_mes=iva_pagado,
            iva_cobrado_mes=iva_cobrado,
            saldo_anterior=saldo_anterior
        )

        # Verificar si ya existe registro
        saldo_existente = SaldoIVAMes.query.filter_by(
            usuario_id=usuario_id,
            anio=anio,
            mes=mes
        ).first()

        if saldo_existente:
            # Actualizar
            saldo_existente.iva_cobrado = round(iva_cobrado, 2)
            saldo_existente.iva_pagado = round(iva_pagado, 2)
            saldo_existente.saldo_anterior = round(saldo_anterior, 2)
            saldo_existente.saldo_final = round(saldo_final, 2)
            saldo_existente.fecha_actualizacion = datetime.utcnow()
            db.session.commit()
        else:
            # Crear nuevo
            saldo = SaldoIVAMes(
                usuario_id=usuario_id,
                anio=anio,
                mes=mes,
                iva_cobrado=round(iva_cobrado, 2),
                iva_pagado=round(iva_pagado, 2),
                saldo_anterior=round(saldo_anterior, 2),
                saldo_final=round(saldo_final, 2),
            )
            db.session.add(saldo)
            db.session.commit()

        return {
            'anio': anio,
            'mes': mes,
            'iva_cobrado': round(iva_cobrado, 2),
            'iva_pagado': round(iva_pagado, 2),
            'saldo_anterior': round(saldo_anterior, 2),
            'saldo_final': round(saldo_final, 2),
            'estado': 'Crédito' if saldo_final > 0 else ('Deuda' if saldo_final < 0 else 'Neto'),
        }

    @staticmethod
    def obtener_saldos_anio(usuario_id, anio):
        """Obtiene todos los saldos IVA de un año"""
        saldos = SaldoIVAMes.query.filter_by(
            usuario_id=usuario_id,
            anio=anio
        ).order_by(SaldoIVAMes.mes).all()

        result = []
        for saldo in saldos:
            result.append({
                'mes': saldo.mes,
                'iva_cobrado': float(saldo.iva_cobrado or 0),
                'iva_pagado': float(saldo.iva_pagado or 0),
                'saldo_anterior': float(saldo.saldo_anterior or 0),
                'saldo_final': float(saldo.saldo_final or 0),
                'estado': 'Crédito' if saldo.saldo_final > 0 else ('Deuda' if saldo.saldo_final < 0 else 'Neto'),
            })
        return result

    @staticmethod
    def recalcular_saldos_anio(usuario_id, anio):
        """Recalcula TODOS los saldos del año (útil si hay facturas nuevas)"""
        saldos_recalculados = []
        for mes in range(1, 13):
            saldo = CreditoTributario.calcular_saldo_iva_mes(usuario_id, anio, mes)
            saldos_recalculados.append(saldo)
        return saldos_recalculados

    @staticmethod
    def obtener_resumen_anio(usuario_id, anio):
        """Resumen de todo el año: totales + saldo acumulado final"""
        saldos = CreditoTributario.obtener_saldos_anio(usuario_id, anio)

        if not saldos:
            return None

        total_iva_cobrado = sum(s['iva_cobrado'] for s in saldos)
        total_iva_pagado = sum(s['iva_pagado'] for s in saldos)
        saldo_final = saldos[-1]['saldo_final'] if saldos else 0

        return {
            'anio': anio,
            'total_iva_cobrado': round(total_iva_cobrado, 2),
            'total_iva_pagado': round(total_iva_pagado, 2),
            'saldo_final_anio': round(saldo_final, 2),
            'estado': 'Crédito' if saldo_final > 0 else ('Deuda' if saldo_final < 0 else 'Neto'),
            'meses': saldos,
        }
