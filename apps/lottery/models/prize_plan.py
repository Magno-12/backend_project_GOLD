from django.db import models

from apps.default.models.base_model import BaseModel


class PrizePlan(BaseModel):
    """Plan de premios de una lotería"""
    lottery = models.ForeignKey(
        'lottery.Lottery',
        on_delete=models.CASCADE,
        related_name='prize_plans'
    )
    name = models.CharField('Nombre', max_length=150)
    start_date = models.DateField('Fecha inicio')
    end_date = models.DateField('Fecha fin', null=True, blank=True)
    is_active = models.BooleanField('Activo', default=True)
    description = models.TextField('Descripción', blank=True)
    sorteo_number = models.CharField(
        'Número de sorteo',
        max_length=20,
        blank=True,
        help_text='Ej: 2720'
    )

    class Meta:
        verbose_name = 'Plan de premios'
        verbose_name_plural = 'Planes de premios'

    def __str__(self):
        return f"{self.lottery.name} - {self.name}"
