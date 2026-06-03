"""
Tests para validar IVA agrupado por tarifa (CRÍTICO para SRI)
Formulario 104 requiere desglose por: 0%, 5%, 12%, 15%
"""
import pytest
from services.validaciones_sri import ValidacionesSRI


class TestIVATarifas:
    """Tests para agrupación de IVA por tarifa"""

    def test_agrupar_iva_simple_tarifa_unica(self):
        """Un solo producto con tarifa 12%"""
        productos = [
            {'tarifa': '12', 'base_iva': 100, 'iva': 12}
        ]
        resultado = ValidacionesSRI.agrupar_iva_por_tarifa(productos)

        assert resultado['12']['base'] == 100
        assert resultado['12']['iva'] == 12
        assert resultado['0']['iva'] == 0
        assert resultado['5']['iva'] == 0
        assert resultado['15']['iva'] == 0

    def test_agrupar_iva_multiples_tarifas(self):
        """Múltiples productos con diferentes tarifas"""
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

    def test_agrupar_iva_suma_correcta_misma_tarifa(self):
        """Múltiples productos con MISMA tarifa se suman correctamente"""
        productos = [
            {'tarifa': '12', 'base_iva': 100, 'iva': 12},
            {'tarifa': '12', 'base_iva': 200, 'iva': 24},
            {'tarifa': '12', 'base_iva': 300, 'iva': 36},
        ]
        resultado = ValidacionesSRI.agrupar_iva_por_tarifa(productos)

        assert resultado['12']['base'] == 600
        assert resultado['12']['iva'] == 72

    def test_agrupar_iva_tarifa_mixta_comun(self):
        """Caso real: mezcla de tarifas comunes"""
        productos = [
            # Alimentos (0%)
            {'tarifa': '0', 'base_iva': 500, 'iva': 0},
            # Servicios varios (5%)
            {'tarifa': '5', 'base_iva': 200, 'iva': 10},
            # Electrónica (12%)
            {'tarifa': '12', 'base_iva': 1000, 'iva': 120},
            # Lujos (15%)
            {'tarifa': '15', 'base_iva': 300, 'iva': 45},
        ]
        resultado = ValidacionesSRI.agrupar_iva_por_tarifa(productos)

        # Validar suma total correcta
        total_base = (500 + 200 + 1000 + 300)
        total_iva = (0 + 10 + 120 + 45)

        suma_base = sum(resultado[t]['base'] for t in resultado)
        suma_iva = sum(resultado[t]['iva'] for t in resultado)

        assert suma_base == total_base
        assert suma_iva == total_iva

    def test_agrupar_iva_redondeo_a_2_decimales(self):
        """IVA debe redondearse a 2 decimales"""
        productos = [
            {'tarifa': '12', 'base_iva': 100.556, 'iva': 12.067},
        ]
        resultado = ValidacionesSRI.agrupar_iva_por_tarifa(productos)

        assert resultado['12']['base'] == 100.56
        assert resultado['12']['iva'] == 12.07

    def test_agrupar_iva_productos_sin_tarifa_defaultean_a_12(self):
        """Productos sin tarifa especificada usan 12% por default"""
        productos = [
            {'base_iva': 100, 'iva': 12},  # Sin tarifa
            {'tarifa': '', 'base_iva': 100, 'iva': 12},  # Tarifa vacía
            {'tarifa': None, 'base_iva': 100, 'iva': 12},  # Tarifa None
        ]
        resultado = ValidacionesSRI.agrupar_iva_por_tarifa(productos)

        # Todos van a 12% por defecto
        assert resultado['12']['base'] == 300
        assert resultado['12']['iva'] == 36

    def test_agrupar_iva_lista_vacia(self):
        """Lista vacía de productos retorna ceros"""
        resultado = ValidacionesSRI.agrupar_iva_por_tarifa([])

        assert resultado['0']['base'] == 0
        assert resultado['0']['iva'] == 0
        assert resultado['5']['base'] == 0
        assert resultado['5']['iva'] == 0
        assert resultado['12']['base'] == 0
        assert resultado['12']['iva'] == 0
        assert resultado['15']['base'] == 0
        assert resultado['15']['iva'] == 0

    def test_agrupar_iva_estructura_correcta(self):
        """Resultado tiene estructura correcta con 4 tarifas"""
        resultado = ValidacionesSRI.agrupar_iva_por_tarifa([])

        assert '0' in resultado
        assert '5' in resultado
        assert '12' in resultado
        assert '15' in resultado

        for tarifa in resultado:
            assert 'base' in resultado[tarifa]
            assert 'iva' in resultado[tarifa]

    def test_agrupar_iva_con_valores_faltantes(self):
        """Producto sin base_iva o iva usan 0"""
        productos = [
            {'tarifa': '12', 'base_iva': 100},  # Sin 'iva'
            {'tarifa': '12', 'iva': 12},  # Sin 'base_iva'
            {'tarifa': '12'},  # Sin ambos
        ]
        resultado = ValidacionesSRI.agrupar_iva_por_tarifa(productos)

        # Debe manejarlo sin error
        assert resultado['12']['base'] == 100
        assert resultado['12']['iva'] == 12

    def test_agrupar_iva_valores_negativos_no_ocurren(self):
        """Valores negativos se tratan como 0"""
        productos = [
            {'tarifa': '12', 'base_iva': 100, 'iva': 12},
            {'tarifa': '12', 'base_iva': -50, 'iva': -6},  # Negativo (descuento)
        ]
        resultado = ValidacionesSRI.agrupar_iva_por_tarifa(productos)

        # Suma algebraica
        assert resultado['12']['base'] == 50
        assert resultado['12']['iva'] == 6

    def test_agrupar_iva_formador_104_sri(self):
        """Simular desglose para Formulario 104 SRI"""
        # Facturas reales
        facturas = [
            # Factura 1: Alimentos 0% + Servicios 12%
            {'tarifa': '0', 'base_iva': 1000, 'iva': 0},
            {'tarifa': '12', 'base_iva': 500, 'iva': 60},
            # Factura 2: Todo a 15%
            {'tarifa': '15', 'base_iva': 2000, 'iva': 300},
        ]

        resultado = ValidacionesSRI.agrupar_iva_por_tarifa(facturas)

        # Lo que SRI espera en Formulario 104:
        # Línea 200: Base imponible tasa 0% = 1000, IVA 0% = 0
        # Línea 300: Base imponible tasa 12% = 500, IVA 12% = 60
        # Línea 400: Base imponible tasa 15% = 2000, IVA 15% = 300

        assert resultado['0']['base'] == 1000
        assert resultado['0']['iva'] == 0
        assert resultado['12']['base'] == 500
        assert resultado['12']['iva'] == 60
        assert resultado['15']['base'] == 2000
        assert resultado['15']['iva'] == 300


