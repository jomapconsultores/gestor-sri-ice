"""
Tests de integración para endpoints de reportes SRI
"""
import unittest
import json
from datetime import datetime
from models import db
from models.user import Usuario, Factura
from app import create_app


class TestEndpointsReportes(unittest.TestCase):
    """Tests para endpoints de reportes"""

    def setUp(self):
        self.app = create_app(init_db_now=False)
        self.app.config['TESTING'] = True
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'

        self.ctx = self.app.app_context()
        self.ctx.push()

        db.drop_all()
        db.create_all()

        self.client = self.app.test_client()

        # Crear usuario
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

        # Crear facturas
        self.crear_facturas_prueba()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def crear_facturas_prueba(self):
        """Crea facturas de prueba"""
        hoy = datetime.now()

        for i in range(3):
            f = Factura(
                usuario_id=self.usuario.id,
                numero_factura=f'001-001-{i:09d}',
                ruc_proveedor='0192000000001',
                descripcion=f'Factura {i+1}',
                tipo='ingreso' if i % 2 == 0 else 'gasto',
                fecha_emision=hoy,
                base_iva=1000.00,
                valor_iva=120.00,
                tarifa_iva='12',
                importe_total=1120.00,
            )
            db.session.add(f)
        db.session.commit()

    def login(self):
        """Login del usuario de prueba"""
        self.client.post('/auth/login', data={
            'email': 'test@test.com',
            'password': 'test123'
        }, follow_redirects=True)

    def test_formulario_104_json_no_autenticado(self):
        """Test: Acceso sin autenticación rechazado"""
        response = self.client.get(
            '/reportes/formulario_104/2026/6?formato=json'
        )
        self.assertEqual(response.status_code, 302)  # Redirect a login

    def test_formulario_104_json_autenticado(self):
        """Test: Descarga Formulario 104 en JSON"""
        self.login()
        response = self.client.get(
            '/reportes/formulario_104/2026/6?formato=json'
        )

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['tipo'], 'Formulario 104')

    def test_formulario_104_preview(self):
        """Test: Preview del Formulario 104"""
        self.login()
        response = self.client.get(
            '/reportes/formulario_104/2026/6/preview'
        )

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('formulario', data)

    def test_formulario_104_mes_invalido(self):
        """Test: Mes inválido rechazado"""
        self.login()
        response = self.client.get(
            '/reportes/formulario_104/2026/13?formato=json'
        )

        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('error', data)

    def test_formulario_104_anio_invalido(self):
        """Test: Año inválido rechazado"""
        self.login()
        response = self.client.get(
            '/reportes/formulario_104/1900/6?formato=json'
        )

        self.assertEqual(response.status_code, 400)

    def test_anexo_ice_json(self):
        """Test: Descarga Anexo ICE en JSON"""
        self.login()
        response = self.client.get(
            '/reportes/anexo_ice/2026/6?formato=json'
        )

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['tipo'], 'Anexo ICE/PVP')

    def test_ats_json(self):
        """Test: Descarga ATS en JSON"""
        self.login()
        response = self.client.get(
            '/reportes/ats/2026/6?formato=json'
        )

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['tipo'], 'ATS')

    def test_ats_archivo_plano(self):
        """Test: Descarga ATS en formato plano"""
        self.login()
        response = self.client.get(
            '/reportes/ats/2026/6?formato=plano'
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content_type, 'text/plain; charset=utf-8')

    def test_retenciones_json(self):
        """Test: Descarga Retenciones en JSON"""
        self.login()
        response = self.client.get(
            '/reportes/retenciones/2026/6?formato=json'
        )

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['tipo'], 'Certificado de Retención')

    def test_retenciones_html(self):
        """Test: Descarga Retenciones en HTML"""
        self.login()
        response = self.client.get(
            '/reportes/retenciones/2026/6?formato=html'
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content_type, 'text/html; charset=utf-8')
        self.assertIn(b'CERTIFICADO', response.data)

    def test_lista_periodos(self):
        """Test: Listar períodos disponibles"""
        self.login()
        response = self.client.get(
            '/reportes/lista_periodos'
        )

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('periodos', data)
        self.assertGreater(len(data['periodos']), 0)

    def test_resumen_anio(self):
        """Test: Resumen anual"""
        self.login()
        response = self.client.get(
            '/reportes/resumen_anio/2026'
        )

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('resumen', data)

    def test_formato_invalido(self):
        """Test: Formato inválido rechazado"""
        self.login()
        response = self.client.get(
            '/reportes/formulario_104/2026/6?formato=pdf'
        )

        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('error', data)

    def test_excel_descargable(self):
        """Test: Excel se descarga correctamente"""
        self.login()
        response = self.client.get(
            '/reportes/formulario_104/2026/6?formato=excel'
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn('spreadsheetml', response.content_type)
        self.assertGreater(len(response.data), 0)

    def test_paquete_completo_zip(self):
        """Test: Paquete completo en ZIP"""
        self.login()
        response = self.client.get(
            '/reportes/paquete_completo/2026/6'
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content_type, 'application/zip')
        self.assertGreater(len(response.data), 0)

    def test_respuesta_json_valida(self):
        """Test: Respuestas JSON tienen estructura válida"""
        self.login()

        endpoints = [
            '/reportes/formulario_104/2026/6?formato=json',
            '/reportes/anexo_ice/2026/6?formato=json',
            '/reportes/ats/2026/6?formato=json',
            '/reportes/retenciones/2026/6?formato=json',
        ]

        for endpoint in endpoints:
            response = self.client.get(endpoint)
            self.assertEqual(response.status_code, 200)

            try:
                data = json.loads(response.data)
                self.assertIsInstance(data, dict)
            except json.JSONDecodeError:
                self.fail(f"Respuesta no es JSON válido: {endpoint}")

    def test_xml_valido(self):
        """Test: Respuestas XML tienen estructura válida"""
        self.login()

        endpoints = [
            '/reportes/formulario_104/2026/6?formato=xml',
            '/reportes/anexo_ice/2026/6?formato=xml',
            '/reportes/ats/2026/6?formato=xml',
            '/reportes/retenciones/2026/6?formato=xml',
        ]

        for endpoint in endpoints:
            response = self.client.get(endpoint)
            self.assertEqual(response.status_code, 200)

            # Validar que es XML
            self.assertIn(b'<?xml', response.data)
            self.assertIn(b'?>', response.data)


class TestAuditoriaEndpoints(unittest.TestCase):
    """Tests para endpoints de auditoría"""

    def setUp(self):
        self.app = create_app(init_db_now=False)
        self.app.config['TESTING'] = True
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'

        self.ctx = self.app.app_context()
        self.ctx.push()

        db.drop_all()
        db.create_all()

        self.client = self.app.test_client()

        # Crear usuario
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

    def login(self):
        """Login del usuario"""
        self.client.post('/auth/login', data={
            'email': 'test@test.com',
            'password': 'test123'
        }, follow_redirects=True)

    def test_historial_auditoria(self):
        """Test: Obtener historial de auditoría"""
        self.login()
        response = self.client.get('/auditoria/historial')

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('cambios', data)

    def test_historial_con_limite(self):
        """Test: Historial con límite de registros"""
        self.login()
        response = self.client.get('/auditoria/historial?limite=10')

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertLessEqual(len(data['cambios']), 10)

    def test_historial_limite_maximo(self):
        """Test: Límite máximo de registros no se excede"""
        self.login()
        response = self.client.get('/auditoria/historial?limite=500')

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertLessEqual(len(data['cambios']), 200)  # Max 200

    def test_rango_fechas_valido(self):
        """Test: Rango de fechas válido"""
        self.login()
        response = self.client.get(
            '/auditoria/rango_fechas?desde=2026-01-01&hasta=2026-12-31'
        )

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('cambios', data)

    def test_rango_fechas_invalido(self):
        """Test: Rango de fechas inválido rechazado"""
        self.login()
        response = self.client.get(
            '/auditoria/rango_fechas?desde=01/01/2026&hasta=31/12/2026'
        )

        self.assertEqual(response.status_code, 400)

    def test_rango_fechas_faltante(self):
        """Test: Parámetros faltantes rechazados"""
        self.login()
        response = self.client.get(
            '/auditoria/rango_fechas?desde=2026-01-01'
        )

        self.assertEqual(response.status_code, 400)

    def test_por_accion_valida(self):
        """Test: Filtrar por acción válida"""
        self.login()
        response = self.client.get('/auditoria/por_accion/CREATE')

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['accion'], 'CREATE')

    def test_por_accion_invalida(self):
        """Test: Acción inválida rechazada"""
        self.login()
        response = self.client.get('/auditoria/por_accion/INVALID')

        self.assertEqual(response.status_code, 400)

    def test_resumen_auditoria(self):
        """Test: Resumen de auditoría"""
        self.login()
        response = self.client.get('/auditoria/resumen')

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('total_cambios', data)
        self.assertIn('por_accion', data)
        self.assertIn('por_tabla', data)


if __name__ == '__main__':
    unittest.main()
