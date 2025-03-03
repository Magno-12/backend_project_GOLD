from typing import List, Dict, Optional, Tuple
from django.utils import timezone
from datetime import datetime, time
from decimal import Decimal
from django.db import models, transaction

from apps.lottery.models import Lottery, Bet, PrizePlan, LotteryNumberCombination
from apps.users.models import User
from apps.payments.models import UserBalance
import logging

logger = logging.getLogger(__name__)


class LotteryValidationService:
    def __init__(self, lottery: Lottery):
        self.lottery = lottery
        self.validation_errors = []

    def validate_combination_fractions(self, number: str, series: str, fractions: int, next_draw_date, fraction_counts=None) -> tuple[bool, int]:
        """
        Valida si hay suficientes fracciones disponibles para una combinación.
        """
        from django.db.models import Sum
        
        # Obtener todas las apuestas existentes para esta combinación
        existing_bets = Bet.objects.filter(
            lottery=self.lottery,
            number=number,
            series=series,
            draw_date=next_draw_date,
            status='PENDING'
        )
        
        # Calcular el total de fracciones ya vendidas
        sold_fractions = existing_bets.aggregate(
            total=Sum('fractions')
        )['total'] or 0
        
        # Número máximo de fracciones permitidas para esta lotería
        max_fractions = self.lottery.fraction_count
        
        # Calcular fracciones disponibles
        available_fractions = max_fractions - sold_fractions
        
        # Si no quedan fracciones disponibles
        if available_fractions <= 0:
            return False, 0
        
        # Si piden más de las disponibles
        if fractions > available_fractions:
            return False, available_fractions
        
        # Si hay suficientes, devolver válido
        return True, available_fractions - fractions

    def get_available_numbers(self, series: str) -> List[str]:
        """Obtiene números disponibles en una serie"""
        valid_combinations = set(
            LotteryNumberCombination.objects.filter(
                lottery=self.lottery,
                series=series,
                draw_date=self.lottery.next_draw_date,
                is_active=True
            ).exclude(
                used_fractions__gte=models.F('total_fractions')
            ).values_list('number', flat=True)
        )

        if valid_combinations:
            return sorted(list(valid_combinations))

        used_numbers = set(Bet.objects.filter(
            lottery=self.lottery,
            series=series,
            draw_date=self.lottery.next_draw_date,
            status='PENDING'
        ).values_list('number', flat=True))

        all_numbers = set(f"{i:04d}" for i in range(10000))
        return sorted(all_numbers - used_numbers)

    def validate_bet_request(self,
                           user: User,
                           number: str,
                           series: str,
                           fractions: int,
                           amount: Decimal,
                           fraction_counts: dict = None) -> Dict:
        """Validación completa de una solicitud de apuesta"""
        fraction_counts = fraction_counts or {}

        # 1. Validar estado de la lotería
        if not self.lottery.is_active:
            self.validation_errors.append("La lotería no está activa")

        # 2. Validar horario
        if not self.lottery.is_open_for_bets():
            self.validation_errors.append(
                f"Fuera del horario permitido para apuestas (hasta {self.lottery.closing_time})"
            )

        # 3. Validar fracciones disponibles
        is_valid, remaining = self.validate_combination_fractions(
            number, series, fractions,
            self.lottery.next_draw_date, fraction_counts
        )
        if not is_valid:
            if remaining == 0:
                self.validation_errors.append(
                    'No hay fracciones disponibles para esta combinación'
                )
            else:
                self.validation_errors.append(
                    f'Solo quedan {remaining} fracciones disponibles para esta combinación'
                )

        # 4. Validar número y serie
        if not self.validate_number_format(number):
            self.validation_errors.append(
                "El número debe ser de 4 dígitos (0000-9999)"
            )

        if not self.validate_series_format(series):
            self.validation_errors.append(
                "La serie debe ser de 3 dígitos (000-999)"
            )

        # 5. Validar monto
        if not self.validate_bet_amount(amount, fractions):
            self.validation_errors.append(
                f"Monto inválido para {fractions} fracciones"
            )

        # 6. Validar saldo del usuario
        if not self.validate_user_balance(user, amount):
            self.validation_errors.append("Saldo insuficiente")

        # 7. Validar límites de apuesta
        if not self.validate_bet_limits(amount):
            self.validation_errors.append(
                f"El monto debe estar entre {self.lottery.min_bet_amount} y {self.lottery.max_bet_amount}"
            )

        return {
            'is_valid': len(self.validation_errors) == 0,
            'errors': self.validation_errors
        }

    def validate_number_format(self, number: str) -> bool:
        """Valida formato del número"""
        return (
            number.isdigit() and
            len(number) == 4 and
            0 <= int(number) <= 9999
        )

    def validate_series_format(self, series: str) -> bool:
        """Valida formato de la serie"""
        if not self.lottery.requires_series:
            return True

        return (
            series.isdigit() and
            len(series) == 3 and
            0 <= int(series) <= 999
        )

    def validate_bet_amount(self, amount: Decimal, fractions: int) -> bool:
        """Valida que el monto corresponda a las fracciones"""
        expected_amount = self.lottery.fraction_price * fractions
        return amount == expected_amount

    def validate_user_balance(self, user: User, amount: Decimal) -> bool:
        """Valida que el usuario tenga saldo suficiente"""
        try:
            balance = UserBalance.objects.get(user=user)
            return balance.balance >= amount
        except UserBalance.DoesNotExist:
            return False

    def validate_bet_limits(self, amount: Decimal) -> bool:
        """Valida límites de apuesta"""
        return (
            self.lottery.min_bet_amount <= amount <= self.lottery.max_bet_amount
        )

    @transaction.atomic
    def reserve_fractions(self, number: str, series: str, fractions: int) -> bool:
        """Reserva fracciones para una combinación"""
        try:
            combination = LotteryNumberCombination.objects.select_for_update().get(
                lottery=self.lottery,
                number=number,
                series=series,
                draw_date=self.lottery.next_draw_date,
                is_active=True
            )
            
            if combination.available_fractions() >= fractions:
                combination.used_fractions += fractions
                combination.save()
                return True
            return False
        except LotteryNumberCombination.DoesNotExist:
            return True

    def get_bet_summary(self,
                       number: str,
                       series: str,
                       fractions: int) -> Dict:
        """Obtiene resumen de la apuesta y premios posibles"""
        active_plan = PrizePlan.get_active_plan(self.lottery)
        if not active_plan:
            return None

        fraction_ratio = fractions / self.lottery.fraction_count

        return {
            'lottery': self.lottery.name,
            'number': number,
            'series': series,
            'fractions': fractions,
            'amount_per_fraction': float(self.lottery.fraction_price),
            'total_amount': float(self.lottery.fraction_price * fractions),
            'draw_date': self.lottery.next_draw_date,
            'draw_number': self.lottery.last_draw_number + 1,
            'potential_prizes': {
                'major': {
                    'amount': float(active_plan.get_major_prize().fraction_amount * fractions),
                    'description': 'Premio Mayor'
                },
                'approximations': [
                    {
                        'type': prize.prize_type.name,
                        'amount': float(prize.fraction_amount * fractions),
                        'description': prize.name or prize.prize_type.name
                    }
                    for prize in active_plan.prizes.filter(
                        prize_type__code__startswith='APPROX_'
                    )
                ]
            }
        }

    def get_last_results(self, limit: int = 5) -> List[Dict]:
        """Obtiene últimos resultados de la lotería"""
        from apps.lottery.models import LotteryResult

        results = LotteryResult.objects.filter(
            lottery=self.lottery
        ).order_by('-fecha')[:limit]

        return [{
            'date': result.fecha,
            'number': result.numero,
            'series': result.numero_serie,
            'prizes': result.premios_secos
        } for result in results]
