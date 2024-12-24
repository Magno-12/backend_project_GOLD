from typing import List, Dict, Optional
from django.utils import timezone
from datetime import datetime, time
from decimal import Decimal

from apps.lottery.models import Lottery, Bet, PrizePlan
from apps.users.models import User
from apps.payments.models import UserBalance


class LotteryValidationService:
    def __init__(self, lottery: Lottery):
        self.lottery = lottery
        self.validation_errors = []

    def validate_number_availability(self, number: str, series: str) -> bool:
        """Valida disponibilidad de número en serie"""
        return not Bet.objects.filter(
            lottery=self.lottery,
            number=number,
            series=series,
            draw_date=self.lottery.next_draw_date,
            status='PENDING'
        ).exists()

    def get_available_numbers(self, series: str) -> List[str]:
        """Obtiene números disponibles en una serie"""
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
                           amount: Decimal) -> Dict:
        """Validación completa de una solicitud de apuesta"""

        # 1. Validar estado de la lotería
        if not self.lottery.is_active:
            self.validation_errors.append("La lotería no está activa")

        # 2. Validar horario
        now = timezone.now().time()
        if now >= self.lottery.closing_time:
            self.validation_errors.append(
                f"Fuera del horario permitido para apuestas (hasta {self.lottery.closing_time})"
            )

        # 3. Validar número
        if not self.validate_number_format(number):
            self.validation_errors.append(
                "El número debe ser de 4 dígitos (0000-9999)"
            )
        elif not self.validate_number_availability(number, series):
            self.validation_errors.append(
                f"El número {number} no está disponible en la serie {series}"
            )

        # 4. Validar serie
        if not self.validate_series_format(series):
            self.validation_errors.append(
                "La serie debe ser de 3 dígitos (000-999)"
            )

        # 5. Validar fracciones
        if not self.validate_fractions(fractions):
            self.validation_errors.append(
                f"Cantidad de fracciones inválida. Máximo: {self.lottery.fraction_count}"
            )

        # 6. Validar monto
        if not self.validate_bet_amount(amount, fractions):
            self.validation_errors.append(
                f"Monto inválido para {fractions} fracciones"
            )

        # 7. Validar saldo del usuario
        if not self.validate_user_balance(user, amount):
            self.validation_errors.append("Saldo insuficiente")

        # 8. Validar límites de apuesta
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

    def validate_fractions(self, fractions: int) -> bool:
        """Valida cantidad de fracciones"""
        return (
            isinstance(fractions, int) and 
            1 <= fractions <= self.lottery.fraction_count
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
