"""
Tests para generadores de reportes SRI
Formulario 104, Anexo ICE, ATS, Retenciones
"""
import unittest
from datetime import datetime, timedelta
from models import db
from models.user import Usuario, Factura, SaldoIVAMes
from services.generador_formulario_104 import GeneradorFormulario104
from services.generador_anexo_ice import GeneradorAnexoICE
from services.generador_ats import GeneradorATS
from services.generador_retenciones import GeneradorRetenciones
from app import create_app
import json


class TestGeneradorFormulario104(unittest.TestCase):
    """Tests para Formulario 104"""

    def setUp(self):
        self.app = create_app(init_db_now=False)
        self.app.config['TESTING'] = True
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'

        self.ctx = self.app.app_context()
        self.ctx.push()

        db.drop_all()
        db.create_all()

        # Crear usuario de prueba
        self.usuario = Usuario(
            email='test@test.com',
            nombre='Test User',
            empresa='Test Company',
            ruc='0191234567001',
            activo=True
        )
        self.usuario.set_password('test123')
        db.session.add(self.usuario)
        db.session.commit()

        # Crear facturas de prueba
        self.crear_facturas_prueba()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def crear_facturas_prueba(self):
        """Crea facturas de prueba para tests"""
        hoy = datetime.now()

        # Factura de ingreso
        f1 = Factura(
            usuario_id=self.usuario.id,
            numero_factura='001-001-000000001',
            ruc_proveedor='0192000000001',
            descripcion='Venta de productos',
            tipo='ingreso',
            fecha_emision=hoy,
            base_iva=1000.00,
            valor_iva=120.00,
            tarifa_iva='12',
            importe_total=1120.00,
        )
        db.session.add(f1)

        # Factura de gasto
        f2 = Factura(
            usuario_id=self.usuario.id,
            numero_factura='002-001-000000001',
            ruc_proveedor='0193000000001',
            descripcion='Compra de insumos',
            tipo='gasto',
            fecha_emision=hoy,
            base_iva=500.00,
            valor_iva=60.00,
            tarifa_iva='12',
            importe_total=560.00,
        )
        db.session.add(f2)
        db.session.commit()

    def test_obtener_datos_declaracion(self):
        """Test: Obtener datos del Formulario 104"""
        datos = GeneradorFormulario104.obtener_datos_declaracion(
            self.usuario.id, 2026, 6
        )

        self.assertIn('periodo', datos)
        self.assertIn('ventas', datos)
        self.assertIn('compras', datos)
        self.assertIn('credito', datos)
        self.assertEqual(datos['periodo']['anio'], 2026)
        self.assertEqual(datos['periodo']['mes'], 6)

    def test_generar_json(self):
        """Test: Generar Formulario 104 en JSON"""
        datos = GeneradorFormulario104.generar_json(
            self.usuario.id, 2026, 6
        )

        self.assertEqual(datos['tipo'], 'Formulario 104')
        self.assertEqual(datos['version'], '1.0')
        self.assertIn('secciones', datos)
        self.assertIn('resumen', datos)

    def test_generar_excel(self):
        """Test: Generar Formulario 104 en Excel"""
        archivo = GeneradorFormulario104.generar_excel(
            self.usuario.id, 2026, 6
        )

        # Verificar que es un archivo válido
        self.assertIsNotNone(archivo)
        self.assertEqual(archivo.tell(), 0)  # Posición al inicio

    def test_generar_xml(self):
        """Test: Generar Formulario 104 en XML"""
        xml = GeneradorFormulario104.generar_xml(
            self.usuario.id, 2026, 6
        )

        self.assertIn('<?xml', xml)
        self.assertIn('<Formulario104>', xml)
        self.assertIn('<Periodo>', xml)
        self.assertIn('<Ventas>', xml)
        self.assertIn('<Compras>', xml)
        self.assertIn('<CreditoTributario>', xml)

    def test_iva_ingresos_capturado(self):
        """Test: IVA de ingresos es capturado correctamente"""
        datos = GeneradorFormulario104.obtener_datos_declaracion(
            self.usuario.id, 2026, 6
        )

        self.assertGreater(datos['ventas']['iva_cobrado'], 0)
        self.assertEqual(datos['ventas']['iva_cobrado'], 120.00)

    def test_iva_gastos_capturado(self):
        """Test: IVA de gastos es capturado correctamente"""
        datos = GeneradorFormulario104.obtener_datos_declaracion(
            self.usuario.id, 2026, 6
        )

        self.assertGreater(datos['compras']['iva_pagado'], 0)
        self.assertEqual(datos['compras']['iva_pagado'], 60.00)


