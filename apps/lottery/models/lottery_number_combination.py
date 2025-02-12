from django.db import models
from django.core.validators import RegexValidator


class LotteryNumberCombination(models.Model):
    """Modelo para gestionar combinaciones válidas de números y series"""
    lottery = models.ForeignKey(
        'lottery.Lottery',
        on_delete=models.CASCADE,
        related_name='valid_combinations'
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
        max_length=3,
        validators=[
            RegexValidator(
                r'^\d{3}$',
                'Debe ser una serie de 3 dígitos'
            )
        ]
    )
    total_fractions = models.PositiveIntegerField(
        'Total de fracciones',
        help_text='Número total de fracciones disponibles'
    )
    used_fractions = models.PositiveIntegerField(
        'Fracciones usadas',
        default=0
    )
    is_active = models.BooleanField(
        'Activa',
        default=True
    )
    draw_date = models.DateField(
        'Fecha del sorteo',
        null=True
    )

    class Meta:
        verbose_name = 'Combinación de Lotería'
        verbose_name_plural = 'Combinaciones de Lotería'
        unique_together = ['lottery', 'number', 'series', 'draw_date']
        indexes = [
            models.Index(fields=['lottery', 'number', 'series']),
            models.Index(fields=['draw_date'])
        ]

    def available_fractions(self):
        return self.total_fractions - self.used_fractions

    def __str__(self):
        return f"{self.lottery.name} - {self.number}-{self.series}"
