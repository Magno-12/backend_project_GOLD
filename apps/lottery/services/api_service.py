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
            external_url = 'https://lottery-results-api.onrender.com/results'
            external_headers = {
                'x-api-key': '47SFw0COzXcwePfecOUwWUXe9BrZhg'
            }
            
            print(f"\nIntentando obtener resultados de: {external_url}")
            print(f"Headers utilizados: {external_headers}")
            
            response = requests.get(external_url, headers=external_headers)
            
            print(f"\nRespuesta recibida:")
            print(f"Status Code: {response.status_code}")
            print(f"Content-Type: {response.headers.get('content-type')}")
            print(f"Contenido: {response.text[:200]}...")  # Primeros 200 caracteres
            
            if response.status_code == 200:
                results = response.json()
                print(f"\nResultados procesados:")
                print(f"Tipo de datos: {type(results)}")
                print(f"Cantidad de resultados: {len(results) if results else 0}")
                if results:
                    print(f"Primer resultado: {results[0]}")
                return results
            else:
                print(f"\nError en la respuesta: {response.text}")
                return []

        except requests.RequestException as e:
            print(f"\nError en la petición HTTP: {str(e)}")
            return []
        except json.JSONDecodeError as e:
            print(f"\nError decodificando JSON: {str(e)}")
            print(f"Respuesta recibida: {response.text}")
            return []
        except Exception as e:
            print(f"\nError inesperado: {str(e)}")
            print(f"Traceback: {traceback.format_exc()}")
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
