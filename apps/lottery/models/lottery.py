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
    series = models.CharField(
        'Serie por defecto',
        max_length=3,
        validators=[
            RegexValidator(
                r'^\d{3}$',
                'Debe ser una serie de 3 dígitos'
            )
        ],
        default='000',
        null=True,
        blank=True
    )
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
        validators=[MinValueValidator(1)],
        help_text='Máximo de fracciones que un usuario puede comprar por combinación número-serie'
    )

    available_series = ArrayField(
        models.CharField(max_length=3),
        verbose_name='Series disponibles',
        help_text='Series disponibles para esta lotería',
        default=list,
        blank=True
    )

    def validate_number_in_range(self, number: str) -> bool:
        """Valifica si el número está dentro del rango permitido"""
        try:
            num = int(number)
            # Aseguramos que el número esté entre 0000 y 9999
            return 0 <= num <= 9999
        except ValueError:
            return False

    def validate_bet(self, number: str, series: str, fractions: int) -> tuple[bool, str]:
        """Valida una apuesta para esta lotería específica"""
        # 1. Validar que el número está en el rango correcto (0000-9999)
        try:
            num = int(number)
            if not (0 <= num <= 9999):
                return False, f"El número debe estar entre 0000 y 9999"
        except ValueError:
            return False, "El número debe ser un valor numérico de 4 dígitos"

        # 2. Si la lotería requiere series, validar que la serie exista en las disponibles
        if self.requires_series and self.available_series:
            if series not in self.available_series:
                return False, f"Serie {series} no disponible para esta lotería"

        # 3. Validar que esta combinación número-serie no esté ya apostada para el próximo sorteo
        existing_bet = Bet.objects.filter(
            lottery=self,
            number=number,
            series=series,
            draw_date=self.next_draw_date,
            status='PENDING'  # Solo considerar apuestas pendientes
        ).exists()
        
        if existing_bet:
            return False, "Esta combinación número-serie ya está apostada para el próximo sorteo"

        # 4. Validar el número de fracciones
        if fractions > self.max_fractions_per_combination:
            return False, f"Máximo {self.max_fractions_per_combination} fracciones por combinación"

        return True, "Apuesta válida"

    def get_days_until_next_draw(self):
        """Calcula la próxima fecha de sorteo"""
        # Usar zona horaria de Colombia
        bogota_tz = pytz.timezone('America/Bogota')
        now = timezone.now().astimezone(bogota_tz)
        today = now.date()
        current_time = now.time()

        # Mapear días de la semana
        draw_weekday = {
            'MONDAY': 0,
            'TUESDAY': 1,
            'WEDNESDAY': 2,
            'THURSDAY': 3,
            'FRIDAY': 4,
            'SATURDAY': 5,
        }[self.draw_day]

        current_weekday = today.weekday()
        days_ahead = draw_weekday - current_weekday

        # Si es el mismo día pero no ha pasado la hora de cierre, usar la fecha actual
        if days_ahead == 0 and current_time < self.closing_time:
            return today
        
        # Si ya pasó la hora de cierre o es otro día
        if days_ahead <= 0:
            days_ahead += 7

        return today + timedelta(days=days_ahead)

    def is_open_for_bets(self):
        """Verifica si la lotería está abierta para apuestas"""
        # Verificar si la lotería está activa
        if not self.is_active:
            return False

        # Obtener la hora actual en la zona horaria de Colombia
        bogota_tz = pytz.timezone('America/Bogota')
        now = timezone.now().astimezone(bogota_tz)
        
        # Obtener el día actual
        current_day = now.strftime('%A').upper()
        day_mapping = {
            'MONDAY': 'MONDAY',
            'TUESDAY': 'TUESDAY',
            'WEDNESDAY': 'WEDNESDAY',
            'THURSDAY': 'THURSDAY',
            'FRIDAY': 'FRIDAY',
            'SATURDAY': 'SATURDAY'
        }
        
        # Verificar si es el día correcto
        if self.draw_day != day_mapping.get(current_day):
            return True  # Si no es el día del sorteo, permite apostar
            
        # Si es el día del sorteo, verificar la hora
        return now.time() < self.closing_time

    def save(self, *args, **kwargs):
        if self.is_active:
            if not self.pk or 'last_draw_number' in kwargs:
                self.last_draw_number = (self.last_draw_number or 0) + 1
            
            # Actualizar next_draw_date cada vez que se guarda
            if not self.next_draw_date or timezone.now().date() >= self.next_draw_date:
                self.next_draw_date = self.get_days_until_next_draw()
                
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
