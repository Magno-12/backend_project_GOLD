import requests
import hashlib
import time
import random
import string
from typing import Dict, Any, Optional
from django.conf import settings
from apps.payments.config import WOMPI_SETTINGS


class WompiService:
    """Servicio para interactuar con la API de Wompi y generar datos para el widget"""

    def __init__(self):
        self.base_url = WOMPI_SETTINGS['SANDBOX_URL']
        self.public_key = WOMPI_SETTINGS['SANDBOX_PUBLIC_KEY']
        self.private_key = WOMPI_SETTINGS['SANDBOX_PRIVATE_KEY']
        self.events_key = WOMPI_SETTINGS.get('SANDBOX_EVENTS_KEY')
        self.integrity_key = WOMPI_SETTINGS.get('SANDBOX_INTEGRITY_KEY')
        self.currency = WOMPI_SETTINGS['CURRENCY']
        self.min_amount = WOMPI_SETTINGS['MIN_AMOUNT']
        self.max_amount = WOMPI_SETTINGS['MAX_AMOUNT']

    def _get_headers(self, private: bool = False) -> Dict:
        """Obtener headers para la API de Wompi"""
        key = self.private_key if private else self.public_key
        return {
            'Authorization': f'Bearer {key}',
            'Content-Type': 'application/json'
        }

    def generate_reference(self) -> str:
        """
        Genera una referencia única para la transacción
        Format: PAY + timestamp + random_string
        Example: PAY1640995200ABCD1234
        """
        timestamp = int(time.time())
        random_str = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
        return f"PAY{timestamp}{random_str}"

    def generate_signature(self, reference: str, amount_in_cents: int) -> Optional[str]:
        """
        Genera la firma de integridad SHA256
        Format: reference + amount_in_cents + currency + integrity_key
        
        Args:
            reference (str): Referencia única de la transacción
            amount_in_cents (int): Monto en centavos
            
        Returns:
            Optional[str]: Firma generada o None si no hay integrity_key
        """
        if not self.integrity_key:
            return None
            
        integrity_string = f"{reference}{amount_in_cents}{self.currency}{self.integrity_key}"
        return hashlib.sha256(integrity_string.encode()).hexdigest()

    def validate_amount(self, amount_in_cents: int) -> bool:
        """
        Valida que el monto esté dentro de los límites permitidos
        
        Args:
            amount_in_cents (int): Monto en centavos
            
        Returns:
            bool: True si el monto es válido
        """
        return self.min_amount <= amount_in_cents <= self.max_amount

    def get_acceptance_token(self) -> Optional[str]:
        """
        Obtener token de aceptación de términos y condiciones
        Necesario para transacciones con API directa
        """
        url = f"{self.base_url}/merchants/{self.public_key}"
        try:
            response = requests.get(
                url,
                headers=self._get_headers()
            )
            response.raise_for_status()
            return response.json().get('data', {}).get('presigned_acceptance', {}).get('acceptance_token')
        except Exception as e:
            print(f"Error getting acceptance token: {str(e)}")
            return None

    def get_transaction(self, transaction_id: str) -> Dict:
        """
        Obtener detalles de una transacción
        Útil para verificar estado en webhook
        
        Args:
            transaction_id (str): ID de la transacción en Wompi
            
        Returns:
            Dict: Datos de la transacción o dict vacío si hay error
        """
        url = f"{self.base_url}/transactions/{transaction_id}"
        try:
            response = requests.get(
                url,
                headers=self._get_headers(private=True)
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error getting transaction: {str(e)}")
            return {}

    def verify_webhook_signature(self, webhook_event_id: str, webhook_signature: str) -> bool:
        """
        Verifica la firma del webhook para garantizar que viene de Wompi
        
        Args:
            webhook_event_id (str): ID del evento del webhook
            webhook_signature (str): Firma proporcionada en el webhook
            
        Returns:
            bool: True si la firma es válida
        """
        if not self.events_key:
            return False

        timestamp = int(time.time())
        signature_string = f"{webhook_event_id}{timestamp}{self.events_key}"
        generated_signature = hashlib.sha256(signature_string.encode()).hexdigest()
        
        return generated_signature == webhook_signature

    def get_payment_link_data(self, reference: str, amount_in_cents: int) -> Dict:
        """
        Obtiene los datos necesarios para el widget de pago
        
        Args:
            reference (str): Referencia única de la transacción
            amount_in_cents (int): Monto en centavos
            
        Returns:
            Dict: Datos necesarios para inicializar el widget
        """
        signature = self.generate_signature(reference, amount_in_cents)
        
        return {
            'public_key': self.public_key,
            'currency': self.currency,
            'amount_in_cents': amount_in_cents,
            'reference': reference,
            'signature': signature
        }

    def validate_currency(self, currency: str) -> bool:
        """
        Valida que la moneda sea la correcta
        
        Args:
            currency (str): Código de la moneda
            
        Returns:
            bool: True si la moneda es válida
        """
        return currency == self.currency

    # Mantenemos estos métodos por compatibilidad aunque no se usen en el widget
    def tokenize_card(self, card_data: Dict) -> Dict:
        """Tokenizar una tarjeta de crédito"""
        url = f"{self.base_url}/tokens/cards"
        try:
            response = requests.post(
                url,
                json=card_data,
                headers=self._get_headers()
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error tokenizing card: {str(e)}")
            return {}

    def get_pse_banks(self) -> Dict:
        """Obtener lista de bancos PSE"""
        url = f"{self.base_url}/pse/financial_institutions"
        try:
            response = requests.get(
                url,
                headers=self._get_headers()
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error getting PSE banks: {str(e)}")
            return {}
