from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator, RegexValidator
from django.utils import timezone
from django.db.models import Sum, F
from datetime import time, timedelta
from cloudinary.models import CloudinaryField
from django.contrib.postgres.fields import ArrayField
import pytz
from decimal import Decimal
from datetime import datetime, time

from apps.default.models.base_model import BaseModel
from apps.lottery.models.bet import Bet


class Lottery(BaseModel):
    DAYS_CHOICES = [
        ('MONDAY', 'Lunes'),
        ('TUESDAY', 'Martes'),
        ('WEDNESDAY', 'Miércoles'),
        ('THURSDAY', 'Jueves'),
        ('FRIDAY', 'Viernes'),
        ('SATURDAY', 'Sábado'),
    ]

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
        validators=[MinValueValidator(Decimal('0'))]
    )
    max_bet_amount = models.DecimalField(
        'Apuesta máxima',
        max_digits=20,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0'))]
    )
    logo_url = models.URLField('Logo URL', blank=True)
    is_active = models.BooleanField('Activa', default=True)
    requires_series = models.BooleanField('Requiere serie', default=True)

    # Campos de archivos
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

    # Campos de sorteo
    closing_time = models.TimeField(
        'Hora límite de compra',
        default=time(20, 0),
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

    # Nuevos campos de validación
    number_range_start = models.CharField(
        'Rango inicial',
        max_length=4,
        validators=[
            RegexValidator(
                r'^\d{4}$',
                'Debe ser un número de 4 dígitos'
            )
        ],
        help_text='Número inicial del rango válido'
    )
    number_range_end = models.CharField(
        'Rango final',
        max_length=4,
        validators=[
            RegexValidator(
                r'^\d{4}$',
                'Debe ser un número de 4 dígitos'
            )
        ],
        help_text='Número final del rango válido'
    )
    allow_duplicate_numbers = models.BooleanField(
        'Permitir números duplicados en series',
        default=False,
        help_text='Si está activo, permite el mismo número en diferentes series'
    )
    max_fractions_per_combination = models.PositiveIntegerField(
        'Máximo fracciones por combinación',
        default=1,
        help_text='Máximo de fracciones por combinación número-serie'
    )

    available_series = ArrayField(
        models.CharField(max_length=3),
        verbose_name='Series disponibles',
        help_text='Series disponibles para esta lotería',
        default=list,
        blank=True
    )

    def validate_number_in_range(self, number: str) -> bool:
        try:
            num = int(number)
            start = int(self.number_range_start)
            end = int(self.number_range_end)
            return start <= num <= end
        except ValueError:
            return False

    def validate_bet(self, number: str, series: str, fractions: int) -> tuple[bool, str]:
        # Validar rango
        if not self.validate_number_in_range(number):
            return False, f"Número fuera del rango permitido ({self.number_range_start}-{self.number_range_end})"
            
        # Validar serie disponible
        if self.requires_series and series not in self.available_series:
            return False, "Serie no disponible para esta lotería"

        # Validar combinación número-serie SOLO en esta lotería
        existing_bet = Bet.objects.filter(
            lottery=self,  # Solo en esta lotería
            number=number,
            series=series,
            draw_date=self.next_draw_date
        ).exists()
        
        if existing_bet:
            return False, "Esta combinación número-serie ya existe para esta lotería"

        # Validar fracciones para esta combinación
        existing_fractions = Bet.objects.filter(
            lottery=self,  # Solo en esta lotería
            number=number,
            series=series,
            draw_date=self.next_draw_date
        ).aggregate(
            total_fractions=models.Sum(
                models.F('amount') / models.F('lottery__fraction_price')
            )
        )['total_fractions'] or 0

        if existing_fractions + fractions > self.max_fractions_per_combination:
            return False, f"Máximo {self.max_fractions_per_combination} fracciones por combinación"

        return True, "Apuesta válida"

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
        if days_ahead <= 0:  # Si ya pasó el día esta semana
            days_ahead += 7
        return days_ahead

    def is_open_for_bets(self):
        now = timezone.now().time()
        return now < self.closing_time and self.is_active

    def save(self, *args, **kwargs):
        if self.is_active:
            if not self.pk or 'last_draw_number' in kwargs:
                self.last_draw_number = (self.last_draw_number or 0) + 1
            
            if not self.next_draw_date:
                today = timezone.now().date()
                days_ahead = self.get_days_until_next_draw()
                self.next_draw_date = today + timedelta(days=days_ahead)
            
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = 'Lotería'
        verbose_name_plural = 'Loterías'
        ordering = ['name']
        constraints = [
        # Este constraint no debería estar aquí
        models.UniqueConstraint(
            fields=['code', 'name'],
            name='unique_lottery_code_name'
        ),
        models.CheckConstraint(
            check=models.Q(number_range_start__lte=models.F('number_range_end')),
            name='valid_number_range'
        )
    ]

    def __str__(self):
        return self.name
