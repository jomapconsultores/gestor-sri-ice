"""
Tests para validaciones tributarias SRI
Pruebas de: IVA, gastos personales, RUC, períodos, importes
"""
import pytest
from datetime import datetime, timedelta
from services.validaciones_sri import ValidacionesSRI, TarifaIVA
from config import Config


class TestValidacionesIVA:
    """Tests para validaciones de IVA"""

    def test_validar_tarifa_iva_valida(self):
        """Tarifa válida debe pasar"""
        assert ValidacionesSRI.validar_tarifa_iva(0.00) == 0.00
        assert ValidacionesSRI.validar_tarifa_iva(0.05) == 0.05
        assert ValidacionesSRI.validar_tarifa_iva(0.12) == 0.12
        assert ValidacionesSRI.validar_tarifa_iva(0.15) == 0.15

    def test_validar_tarifa_iva_invalida(self):
        """Tarifa inválida debe lanzar error"""
        with pytest.raises(ValueError):
            ValidacionesSRI.validar_tarifa_iva(0.20)

    def test_agrupar_iva_por_tarifa(self):
        """Debe agrupar productos por tarifa correctamente"""
        productos = [
            {'tarifa': '0', 'base_iva': 100, 'iva': 0},
            {'tarifa': '5', 'base_iva': 200, 'iva': 10},
            {'tarifa': '12', 'base_iva': 500, 'iva': 60},
            {'tarifa': '15', 'base_iva': 300, 'iva': 45},
        ]

        resultado = ValidacionesSRI.agrupar_iva_por_tarifa(productos)

        assert resultado['0']['base'] == 100
        assert resultado['0']['iva'] == 0
        assert resultado['5']['base'] == 200
        assert resultado['5']['iva'] == 10
        assert resultado['12']['base'] == 500
        assert resultado['12']['iva'] == 60
        assert resultado['15']['base'] == 300
        assert resultado['15']['iva'] == 45

    def test_agrupar_iva_por_tarifa_suma_correcta(self):
        """Debe sumar correctamente productos con misma tarifa"""
        productos = [
            {'tarifa': '12', 'base_iva': 100, 'iva': 12},
            {'tarifa': '12', 'base_iva': 200, 'iva': 24},
        ]

        resultado = ValidacionesSRI.agrupar_iva_por_tarifa(productos)

        assert resultado['12']['base'] == 300
        assert resultado['12']['iva'] == 36

    def test_calcular_credito_tributario_iva(self):
        """Debe calcular crédito tributario correctamente"""
        # Caso 1: IVA pagado > IVA cobrado (crédito positivo)
        credito = ValidacionesSRI.calcular_credito_tributario_iva(
            iva_pagado_mes=500,
            iva_cobrado_mes=300,
            saldo_anterior=0
        )
        assert credito == 200

        # Caso 2: Con saldo anterior
        credito = ValidacionesSRI.calcular_credito_tributario_iva(
            iva_pagado_mes=500,
            iva_cobrado_mes=300,
            saldo_anterior=100
        )
        assert credito == 300

        # Caso 3: IVA cobrado > IVA pagado (debe pagar)
        credito = ValidacionesSRI.calcular_credito_tributario_iva(
            iva_pagado_mes=300,
            iva_cobrado_mes=500,
            saldo_anterior=0
        )
        assert credito == -200


class TestValidacionesGastos:
    """Tests para validaciones de gastos personales"""

    def test_gastos_personales_bajo_limite(self):
        """Gastos personales bajo límite SRI (0 cargas = USD 1,035.47)"""
        gastos = [
            {'categoria': 'ALIMENTACION', 'monto': 500},
            {'categoria': 'EDUCACION', 'monto': 400},
        ]

        resultado = ValidacionesSRI.validar_gasto_personal(gastos, 2026, numero_cargas=0)

        assert resultado['valido'] == True
        assert len(resultado['errores']) == 0
        assert resultado['desglose']['total_personal'] == 900
        assert resultado['desglose']['deducible'] == 900  # 900 < 1035.47

    def test_gastos_personales_sobre_limite(self):
        """Gastos personales > límite SRI 2026 (0 cargas = USD 1,035.47)"""
        gastos = [
            {'categoria': 'ALIMENTACION', 'monto': 1000},
            {'categoria': 'VIVIENDA', 'monto': 800},
        ]

        resultado = ValidacionesSRI.validar_gasto_personal(gastos, 2026, numero_cargas=0)

        # SIEMPRE es válido, solo informativo
        assert resultado['valido'] == True
        assert len(resultado['advertencias']) > 0
        assert 'deducible' in resultado['advertencias'][0].lower()
        # 0 cargas: límite USD 1,035.47
        assert resultado['desglose']['deducible'] == 1035.47
        assert abs(resultado['desglose']['no_deducible'] - 764.53) < 0.01  # 1800 - 1035.47

    def test_gasto_turismo_limite_20_pct(self):
        """Turismo > 20% del total debe advertencia"""
        gastos = [
            {'categoria': 'TURISMO', 'monto': 600},
            {'categoria': 'ALIMENTACION', 'monto': 400},
        ]

        resultado = ValidacionesSRI.validar_gasto_personal(gastos, 2026, numero_cargas=0)

        assert resultado['valido'] == True
        assert len(resultado['advertencias']) > 0
        assert 'turismo' in resultado['advertencias'][0].lower()

    def test_gasto_arte_cultura_limite_10_pct(self):
        """Arte/Cultura > 10% del total debe advertencia"""
        gastos = [
            {'categoria': 'ARTE Y CULTURA', 'monto': 300},
            {'categoria': 'ALIMENTACION', 'monto': 700},
        ]

        resultado = ValidacionesSRI.validar_gasto_personal(gastos, 2026, numero_cargas=0)

        assert resultado['valido'] == True
        assert len(resultado['advertencias']) > 0
        assert 'arte' in resultado['advertencias'][0].lower()


