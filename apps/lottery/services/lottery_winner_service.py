from typing import Dict, List, Optional
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


class LotteryWinnerService:
    """Servicio mejorado para procesar resultados y determinar ganadores de lotería"""

    def __init__(self, lottery_result: 'LotteryResult'):
        self.result = lottery_result
        self.lottery = lottery_result.lottery
        self.prize_plan = self.lottery.prize_plans.filter(
            is_active=True,
            start_date__lte=lottery_result.fecha,
            end_date__isnull=True
        ).first()
        self.winning_number = lottery_result.numero
        self.winning_series = lottery_result.numero_serie
        self.premios_secos = lottery_result.premios_secos or []

    @transaction.atomic
    def process_results(self):
        """Procesa los resultados y actualiza todas las apuestas pendientes"""
        # Verificar que tenemos un plan de premios
        if not self.prize_plan:
            logger.error(f"No se encontró plan de premios activo para {self.lottery.name} - {self.result.fecha}")
            return
            
        logger.info(f"Procesando resultados para {self.lottery.name} - {self.result.fecha}")
        logger.info(f"Número ganador: {self.winning_number}, Serie: {self.winning_series}")
        
        # Procesar combinaciones ganadoras primero
        self.mark_winning_combinations()
        
        # Luego procesar apuestas pendientes
        pending_bets = self.lottery.bets.filter(
            draw_date=self.result.fecha,
            status='PENDING'
        ).select_related('user')
        
        processed_count = 0
        won_count = 0
        for bet in pending_bets:
            if self.process_bet(bet):
                won_count += 1
            processed_count += 1
            
            # Loguear progreso cada 100 apuestas
            if processed_count % 100 == 0:
                logger.info(f"Procesadas {processed_count} apuestas, {won_count} ganadoras")
        
        logger.info(f"Procesamiento completado: {processed_count} apuestas procesadas, {won_count} ganadoras")

    def mark_winning_combinations(self):
        """Marca las combinaciones ganadoras en LotteryNumberCombination"""
        try:
            from apps.lottery.models import LotteryNumberCombination
            
            # Marcar el premio mayor
            major_combinations = LotteryNumberCombination.objects.filter(
                lottery=self.lottery,
                number=self.winning_number,
                series=self.winning_series,
                draw_date=self.result.fecha,
                is_active=True
            )
            
            if major_combinations.exists():
                # Buscar el premio mayor en el plan
                major_prize = next((prize for prize in self.prize_plan.prizes.all() 
                                   if prize.prize_type.code == 'MAJOR'), None)
                                   
                if major_prize:
                    major_combinations.update(
                        is_winner=True,
                        prize_type='MAJOR',
                        prize_amount=major_prize.amount,
                        prize_detail={
                            'type': 'MAJOR',
                            'name': 'Premio Mayor',
                            'amount': str(major_prize.amount)
                        }
                    )
                    logger.info(f"Marcada combinación ganadora del premio mayor: {self.winning_number}-{self.winning_series}")
            
            # Marcar premios secos
            if isinstance(self.premios_secos, list):
                for premio_seco in self.premios_secos:
                    if isinstance(premio_seco, dict) and 'numero' in premio_seco and 'serie' in premio_seco:
                        numero = premio_seco.get('numero')
                        serie = premio_seco.get('serie')
                        
                        seco_combinations = LotteryNumberCombination.objects.filter(
                            lottery=self.lottery,
                            number=numero,
                            series=serie,
                            draw_date=self.result.fecha,
                            is_active=True
                        )
                        
                        if seco_combinations.exists():
                            # Buscar premios secos en el plan
                            seco_prize = next((prize for prize in self.prize_plan.prizes.all() 
                                              if prize.prize_type.code == 'SECO'), None)
                                              
                            if seco_prize:
                                seco_combinations.update(
                                    is_winner=True,
                                    prize_type='SECO',
                                    prize_amount=seco_prize.amount,
                                    prize_detail={
                                        'type': 'SECO',
                                        'name': seco_prize.name or 'Premio Seco',
                                        'amount': str(seco_prize.amount)
                                    }
                                )
                                logger.info(f"Marcada combinación ganadora de premio seco: {numero}-{serie}")
                        
        except Exception as e:
            logger.error(f"Error marcando combinaciones ganadoras: {str(e)}")

    def process_bet(self, bet: 'Bet') -> bool:
        """
        Procesa una apuesta individual y determina si ha ganado
        Retorna True si la apuesta ganó, False en caso contrario
        """
        logger.info(f"Procesando apuesta {bet.id} para lotería {bet.lottery.name}: {bet.number}-{bet.series}")
        
        try:
            winning_details = self.check_all_prizes(bet)
            
            if winning_details['total_amount'] > 0:
                logger.info(f"Apuesta {bet.id} ganadora. Monto: {winning_details['total_amount']}")
                bet.status = 'WON'
                bet.won_amount = winning_details['total_amount']
                bet.winning_details = winning_details
                bet.save()
                
                # Añadir registro explícito de cada premio ganado
                for prize in winning_details['prizes']:
                    logger.info(f"Premio ganado: {prize['type']} - {prize['name']} - {prize['amount']}")
                
                return True
            else:
                logger.info(f"Apuesta {bet.id} no ganadora")
                bet.status = 'LOST'
                bet.won_amount = Decimal('0')
                bet.save()
                return False
                
        except Exception as e:
            logger.error(f"Error procesando apuesta {bet.id}: {str(e)}")
            # Evitar que la apuesta quede en estado indefinido
            bet.status = 'PLAYED'
            bet.save()
            return False

    def check_all_prizes(self, bet: 'Bet') -> Dict:
        """
        Verifica todos los tipos de premios posibles para una apuesta.
        Mejorado para evitar duplicación de premios y con mejor estructura de datos.
        """
        winning_details = {
            'prizes': [],
            'total_amount': Decimal('0'),
            'number': bet.number,
            'series': bet.series,
            'matches': [],
            'winning_number': self.winning_number,
            'winning_series': self.winning_series
        }

        # Verificación jerárquica de premios, de mayor a menor valor
        # 1. Verificar Premio Mayor (más importante)
        major_prize = self.check_major_prize(bet)
        if major_prize:
            # Si gana el premio mayor, no verifica otros premios menores
            winning_details['prizes'].append(major_prize)
            winning_details['total_amount'] += Decimal(major_prize['amount'])
            winning_details['matches'].append('MAJOR')
            # Retornamos inmediatamente porque el premio mayor excluye otros premios
            return winning_details

        # 2. Verificar Premios Secos (segundo en jerarquía)
        seco_prizes = self.check_seco_prizes(bet)
        if seco_prizes:
            for prize in seco_prizes:
                winning_details['prizes'].append(prize)
                winning_details['total_amount'] += Decimal(prize['amount'])
                winning_details['matches'].append('SECO')
            # Si gana premio seco, no verifica aproximaciones
            return winning_details

        # 3. Verificar Aproximaciones - solo si no ganó mayor ni seco
        has_won_approx = False
        
        # 3.1 Verificar Aproximaciones Misma Serie
        if bet.series == self.winning_series:
            same_series_prizes = self.check_same_series_approximations(bet)
            for prize in same_series_prizes:
                winning_details['prizes'].append(prize)
                winning_details['total_amount'] += Decimal(prize['amount'])
                winning_details['matches'].append(prize['match_type'])
                has_won_approx = True

        # 3.2 Verificar Aproximaciones Diferente Serie (solo si no ganó en misma serie)
        if bet.series != self.winning_series and not has_won_approx:
            diff_series_prizes = self.check_different_series_approximations(bet)
            for prize in diff_series_prizes:
                winning_details['prizes'].append(prize)
                winning_details['total_amount'] += Decimal(prize['amount'])
                winning_details['matches'].append(prize['match_type'])

        # 4. Verificar Premios Especiales (compatibles con aproximaciones)
        special_prizes = self.check_special_prizes(bet)
        for prize in special_prizes:
            winning_details['prizes'].append(prize)
            winning_details['total_amount'] += Decimal(prize['amount'])
            winning_details['matches'].append(prize['match_type'])

        return winning_details

    def check_major_prize(self, bet: 'Bet') -> Optional[Dict]:
        """Verifica si la apuesta ganó el premio mayor"""
        if bet.number == self.winning_number:
            if not self.lottery.requires_series or bet.series == self.winning_series:
                prize = self.prize_plan.prizes.filter(
                    prize_type__code='MAJOR'
                ).first()
                
                if prize:
                    return {
                        'type': 'MAJOR',
                        'name': 'Premio Mayor',
                        'amount': str(self.calculate_prize_amount(bet, prize)),
                        'match_type': 'Coincidencia Exacta',
                        'details': {
                            'number': bet.number,
                            'series': bet.series,
                            'matched': 'full'
                        }
                    }
        return None

    def check_seco_prizes(self, bet: 'Bet') -> List[Dict]:
        """Verifica si la apuesta coincide con premios secos"""
        seco_prizes = []
        
        # Verificar que premios_secos tenga el formato correcto
        if not isinstance(self.premios_secos, list):
            logger.warning(f"El formato de premios_secos no es una lista: {type(self.premios_secos)}")
            return []

        # Iterar sobre premios secos del resultado
        for premio_seco in self.premios_secos:
            # Validar estructura del premio seco
            if not isinstance(premio_seco, dict):
                logger.warning(f"Premio seco con formato inválido: {premio_seco}")
                continue
                
            numero = premio_seco.get('numero')
            serie = premio_seco.get('serie')
            
            if not (numero and serie):
                logger.warning(f"Premio seco sin número o serie: {premio_seco}")
                continue

            if bet.number == numero and bet.series == serie:
                # Encontrar el premio correspondiente en el plan
                secos = self.prize_plan.prizes.filter(
                    prize_type__code='SECO'
                ).order_by('-amount')
                
                if secos.exists():
                    # Asignar el premio seco de mayor valor
                    prize = secos.first()
                    seco_prizes.append({
                        'type': 'SECO',
                        'name': prize.name or 'Premio Seco',
                        'amount': str(self.calculate_prize_amount(bet, prize)),
                        'match_type': 'Premio Seco',
                        'details': {
                            'number': bet.number,
                            'series': bet.series
                        }
                    })
                    break  # Una apuesta solo puede ganar un premio seco

        return seco_prizes

    def check_same_series_approximations(self, bet: 'Bet') -> List[Dict]:
        """Verifica todas las aproximaciones posibles en la misma serie"""
        approximations = []
        
        # Obtener premios de aproximación misma serie
        same_series_prizes = self.prize_plan.prizes.filter(
            prize_type__code='APPROX_SAME_SERIES'
        ).select_related('prize_type')
        
        # No permitiremos ganar múltiples aproximaciones de la misma serie
        # Seleccionamos la de mayor valor
        best_approx = None
        best_amount = Decimal('0')

        for prize in same_series_prizes:
            match_type = self.check_approximation_match(bet, prize, same_series=True)
            if match_type:
                amount = self.calculate_prize_amount(bet, prize)
                if amount > best_amount:
                    best_amount = amount
                    best_approx = {
                        'type': 'APPROX_SAME_SERIES',
                        'name': prize.name or prize.prize_type.name,
                        'amount': str(amount),
                        'match_type': match_type,
                        'details': {
                            'matched_positions': self.get_matched_positions(bet.number, self.winning_number),
                            'series': bet.series
                        }
                    }

        if best_approx:
            approximations.append(best_approx)

        return approximations

    def check_different_series_approximations(self, bet: 'Bet') -> List[Dict]:
        """Verifica todas las aproximaciones posibles en diferente serie"""
        approximations = []
        
        diff_series_prizes = self.prize_plan.prizes.filter(
            prize_type__code='APPROX_DIFF_SERIES'
        ).select_related('prize_type')
        
        # No permitiremos ganar múltiples aproximaciones de diferente serie
        # Seleccionamos la de mayor valor
        best_approx = None
        best_amount = Decimal('0')

        for prize in diff_series_prizes:
            match_type = self.check_approximation_match(bet, prize, same_series=False)
            if match_type:
                amount = self.calculate_prize_amount(bet, prize)
                if amount > best_amount:
                    best_amount = amount
                    best_approx = {
                        'type': 'APPROX_DIFF_SERIES',
                        'name': prize.name or prize.prize_type.name,
                        'amount': str(amount),
                        'match_type': match_type,
                        'details': {
                            'matched_positions': self.get_matched_positions(bet.number, self.winning_number),
                            'series': bet.series
                        }
                    }

        if best_approx:
            approximations.append(best_approx)

        return approximations

    def check_special_prizes(self, bet: 'Bet') -> List[Dict]:
        """Verifica premios especiales como números invertidos, combinados, etc."""
        special_prizes = []
        
        special_types = self.prize_plan.prizes.filter(
            prize_type__is_special=True
        ).select_related('prize_type')

        for prize in special_types:
            if self.check_special_match(bet, prize):
                special_prizes.append({
                    'type': 'SPECIAL',
                    'name': prize.name,
                    'amount': str(self.calculate_prize_amount(bet, prize)),
                    'match_type': prize.prize_type.code,
                    'details': self.get_special_prize_details(bet, prize)
                })

        return special_prizes

    def check_approximation_match(self, bet: 'Bet', prize: 'Prize', same_series: bool) -> Optional[str]:
        """Verifica coincidencias específicas para aproximaciones"""
        prize_type = prize.prize_type
        match_rules = prize_type.match_rules
        
        # Si requiere misma serie pero no coincide, no hay premio
        if same_series and bet.series != self.winning_series:
            return None

        # Verificar coincidencias según reglas específicas
        if 'positions' in match_rules:
            positions = match_rules['positions']
            bet_digits = [bet.number[i] for i in range(4)]
            win_digits = [self.winning_number[i] for i in range(4)]
            
            # Verificar coincidencias en posiciones específicas
            matches = all(bet_digits[p] == win_digits[p] for p in positions)
            if matches:
                return self.get_match_description(positions)

        # Verificar tipos específicos de coincidencias
        if prize_type.code == 'FIRST_THREE':
            if bet.number[:3] == self.winning_number[:3]:
                return 'Tres Primeras'
        elif prize_type.code == 'LAST_THREE':
            if bet.number[-3:] == self.winning_number[-3:]:
                return 'Tres Últimas'
        elif prize_type.code == 'FIRST_TWO_LAST_ONE':
            if bet.number[:2] == self.winning_number[:2] and bet.number[-1] == self.winning_number[-1]:
                return 'Dos Primeras y Última'
        elif prize_type.code == 'FIRST_ONE_LAST_TWO':
            if bet.number[0] == self.winning_number[0] and bet.number[-2:] == self.winning_number[-2:]:
                return 'Primera y Dos Últimas'
        elif prize_type.code == 'TWO_CENTER':
            if bet.number[1:3] == self.winning_number[1:3]:
                return 'Dos del Centro'

        return None

    def check_special_match(self, bet: 'Bet', prize: 'Prize') -> bool:
        """Verifica coincidencias para premios especiales"""
        prize_type = prize.prize_type
        
        if prize_type.code == 'INVERTED':
            return bet.number == self.winning_number[::-1]
        
        elif prize_type.code == 'COMBINADO':
            # Verifica si los dígitos coinciden en cualquier orden
            return sorted(bet.number) == sorted(self.winning_number)
        
        elif prize_type.code == 'ANTERIOR':
            try:
                anterior = str(int(self.winning_number) - 1).zfill(4)
                return bet.number == anterior
            except ValueError:
                return False
        
        elif prize_type.code == 'POSTERIOR':
            try:
                posterior = str(int(self.winning_number) + 1).zfill(4)
                return bet.number == posterior
            except ValueError:
                return False
        
        elif prize_type.code == 'SERIES':
            return bet.series == self.winning_series
        
        return False

    def check_seco_match(self, bet: 'Bet', prize: 'Prize') -> bool:
        """Verifica coincidencia con premio seco"""
        if not self.premios_secos:
            return False
            
        # Verificar en la lista de premios secos
        for premio_seco in self.premios_secos:
            if bet.number == premio_seco.get('numero'):
                if prize.prize_type.requires_series:
                    return bet.series == premio_seco.get('serie')
                return True
                
        return False

    def calculate_prize_amount(self, bet: 'Bet', prize: 'Prize') -> Decimal:
        """
        Calcula el monto de premio que corresponde a una apuesta según las fracciones
        """
        try:
            # Validar que los valores sean números y no estén vacíos
            bet_amount = bet.amount or Decimal('0')
            fraction_price = self.lottery.fraction_price or Decimal('1')
            prize_amount = prize.amount or Decimal('0')
            
            if fraction_price == 0:
                logger.error(f"Precio de fracción es 0 para lotería {self.lottery.name}, no se puede calcular premio")
                return Decimal('0')
            
            # 1. Calcular cuántas fracciones compró el apostador
            fractions_bought = bet.fractions if hasattr(bet, 'fractions') and bet.fractions > 0 else Decimal(bet_amount / fraction_price)
            
            # 2. Si la apuesta es por todas las fracciones, paga el premio completo
            if fractions_bought >= self.lottery.fraction_count:
                logger.info(f"Apuesta por billete completo: {fractions_bought} fracciones. Premio completo: {prize_amount}")
                return prize_amount
            
            # 3. Si es fracción, calcular la parte proporcional usando el fraction_amount pre-calculado
            if prize.fraction_amount:
                prize_per_fraction = prize.fraction_amount
            else:
                # Si no tiene fraction_amount, dividir entre total de fracciones
                prize_per_fraction = prize_amount / self.lottery.fraction_count
                
            total_prize = prize_per_fraction * fractions_bought
            
            # Registro para auditoría
            logger.info(
                f"Cálculo de premio: {fractions_bought} fracciones x {prize_per_fraction}/fracción = {total_prize} " +
                f"(Premio total: {prize_amount}, Fracciones totales: {self.lottery.fraction_count})"
            )
            
            return total_prize
                
        except (TypeError, ValueError, ZeroDivisionError) as e:
            logger.error(
                f"Error calculando premio para apuesta {bet.id}: {str(e)} - " +
                f"Amount: {bet_amount}, Fraction Price: {fraction_price}, Prize Amount: {prize_amount}"
            )
            return Decimal('0')

    def get_matched_positions(self, number1: str, number2: str) -> List[int]:
        """Obtiene las posiciones coincidentes entre dos números"""
        return [i for i in range(len(number1)) if i < len(number2) and number1[i] == number2[i]]

    def get_match_description(self, positions: List[int]) -> str:
        """Genera descripción del tipo de coincidencia"""
        # Patrones comunes de coincidencia
        patterns = {
            (0, 1, 2): 'Tres Primeras',
            (1, 2, 3): 'Tres Últimas',
            (0, 1): 'Dos Primeras',
            (2, 3): 'Dos Últimas',
            (1, 2): 'Dos del Centro',
            (3,): 'Última',
            (0,): 'Primera',
            (0, 1, 3): 'Dos Primeras y Última',
            (0, 2, 3): 'Primera y Dos Últimas'
        }
        
        # Convertir posiciones a tupla para búsqueda en diccionario
        pos_tuple = tuple(sorted(positions))
        return patterns.get(pos_tuple, 'Coincidencia Parcial')

    def get_special_prize_details(self, bet: 'Bet', prize: 'Prize') -> Dict:
        """Obtiene detalles específicos para premios especiales"""
        details = {
            'prize_name': prize.name,
            'number': bet.number,
            'series': bet.series if prize.prize_type.requires_series else None,
            'special_type': prize.prize_type.code
        }
        
        if prize.prize_type.code == 'INVERTED':
            details['inverted_number'] = self.winning_number[::-1]
        elif prize.prize_type.code == 'COMBINADO':
            details['original_number'] = bet.number
            details['winning_number'] = self.winning_number
        
        return details
