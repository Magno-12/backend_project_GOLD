from django.db import models

from apps.default.models.base_model import BaseModel


class BankDestinationAccount(BaseModel):
    """Modelo para almacenar las cuentas bancarias destino para envío de premios"""
    BANK_CHOICES = (
        # Bancos tradicionales
        ('BANCOLOMBIA', 'Bancolombia'),
        ('BANCO_BOGOTA', 'Banco de Bogotá'),
        ('DAVIVIENDA', 'Davivienda'),
        ('BBVA', 'BBVA Colombia'),
        ('OCCIDENTE', 'Banco de Occidente'),
        ('POPULAR', 'Banco Popular'),
        ('AVVILLAS', 'Banco AV Villas'),
        ('CAJA_SOCIAL', 'Banco Caja Social'),
        ('ITAU', 'Itaú'),
        ('SCOTIABANK', 'Scotiabank Colpatria'),
        ('FALABELLA', 'Banco Falabella'),
        ('PICHINCHA', 'Banco Pichincha'),
        ('BANCAMIA', 'Bancamía'),
        ('BANCOW', 'Banco W'),
        ('COOPCENTRAL', 'Banco Coopcentral'),
        ('FINANDINA', 'Banco Finandina'),
        ('SANTANDER', 'Banco Santander'),
        ('AGRARIO', 'Banco Agrario'),
        # Neobancos y billeteras digitales
        ('NEQUI', 'Nequi'),
        ('DAVIPLATA', 'Daviplata'),
        ('DALE', 'Dale'),
        ('MOVII', 'Movii'),
        ('RAPPIPAY', 'RappiPay'),
        ('IRIS', 'Iris'),
        ('TPAGA', 'Tpaga'),
        ('LULO', 'Lulo Bank'),
        ('NU_BANK', 'Nu Bank'),
        # Cooperativas financieras
        ('CONFIAR', 'Confiar Cooperativa Financiera'),
        ('COOFINEP', 'Coofinep'),
        ('COTRAFA', 'Cotrafa'),
        ('JFK', 'Cooperativa Financiera JFK')
    )

    ACCOUNT_TYPE_CHOICES = (
        ('SAVINGS', 'Cuenta de Ahorros'),
        ('CHECKING', 'Cuenta Corriente'),
        ('DIGITAL', 'Cuenta Digital')
    )

    bank = models.CharField(
        'Banco',
        max_length=50,
        choices=BANK_CHOICES
    )
    account_type = models.CharField(
        'Tipo de cuenta',
        max_length=20,
        choices=ACCOUNT_TYPE_CHOICES
    )
    account_number = models.CharField(
        'Número de cuenta',
        max_length=30
    )
    account_owner = models.CharField(
        'Titular de la cuenta',
        max_length=200
    )
    identification_type = models.CharField(
        'Tipo de identificación',
        max_length=20,
        choices=(
            ('CC', 'Cédula de Ciudadanía'),
            ('CE', 'Cédula de Extranjería'),
            ('NIT', 'NIT'),
            ('PP', 'Pasaporte')
        )
    )
    identification_number = models.CharField(
        'Número de identificación',
        max_length=20
    )
    is_active = models.BooleanField(
        'Activa',
        default=True
    )
    description = models.CharField(
        'Descripción',
        max_length=200,
        help_text='Descripción para identificar la cuenta (ej: Cuenta principal premios)'
    )

    class Meta:
        verbose_name = 'Cuenta bancaria destino'
        verbose_name_plural = 'Cuentas bancarias destino'
        ordering = ['bank', '-is_active']

    def __str__(self):
        return f"{self.bank} - {self.account_number} - {self.description}"