class TestValidacionesRUC:
    """Tests para validación de RUC"""

    def test_ruc_valido(self):
        """RUC válido debe pasar"""
        # RUC real válido de Ecuador
        assert ValidacionesSRI.validar_ruc('1791246600001') == True

    def test_ruc_longitud_incorrecta(self):
        """RUC sin 13 dígitos debe fallar"""
        with pytest.raises(ValueError):
            ValidacionesSRI.validar_ruc('179124660000')  # 12 dígitos

    def test_ruc_con_caracteres_no_numericos(self):
        """RUC con letras debe fallar"""
        with pytest.raises(ValueError):
            ValidacionesSRI.validar_ruc('179124660000A')

    def test_ruc_digito_verificador_incorrecto(self):
        """RUC con dígito verificador incorrecto debe fallar"""
        with pytest.raises(ValueError):
            # Cambiar el último dígito de un RUC válido
            ValidacionesSRI.validar_ruc('1791246600002')


class TestValidacionesPeriodoFiscal:
    """Tests para validación de período fiscal"""

    def test_fecha_valida_actual(self):
        """Fecha actual debe pasar"""
        hoy = datetime.now().date()
        assert ValidacionesSRI.validar_periodo_fiscal(hoy) == True

    def test_fecha_futura_invalida(self):
        """Fecha futura debe fallar"""
        manana = (datetime.now() + timedelta(days=1)).date()
        with pytest.raises(ValueError):
            ValidacionesSRI.validar_periodo_fiscal(manana)

    def test_fecha_prescrita_invalida(self):
        """Fecha > 5 años debe fallar"""
        fecha_prescrita = datetime.now().date() - timedelta(days=Config.PRESCRIPCION_ANOS * 365 + 1)
        with pytest.raises(ValueError):
            ValidacionesSRI.validar_periodo_fiscal(fecha_prescrita)

    def test_fecha_dentro_plazo(self):
        """Fecha dentro de 5 años debe pasar"""
        hace_1_ano = (datetime.now() - timedelta(days=365)).date()
        assert ValidacionesSRI.validar_periodo_fiscal(hace_1_ano) == True

    def test_fecha_string_valida(self):
        """Fecha como string debe parsearse"""
        assert ValidacionesSRI.validar_periodo_fiscal('2025-01-01') == True


class TestValidacionesImporte:
    """Tests para validación de importes"""

    def test_importe_valido_positivo(self):
        """Importe positivo debe pasar"""
        assert ValidacionesSRI.validar_importe(100) == 100.0
        assert ValidacionesSRI.validar_importe(0.01) == 0.01

    def test_importe_negativo_invalido(self):
        """Importe negativo debe fallar"""
        with pytest.raises(ValueError):
            ValidacionesSRI.validar_importe(-100)

    def test_importe_cero_invalido(self):
        """Importe 0 debe fallar con mínimo 0.01"""
        with pytest.raises(ValueError):
            ValidacionesSRI.validar_importe(0, minimo=0.01)

    def test_importe_redondea_a_2_decimales(self):
        """Importe debe redondearse a 2 decimales"""
        assert ValidacionesSRI.validar_importe(100.555) == 100.56
        assert ValidacionesSRI.validar_importe(100.554) == 100.55

    def test_importe_con_maximo(self):
        """Importe excediendo máximo debe fallar"""
        with pytest.raises(ValueError):
            ValidacionesSRI.validar_importe(1000, maximo=500)


class TestValidacionFacturaCompleta:
    """Tests para validación de factura completa"""

    def test_factura_valida_completa(self):
        """Factura completa y válida debe pasar"""
        factura = {
            'clave_acceso': '1234567890123456789012345678901234567890123456789',  # 49 chars
            'ruc_emisor': '1791246600001',
            'numero_factura': '001-001-000000001',
            'fecha_emision': '2025-01-15',
            'importe_total': '100.00',
        }

        resultado = ValidacionesSRI.validar_factura_completa(factura)

        assert resultado['valido'] == True
        assert len(resultado['errores']) == 0

    def test_factura_sin_campo_obligatorio(self):
        """Factura sin campo obligatorio debe fallar"""
        factura = {
            'clave_acceso': '1234567890123456789012345678901234567890123456789',
            'ruc_emisor': '1791246600001',
            # Falta: numero_factura
            'fecha_emision': '2025-01-15',
            'importe_total': '100.00',
        }

        resultado = ValidacionesSRI.validar_factura_completa(factura)

        assert resultado['valido'] == False
        assert any('numero_factura' in err for err in resultado['errores'])

    def test_factura_clave_acceso_longitud_incorrecta(self):
        """Clave de acceso con longitud incorrecta debe fallar"""
        factura = {
            'clave_acceso': '12345678901234567890',  # Menos de 49
            'ruc_emisor': '1791246600001',
            'numero_factura': '001-001-000000001',
            'fecha_emision': '2025-01-15',
            'importe_total': '100.00',
        }

        resultado = ValidacionesSRI.validar_factura_completa(factura)

        assert resultado['valido'] == False
        assert any('clave de acceso' in err.lower() for err in resultado['errores'])


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
