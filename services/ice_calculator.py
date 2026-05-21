from datetime import datetime

TAX_DB = {
    "2021": {"esp": 7.18, "art": 1.49, "ind": {"Rango 1: Hasta 730.000 hl": 8.41, "Rango 2: >730k a 1.4M hl": 10.48, "Rango 3: >1.4M hl": 13.08}, "umb": 4.29, "iva": 0.12},
    "2022": {"esp": 10.00, "art": 1.50, "ind": 13.08, "umb": 4.37, "iva": 0.12},
    "2023": {"esp": 10.00, "art": 1.50, "ind": 13.08, "umb": 4.53, "iva": 0.12},
    "2024": {"esp": 10.15, "art": 1.52, "ind": 13.28, "umb": 4.60, "iva": "MIXTO"},
    "2025": {"esp": 10.30, "art": 1.54, "ind": 13.48, "umb": 4.67, "iva": 0.15},
    "2026": {"esp": 10.41, "art": 1.56, "ind": 13.62, "umb": 4.72, "iva": 0.15}
}

class IceCalculator:

    @staticmethod
    def get_tax_info(anio):
        return TAX_DB.get(str(anio), TAX_DB["2026"])

    @staticmethod
    def get_tarifa_especifica(tipo_producto, anio, escala=None):
        info = TAX_DB.get(str(anio), TAX_DB["2026"])
        if "Industrial" in tipo_producto:
            if isinstance(info['ind'], dict):
                return info['ind'].get(escala, 13.08)
            return info['ind']
        elif "Artesanal" in tipo_producto:
            return info['art']
        else:
            return info['esp']

    @staticmethod
    def calcular_ice_especifico(tarifa_esp, grado, volumen_cc):
        return tarifa_esp * (grado / 100.0) * (volumen_cc / 1000.0)

    @staticmethod
    def calcular_ice_advalorem(precio, volumen_cc, umbral):
        precio_litro = (precio * 1000.0) / volumen_cc if volumen_cc > 0 else 0
        if precio_litro > umbral:
            return (precio_litro - umbral) * 0.75 * (volumen_cc / 1000.0)
        return 0.0

    @staticmethod
    def calcular_liquidacion_completa(datos, anio, iva_tasa=None):
        info = IceCalculator.get_tax_info(anio)
        tarifa_esp = IceCalculator.get_tarifa_especifica(datos.get('tipo_producto', 'Licor'), anio, datos.get('escala'))
        if iva_tasa is None:
            iva_tasa = 0.15 if isinstance(info['iva'], str) else info['iva']
        cantidad = datos.get('cantidad', 1)
        precio = datos['precio_fabrica']
        vol = datos['volumen_cc']
        grado = datos['grado_alcoholico']
        umb = info['umb']
        ice_esp_u = IceCalculator.calcular_ice_especifico(tarifa_esp, grado, vol)
        ice_adv_u = IceCalculator.calcular_ice_advalorem(precio, vol, umb)
        ice_esp_t = ice_esp_u * cantidad
        ice_adv_t = ice_adv_u * cantidad
        ice_t = ice_esp_t + ice_adv_t
        base_iva = (precio * cantidad) + ice_t
        iva_t = base_iva * iva_tasa
        pvp = base_iva + iva_t
        return {
            'anio': anio, 'tarifa_especifica': round(tarifa_esp, 4),
            'umbral_advalorem': umb, 'iva_tasa': iva_tasa,
            'precio_fabrica_unitario': precio, 'volumen_cc': vol,
            'grado_alcoholico': grado, 'cantidad': cantidad,
            'ice_especifico_unitario': round(ice_esp_u, 4),
            'ice_advalorem_unitario': round(ice_adv_u, 4),
            'ice_total_unitario': round(ice_esp_u + ice_adv_u, 4),
            'ice_especifico_total': round(ice_esp_t, 2),
            'ice_advalorem_total': round(ice_adv_t, 2),
            'ice_total': round(ice_t, 2),
            'base_iva': round(base_iva, 2),
            'iva_total': round(iva_t, 2),
            'pvp': round(pvp, 2)
        }

    @staticmethod
    def generar_comparativa(datos, anios):
        return {a: IceCalculator.calcular_liquidacion_completa(datos, a) for a in anios}