class TestCreditoTributarioIVA:
    """Tests para cálculo de crédito tributario IVA"""

    def test_credito_iva_pagado_mayor_que_cobrado(self):
        """IVA pagado > IVA cobrado = crédito positivo"""
        credito = ValidacionesSRI.calcular_credito_tributario_iva(
            iva_pagado_mes=500,
            iva_cobrado_mes=300,
            saldo_anterior=0
        )
        assert credito == 200

    def test_credito_iva_cobrado_mayor_que_pagado(self):
        """IVA cobrado > IVA pagado = debe pagar"""
        credito = ValidacionesSRI.calcular_credito_tributario_iva(
            iva_pagado_mes=300,
            iva_cobrado_mes=500,
            saldo_anterior=0
        )
        assert credito == -200

    def test_credito_iva_con_saldo_anterior(self):
        """Saldo anterior se suma al crédito del mes"""
        credito = ValidacionesSRI.calcular_credito_tributario_iva(
            iva_pagado_mes=500,
            iva_cobrado_mes=300,
            saldo_anterior=100
        )
        assert credito == 300

    def test_credito_iva_saldo_negativo(self):
        """Saldo anterior negativo (deuda) se resta"""
        credito = ValidacionesSRI.calcular_credito_tributario_iva(
            iva_pagado_mes=500,
            iva_cobrado_mes=300,
            saldo_anterior=-100
        )
        assert credito == 100

    def test_credito_iva_iguales(self):
        """IVA pagado = IVA cobrado = sin crédito"""
        credito = ValidacionesSRI.calcular_credito_tributario_iva(
            iva_pagado_mes=500,
            iva_cobrado_mes=500,
            saldo_anterior=0
        )
        assert credito == 0

    def test_credito_iva_redondeo_2_decimales(self):
        """Resultado redondeado a 2 decimales"""
        credito = ValidacionesSRI.calcular_credito_tributario_iva(
            iva_pagado_mes=500.556,
            iva_cobrado_mes=300.444,
            saldo_anterior=0
        )
        assert credito == 200.11  # Redondeado


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
