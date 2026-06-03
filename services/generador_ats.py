"""
Generador ATS - Archivo Técnico Tributario
Formato: Archivo plano SRI Ecuador
Período: Mensual
"""
from models import db
from models.user import Factura, Usuario
from datetime import datetime
from sqlalchemy import extract
import hashlib
import json


class GeneradorATS:
    """Generador del ATS (Archivo Técnico Tributario) SRI"""

    # Formato SRI: campos en posiciones fijas
    CAMPOS_CABECERA = [
        ('ruc', 13),
        ('periodo', 6),
        ('secuencial', 9),
        ('codigo_documento', 2),
        ('tipo_ambiente', 1),
    ]

    @staticmethod
    def calcular_checksum(linea):
        """Calcula checksum MD5 de una línea

        Args:
            linea: Línea del archivo

        Returns:
            String con checksum en hexadecimal
        """
        return hashlib.md5(linea.encode()).hexdigest()[:15]

    @staticmethod
    def formatear_campo(valor, longitud, alineacion='D'):
        """Formatea un campo al tamaño requerido

        Args:
            valor: Valor a formatear
            longitud: Longitud requerida
            alineacion: 'D' (derecha, rellenado con 0), 'I' (izquierda)

        Returns:
            String formateado
        """
        valor_str = str(valor)
        if alineacion == 'D':
            return valor_str.rjust(longitud, '0')
        else:
            return valor_str.ljust(longitud)[:longitud]

    @staticmethod
    def obtener_datos_ats(usuario_id, anio, mes):
        """Obtiene datos para generar ATS

        Args:
            usuario_id: ID del usuario
            anio: Año fiscal
            mes: Mes fiscal (1-12)

        Returns:
            Dict con datos del ATS
        """
        usuario = Usuario.query.get(usuario_id)
        if not usuario:
            raise ValueError(f"Usuario {usuario_id} no encontrado")

        # Obtener todas las facturas del período
        facturas = Factura.query.filter(
            Factura.usuario_id == usuario_id,
            extract('year', Factura.fecha_emision) == anio,
            extract('month', Factura.fecha_emision) == mes,
        ).order_by(Factura.fecha_emision).all()

        # Procesar facturas
        registros = []
        total_ingresos = 0
        total_gastos = 0
        total_iva = 0

        for idx, factura in enumerate(facturas, 1):
            base_iva = float(factura.base_iva or 0)
            valor_iva = float(factura.valor_iva or 0)

            # Determinar tipo según si es ingreso o gasto
            if factura.tipo == 'ingreso':
                tipo_ats = '01'  # Venta
                total_ingresos += base_iva
            else:
                tipo_ats = '02'  # Compra
                total_gastos += base_iva

            total_iva += valor_iva

            registros.append({
                'secuencial': idx,
                'fecha': factura.fecha_emision,
                'numero_factura': factura.numero_factura,
                'ruc_contraparte': factura.ruc_proveedor or '9999999999999',
                'tipo': tipo_ats,
                'base_imponible': base_iva,
                'valor_iva': valor_iva,
                'descuento': 0,
                'importe_total': base_iva + valor_iva,
            })

        return {
            'usuario': {
                'ruc': usuario.ruc,
                'nombre': usuario.nombre,
                'empresa': usuario.empresa,
            },
            'periodo': {
                'anio': anio,
                'mes': f"{mes:02d}",
                'fecha_generacion': datetime.now().isoformat(),
            },
            'resumen': {
                'total_ingresos': total_ingresos,
                'total_gastos': total_gastos,
                'total_iva': total_iva,
                'total_registros': len(registros),
            },
            'registros': registros,
        }

    @staticmethod
    def generar_archivo_plano(usuario_id, anio, mes):
        """Genera ATS en formato archivo plano SRI

        Returns:
            String con contenido del archivo plano
        """
        datos = GeneradorATS.obtener_datos_ats(usuario_id, anio, mes)

        lineas = []

        # CABECERA DEL ATS
        cabecera = (
            GeneradorATS.formatear_campo(datos['usuario']['ruc'], 13) +
            GeneradorATS.formatear_campo(f"{datos['periodo']['anio']}{datos['periodo']['mes']}", 6) +
            GeneradorATS.formatear_campo('1', 2) +  # Versión
            GeneradorATS.formatear_campo('ATS', 3) +
            GeneradorATS.formatear_campo(datos['resumen']['total_registros'], 9) +
            GeneradorATS.formatear_campo(int(datos['resumen']['total_iva'] * 100), 18) +
            GeneradorATS.formatear_campo('1', 1)  # Producción
        )
        lineas.append(cabecera)

        # REGISTROS DE TRANSACCIONES
        for registro in datos['registros']:
            fecha_str = registro['fecha'].strftime('%d%m%Y') if registro['fecha'] else '01010000'

            linea = (
                GeneradorATS.formatear_campo(registro['secuencial'], 9) +
                GeneradorATS.formatear_campo(fecha_str, 8) +
                GeneradorATS.formatear_campo(
                    registro['numero_factura'][:17], 17, 'I'
                ) +
                GeneradorATS.formatear_campo(registro['ruc_contraparte'], 13) +
                GeneradorATS.formatear_campo(registro['tipo'], 2) +
                GeneradorATS.formatear_campo(
                    int(registro['base_imponible'] * 100), 18
                ) +
                GeneradorATS.formatear_campo(
                    int(registro['valor_iva'] * 100), 12
                ) +
                GeneradorATS.formatear_campo('0', 2) +  # Descuento
                GeneradorATS.formatear_campo(
                    int(registro['importe_total'] * 100), 18
                )
            )

            # Agregar checksum
            checksum = GeneradorATS.calcular_checksum(linea)
            linea += checksum

            lineas.append(linea)

        return '\n'.join(lineas)

    @staticmethod
    def generar_json(usuario_id, anio, mes):
        """Genera ATS en formato JSON

        Returns:
            Dict con datos del ATS
        """
        datos = GeneradorATS.obtener_datos_ats(usuario_id, anio, mes)
        return {
            'tipo': 'ATS',
            'version': '1.0',
            'usuario': datos['usuario'],
            'periodo': datos['periodo'],
            'resumen': datos['resumen'],
            'registros': [
                {
                    'secuencial': r['secuencial'],
                    'fecha': r['fecha'].isoformat() if r['fecha'] else '',
                    'numero_factura': r['numero_factura'],
                    'ruc_contraparte': r['ruc_contraparte'],
                    'tipo': r['tipo'],
                    'base_imponible': r['base_imponible'],
                    'valor_iva': r['valor_iva'],
                    'importe_total': r['importe_total'],
                }
                for r in datos['registros'][:500]  # Max 500 para JSON
            ]
        }

    @staticmethod
    def generar_xml(usuario_id, anio, mes):
        """Genera ATS en formato XML

        Returns:
            String con XML del ATS
        """
        datos = GeneradorATS.obtener_datos_ats(usuario_id, anio, mes)

        xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<ATS>
    <Encabezado>
        <RUC>{datos['usuario']['ruc']}</RUC>
        <RazonSocial>{datos['usuario']['nombre']}</RazonSocial>
        <Periodo>{datos['periodo']['anio']}-{datos['periodo']['mes']}</Periodo>
        <FechaGeneracion>{datos['periodo']['fecha_generacion']}</FechaGeneracion>
    </Encabezado>
    <Resumen>
        <TotalIngresos>{datos['resumen']['total_ingresos']:.2f}</TotalIngresos>
        <TotalGastos>{datos['resumen']['total_gastos']:.2f}</TotalGastos>
        <TotalIVA>{datos['resumen']['total_iva']:.2f}</TotalIVA>
        <TotalRegistros>{datos['resumen']['total_registros']}</TotalRegistros>
    </Resumen>
    <Transacciones>
"""
        for registro in datos['registros'][:1000]:
            xml += f"""        <Transaccion>
            <Secuencial>{registro['secuencial']}</Secuencial>
            <Fecha>{registro['fecha'].isoformat() if registro['fecha'] else ''}</Fecha>
            <NumeroFactura>{registro['numero_factura']}</NumeroFactura>
            <RUCContraparte>{registro['ruc_contraparte']}</RUCContraparte>
            <Tipo>{registro['tipo']}</Tipo>
            <BaseImponible>{registro['base_imponible']:.2f}</BaseImponible>
            <ValorIVA>{registro['valor_iva']:.2f}</ValorIVA>
            <ImporteTotal>{registro['importe_total']:.2f}</ImporteTotal>
        </Transaccion>
"""
        xml += """    </Transacciones>
</ATS>
"""
        return xml
