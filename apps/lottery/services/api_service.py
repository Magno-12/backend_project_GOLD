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
            url = f"{settings.LOTTERY_API_URL}"
            response = requests.get(
                url,
                headers={'Authorization': f'Bearer {settings.LOTTERY_API_KEY}'}
            )
            response.raise_for_status()
            results = response.json()
            # La API devuelve directamente una lista, no necesitamos .get('resultados')
            return results if isinstance(results, list) else []
        except Exception as e:
            print(f"Error fetching lottery results: {str(e)}")
            return []

    @staticmethod
    def get_lottery_by_date(lottery_name: str, date: str) -> Optional[Dict]:
        """Obtiene resultado de una lotería específica por fecha"""
        try:
            url = f"{settings.LOTTERY_API_URL}"
            response = requests.get(
                url,
                headers={'Authorization': f'Bearer {settings.LOTTERY_API_KEY}'}
            )
            response.raise_for_status()
            results = response.json()
            
            # Buscar el resultado específico en la lista de resultados
            if isinstance(results, list):
                return next(
                    (result for result in results 
                     if result['nombre_loteria'] == lottery_name 
                     and result['fecha'] == date),
                    None
                )
            return None
        except Exception as e:
            print(f"Error fetching specific lottery result: {str(e)}")
            return None
