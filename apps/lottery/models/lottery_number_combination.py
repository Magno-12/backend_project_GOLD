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
    # Añadir el campo is_winner con un valor predeterminado
    is_winner = models.BooleanField(
        'Es ganadora',
        default=False,
        help_text='Indica si esta combinación resultó ganadora en el sorteo'
    )
    prize_amount = models.DecimalField(
        'Monto del premio',
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Monto del premio ganado si esta combinación es ganadora'
    )
    prize_type = models.CharField(
        'Tipo de premio',
        max_length=50,
        null=True,
        blank=True,
        help_text='Tipo de premio ganado (Mayor, Seco, Aproximación, etc.)'
    )
    prize_detail = models.JSONField(
        'Detalle del premio',
        null=True,
        blank=True,
        default=dict,
        help_text='Información detallada del premio ganado'
    )

    class Meta:
        verbose_name = 'Combinación de Lotería'
        verbose_name_plural = 'Combinaciones de Lotería'
        unique_together = ['lottery', 'number', 'series', 'draw_date']
        indexes = [
            models.Index(fields=['lottery', 'number', 'series']),
            models.Index(fields=['draw_date']),
            models.Index(fields=['is_winner'])
        ]

    def available_fractions(self):
        return self.total_fractions - self.used_fractions

    def reserve_fractions_atomic(self, fractions_to_reserve):
        """
        Reserva fracciones de forma atómica, verificando nuevamente la disponibilidad.
        Retorna True si se reservaron correctamente, False si no hay suficientes disponibles.
        """
        from django.db import transaction

        with transaction.atomic():
            # Volver a cargar la instancia con bloqueo para garantizar consistencia
            fresh_instance = LotteryNumberCombination.objects.select_for_update().get(pk=self.pk)

            # Verificar disponibilidad
            available = fresh_instance.total_fractions - fresh_instance.used_fractions
            if available < fractions_to_reserve:
                return False

            # Actualizar fracciones usadas
            fresh_instance.used_fractions += fractions_to_reserve
            fresh_instance.save()

            # Actualizar la instancia actual con los nuevos valores
            self.used_fractions = fresh_instance.used_fractions

            return True

    def __str__(self):
        return f"{self.lottery.name} - {self.number}-{self.series}"
