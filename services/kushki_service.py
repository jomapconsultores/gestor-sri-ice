import requests
import json
from config import Config

class KushkiService:
    """Servicio de integracion con Kushki via API REST"""
    
    API_URL = "https://api-ecuador.kushkipagos.com"
    
    @staticmethod
    def get_headers():
        return {
            "Content-Type": "application/json",
            "Private-Merchant-Id": Config.KUSHKI_PRIVATE_KEY
        }
    
    @staticmethod
    def procesar_pago(token_tarjeta, monto, descripcion, email_cliente, transaction_id):
        """
        Procesa un pago con el token de tarjeta generado por Kushki.js
        """
        # Si no hay credenciales configuradas, modo prueba
        if Config.KUSHKI_PRIVATE_KEY == 'TU_KUSHKI_PRIVATE_KEY':
            return {'aprobado': True, 'ticketNumber': 'TEST-' + transaction_id, 'modo_prueba': True}, None
        
        try:
            # Calcular IVA
            subtotal = round(monto / 1.15, 2)
            iva = round(monto - subtotal, 2)
            
            payload = {
                "token": token_tarjeta,
                "amount": {
                    "subtotalIva": subtotal,
                    "iva": iva,
                    "ice": 0,
                    "extraTaxes": {},
                    "currency": "USD"
                },
                "metadata": {
                    "transactionId": transaction_id,
                    "description": descripcion,
                    "email": email_cliente
                },
                "fullResponse": True
            }
            
            response = requests.post(
                f"{KushkiService.API_URL}/charges/v1",
                json=payload,
                headers=KushkiService.get_headers(),
                timeout=20
            )
            
            if response.status_code in [200, 201]:
                data = response.json()
                return {
                    'aprobado': True,
                    'ticketNumber': data.get('ticketNumber', ''),
                    'transactionReference': data.get('transactionReference', {}).get('transactionReference', ''),
                    'responseCode': data.get('responseCode', '')
                }, None
            else:
                return None, f"Error Kushki: {response.text}"
        
        except Exception as e:
            return None, f"Error de conexion: {str(e)}"