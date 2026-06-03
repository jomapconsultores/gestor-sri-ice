"""
Tests para validar límites de gastos personales según SRI 2026
Límites dependen del número de cargas (Rebaja Máxima de Impuestos)
"""
import pytest
from services.validaciones_sri import ValidacionesSRI


class TestGastosPersonalesLimites:
    """Tests para límites de gastos personales SRI 2026"""

    def test_gastos_bajo_limite(self):
        """Gastos personales por debajo del límite (0 cargas = USD 1,035.47)"""
        gastos = [
            {'categoria': 'ALIMENTACION', 'monto': 500},
            {'categoria': 'EDUCACION', 'monto': 400},
        ]
        resultado = ValidacionesSRI.validar_gasto_personal(gastos, 2026, numero_cargas=0)

        assert resultado['valido'] == True
        assert len(resultado['errores']) == 0
        assert resultado['desglose']['total_personal'] == 900
        assert resultado['desglose']['deducible'] == 900  # 900 < 1,035.47

    def test_gastos_exactamente_limite(self):
        """Gastos exactamente en el límite SRI (0 cargas)"""
        gastos = [
            {'categoria': 'ALIMENTACION', 'monto': 1035.47},
        ]
        resultado = ValidacionesSRI.validar_gasto_personal(gastos, 2026, numero_cargas=0)

        assert resultado['valido'] == True
        assert len(resultado['errores']) == 0
        assert resultado['desglose']['deducible'] == 1035.47

    def test_gastos_sobre_limite(self):
        """Gastos personales sobre límite SRI - Sistema calcula deducible"""
        gastos = [
            {'categoria': 'ALIMENTACION', 'monto': 1000},
            {'categoria': 'EDUCACION', 'monto': 800},
        ]
        resultado = ValidacionesSRI.validar_gasto_personal(gastos, 2026, numero_cargas=0)

        assert resultado['valido'] == True
        assert len(resultado['advertencias']) > 0
        assert 'deducible' in resultado['advertencias'][0].lower()
        assert resultado['desglose']['deducible'] == 1035.47  # Máximo para 0 cargas
        assert abs(resultado['desglose']['no_deducible'] - 764.53) < 0.01  # 1800 - 1035.47

    def test_gastos_ejercicio_sin_limite(self):
        """Gastos de ejercicio (no personales) sin límite"""
        gastos = [
            {'categoria': 'SERVICIOS PROFESIONALES', 'monto': 5000},
            {'categoria': 'MANTENIMIENTO', 'monto': 3000},
        ]
        resultado = ValidacionesSRI.validar_gasto_personal(gastos, 2026, numero_cargas=0)

        assert resultado['valido'] == True
        assert len(resultado['errores']) == 0

    def test_turismo_20_pct_limite(self):
        """Turismo > 20% - Sistema muestra información"""
        gastos = [
            {'categoria': 'TURISMO', 'monto': 300},
            {'categoria': 'ALIMENTACION', 'monto': 700},
        ]
        resultado = ValidacionesSRI.validar_gasto_personal(gastos, 2026, numero_cargas=0)

        assert resultado['valido'] == True
        assert len(resultado['advertencias']) > 0
        assert 'turismo' in resultado['advertencias'][0].lower()

    def test_turismo_exactamente_20_pct(self):
        """Turismo exactamente 20% es válido"""
        gastos = [
            {'categoria': 'TURISMO', 'monto': 200},
            {'categoria': 'ALIMENTACION', 'monto': 800},
        ]
        resultado = ValidacionesSRI.validar_gasto_personal(gastos, 2026, numero_cargas=0)

        assert resultado['valido'] == True
        assert len(resultado['advertencias']) == 0

    def test_arte_cultura_10_pct_limite(self):
        """Arte/Cultura > 10% genera advertencia"""
        gastos = [
            {'categoria': 'ARTE Y CULTURA', 'monto': 150},
            {'categoria': 'ALIMENTACION', 'monto': 850},
        ]
        resultado = ValidacionesSRI.validar_gasto_personal(gastos, 2026, numero_cargas=0)

        assert resultado['valido'] == True
        assert len(resultado['advertencias']) > 0
        assert 'arte' in resultado['advertencias'][0].lower()

    def test_arte_cultura_exactamente_10_pct(self):
        """Arte/Cultura exactamente 10% es válido"""
        gastos = [
            {'categoria': 'ARTE Y CULTURA', 'monto': 100},
            {'categoria': 'ALIMENTACION', 'monto': 900},
        ]
        resultado = ValidacionesSRI.validar_gasto_personal(gastos, 2026, numero_cargas=0)

        assert resultado['valido'] == True
        assert len(resultado['advertencias']) == 0

    def test_multiples_advertencias(self):
        """Turismo + Arte/Cultura simultáneamente sobre límite"""
        gastos = [
            {'categoria': 'TURISMO', 'monto': 300},
            {'categoria': 'ARTE Y CULTURA', 'monto': 200},
            {'categoria': 'ALIMENTACION', 'monto': 500},
        ]
        resultado = ValidacionesSRI.validar_gasto_personal(gastos, 2026, numero_cargas=0)

        assert resultado['valido'] == True
        assert len(resultado['advertencias']) >= 2

    def test_desglose_completo(self):
        """Desglose tiene todos los campos requeridos"""
        gastos = [
            {'categoria': 'ALIMENTACION', 'monto': 500},
            {'categoria': 'SERVICIOS', 'monto': 1000},
        ]
        resultado = ValidacionesSRI.validar_gasto_personal(gastos, 2026, numero_cargas=0)

        desglose = resultado['desglose']
        assert 'total_personal' in desglose
        assert 'total_ejercicio' in desglose
        assert 'turismo' in desglose
        assert 'arte_cultura' in desglose
        assert 'deducible' in desglose
        assert 'no_deducible' in desglose
        assert 'limite_cargas' in desglose
        assert 'limite_permitido' in desglose

    def test_gastos_vacio(self):
        """Lista vacía de gastos es válida"""
        resultado = ValidacionesSRI.validar_gasto_personal([], 2026)

        assert resultado['valido'] == True
        assert resultado['desglose']['total_personal'] == 0

    def test_gastos_mixtos_personal_ejercicio(self):
        """Mezcla de gastos personales y de ejercicio"""
        gastos = [
            {'categoria': 'ALIMENTACION', 'monto': 600},
            {'categoria': 'EDUCACION', 'monto': 400},
            {'categoria': 'SERVICIOS PROFESIONALES', 'monto': 2000},
            {'categoria': 'MANTENIMIENTO', 'monto': 500},
        ]
        resultado = ValidacionesSRI.validar_gasto_personal(gastos, 2026, numero_cargas=0)

        assert resultado['valido'] == True
        assert resultado['desglose']['total_personal'] == 1000
        assert resultado['desglose']['total_ejercicio'] == 2500

    def test_categoria_variantes_minusculas(self):
        """Categorías en minúsculas se reconocen"""
        gastos = [
            {'categoria': 'alimentacion', 'monto': 500},
            {'categoria': 'EDUCACION', 'monto': 400},
        ]
        resultado = ValidacionesSRI.validar_gasto_personal(gastos, 2026, numero_cargas=0)

        assert resultado['desglose']['total_personal'] == 900

    def test_limites_por_cargas(self):
        """Verificar que los límites cambian según número de cargas"""
        gastos = [
            {'categoria': 'ALIMENTACION', 'monto': 1500},
        ]

        # 0 cargas: USD 1,035.47
        resultado_0 = ValidacionesSRI.validar_gasto_personal(gastos, 2026, numero_cargas=0)
        assert resultado_0['desglose']['deducible'] == 1035.47

        # 1 carga: USD 1,331.32
        resultado_1 = ValidacionesSRI.validar_gasto_personal(gastos, 2026, numero_cargas=1)
        assert resultado_1['desglose']['deducible'] == 1331.32

        # 2 cargas: USD 1,627.16
        resultado_2 = ValidacionesSRI.validar_gasto_personal(gastos, 2026, numero_cargas=2)
        assert resultado_2['desglose']['deducible'] == 1500  # Todo se deduce

        # 3 cargas: USD 2,070.94
        resultado_3 = ValidacionesSRI.validar_gasto_personal(gastos, 2026, numero_cargas=3)
        assert resultado_3['desglose']['deducible'] == 1500

    def test_caso_real_gasto_excesivo(self):
        """Caso real: gasto personal excede límite"""
        gastos = [
            {'categoria': 'ALIMENTACION', 'monto': 800},
            {'categoria': 'TURISMO', 'monto': 400},
            {'categoria': 'EDUCACION', 'monto': 500},
        ]
        resultado = ValidacionesSRI.validar_gasto_personal(gastos, 2026, numero_cargas=0)

        assert resultado['valido'] == True
        assert len(resultado['advertencias']) >= 1
        assert resultado['desglose']['deducible'] == 1035.47
        assert abs(resultado['desglose']['no_deducible'] - 664.53) < 0.01


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