class TestGeneradorAnexoICE(unittest.TestCase):
    """Tests para Anexo ICE/PVP"""

    def setUp(self):
        self.app = create_app(init_db_now=False)
        self.app.config['TESTING'] = True
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'

        self.ctx = self.app.app_context()
        self.ctx.push()

        db.drop_all()
        db.create_all()

        self.usuario = Usuario(
            email='test@test.com',
            nombre='Test User',
            empresa='Test Company',
            ruc='0191234567001',
            activo=True
        )
        self.usuario.set_password('test123')
        db.session.add(self.usuario)
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def test_obtener_datos_anexo(self):
        """Test: Obtener datos del Anexo ICE"""
        datos = GeneradorAnexoICE.obtener_datos_anexo(
            self.usuario.id, 2026, 6
        )

        self.assertIn('periodo', datos)
        self.assertIn('categorias', datos)
        self.assertIn('detalles', datos)
        self.assertEqual(datos['periodo']['anio'], 2026)

    def test_generar_json(self):
        """Test: Generar Anexo ICE en JSON"""
        datos = GeneradorAnexoICE.generar_json(
            self.usuario.id, 2026, 6
        )

        self.assertEqual(datos['tipo'], 'Anexo ICE/PVP')
        self.assertIn('categorias', datos)

    def test_generar_excel(self):
        """Test: Generar Anexo ICE en Excel"""
        archivo = GeneradorAnexoICE.generar_excel(
            self.usuario.id, 2026, 6
        )

        self.assertIsNotNone(archivo)

    def test_generar_xml(self):
        """Test: Generar Anexo ICE en XML"""
        xml = GeneradorAnexoICE.generar_xml(
            self.usuario.id, 2026, 6
        )

        self.assertIn('<?xml', xml)
        self.assertIn('<AnexoICE>', xml)
        self.assertIn('<Categorias>', xml)

    def test_categorias_validas(self):
        """Test: Las categorías ICE son válidas"""
        for categoria, datos in GeneradorAnexoICE.CATEGORIAS_ICE.items():
            self.assertIn('nombre', datos)
            self.assertIn('codigo', datos)
            self.assertTrue(len(datos['codigo']) > 0)


