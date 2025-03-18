# apps/lottery/services/combination_processor.py

import pandas as pd
import numpy as np
import json
import io
import requests
from django.db import transaction
from django.db.models import Q
from django.core.files.base import ContentFile
from django.utils import timezone
from typing import Dict, List, Set, Tuple, Optional
import logging

from apps.lottery.models import Lottery, LotteryNumberCombination

logger = logging.getLogger(__name__)

class CombinationProcessor:
    """
    Procesador para archivos CSV de combinaciones de loterías.
    Permite cargar, procesar y almacenar combinaciones de números y series
    para diferentes loterías.
    """
    
    def __init__(self, lottery_id: str = None):
        """
        Inicializa el procesador con una lotería específica (opcional)
        
        Args:
            lottery_id: El ID de la lotería a la que se asignarán las combinaciones
        """
        self.lottery_id = lottery_id
        self.lottery = None
        if lottery_id:
            try:
                self.lottery = Lottery.objects.get(id=lottery_id)
            except Lottery.DoesNotExist:
                logger.error(f"No se encontró la lotería con ID {lottery_id}")
                raise ValueError(f"No existe lotería con ID {lottery_id}")
    
    def process_cloudinary_file(self, file_url: str, lottery_id: str = None) -> Dict:
        """
        Procesa un archivo de Cloudinary para extraer combinaciones
        
        Args:
            file_url: URL del archivo en Cloudinary
            lottery_id: ID de la lotería (opcional, si no se proporcionó en __init__)
            
        Returns:
            dict: Resultados del procesamiento
        """
        if lottery_id:
            self.lottery_id = lottery_id
            try:
                self.lottery = Lottery.objects.get(id=lottery_id)
            except Lottery.DoesNotExist:
                logger.error(f"No se encontró la lotería con ID {lottery_id}")
                return {"error": f"No existe lotería con ID {lottery_id}"}
        
        if not self.lottery:
            return {"error": "No se ha especificado una lotería válida"}
        
        try:
            # Descargar el archivo desde Cloudinary
            response = requests.get(file_url)
            if response.status_code != 200:
                return {"error": f"Error al descargar el archivo: {response.status_code}"}
            
            # Procesar el contenido del archivo
            file_content = io.BytesIO(response.content)
            return self.process_csv_content(file_content)
            
        except Exception as e:
            logger.exception(f"Error procesando archivo: {e}")
            return {"error": str(e)}
    
    def process_csv_content(self, file_content) -> Dict:
        """
        Procesa el contenido de un archivo CSV
        
        Args:
            file_content: Contenido del archivo CSV (BytesIO o similar)
            
        Returns:
            dict: Resultados del procesamiento
        """
        try:
            # Leer el CSV con pandas
            df = pd.read_csv(file_content, header=None, dtype=str)
            
            # Validar que el CSV tenga al menos 4 columnas
            if df.shape[1] < 4:
                return {"error": "El archivo CSV debe tener al menos 4 columnas"}
            
            # Tomar las columnas correspondientes a series (3) y números (4)
            # Ajustar índices a base 0
            series_col = 2  # 3ra columna (índice 2 en base 0)
            number_col = 3  # 4ta columna (índice 3 en base 0)
            
            # Procesar los datos
            series_list, numbers_list = self._extract_series_and_numbers(df, series_col, number_col)
            
            # Guardar las combinaciones en la base de datos
            result = self._save_combinations(series_list, numbers_list)
            
            return result
            
        except Exception as e:
            logger.exception(f"Error procesando CSV: {e}")
            return {"error": str(e)}
    
    def _extract_series_and_numbers(self, df: pd.DataFrame, series_col: int, number_col: int) -> Tuple[List[str], List[str]]:
        """
        Extrae y formatea las series y números del DataFrame
        
        Args:
            df: DataFrame con los datos
            series_col: Índice de la columna de series
            number_col: Índice de la columna de números
            
        Returns:
            Tuple[List[str], List[str]]: Series y números formateados
        """
        # Convertir a string y limpiar
        series = df.iloc[:, series_col].astype(str).str.strip()
        numbers = df.iloc[:, number_col].astype(str).str.strip()
        
        # Formatear series (3 dígitos)
        series_list = [s.zfill(3) for s in series if s and s.isdigit()]
        
        # Formatear números (4 dígitos)
        numbers_list = [n.zfill(4) for n in numbers if n and n.isdigit()]
        
        # Verificar que tengan la misma longitud
        min_length = min(len(series_list), len(numbers_list))
        
        return series_list[:min_length], numbers_list[:min_length]
    
    @transaction.atomic
    def _save_combinations(self, series_list: List[str], numbers_list: List[str]) -> Dict:
        """
        Guarda las combinaciones en la base de datos
        
        Args:
            series_list: Lista de series formateadas
            numbers_list: Lista de números formateados
            
        Returns:
            dict: Resultado del proceso
        """
        if not self.lottery:
            return {"error": "No se ha especificado una lotería válida"}
        
        draw_date = self.lottery.next_draw_date or timezone.now().date()
        
        # Recolectar series únicas para actualizar el campo available_series de la lotería
        unique_series = set(series_list)
        
        # Desactivar combinaciones anteriores para esta lotería y esta fecha
        LotteryNumberCombination.objects.filter(
            lottery=self.lottery,
            draw_date=draw_date
        ).update(is_active=False)
        
        # Preparar datos para bulk create
        combinations_to_create = []
        unique_combinations = set()  # Para evitar duplicados
        
        for i, (series, number) in enumerate(zip(series_list, numbers_list)):
            # Evitar duplicados
            key = f"{number}-{series}"
            if key in unique_combinations:
                continue
            
            unique_combinations.add(key)
            
            # Crear objeto de combinación con solo los campos que sabemos que existen
            new_combination = LotteryNumberCombination(
                lottery=self.lottery,
                number=number,
                series=series,
                draw_date=draw_date,
                total_fractions=self.lottery.fraction_count,
                used_fractions=0,
                is_active=True,
                is_winner=False  # Solo incluimos campos que sabemos que existen
            )
            
            # Si hay campos adicionales que necesiten valores específicos,
            # podemos establecerlos después de la creación
            # Por ejemplo:
            # if hasattr(new_combination, 'prize_detail'):
            #     new_combination.prize_detail = {}
            
            combinations_to_create.append(new_combination)
            
            # Procesamiento por lotes para evitar sobrecarga de memoria
            if len(combinations_to_create) >= 5000:
                LotteryNumberCombination.objects.bulk_create(combinations_to_create)
                combinations_to_create = []
        
        # Guardar cualquier combinación restante
        if combinations_to_create:
            LotteryNumberCombination.objects.bulk_create(combinations_to_create)
        
        # Actualizar available_series en la lotería (sin duplicados)
        # current_series = set(self.lottery.available_series or [])
        # updated_series = list(current_series.union(unique_series))
        # self.lottery.available_series = updated_series
        # self.lottery.save(update_fields=['available_series'])
        
        # Crear estructura JSON para el resultado
        result_json = {
            "combinaciones": [
                {
                    "loteria": self.lottery.name,
                    "serie": series,
                    "numero": number
                }
                for series, number in zip(series_list[:10], numbers_list[:10])  # Solo mostrar los primeros 10 para el reporte
            ]
        }
        
        # Preparar resultado detallado
        result = {
            "success": True,
            "lottery_id": str(self.lottery.id),
            "lottery_name": self.lottery.name,
            "combinations_count": len(unique_combinations),
            "series_count": len(unique_series),
            "sample_combinations": result_json,
            "draw_date": str(draw_date)
        }
        
        return result

    @staticmethod
    def get_all_lotteries() -> List[Dict]:
        """
        Obtiene todas las loterías activas
        
        Returns:
            List[Dict]: Lista de loterías con id y nombre
        """
        return [
            {
                "id": str(lottery.id),
                "name": lottery.name
            }
            for lottery in Lottery.objects.filter(is_active=True).order_by('name')
        ]
