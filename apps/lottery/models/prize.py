from django.db import models

from apps.default.models.base_model import BaseModel


class Prize(BaseModel):
    """Premios específicos del plan"""
    prize_plan = models.ForeignKey(
        'lottery.PrizePlan',
        on_delete=models.CASCADE,
        related_name='prizes'
    )
    prize_type = models.ForeignKey(
        'lottery.PrizeType',
        on_delete=models.PROTECT,
        related_name='prizes'
    )
    amount = models.DecimalField(
        'Monto',
        max_digits=20,
        decimal_places=2
    )
    quantity = models.PositiveIntegerField(
        'Cantidad',
        default=1,
        help_text='Número de premios de este tipo'
    )
    fraction_amount = models.DecimalField(
        'Monto por fracción',
        max_digits=20,
        decimal_places=2
    )
    custom_rules = models.JSONField(
        'Reglas personalizadas',
        default=dict,
        blank=True,
        help_text='Reglas específicas para este premio'
    )
    name = models.CharField(
        'Nombre personalizado',
        max_length=100,
        blank=True,
        help_text='Para premios especiales como "Sueldazo cafetero"'
    )
    order = models.PositiveIntegerField('Orden', default=0)

    class Meta:
        verbose_name = 'Premio'
        verbose_name_plural = 'Premios'
        ordering = ['order', 'id']

    def __str__(self):
        if self.name:
            return f"{self.prize_plan.lottery.name} - {self.name}"
        return f"{self.prize_plan.lottery.name} - {self.prize_type.name}"
