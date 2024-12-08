import requests
from typing import Dict, List, Optional
from django.conf import settings
from datetime import datetime


class LotteryAPIService:
    """Servicio para consumir la API externa de loterías"""

    @staticmethod
    def get_lottery_results() -> List[Dict]:
        """Obtiene los resultados desde la API externa"""
        try:
            url = f"{settings.LOTTERY_API_URL}/resultados"
            response = requests.get(
                url,
                headers={'Authorization': f'Bearer {settings.LOTTERY_API_KEY}'}
            )
            response.raise_for_status()
            return response.json().get('resultados', [])
        except Exception as e:
            print(f"Error fetching lottery results: {str(e)}")
            return []

    @staticmethod
    def get_lottery_by_date(lottery_id: str, date: str) -> Optional[Dict]:
        """Obtiene resultado de una lotería específica por fecha"""
        try:
            url = f"{settings.LOTTERY_API_URL}/resultados/{lottery_id}"
            response = requests.get(
                url,
                params={'fecha': date},
                headers={'Authorization': f'Bearer {settings.LOTTERY_API_KEY}'}
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error fetching specific lottery result: {str(e)}")
            return None
