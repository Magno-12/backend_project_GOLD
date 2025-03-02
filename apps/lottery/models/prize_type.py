from django.db import models

from apps.default.models.base_model import BaseModel


class PrizeType(BaseModel):
    """Tipos de premios disponibles"""
    name = models.CharField('Nombre', max_length=100)
    code = models.CharField('Código', max_length=50, unique=True)
    description = models.TextField('Descripción', blank=True)
    match_rules = models.JSONField(
        'Reglas de coincidencia',
        default=dict,
        help_text='Reglas para validar coincidencias {"type": "exact", "positions": [0,1,2,3]}'
    )
    requires_series = models.BooleanField('Requiere serie', default=False)
    requires_exact_match = models.BooleanField('Coincidencia exacta', default=True)
    is_special = models.BooleanField('Premio especial', default=False)

    class Meta:
        verbose_name = 'Tipo de premio'
        verbose_name_plural = 'Tipos de premios'

    def __str__(self):
        return self.name

    @classmethod
    def get_default_types(cls):
        """Retorna los tipos de premios básicos"""
        return [
            ('MAJOR', 'Premio Mayor'),
            ('SECO', 'Premio Seco'),
            ('APPROX_SAME_SERIES', 'Aproximación Misma Serie'),
            ('APPROX_DIFF_SERIES', 'Aproximación Diferente Serie'),
            ('FIRST_THREE', 'Tres Primeras'),
            ('LAST_THREE', 'Tres Últimas'),
            ('FIRST_TWO', 'Dos Primeras'),
            ('LAST_TWO', 'Dos Últimas'),
            ('FIRST_TWO_LAST_ONE', 'Dos Primeras y Última'),
            ('FIRST_ONE_LAST_TWO', 'Primera y Dos Últimas'),
            ('SERIES', 'Serie'),
        ]
