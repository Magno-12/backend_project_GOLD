from django.db import models
from django.core.validators import RegexValidator, MinValueValidator, MaxValueValidator

from apps.default.models.base_model import BaseModel


class Bet(BaseModel):
    """Apuestas de usuarios"""
    lottery = models.ForeignKey(
        'lottery.Lottery',
        on_delete=models.PROTECT,
        related_name='bets'
    )
    user = models.ForeignKey(
        'users.User',
        on_delete=models.PROTECT,
        related_name='bets'
    )
    number = models.CharField(
        'Número',
        max_length=4,
        validators=[
            RegexValidator(
                r'^\d{4}$',
                'Debe ser un número de 4 dígitos'
            )
        ]
    )
    series = models.CharField(
        'Serie',
        max_length=10,
        blank=True,
        null=True
    )
    amount = models.DecimalField(
        'Monto apostado',
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    draw_date = models.DateField('Fecha del sorteo')
    status = models.CharField(
        'Estado',
        max_length=20,
        choices=[
            ('PENDING', 'Pendiente'),
            ('PLAYED', 'Jugada'),
            ('WON', 'Ganadora'),
            ('LOST', 'Perdedora'),
            ('CANCELLED', 'Cancelada')
        ],
        default='PENDING'
    )
    won_amount = models.DecimalField(
        'Monto ganado',
        max_digits=20,
        decimal_places=2,
        default=0
    )
    winning_details = models.JSONField(
        'Detalles de premio',
        default=dict,
        blank=True
    )

    class Meta:
        verbose_name = 'Apuesta'
        verbose_name_plural = 'Apuestas'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.lottery.name} - {self.number}"
