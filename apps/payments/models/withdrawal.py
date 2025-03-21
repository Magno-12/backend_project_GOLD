from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.db import transaction
from datetime import timedelta
import uuid

from apps.default.models.base_model import BaseModel
from apps.payments.models.bank_account import BankDestinationAccount
from apps.payments.models.transaction import UserBalance

def generate_withdrawal_code():
    """Genera un código único para el retiro"""
    return f"PR-{uuid.uuid4().hex[:6].upper()}"


class PrizeWithdrawal(BaseModel):
    """Modelo para manejar solicitudes de retiro de premios"""
    STATUS_CHOICES = (
        ('PENDING', 'Pendiente'),
        ('APPROVED', 'Aprobado'),
        ('REJECTED', 'Rechazado'),
        ('EXPIRED', 'Expirado'),
        ('REVERSED', 'Reversado')
    )

    ACCOUNT_TYPE_CHOICES = (
        ('SAVINGS', 'Cuenta de Ahorros'),
        ('CHECKING', 'Cuenta Corriente'),
        ('DIGITAL', 'Cuenta Digital')
    )

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
        # Cooperativas financieras importantes
        ('CONFIAR', 'Confiar Cooperativa Financiera'),
        ('COOFINEP', 'Coofinep'),
        ('COTRAFA', 'Cotrafa'),
        ('JFK', 'Cooperativa Financiera JFK')
    )

    # Relaciones y campos básicos
    user = models.ForeignKey(
        'users.User',
        on_delete=models.PROTECT,
        related_name='prize_withdrawals',
        verbose_name='Usuario'
    )
    amount = models.DecimalField(
        'Monto',
        max_digits=12,
        decimal_places=2,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(10000000)
        ]
    )
    withdrawal_code = models.CharField(
        'Código de retiro',
        max_length=10,
        unique=True,
        default=generate_withdrawal_code
    )

    # Información bancaria
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
    
    # Nuevo campo: Utilizar llaves para pago
    use_keys = models.BooleanField(
        'Utilizar llaves para pago',
        default=False,
        help_text='Indica si se utilizará el sistema de llaves para realizar el pago'
    )

    # Estado y fechas
    status = models.CharField(
        'Estado',
        max_length=20,
        choices=STATUS_CHOICES,
        default='PENDING'
    )
    expiration_date = models.DateTimeField(
        'Fecha de expiración',
        blank=True,
        null=True
    )
    processed_date = models.DateTimeField(
        'Fecha de procesamiento',
        blank=True,
        null=True
    )

    # Notas y campos adicionales
    admin_notes = models.TextField(
        'Notas del administrador',
        blank=True
    )

    destination_account = models.ForeignKey(
        BankDestinationAccount,
        on_delete=models.PROTECT,
        verbose_name='Cuenta destino',
        help_text='Cuenta bancaria donde se enviará el premio'
    )

    class Meta:
        verbose_name = 'Retiro de premio'
        verbose_name_plural = 'Retiros de premios'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['withdrawal_code']),
            models.Index(fields=['status']),
            models.Index(fields=['created_at']),
            models.Index(fields=['user', 'status']),
        ]

    def __str__(self):
        return f"{self.withdrawal_code} - {self.user.get_full_name()} - {self.amount}"

    def save(self, *args, **kwargs):
        # Si es una creación nueva, establecer fecha de expiración
        if not self.pk:
            self.expiration_date = timezone.now() + timedelta(hours=48)
            super().save(*args, **kwargs)
            return

        # Obtener el estado anterior
        old_instance = PrizeWithdrawal.objects.get(pk=self.pk)
        
        # Si el estado cambió a REJECTED, devolver el saldo
        if old_instance.status == 'PENDING' and self.status == 'REJECTED':
            with transaction.atomic():
                balance = UserBalance.objects.select_for_update().get(user=self.user)
                balance.balance += self.amount
                balance.save()
                self.processed_date = timezone.now()

        super().save(*args, **kwargs)

    @property
    def should_revert(self) -> bool:
        """
        Determina si el retiro debe ser revertido basado en el tiempo transcurrido.
        Se revierte después de 48 horas de la solicitud.
        """
        if self.status != 'PENDING':
            return False

        time_elapsed = timezone.now() - self.created_at
        return time_elapsed > timedelta(hours=48)

    def revert_balance(self):
        """Revierte el balance al usuario después de 48 horas"""
        with transaction.atomic():
            if self.status == 'PENDING' and self.should_revert:
                # Actualizar balance del usuario
                balance = self.user.balance
                balance.balance += self.amount
                balance.save()

                # Actualizar estado del retiro
                self.status = 'REVERSED'
                self.processed_date = timezone.now()
                self.admin_notes = (
                    f"Reversión automática por exceder 48 horas de espera. "
                    f"Fecha de solicitud: {self.created_at}, "
                    f"Fecha de reversión: {timezone.now()}"
                )
                self.save()
                return True
        return False

    def clean(self):
        """Validaciones adicionales del modelo"""
        from django.core.exceptions import ValidationError

        # Validar monto máximo
        if self.amount > 10000000:
            raise ValidationError({
                'amount': 'El monto máximo permitido es de 10.000.000'
            })

        # Validar tipo de cuenta para billeteras digitales
        if self.bank in ['NEQUI', 'DAVIPLATA', 'DALE', 'MOVII', 'RAPPIPAY', 'IRIS', 'TPAGA']:
            if self.account_type != 'DIGITAL':
                raise ValidationError({
                    'account_type': 'Las billeteras digitales solo pueden tener cuenta tipo Digital'
                })

        # Validar número de cuenta según el banco
        if self.bank in ['NEQUI', 'DAVIPLATA']:
            if not self.account_number.isdigit() or len(self.account_number) != 10:
                raise ValidationError({
                    'account_number': 'Para Nequi y Daviplata, el número debe ser un celular de 10 dígitos'
                })
