from typing import Dict, List, Optional
from decimal import Decimal
from django.db import transaction
from django.utils import timezone


class LotteryWinnerService:
    """Servicio completo para procesar resultados y determinar ganadores de lotería"""

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
        self.premios_secos = lottery_result.premios_secos

    @transaction.atomic
    def process_results(self):
        """Procesa los resultados y actualiza todas las apuestas pendientes"""
        print(f"Procesando resultados para {self.lottery.name} - {self.result.fecha}")
        
        pending_bets = self.lottery.bets.filter(
            draw_date=self.result.fecha,
            status='PENDING'
        ).select_related('user')

        for bet in pending_bets:
            self.process_bet(bet)

    def process_bet(self, bet: 'Bet'):
        """Procesa una apuesta individual y determina todos sus premios posibles"""
        print(f"Procesando apuesta {bet.id}: {bet.number}-{bet.series}")
        
        winning_details = self.check_all_prizes(bet)
        
        if winning_details['total_amount'] > 0:
            bet.status = 'WON'
            bet.won_amount = winning_details['total_amount']
            bet.winning_details = winning_details
            print(f"¡Apuesta ganadora! Monto: {bet.won_amount}")
        else:
            bet.status = 'LOST'
            bet.won_amount = Decimal('0')
            print("Apuesta no ganadora")
        
        bet.save()

    def check_all_prizes(self, bet: 'Bet') -> Dict:
        """Verifica todos los tipos de premios posibles para una apuesta"""
        winning_details = {
            'prizes': [],
            'total_amount': Decimal('0'),
            'number': bet.number,
            'series': bet.series,
            'matches': []
        }

        # 1. Verificar Premio Mayor
        major_prize = self.check_major_prize(bet)
        if major_prize:
            winning_details['prizes'].append(major_prize)
            winning_details['total_amount'] += Decimal(major_prize['amount'])
            winning_details['matches'].append('MAJOR')

        # 2. Verificar Premios Secos
        seco_prizes = self.check_seco_prizes(bet)
        for prize in seco_prizes:
            winning_details['prizes'].append(prize)
            winning_details['total_amount'] += Decimal(prize['amount'])
            winning_details['matches'].append('SECO')

        # 3. Verificar Aproximaciones Misma Serie
        if bet.series == self.winning_series:
            same_series_prizes = self.check_same_series_approximations(bet)
            for prize in same_series_prizes:
                winning_details['prizes'].append(prize)
                winning_details['total_amount'] += Decimal(prize['amount'])
                winning_details['matches'].append(prize['match_type'])

        # 4. Verificar Aproximaciones Diferente Serie
        if bet.series != self.winning_series:
            diff_series_prizes = self.check_different_series_approximations(bet)
            for prize in diff_series_prizes:
                winning_details['prizes'].append(prize)
                winning_details['total_amount'] += Decimal(prize['amount'])
                winning_details['matches'].append(prize['match_type'])

        # 5. Verificar Premios Especiales
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
        """Verifica todos los premios secos posibles"""
        seco_prizes = []
        
        # Obtener premios secos del plan
        plan_secos = self.prize_plan.prizes.filter(
            prize_type__code='SECO'
        ).select_related('prize_type')

        for prize in plan_secos:
            # Verificar coincidencia con número y serie si aplica
            if self.check_seco_match(bet, prize):
                seco_prizes.append({
                    'type': 'SECO',
                    'name': prize.name or 'Premio Seco',
                    'amount': str(self.calculate_prize_amount(bet, prize)),
                    'match_type': 'Premio Seco',
                    'details': {
                        'number': bet.number,
                        'series': bet.series if prize.prize_type.requires_series else None
                    }
                })

        return seco_prizes

    def check_same_series_approximations(self, bet: 'Bet') -> List[Dict]:
        """Verifica todas las aproximaciones posibles en la misma serie"""
        approximations = []
        
        # Obtener premios de aproximación misma serie
        same_series_prizes = self.prize_plan.prizes.filter(
            prize_type__code='APPROX_SAME_SERIES'
        ).select_related('prize_type')

        for prize in same_series_prizes:
            match_type = self.check_approximation_match(bet, prize, same_series=True)
            if match_type:
                approximations.append({
                    'type': 'APPROX_SAME_SERIES',
                    'name': prize.name or prize.prize_type.name,
                    'amount': str(self.calculate_prize_amount(bet, prize)),
                    'match_type': match_type,
                    'details': {
                        'matched_positions': self.get_matched_positions(bet.number, self.winning_number),
                        'series': bet.series
                    }
                })

        return approximations

    def check_different_series_approximations(self, bet: 'Bet') -> List[Dict]:
        """Verifica todas las aproximaciones posibles en diferente serie"""
        approximations = []
        
        diff_series_prizes = self.prize_plan.prizes.filter(
            prize_type__code='APPROX_DIFF_SERIES'
        ).select_related('prize_type')

        for prize in diff_series_prizes:
            match_type = self.check_approximation_match(bet, prize, same_series=False)
            if match_type:
                approximations.append({
                    'type': 'APPROX_DIFF_SERIES',
                    'name': prize.name or prize.prize_type.name,
                    'amount': str(self.calculate_prize_amount(bet, prize)),
                    'match_type': match_type,
                    'details': {
                        'matched_positions': self.get_matched_positions(bet.number, self.winning_number),
                        'series': bet.series
                    }
                })

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
            anterior = str(int(self.winning_number) - 1).zfill(4)
            return bet.number == anterior
        
        elif prize_type.code == 'POSTERIOR':
            posterior = str(int(self.winning_number) + 1).zfill(4)
            return bet.number == posterior
        
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
        """Calcula monto del premio basado en la apuesta y fracciones"""
        fraction_ratio = Decimal(bet.amount) / self.lottery.fraction_price
        return prize.fraction_amount * fraction_ratio

    def get_matched_positions(self, number1: str, number2: str) -> List[int]:
        """Obtiene las posiciones coincidentes entre dos números"""
        return [i for i in range(len(number1)) if number1[i] == number2[i]]

    def get_match_description(self, positions: List[int]) -> str:
        """Genera descripción del tipo de coincidencia"""
        if positions == [0, 1, 2]:
            return 'Tres Primeras'
        elif positions == [-3, -2, -1]:
            return 'Tres Últimas'
        elif positions == [0, 1]:
            return 'Dos Primeras'
        elif positions == [-2, -1]:
            return 'Dos Últimas'
        elif positions == [1, 2]:
            return 'Dos del Centro'
        elif positions == [-1]:
            return 'Última'
        return 'Coincidencia Parcial'

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
