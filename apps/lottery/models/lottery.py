# Modificar apps/lottery/models/lottery.py para añadir el campo JSON de combinaciones

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator, RegexValidator
from django.utils import timezone
from django.db.models import Sum, F
from datetime import time, timedelta
from cloudinary.models import CloudinaryField
from django.contrib.postgres.fields import ArrayField
import os
from django.core.files.storage import default_storage
from cloudinary.uploader import upload
import pytz
from decimal import Decimal
from datetime import datetime, time

from apps.default.models.base_model import BaseModel
from apps.lottery.models.bet import Bet


class Lottery(BaseModel):
    # Mantener todos los campos existentes
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
    max_fractions_per_bet = models.PositiveIntegerField(
        'Máximo fracciones por apuesta',
        validators=[MinValueValidator(1)],
        help_text='Máximo de fracciones que un usuario puede comprar en una sola apuesta. No puede ser mayor que el total de fracciones del billete.'
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

    # Campos de validación
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

    available_series = ArrayField(
        models.CharField(max_length=3),
        verbose_name='Series disponibles',
        help_text='Series disponibles para esta lotería',
        default=list,
        blank=True
    )

    combinations_file = CloudinaryField(
        'Archivo de combinaciones',
        folder='lottery/combinations/',
        resource_type='raw',
        null=True,
        blank=True,
        help_text='Archivo CSV con combinaciones de números y series'
    )

    prize_plan_file = CloudinaryField(
        'Archivo de plan de premios',
        folder='lottery/prize_plans/',
        resource_type='auto',
        null=True,
        blank=True,
        help_text='Archivo PDF o imagen del plan de premios actual'
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

        # 3. Validar el número de fracciones por apuesta individual
        if fractions > self.max_fractions_per_bet:
            return False, f"Máximo {self.max_fractions_per_bet} fracciones por apuesta"

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
    
    def update_next_draw_date(self):
        """Actualizar next_draw_date a la próxima ocurrencia de draw_day"""
        current_date = timezone.now().date()
        
        # Si next_draw_date está en el pasado o es hoy, calcular nueva fecha
        if not self.next_draw_date or self.next_draw_date <= current_date:
            self.next_draw_date = self.get_days_until_next_draw()
            self.save(update_fields=['next_draw_date'])
        
        return self.next_draw_date

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
        file_to_upload = None
        is_new_file = False
        
        # Verificar si hay un nuevo archivo por subir
        if hasattr(self, 'prize_plan_file') and self.prize_plan_file and hasattr(self.prize_plan_file, 'file'):
            file_to_upload = self.prize_plan_file
            is_new_file = True
            temp_file = self.prize_plan_file
            self.prize_plan_file = None
        
        # Lógica de negocio existente
        if self.is_active:
            if not self.pk or 'last_draw_number' in kwargs:
                self.last_draw_number = (self.last_draw_number or 0) + 1
            if not self.next_draw_date or timezone.now().date() >= self.next_draw_date:
                self.next_draw_date = self.get_days_until_next_draw()
            if self.max_fractions_per_bet > self.fraction_count:
                self.max_fractions_per_bet = self.fraction_count
        
        # Guardar la instancia primero
        super().save(*args, **kwargs)
        
        # Si hay archivo nuevo, subirlo correctamente
        if is_new_file and file_to_upload:
            try:
                # Obtener extensión real del archivo
                original_name = getattr(file_to_upload, 'name', None)
                ext = os.path.splitext(original_name)[1] if original_name and '.' in original_name else '.pdf'
                
                timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
                public_id = f"plan_{self.id}_{timestamp}"
                
                # IMPORTANTE: Usar resource_type='auto' para que Cloudinary detecte el tipo
                result = upload(
                    temp_file,
                    public_id=public_id,
                    folder='lottery/prize_plans',
                    resource_type='auto',  # Detectar automáticamente el tipo
                    type='upload',         # Tipo explícito
                    access_mode='public',  # Acceso público
                    overwrite=True         # Sobrescribir si existe
                )
                
                # Usar la URL generada por Cloudinary directamente
                secure_url = result['secure_url']
                
                # Actualizar la base de datos con la URL correcta
                self.__class__.objects.filter(pk=self.pk).update(prize_plan_file=secure_url)
                print(f"Archivo subido correctamente: {secure_url}")
            except Exception as e:
                print(f"Error al subir archivo a Cloudinary: {str(e)}")

    class Meta:
        verbose_name = 'Lotería'
        verbose_name_plural = 'Loterías'
        ordering = ['name']
        constraints = [
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
