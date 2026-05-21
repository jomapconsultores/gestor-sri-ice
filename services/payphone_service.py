import requests
import json
from config import Config

class PayPhoneService:
    API_URL = "https://pay.payphonetodoesposible.com/api"

    @staticmethod
    def get_token():
        try:
            response = requests.post(
                f"{PayPhoneService.API_URL}/v1/auth/token",
                json={
                    "client_id": Config.PAYPHONE_CLIENT_ID,
                    "client_secret": Config.PAYPHONE_CLIENT_SECRET
                },
                timeout=10
            )
            if response.status_code == 200:
                return response.json().get('token')
            return None
        except:
            return None

    @staticmethod
    def crear_pago(plan_id, usuario_email, usuario_nombre):
        planes = {
            'basico': Config.PLAN_BASICO,
            'profesional': Config.PLAN_PROFESIONAL,
            'empresarial': Config.PLAN_EMPRESARIAL
        }
        if plan_id not in planes:
            return None, "Plan no valido"
        plan = planes[plan_id]
        token = PayPhoneService.get_token()
        if not token:
            return None, "Error de conexion con PayPhone"
        try:
            payload = {
                "amount": plan['precio'],
                "amountWithoutTax": plan['precio'],
                "amountWithTax": 0,
                "tax": 0,
                "clientTransactionId": f"{plan_id}_{usuario_email}",
                "responseUrl": f"{Config.BASE_URL}/payments/respuesta",
                "cancellationUrl": f"{Config.BASE_URL}/payments/planes",
                "reference": f"Suscripcion {plan['nombre']} - Gestor SRI",
                "phoneNumber": "0999999999",
                "email": usuario_email,
                "optionalParameter": json.dumps({
                    "plan_id": plan_id,
                    "usuario_email": usuario_email
                })
            }
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
            response = requests.post(
                f"{PayPhoneService.API_URL}/v1/button/pay",
                json=payload,
                headers=headers,
                timeout=15
            )
            if response.status_code == 200:
                data = response.json()
                return data.get('payUrl'), None
            else:
                return None, f"Error: {response.text}"
        except Exception as e:
            return None, f"Error: {str(e)}"

    @staticmethod
    def verificar_pago(transaction_id):
        token = PayPhoneService.get_token()
        if not token:
            return None
        try:
            headers = {"Authorization": f"Bearer {token}"}
            response = requests.get(
                f"{PayPhoneService.API_URL}/v1/button/validate/{transaction_id}",
                headers=headers,
                timeout=10
            )
            if response.status_code == 200:
                return response.json()
            return None
        except:
            return None