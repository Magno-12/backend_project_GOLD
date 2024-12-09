import requests
from typing import Dict, Any
from django.conf import settings
from apps.payments.config import WOMPI_SETTINGS


class WompiService:
    """Servicio para interactuar con la API de Wompi"""

    def __init__(self):
        self.base_url = WOMPI_SETTINGS['SANDBOX_URL']
        self.public_key = WOMPI_SETTINGS['SANDBOX_PUBLIC_KEY']
        self.private_key = WOMPI_SETTINGS['SANDBOX_PRIVATE_KEY']

    def _get_headers(self, private: bool = False) -> Dict:
        """Obtener headers para la API de Wompi"""
        key = self.private_key if private else self.public_key
        return {
            'Authorization': f'Bearer {key}',
            'Content-Type': 'application/json'
        }

    def create_transaction(self, data: Dict) -> Dict:
        """Crear una transacción en Wompi"""
        url = f"{self.base_url}/transactions"
        try:
            response = requests.post(
                url,
                json=data,
                headers=self._get_headers()
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error creating transaction: {str(e)}")
            return {}

    def get_transaction(self, transaction_id: str) -> Dict:
        """Obtener detalles de una transacción"""
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
