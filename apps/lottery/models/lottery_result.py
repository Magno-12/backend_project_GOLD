from django.db import models

from apps.default.models.base_model import BaseModel


class LotteryResult(BaseModel):
    """Modelo para almacenar resultados de loterías"""
    lottery = models.ForeignKey(
        'lottery.Lottery',
        on_delete=models.CASCADE,
        related_name='results'
    )
    numero = models.CharField('Número ganador', max_length=4)
    numero_serie = models.CharField('Serie ganadora', max_length=10)
    fecha = models.DateField('Fecha del sorteo')
    premios_secos = models.JSONField('Premios secos', default=dict)

    class Meta:
        verbose_name = 'Resultado de lotería'
        verbose_name_plural = 'Resultados de loterías'
        ordering = ['-fecha']
        unique_together = ['lottery', 'fecha']

    def __str__(self):
        return f"{self.lottery.name} - {self.fecha} - {self.numero}"
