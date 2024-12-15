from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

from cloudinary.models import CloudinaryField

from apps.default.models.base_model import BaseModel


class Lottery(BaseModel):
    """Modelo principal para las loterías"""
    name = models.CharField('Nombre', max_length=100)
    code = models.CharField('Código', max_length=50, unique=True)
    draw_day = models.CharField(
        'Día de sorteo',
        max_length=10,
        choices=[
            ('MONDAY', 'Lunes'),
            ('TUESDAY', 'Martes'),
            ('WEDNESDAY', 'Miércoles'),
            ('THURSDAY', 'Jueves'),
            ('FRIDAY', 'Viernes'),
            ('SATURDAY', 'Sábado'),
        ]
    )
    draw_time = models.TimeField('Hora del sorteo')
    fraction_count = models.PositiveIntegerField('Cantidad de fracciones')
    fraction_price = models.DecimalField(
        'Precio fracción',
        max_digits=20,
        decimal_places=2
    )
    major_prize_amount = models.DecimalField(
        'Premio mayor',
        max_digits=20,
        decimal_places=2
    )
    min_bet_amount = models.DecimalField(
        'Apuesta mínima',
        max_digits=20,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    max_bet_amount = models.DecimalField(
        'Apuesta máxima',
        max_digits=20,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    logo_url = models.URLField('Logo URL', blank=True)
    is_active = models.BooleanField('Activa', default=True)
    requires_series = models.BooleanField('Requiere serie', default=True)

    # Nuevos campos para Cloudinary
    number_ranges_file = CloudinaryField(
        'Archivo de rangos',
        folder='lottery/ranges/',
        resource_type='raw',
        null=True,
        blank=True
    )
    unsold_tickets_file = CloudinaryField(
        'Archivo de billetes no vendidos',
        folder='lottery/unsold/',
        resource_type='raw',
        null=True,
        blank=True
    )
    sales_file = CloudinaryField(
        'Archivo de ventas',
        folder='lottery/sales/',
        resource_type='raw',
        null=True,
        blank=True
    )

    class Meta:
        verbose_name = 'Lotería'
        verbose_name_plural = 'Loterías'
        ordering = ['name']

    def __str__(self):
        return self.name
