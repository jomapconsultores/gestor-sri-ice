#!/usr/bin/env python3
"""
Script de prueba para validar el servicio gastos_processor.py
"""

from services.gastos_processor import parse_xml_gasto_completo, serializar_datos_gasto
import json

# XML de ejemplo (válido según estructura del SRI)
XML_EJEMPLO = """<?xml version="1.0" encoding="UTF-8"?>
<factura id="comprobante" version="1.0.0">
    <infoTributaria>
        <ambiente>1</ambiente>
        <tipoEmision>1</tipoEmision>
        <razonSocial>PROVEEDOR EJEMPLO S.A.</razonSocial>
        <ruc>0191234567001</ruc>
        <claveAcceso>1111111111111111111111111111111111111111111111111</claveAcceso>
        <codDoc>01</codDoc>
        <estab>001</estab>
        <ptoEmi>001</ptoEmi>
        <secuencial>000000001</secuencial>
        <dirMatriz>Calle Principal 123</dirMatriz>
    </infoTributaria>
    <infoFactura>
        <fechaEmision>01/06/2024</fechaEmision>
        <dirEstablecimiento>Calle Principal 123</dirEstablecimiento>
        <contribuyenteEspecial></contribuyenteEspecial>
        <obligadoContabilidad>Si</obligadoContabilidad>
        <tipoIdentificacionComprador>05</tipoIdentificacionComprador>
        <razonSocialComprador>CLIENTE EJEMPLO S.A.</razonSocialComprador>
        <identificacionComprador>0193456789001</identificacionComprador>
        <direccionComprador>Avenida Secundaria 456</direccionComprador>
        <totalSinImpuestos>869.57</totalSinImpuestos>
        <totalDescuento>0.00</totalDescuento>
        <totalConImpuestos>
            <totalImpuesto>
                <codigo>2</codigo>
                <codigoPorcentaje>2</codigoPorcentaje>
                <baseImponible>869.57</baseImponible>
                <valor>130.44</valor>
                <tarifa>15</tarifa>
            </totalImpuesto>
        </totalConImpuestos>
        <importeTotal>1000.01</importeTotal>
        <moneda>USD</moneda>
        <pagos>
            <pago>
                <formaPago>19</formaPago>
                <total>1000.01</total>
            </pago>
        </pagos>
    </infoFactura>
    <detalles>
        <detalle>
            <codigoPrincipal>001</codigoPrincipal>
            <descripcion>Servicio de consultoría en impuestos</descripcion>
            <cantidad>1.00</cantidad>
            <precioUnitario>869.57</precioUnitario>
            <descuento>0.00</descuento>
            <precioTotalSinImpuesto>869.57</precioTotalSinImpuesto>
            <impuestos>
                <impuesto>
                    <codigo>2</codigo>
                    <codigoPorcentaje>2</codigoPorcentaje>
                    <baseImponible>869.57</baseImponible>
                    <tarifa>15</tarifa>
                    <valor>130.44</valor>
                </impuesto>
            </impuestos>
        </detalle>
    </detalles>
    <infoAdicional>
        <campoAdicional nombre="email">contacto@proveedor.com</campoAdicional>
    </infoAdicional>
</factura>
"""

