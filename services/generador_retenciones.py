"""
Generador de Certificados de Retención
Formato: SRI Ecuador
Período: Mensual
"""
from models import db
from models.user import Factura, Usuario
from datetime import datetime
from sqlalchemy import extract
import json


class GeneradorRetenciones:
    """Generador de Certificados de Retención SRI"""

    # Tipos de retención según SRI
    TIPOS_RETENCION = {
        'renta': {'nombre': 'Retención en la Renta', 'codigo': '01', 'porcentaje': 1.0},
        'iva': {'nombre': 'Retención IVA', 'codigo': '02', 'porcentaje': 30.0},
        'iva_100': {'nombre': 'Retención IVA 100%', 'codigo': '03', 'porcentaje': 100.0},
        'otro': {'nombre': 'Otra Retención', 'codigo': '04', 'porcentaje': 0.0},
    }

    @staticmethod
    def obtener_datos_retenciones(usuario_id, anio, mes):
        """Obtiene datos de retenciones realizadas

        Args:
            usuario_id: ID del usuario
            anio: Año fiscal
            mes: Mes fiscal (1-12)

        Returns:
            Dict con datos de retenciones
        """
        usuario = Usuario.query.get(usuario_id)
        if not usuario:
            raise ValueError(f"Usuario {usuario_id} no encontrado")

        # Obtener facturas de gasto que pueden tener retención
        facturas = Factura.query.filter(
            Factura.usuario_id == usuario_id,
            Factura.tipo == 'gasto',
            extract('year', Factura.fecha_emision) == anio,
            extract('month', Factura.fecha_emision) == mes,
        ).order_by(Factura.fecha_emision).all()

        # Procesar facturas y calcular retenciones
        retenciones = []
        total_retenido = 0
        total_pagado_sin_retencion = 0

        for idx, factura in enumerate(facturas, 1):
            base_retencion = float(factura.base_iva or 0)
            valor_iva = float(factura.valor_iva or 0)
            total_factura = base_retencion + valor_iva

            # Determinar tipo de retención
            # Por defecto: Retención IVA al 30%
            tipo_retencion = 'iva'
            tasa = GeneradorRetenciones.TIPOS_RETENCION[tipo_retencion]['porcentaje']
            valor_retencion = (valor_iva * tasa) / 100

            if valor_retencion > 0:
                total_retenido += valor_retencion
                total_pagado_sin_retencion += (total_factura - valor_retencion)

                retenciones.append({
                    'secuencial': idx,
                    'fecha': factura.fecha_emision,
                    'numero_comprobante': factura.numero_factura,
                    'ruc_proveedor': factura.ruc_proveedor or '9999999999999',
                    'razon_social': factura.descripcion[:60],
                    'tipo_retencion': tipo_retencion,
                    'codigo_retencion': GeneradorRetenciones.TIPOS_RETENCION[tipo_retencion]['codigo'],
                    'base_imponible': base_retencion,
                    'tasa_retencion': tasa,
                    'valor_iva': valor_iva,
                    'valor_retencion': valor_retencion,
                    'importe_neto': total_factura - valor_retencion,
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
                'total_retenciones': len(retenciones),
                'total_retenido': total_retenido,
                'total_pagado': total_pagado_sin_retencion,
                'total_original': total_retenido + total_pagado_sin_retencion,
            },
            'retenciones': retenciones,
        }

    @staticmethod
    def generar_certificado_html(usuario_id, anio, mes):
        """Genera certificado de retención en HTML

        Returns:
            String con HTML del certificado
        """
        datos = GeneradorRetenciones.obtener_datos_retenciones(usuario_id, anio, mes)

        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Certificado de Retención {datos['periodo']['anio']}/{datos['periodo']['mes']}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ text-align: center; border-bottom: 3px solid #333; padding-bottom: 20px; }}
        .empresa {{ font-weight: bold; font-size: 14px; }}
        .titulo {{ font-size: 16px; font-weight: bold; margin-top: 20px; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
        th {{ background-color: #4472C4; color: white; padding: 8px; text-align: left; }}
        td {{ padding: 8px; border-bottom: 1px solid #ddd; }}
        .total {{ background-color: #E7E6E6; font-weight: bold; }}
        .resumen {{ margin-top: 30px; border: 1px solid #ddd; padding: 15px; }}
    </style>
</head>
<body>
    <div class="header">
        <p class="empresa">{datos['usuario']['empresa']}</p>
        <p>RUC: {datos['usuario']['ruc']}</p>
        <p class="titulo">CERTIFICADO DE RETENCIÓN</p>
        <p>Período: {datos['periodo']['anio']}/{datos['periodo']['mes']}</p>
    </div>

    <table>
        <thead>
            <tr>
                <th>No.</th>
                <th>Fecha</th>
                <th>Comprobante</th>
                <th>RUC Proveedor</th>
                <th>Razón Social</th>
                <th>Base</th>
                <th>Tasa</th>
                <th>Retención</th>
            </tr>
        </thead>
        <tbody>
"""
        for ret in datos['retenciones']:
            html += f"""            <tr>
                <td>{ret['secuencial']}</td>
                <td>{ret['fecha'].strftime('%d/%m/%Y') if ret['fecha'] else ''}</td>
                <td>{ret['numero_comprobante']}</td>
                <td>{ret['ruc_proveedor']}</td>
                <td>{ret['razon_social']}</td>
                <td>${ret['base_imponible']:.2f}</td>
                <td>{ret['tasa_retencion']:.1f}%</td>
                <td>${ret['valor_retencion']:.2f}</td>
            </tr>
"""

        html += f"""            <tr class="total">
                <td colspan="5">TOTAL</td>
                <td>${datos['resumen']['total_original']:.2f}</td>
                <td></td>
                <td>${datos['resumen']['total_retenido']:.2f}</td>
            </tr>
        </tbody>
    </table>

    <div class="resumen">
        <h3>RESUMEN DE RETENCIONES</h3>
        <p><strong>Total Retenciones:</strong> {datos['resumen']['total_retenciones']}</p>
        <p><strong>Total Retenido:</strong> ${datos['resumen']['total_retenido']:.2f}</p>
        <p><strong>Total Pagado (sin retención):</strong> ${datos['resumen']['total_pagado']:.2f}</p>
        <p><strong>Importe Original:</strong> ${datos['resumen']['total_original']:.2f}</p>
    </div>

    <p style="margin-top: 40px; font-size: 12px; color: #666;">
        Generado: {datos['periodo']['fecha_generacion']}<br>
        Este documento es válido como constancia de retención ante el SRI.
    </p>
</body>
</html>
"""
        return html

    @staticmethod
    def generar_json(usuario_id, anio, mes):
        """Genera certificado de retención en JSON

        Returns:
            Dict con datos de retenciones
        """
        datos = GeneradorRetenciones.obtener_datos_retenciones(usuario_id, anio, mes)
        return {
            'tipo': 'Certificado de Retención',
            'version': '1.0',
            'usuario': datos['usuario'],
            'periodo': datos['periodo'],
            'resumen': datos['resumen'],
            'retenciones': [
                {
                    'secuencial': r['secuencial'],
                    'fecha': r['fecha'].isoformat() if r['fecha'] else '',
                    'numero_comprobante': r['numero_comprobante'],
                    'ruc_proveedor': r['ruc_proveedor'],
                    'razon_social': r['razon_social'],
                    'tipo_retencion': r['tipo_retencion'],
                    'base_imponible': r['base_imponible'],
                    'tasa_retencion': r['tasa_retencion'],
                    'valor_retencion': r['valor_retencion'],
                    'importe_neto': r['importe_neto'],
                }
                for r in datos['retenciones']
            ]
        }

    @staticmethod
    def generar_xml(usuario_id, anio, mes):
        """Genera certificado de retención en XML

        Returns:
            String con XML
        """
        datos = GeneradorRetenciones.obtener_datos_retenciones(usuario_id, anio, mes)

        xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<CertificadoRetencion>
    <Encabezado>
        <RUC>{datos['usuario']['ruc']}</RUC>
        <RazonSocial>{datos['usuario']['nombre']}</RazonSocial>
        <Periodo>{datos['periodo']['anio']}-{datos['periodo']['mes']}</Periodo>
        <FechaGeneracion>{datos['periodo']['fecha_generacion']}</FechaGeneracion>
    </Encabezado>
    <Resumen>
        <TotalRetenciones>{datos['resumen']['total_retenciones']}</TotalRetenciones>
        <TotalRetenido>{datos['resumen']['total_retenido']:.2f}</TotalRetenido>
        <TotalPagado>{datos['resumen']['total_pagado']:.2f}</TotalPagado>
        <TotalOriginal>{datos['resumen']['total_original']:.2f}</TotalOriginal>
    </Resumen>
    <Retenciones>
"""
        for ret in datos['retenciones']:
            xml += f"""        <Retencion>
            <Secuencial>{ret['secuencial']}</Secuencial>
            <Fecha>{ret['fecha'].isoformat() if ret['fecha'] else ''}</Fecha>
            <NumeroComprobante>{ret['numero_comprobante']}</NumeroComprobante>
            <RUCProveedor>{ret['ruc_proveedor']}</RUCProveedor>
            <RazonSocial>{ret['razon_social']}</RazonSocial>
            <TipoRetencion>{ret['tipo_retencion']}</TipoRetencion>
            <BaseImponible>{ret['base_imponible']:.2f}</BaseImponible>
            <TasaRetencion>{ret['tasa_retencion']:.1f}</TasaRetencion>
            <ValorRetencion>{ret['valor_retencion']:.2f}</ValorRetencion>
        </Retencion>
"""
        xml += """    </Retenciones>
</CertificadoRetencion>
"""
        return xml