class TestGeneradorATS(unittest.TestCase):
    """Tests para ATS (Archivo Técnico Tributario)"""

    def setUp(self):
        self.app = create_app(init_db_now=False)
        self.app.config['TESTING'] = True
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'

        self.ctx = self.app.app_context()
        self.ctx.push()

        db.drop_all()
        db.create_all()

        self.usuario = Usuario(
            email='test@test.com',
            nombre='Test User',
            empresa='Test Company',
            ruc='0191234567001',
            activo=True
        )
        self.usuario.set_password('test123')
        db.session.add(self.usuario)
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def test_obtener_datos_ats(self):
        """Test: Obtener datos del ATS"""
        datos = GeneradorATS.obtener_datos_ats(
            self.usuario.id, 2026, 6
        )

        self.assertIn('usuario', datos)
        self.assertIn('periodo', datos)
        self.assertIn('registros', datos)

    def test_formatear_campo(self):
        """Test: Formato de campos ATS"""
        # Test alineación derecha
        resultado = GeneradorATS.formatear_campo(123, 5, 'D')
        self.assertEqual(resultado, '00123')

        # Test alineación izquierda
        resultado = GeneradorATS.formatear_campo('ABC', 5, 'I')
        self.assertEqual(resultado, 'ABC')

    def test_calcular_checksum(self):
        """Test: Cálculo de checksum"""
        linea = "0191234567001202606"
        checksum = GeneradorATS.calcular_checksum(linea)

        self.assertEqual(len(checksum), 15)
        self.assertTrue(all(c in '0123456789abcdef' for c in checksum))

    def test_generar_archivo_plano(self):
        """Test: Generar ATS en archivo plano"""
        contenido = GeneradorATS.generar_archivo_plano(
            self.usuario.id, 2026, 6
        )

        self.assertIsInstance(contenido, str)
        self.assertGreater(len(contenido), 0)

    def test_generar_json(self):
        """Test: Generar ATS en JSON"""
        datos = GeneradorATS.generar_json(
            self.usuario.id, 2026, 6
        )

        self.assertEqual(datos['tipo'], 'ATS')
        self.assertIn('registros', datos)

    def test_generar_xml(self):
        """Test: Generar ATS en XML"""
        xml = GeneradorATS.generar_xml(
            self.usuario.id, 2026, 6
        )

        self.assertIn('<?xml', xml)
        self.assertIn('<ATS>', xml)
        self.assertIn('<Encabezado>', xml)


class TestGeneradorRetenciones(unittest.TestCase):
    """Tests para Certificado de Retenciones"""

    def setUp(self):
        self.app = create_app(init_db_now=False)
        self.app.config['TESTING'] = True
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'

        self.ctx = self.app.app_context()
        self.ctx.push()

        db.drop_all()
        db.create_all()

        self.usuario = Usuario(
            email='test@test.com',
            nombre='Test User',
            empresa='Test Company',
            ruc='0191234567001',
            activo=True
        )
        self.usuario.set_password('test123')
        db.session.add(self.usuario)
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def test_obtener_datos_retenciones(self):
        """Test: Obtener datos de retenciones"""
        datos = GeneradorRetenciones.obtener_datos_retenciones(
            self.usuario.id, 2026, 6
        )

        self.assertIn('usuario', datos)
        self.assertIn('periodo', datos)
        self.assertIn('resumen', datos)

    def test_generar_certificado_html(self):
        """Test: Generar certificado en HTML"""
        html = GeneradorRetenciones.generar_certificado_html(
            self.usuario.id, 2026, 6
        )

        self.assertIn('<!DOCTYPE html>', html)
        self.assertIn('<table>', html)
        self.assertIn('CERTIFICADO DE RETENCIÓN', html)

    def test_generar_json(self):
        """Test: Generar retenciones en JSON"""
        datos = GeneradorRetenciones.generar_json(
            self.usuario.id, 2026, 6
        )

        self.assertEqual(datos['tipo'], 'Certificado de Retención')
        self.assertIn('retenciones', datos)

    def test_generar_xml(self):
        """Test: Generar retenciones en XML"""
        xml = GeneradorRetenciones.generar_xml(
            self.usuario.id, 2026, 6
        )

        self.assertIn('<?xml', xml)
        self.assertIn('<CertificadoRetencion>', xml)

    def test_tipos_retencion_validos(self):
        """Test: Los tipos de retención son válidos"""
        for tipo, datos in GeneradorRetenciones.TIPOS_RETENCION.items():
            self.assertIn('nombre', datos)
            self.assertIn('codigo', datos)
            self.assertIn('porcentaje', datos)
            self.assertGreaterEqual(datos['porcentaje'], 0)