def test_parse_xml():
    """Prueba el parseo de un XML"""
    import tempfile
    import os

    # Crear archivo temporal
    with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False, encoding='utf-8') as f:
        f.write(XML_EJEMPLO)
        tmp_path = f.name

    try:
        # Parsear
        datos = parse_xml_gasto_completo(tmp_path)

        if datos is None:
            print("❌ Error: El parseo retornó None")
            return False

        print("✅ Parseo exitoso!")
        print("\nDatos extraídos:")
        print(json.dumps(datos, indent=2, ensure_ascii=False))

        # Probar serialización
        json_auditoria = serializar_datos_gasto(datos)
        print("\n✅ Serialización exitosa!")
        print(f"JSON para notas_auditoria: {json_auditoria}")

        # Validar campos clave
        campos_requeridos = [
            'clave_acceso', 'ruc_emisor', 'nombre_emisor',
            'ruc_comprador', 'nombre_comprador', 'fecha',
            'total', 'base_15', 'iva_15', 'concepto', 'forma_pago'
        ]

        for campo in campos_requeridos:
            if campo not in datos or datos[campo] is None:
                print(f"⚠️  Campo vacío: {campo}")

        return True

    except Exception as e:
        print(f"❌ Error durante la prueba: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        # Limpiar
        try:
            os.remove(tmp_path)
        except:
            pass


def test_compose_iva():
    """Prueba que la composición de IVA se calcule correctamente"""
    print("\n" + "="*60)
    print("Prueba: Composición de IVA")
    print("="*60)

    import tempfile
    import os

    # XML con múltiples porcentajes de IVA
    xml_multi_iva = """<?xml version="1.0" encoding="UTF-8"?>
<factura id="comprobante" version="1.0.0">
    <infoTributaria>
        <ambiente>1</ambiente>
        <tipoEmision>1</tipoEmision>
        <razonSocial>PROVEEDOR MULTI IVA</razonSocial>
        <ruc>0191111111001</ruc>
        <claveAcceso>2222222222222222222222222222222222222222222222222</claveAcceso>
        <codDoc>01</codDoc>
        <estab>001</estab>
        <ptoEmi>001</ptoEmi>
        <secuencial>000000002</secuencial>
        <dirMatriz>Calle Test 789</dirMatriz>
    </infoTributaria>
    <infoFactura>
        <fechaEmision>02/06/2024</fechaEmision>
        <dirEstablecimiento>Calle Test 789</dirEstablecimiento>
        <obligadoContabilidad>Si</obligadoContabilidad>
        <tipoIdentificacionComprador>05</tipoIdentificacionComprador>
        <razonSocialComprador>CLIENTE MULTI</razonSocialComprador>
        <identificacionComprador>0194444444001</identificacionComprador>
        <direccionComprador>Calle Cliente 999</direccionComprador>
        <totalSinImpuestos>1000.00</totalSinImpuestos>
        <totalDescuento>0.00</totalDescuento>
        <totalConImpuestos>
            <totalImpuesto>
                <codigo>2</codigo>
                <codigoPorcentaje>0</codigoPorcentaje>
                <baseImponible>500.00</baseImponible>
                <valor>0.00</valor>
            </totalImpuesto>
            <totalImpuesto>
                <codigo>2</codigo>
                <codigoPorcentaje>5</codigoPorcentaje>
                <baseImponible>200.00</baseImponible>
                <valor>10.00</valor>
            </totalImpuesto>
            <totalImpuesto>
                <codigo>2</codigo>
                <codigoPorcentaje>2</codigoPorcentaje>
                <baseImponible>300.00</baseImponible>
                <valor>45.00</valor>
            </totalImpuesto>
        </totalConImpuestos>
        <importeTotal>1055.00</importeTotal>
        <moneda>USD</moneda>
        <pagos>
            <pago>
                <formaPago>01</formaPago>
                <total>1055.00</total>
            </pago>
        </pagos>
    </infoFactura>
    <detalles>
        <detalle>
            <codigoPrincipal>001</codigoPrincipal>
            <descripcion>Producto 0% IVA</descripcion>
            <cantidad>1.00</cantidad>
            <precioUnitario>500.00</precioUnitario>
            <precioTotalSinImpuesto>500.00</precioTotalSinImpuesto>
            <impuestos>
                <impuesto>
                    <codigo>2</codigo>
                    <codigoPorcentaje>0</codigoPorcentaje>
                    <baseImponible>500.00</baseImponible>
                    <valor>0.00</valor>
                </impuesto>
            </impuestos>
        </detalle>
        <detalle>
            <codigoPrincipal>002</codigoPrincipal>
            <descripcion>Producto 5% IVA</descripcion>
            <cantidad>1.00</cantidad>
            <precioUnitario>200.00</precioUnitario>
            <precioTotalSinImpuesto>200.00</precioTotalSinImpuesto>
            <impuestos>
                <impuesto>
                    <codigo>2</codigo>
                    <codigoPorcentaje>5</codigoPorcentaje>
                    <baseImponible>200.00</baseImponible>
                    <valor>10.00</valor>
                </impuesto>
            </impuestos>
        </detalle>
        <detalle>
            <codigoPrincipal>003</codigoPrincipal>
            <descripcion>Producto 15% IVA</descripcion>
            <cantidad>1.00</cantidad>
            <precioUnitario>300.00</precioUnitario>
            <precioTotalSinImpuesto>300.00</precioTotalSinImpuesto>
            <impuestos>
                <impuesto>
                    <codigo>2</codigo>
                    <codigoPorcentaje>2</codigoPorcentaje>
                    <baseImponible>300.00</baseImponible>
                    <valor>45.00</valor>
                </impuesto>
            </impuestos>
        </detalle>
    </detalles>
</factura>
"""

    with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False, encoding='utf-8') as f:
        f.write(xml_multi_iva)
        tmp_path = f.name

    try:
        datos = parse_xml_gasto_completo(tmp_path)

        if datos is None:
            print("❌ Error: El parseo retornó None")
            return False

        print("✅ Composición de IVA extraída correctamente!")
        print(f"  Base 0%: ${datos['base_0']:.2f}")
        print(f"  Base 5%: ${datos['base_5']:.2f}")
        print(f"  IVA 5%: ${datos['iva_5']:.2f}")
        print(f"  Base 15%: ${datos['base_15']:.2f}")
        print(f"  IVA 15%: ${datos['iva_15']:.2f}")
        print(f"  Total: ${datos['total']:.2f}")

        # Validar
        assert datos['base_0'] == 500.00, f"Base 0% incorrecta: {datos['base_0']}"
        assert datos['base_5'] == 200.00, f"Base 5% incorrecta: {datos['base_5']}"
        assert datos['iva_5'] == 10.00, f"IVA 5% incorrecto: {datos['iva_5']}"
        assert datos['base_15'] == 300.00, f"Base 15% incorrecta: {datos['base_15']}"
        assert datos['iva_15'] == 45.00, f"IVA 15% incorrecto: {datos['iva_15']}"

        print("\n✅ Todos los valores de IVA son correctos!")
        return True

    except AssertionError as e:
        print(f"❌ Validación fallida: {e}")
        return False

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        try:
            os.remove(tmp_path)
        except:
            pass


if __name__ == '__main__':
    print("="*60)
    print("PRUEBAS DEL SERVICIO gastos_processor.py")
    print("="*60)

    resultado1 = test_parse_xml()
    resultado2 = test_compose_iva()

    print("\n" + "="*60)
    if resultado1 and resultado2:
        print("✅ TODAS LAS PRUEBAS PASARON")
    else:
        print("❌ ALGUNAS PRUEBAS FALLARON")
    print("="*60)
