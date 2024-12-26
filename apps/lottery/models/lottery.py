from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from datetime import time, timedelta
from cloudinary.models import CloudinaryField

from apps.default.models.base_model import BaseModel


class Lottery(BaseModel):
    # Constante para los días
    DAYS_CHOICES = [
        ('MONDAY', 'Lunes'),
        ('TUESDAY', 'Martes'),
        ('WEDNESDAY', 'Miércoles'),
        ('THURSDAY', 'Jueves'),
        ('FRIDAY', 'Viernes'),
        ('SATURDAY', 'Sábado'),
    ]

    """Modelo principal para las loterías"""
    name = models.CharField('Nombre', max_length=100)
    code = models.CharField('Código', max_length=50, unique=True)
    draw_day = models.CharField(
        'Día de sorteo',
        max_length=10,
        choices=DAYS_CHOICES
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
    series = models.CharField('Series', max_length=255, blank=True, help_text='Series de la lotería separadas por comas')

    # Cloudinary files
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

    # Campos para manejo de sorteos
    closing_time = models.TimeField(
        'Hora límite de compra',
        default=time(20, 0),  # 8:00 PM por defecto
        help_text='Hora límite para realizar apuestas'
    )
    last_draw_number = models.PositiveIntegerField(
        'Último número de sorteo',
        help_text='Se incrementa automáticamente',
        default=0
    )
    next_draw_date = models.DateField(
        'Próxima fecha de sorteo',
        help_text='Se actualiza automáticamente',
        null=True,
        blank=True
    )

    class Meta:
        verbose_name = 'Lotería'
        verbose_name_plural = 'Loterías'
        ordering = ['name']

    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        # Solo actualizar sorteo si es una lotería activa
        if self.is_active:
            # Incrementar automáticamente el número de sorteo
            if not self.pk or 'last_draw_number' in kwargs:
                self.last_draw_number = (self.last_draw_number or 0) + 1
            
            # Calcular próxima fecha de sorteo si no existe
            if not self.next_draw_date:
                today = timezone.now().date()
                days_ahead = self.get_days_until_next_draw()
                self.next_draw_date = today + timedelta(days=days_ahead)
            
        super().save(*args, **kwargs)

    def get_days_until_next_draw(self):
        """Calcula días hasta el próximo sorteo"""
        today = timezone.now().date()
        current_weekday = today.weekday()
        
        # Convertir día de sorteo a número (0-6)
        draw_weekday = {
            'MONDAY': 0,
            'TUESDAY': 1,
            'WEDNESDAY': 2,
            'THURSDAY': 3,
            'FRIDAY': 4,
            'SATURDAY': 5,
        }[self.draw_day]
        
        days_ahead = draw_weekday - current_weekday
        if days_ahead <= 0:
            days_ahead += 7
        return days_ahead

    def is_open_for_bets(self):
        """Verifica si la lotería está abierta para apuestas"""
        now = timezone.now().time()
        return now < self.closing_time and self.is_active
