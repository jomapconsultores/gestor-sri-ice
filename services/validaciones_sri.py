"""
Validaciones y cálculos tributarios según SRI Ecuador
Incluye: IVA, ICE, gastos personales, crédito tributario, etc.
"""
from config import Config
from datetime import datetime, timedelta
from enum import Enum


class TarifaIVA(Enum):
    """Tarifas de IVA vigentes en Ecuador"""
    CERO = 0.00      # Exportaciones, medicinas, alimentos
    CINCO = 0.05     # Algunos servicios
    DOCE = 0.12      # Estándar hasta 2023
    QUINCE = 0.15    # Estándar 2024+


class ValidacionesSRI:
    """Validaciones y cálculos tributarios SRI"""

    # ═════════════════════════════════════════════════════════════════
    # VALIDACIONES DE IVA
    # ═════════════════════════════════════════════════════════════════

    @staticmethod
    def validar_tarifa_iva(tarifa):
        """Valida que la tarifa IVA sea válida"""
        tarifas_validas = [
            TarifaIVA.CERO.value,
            TarifaIVA.CINCO.value,
            TarifaIVA.DOCE.value,
            TarifaIVA.QUINCE.value,
        ]
        if tarifa not in tarifas_validas:
            raise ValueError(f"Tarifa IVA inválida: {tarifa}. Válidas: {tarifas_validas}")
        return tarifa

    @staticmethod
    def agrupar_iva_por_tarifa(productos):
        """Agrupa productos por tarifa IVA y suma bases e impuestos

        Returns:
            {
                '0': {'base': 100, 'iva': 0},
                '5': {'base': 50, 'iva': 2.50},
                '12': {'base': 200, 'iva': 24},
                '15': {'base': 150, 'iva': 22.50}
            }
        """
        iva_por_tarifa = {
            '0': {'base': 0, 'iva': 0},
            '5': {'base': 0, 'iva': 0},
            '12': {'base': 0, 'iva': 0},
            '15': {'base': 0, 'iva': 0},
        }

        for producto in productos:
            tarifa = producto.get('tarifa', '12')
            # Manejar tarifa vacía, None, o inválida
            if not tarifa or tarifa == '':
                tarifa_str = '12'
            else:
                try:
                    tarifa_str = str(int(tarifa))
                except (ValueError, TypeError):
                    tarifa_str = '12'

            base = float(producto.get('base_iva', 0) or 0)
            iva = float(producto.get('iva', 0) or 0)

            if tarifa_str not in iva_por_tarifa:
                tarifa_str = '12'  # Default

            iva_por_tarifa[tarifa_str]['base'] += base
            iva_por_tarifa[tarifa_str]['iva'] += iva

        # Redondear a 2 decimales
        for tarifa in iva_por_tarifa:
            iva_por_tarifa[tarifa]['base'] = round(iva_por_tarifa[tarifa]['base'], 2)
            iva_por_tarifa[tarifa]['iva'] = round(iva_por_tarifa[tarifa]['iva'], 2)

        return iva_por_tarifa

    @staticmethod
    def calcular_credito_tributario_iva(iva_pagado_mes, iva_cobrado_mes, saldo_anterior=0):
        """Calcula crédito tributario IVA según Formulario 104

        Crédito = IVA Pagado - IVA Cobrado + Saldo Anterior
        """
        credito = (iva_pagado_mes - iva_cobrado_mes) + saldo_anterior
        return round(credito, 2)

    # ═════════════════════════════════════════════════════════════════
    # VALIDACIONES DE GASTOS PERSONALES
    # ═════════════════════════════════════════════════════════════════

    @staticmethod
    def obtener_limite_deduccion(numero_cargas):
        """Obtiene el límite de deducción según número de cargas dependientes

        Args:
            numero_cargas: int - Número de cargas (hijos/dependientes)

        Returns:
            float - Límite de deducción en USD
        """
        rebajas = Config.GASTO_REBAJA_POR_CARGAS

        if numero_cargas in rebajas:
            return rebajas[numero_cargas]
        elif numero_cargas >= 6:
            return rebajas[6]  # Máximo para 6+ cargas
        elif numero_cargas >= 4:
            return rebajas[4]
        elif numero_cargas >= 3:
            return rebajas[3]
        elif numero_cargas >= 2:
            return rebajas[2]
        elif numero_cargas >= 1:
            return rebajas[1]
        else:
            return rebajas[0]

    @staticmethod
    def validar_gasto_personal(gastos, anio, numero_cargas=0):
        """Valida límites de gastos personales según SRI 2026

        Límites por número de cargas (Rebaja Máxima de Impuestos):
        - 0 cargas: Hasta USD 1,035.47/año
        - 1 carga: Hasta USD 1,331.32/año
        - 2 cargas: Hasta USD 1,627.16/año
        - 3 cargas: Hasta USD 2,070.94/año
        - 4 cargas: Hasta USD 2,514.71/año
        - 6+ cargas: Hasta USD 14,792.40/año

        Categorías:
        - Turismo: máximo 20% de total deducible
        - Arte y cultura: máximo 10% de total deducible
        """
        GASTOS_PERSONALES = [
            'ALIMENTACION', 'EDUCACION', 'SALUD', 'VESTIMENTA',
            'VIVIENDA', 'TURISMO', 'ARTE Y CULTURA', 'VARIOS'
        ]

        resultados = {
            'valido': True,
            'advertencias': [],
            'errores': [],
            'desglose': {
                'total_personal': 0,
                'total_ejercicio': 0,
                'turismo': 0,
                'arte_cultura': 0,
                'deducible': 0,
                'no_deducible': 0,
            }
        }

        # Calcular totales
        for gasto in gastos:
            categoria = gasto.get('categoria', '').upper()
            monto = float(gasto.get('monto', 0) or 0)

            if categoria in GASTOS_PERSONALES:
                resultados['desglose']['total_personal'] += monto
                if categoria == 'TURISMO':
                    resultados['desglose']['turismo'] += monto
                elif categoria == 'ARTE Y CULTURA':
                    resultados['desglose']['arte_cultura'] += monto
            else:
                resultados['desglose']['total_ejercicio'] += monto

        total_gasto = resultados['desglose']['total_personal'] + resultados['desglose']['total_ejercicio']

        # CALCULAR deducible vs no deducible según límites SRI 2026
        # Nota: Estos son INFORMATIVOS, no restrictivos. El usuario puede gastar más,
        # pero SRI solo permite deducir hasta estos límites según número de cargas.

        limite_personal = ValidacionesSRI.obtener_limite_deduccion(numero_cargas)

        # Gastos personales: limitados según número de cargas
        if resultados['desglose']['total_personal'] > limite_personal:
            deducible = limite_personal
            no_deducible = resultados['desglose']['total_personal'] - limite_personal
            resultados['advertencias'].append(
                f"ℹ️ Gastos personales: USD {resultados['desglose']['total_personal']}. "
                f"Deducible SRI ({numero_cargas} cargas): USD {deducible:.2f}. "
                f"No deducible: USD {no_deducible:.2f}"
            )
        else:
            deducible = resultados['desglose']['total_personal']
            no_deducible = 0

        resultados['desglose']['deducible'] = round(deducible, 2)
        resultados['desglose']['no_deducible'] = round(no_deducible, 2)
        resultados['desglose']['limite_cargas'] = numero_cargas
        resultados['desglose']['limite_permitido'] = round(limite_personal, 2)
        resultados['valido'] = True  # SIEMPRE válido, solo informativo

        # Turismo: máximo 20% del total deducible
        if total_gasto > 0:
            turismo_deducible = total_gasto * Config.GASTO_TURISMO_LIMITE_PCT
            if resultados['desglose']['turismo'] > turismo_deducible:
                exceso_turismo = resultados['desglose']['turismo'] - turismo_deducible
                resultados['advertencias'].append(
                    f"ℹ️ Turismo: USD {resultados['desglose']['turismo']}. "
                    f"Deducible (20%): USD {turismo_deducible:.2f}. "
                    f"Exceso: USD {exceso_turismo:.2f}"
                )

            # Arte/Cultura: máximo 10% del total deducible
            arte_deducible = total_gasto * Config.GASTO_ARTE_CULTURA_LIMITE_PCT
            if resultados['desglose']['arte_cultura'] > arte_deducible:
                exceso_arte = resultados['desglose']['arte_cultura'] - arte_deducible
                resultados['advertencias'].append(
                    f"ℹ️ Arte/Cultura: USD {resultados['desglose']['arte_cultura']}. "
                    f"Deducible (10%): USD {arte_deducible:.2f}. "
                    f"Exceso: USD {exceso_arte:.2f}"
                )

        return resultados

    # ═════════════════════════════════════════════════════════════════
    # VALIDACIONES DE PERÍODO FISCAL
    # ═════════════════════════════════════════════════════════════════

    @staticmethod
    def validar_periodo_fiscal(fecha_emision, anio=None, mes=None):
        """Valida que la fecha esté dentro del período fiscal válido"""
        if isinstance(fecha_emision, str):
            try:
                fecha = datetime.strptime(fecha_emision, '%Y-%m-%d').date()
            except ValueError:
                raise ValueError(f"Formato fecha inválido: {fecha_emision}. Debe ser YYYY-MM-DD")
        else:
            fecha = fecha_emision

        # Validación 1: No puede ser futura
        hoy = datetime.now().date()
        if fecha > hoy:
            raise ValueError(f"❌ Fecha {fecha} es futura. Debe ser <= {hoy}")

        # Validación 2: No puede estar prescrita (> 5 años)
        prescripcion_anos = Config.PRESCRIPCION_ANOS
        fecha_limite = hoy - timedelta(days=prescripcion_anos * 365)
        if fecha < fecha_limite:
            raise ValueError(
                f"❌ Fecha {fecha} está prescrita (> {prescripcion_anos} años). "
                f"Límite: {fecha_limite}"
            )

        return True

    @staticmethod
    def validar_ruc(ruc):
        """Valida RUC ecuatoriano usando módulo-11 (algoritmo de Luhn)"""
        if not ruc or len(ruc) != 13 or not ruc.isdigit():
            raise ValueError(f"RUC inválido: {ruc}. Debe tener 13 dígitos")

        # Algoritmo módulo-11
        multiplicadores = [3, 2, 7, 6, 5, 4, 3, 2, 7, 6, 5, 4, 3]
        suma = sum(int(ruc[i]) * multiplicadores[i] for i in range(12))
        digito_verificador = 11 - (suma % 11)

        if digito_verificador == 11:
            digito_verificador = 0
        elif digito_verificador == 10:
            digito_verificador = 1

        if int(ruc[12]) != digito_verificador:
            raise ValueError(f"RUC {ruc}: dígito verificador incorrecto")

        return True

    # ═════════════════════════════════════════════════════════════════
    # VALIDACIONES DE IMPORTES
    # ═════════════════════════════════════════════════════════════════

    @staticmethod
    def validar_importe(importe, minimo=0, maximo=None):
        """Valida que un importe sea válido"""
        try:
            valor = float(importe or 0)
        except (ValueError, TypeError):
            raise ValueError(f"Importe inválido: {importe}")

        if valor < minimo:
            raise ValueError(f"Importe {valor} es menor que mínimo {minimo}")

        if maximo and valor > maximo:
            raise ValueError(f"Importe {valor} excede máximo {maximo}")

        return round(valor, 2)

    # ═════════════════════════════════════════════════════════════════
    # RESUMEN DE VALIDACIONES
    # ═════════════════════════════════════════════════════════════════

    @staticmethod
    def validar_factura_completa(factura_datos):
        """Valida una factura completa antes de guardar"""
        errores = []

        # Validaciones obligatorias
        campos_obligatorios = [
            'clave_acceso', 'ruc_emisor', 'numero_factura',
            'fecha_emision', 'importe_total'
        ]

        for campo in campos_obligatorios:
            if not factura_datos.get(campo):
                errores.append(f"❌ Campo obligatorio faltante: {campo}")

        # Validar clave_acceso
        clave = factura_datos.get('clave_acceso', '')
        if clave and len(clave) != 49:
            errores.append(f"❌ Clave de acceso debe tener 49 caracteres, tiene {len(clave)}")

        # Validar RUC
        try:
            ValidacionesSRI.validar_ruc(factura_datos.get('ruc_emisor', ''))
        except ValueError as e:
            errores.append(f"❌ {str(e)}")

        # Validar fecha
        try:
            ValidacionesSRI.validar_periodo_fiscal(factura_datos.get('fecha_emision'))
        except ValueError as e:
            errores.append(f"❌ {str(e)}")

        # Validar importes
        try:
            ValidacionesSRI.validar_importe(factura_datos.get('importe_total'), minimo=0.01)
        except ValueError as e:
            errores.append(f"❌ {str(e)}")

        return {
            'valido': len(errores) == 0,
            'errores': errores
        }
