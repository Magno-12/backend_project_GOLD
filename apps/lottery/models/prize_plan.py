from django.db import models
from django.utils import timezone
from cloudinary.models import CloudinaryField

from apps.default.models.base_model import BaseModel


class PrizePlan(BaseModel):
    """Plan de premios de una lotería"""
    lottery = models.ForeignKey(
        'lottery.Lottery',
        on_delete=models.CASCADE,
        related_name='prize_plans',
        verbose_name='Lotería'
    )
    name = models.CharField(
        'Nombre', 
        max_length=150,
        help_text='Ejemplo: Plan de Premios 2024'
    )
    start_date = models.DateField('Fecha inicio')
    end_date = models.DateField(
        'Fecha fin', 
        null=True, 
        blank=True,
        help_text='Dejar en blanco si es el plan actual'
    )
    is_active = models.BooleanField('Activo', default=True)
    description = models.TextField(
        'Descripción', 
        blank=True
    )
    sorteo_number = models.CharField(
        'Número de sorteo',
        max_length=20,
        blank=True,
        help_text='Ej: 2720'
    )
    
    # Nuevo campo para archivo del plan
    plan_file = CloudinaryField(
        'Archivo del plan',
        folder='lottery/plans/',
        resource_type='raw',
        null=True,
        blank=True,
        help_text='PDF o documento del plan de premios'
    )

    last_updated = models.DateField(
        'Última actualización',
        auto_now=True
    )

    total_prize_amount = models.DecimalField(
        'Monto total en premios',
        max_digits=20,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Suma total de todos los premios del plan'
    )

    class Meta:
        verbose_name = 'Plan de premios'
        verbose_name_plural = 'Planes de premios'
        ordering = ['-start_date']
        constraints = [
            models.UniqueConstraint(
                fields=['lottery', 'start_date'],
                name='unique_lottery_plan_date'
            )
        ]

    def __str__(self):
        return f"{self.lottery.name} - {self.name}"

    def save(self, *args, **kwargs):
        # Si es un plan nuevo y está activo, desactivar otros planes de la misma lotería
        if self.is_active and not self.pk:
            PrizePlan.objects.filter(
                lottery=self.lottery, 
                is_active=True
            ).update(is_active=False)
            
        # Calcular monto total de premios si no está establecido
        if not self.total_prize_amount:
            self.calculate_total_prize_amount()

        super().save(*args, **kwargs)

    def calculate_total_prize_amount(self):
        """Calcula el monto total de todos los premios en el plan"""
        total = sum(
            prize.amount * prize.quantity 
            for prize in self.prizes.all()
        )
        self.total_prize_amount = total

    def is_current(self):
        """Verifica si el plan está vigente"""
        today = timezone.now().date()
        return (
            self.is_active and
            self.start_date <= today and 
            (not self.end_date or self.end_date >= today)
        )

    def get_major_prize(self):
        """Obtiene el premio mayor del plan"""
        return self.prizes.filter(
            prize_type__code='MAJOR'
        ).first()

    def get_seco_prizes(self):
        """Obtiene lista de premios secos"""
        return self.prizes.filter(
            prize_type__code='SECO'
        ).order_by('order')

    def get_approximation_prizes(self):
        """Obtiene todas las aproximaciones"""
        return {
            'same_series': self.prizes.filter(
                prize_type__code='APPROX_SAME_SERIES'
            ).order_by('order'),
            'different_series': self.prizes.filter(
                prize_type__code='APPROX_DIFF_SERIES'
            ).order_by('order')
        }

    def get_special_prizes(self):
        """Obtiene premios especiales"""
        return self.prizes.filter(
            prize_type__is_special=True
        ).order_by('order')

    def validate_prizes_configuration(self):
        """Valida que el plan tenga la configuración mínima necesaria"""
        errors = []
        
        # Verificar premio mayor
        if not self.prizes.filter(prize_type__code='MAJOR').exists():
            errors.append("El plan debe tener un premio mayor")
            
        # Verificar premios secos
        if not self.prizes.filter(prize_type__code='SECO').exists():
            errors.append("El plan debe tener al menos un premio seco")
            
        # Verificar coincidencia con premio mayor de la lotería
        major_prize = self.get_major_prize()
        if major_prize and major_prize.amount != self.lottery.major_prize_amount:
            errors.append("El premio mayor no coincide con el configurado en la lotería")
            
        return errors

    @classmethod
    def get_active_plan(cls, lottery):
        """Obtiene el plan activo para una lotería"""
        return cls.objects.filter(
            lottery=lottery,
            is_active=True,
            start_date__lte=timezone.now().date()
        ).order_by('-start_date').first()