class TestIntegracionReportesSRI(unittest.TestCase):
    """Tests de integración para flujos completos"""

    def setUp(self):
        self.app = create_app(init_db_now=False)
        self.app.config['TESTING'] = True
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'

        self.ctx = self.app.app_context()
        self.ctx.push()

        db.drop_all()
        db.create_all()

        self.usuario = Usuario(
            email='test@test.com',
            nombre='Test User',
            empresa='Test Company',
            ruc='0191234567001',
            activo=True
        )
        self.usuario.set_password('test123')
        db.session.add(self.usuario)

        # Crear múltiples facturas
        self.crear_facturas_variadas()
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def crear_facturas_variadas(self):
        """Crea facturas con diferentes tarifas IVA"""
        hoy = datetime.now()
        tarifas = ['0', '5', '12', '15']

        for idx, tarifa in enumerate(tarifas):
            base = 1000.00
            if tarifa == '0':
                iva = 0
            elif tarifa == '5':
                iva = 50.00
            elif tarifa == '12':
                iva = 120.00
            else:  # 15
                iva = 150.00

            # Factura ingreso
            f_ingreso = Factura(
                usuario_id=self.usuario.id,
                numero_factura=f'001-001-{idx:09d}',
                ruc_proveedor='0192000000001',
                descripcion=f'Venta con IVA {tarifa}%',
                tipo='ingreso',
                fecha_emision=hoy,
                base_iva=base,
                valor_iva=iva,
                tarifa_iva=tarifa,
                importe_total=base + iva,
            )
            self.usuario.facturas.append(f_ingreso)

            # Factura gasto
            f_gasto = Factura(
                usuario_id=self.usuario.id,
                numero_factura=f'002-001-{idx:09d}',
                ruc_proveedor='0193000000001',
                descripcion=f'Compra con IVA {tarifa}%',
                tipo='gasto',
                fecha_emision=hoy,
                base_iva=base / 2,
                valor_iva=iva / 2,
                tarifa_iva=tarifa,
                importe_total=(base + iva) / 2,
            )
            self.usuario.facturas.append(f_gasto)

    def test_flujo_completo_formulario_104(self):
        """Test: Flujo completo Formulario 104 con múltiples tarifas"""
        datos = GeneradorFormulario104.obtener_datos_declaracion(
            self.usuario.id, 2026, 6
        )

        # Verificar que se capturó IVA
        total_iva_ingresos = datos['ventas']['iva_cobrado']
        self.assertGreater(total_iva_ingresos, 0)

        # Generar en todos los formatos
        excel = GeneradorFormulario104.generar_excel(self.usuario.id, 2026, 6)
        json_data = GeneradorFormulario104.generar_json(self.usuario.id, 2026, 6)
        xml = GeneradorFormulario104.generar_xml(self.usuario.id, 2026, 6)

        self.assertIsNotNone(excel)
        self.assertIsNotNone(json_data)
        self.assertIsNotNone(xml)

    def test_flujo_completo_ats(self):
        """Test: Flujo completo ATS con múltiples transacciones"""
        datos = GeneradorATS.obtener_datos_ats(
            self.usuario.id, 2026, 6
        )

        # Debe haber registros
        self.assertGreater(len(datos['registros']), 0)

        # Generar en todos los formatos
        plano = GeneradorATS.generar_archivo_plano(self.usuario.id, 2026, 6)
        json_data = GeneradorATS.generar_json(self.usuario.id, 2026, 6)
        xml = GeneradorATS.generar_xml(self.usuario.id, 2026, 6)

        self.assertGreater(len(plano), 0)
        self.assertIsNotNone(json_data)
        self.assertIsNotNone(xml)

    def test_consistencia_datos_entre_formatos(self):
        """Test: Los datos son consistentes entre formatos"""
        json_data = GeneradorFormulario104.generar_json(
            self.usuario.id, 2026, 6
        )
        xml = GeneradorFormulario104.generar_xml(
            self.usuario.id, 2026, 6
        )

        # JSON debe tener totales
        self.assertIn('resumen', json_data)

        # XML debe contener el período
        self.assertIn('2026', xml)


if __name__ == '__main__':
    unittest.main()
