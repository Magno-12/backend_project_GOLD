from django.db import models
from django.core.validators import MinValueValidator

from apps.default.models.base_model import BaseModel
from apps.payments.config import PAYMENT_METHODS, TRANSACTION_STATUS


class Transaction(BaseModel):
    """Modelo para almacenar transacciones de pago"""
    user = models.ForeignKey(
        'users.User',
        on_delete=models.PROTECT,
        related_name='transactions'
    )
    amount = models.DecimalField(
        'Monto',
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    wompi_id = models.CharField(
        'ID Wompi',
        max_length=100,
        null=True,
        blank=True
    )
    reference = models.CharField(
        'Referencia',
        max_length=100,
        unique=True
    )
    payment_method = models.CharField(
        'Método de pago',
        max_length=50,
        choices=[(m, m) for m in PAYMENT_METHODS.values()]
    )
    status = models.CharField(
        'Estado',
        max_length=20,
        choices=[(s, s) for s in TRANSACTION_STATUS.values()],
        default=TRANSACTION_STATUS['PENDING']
    )
    status_detail = models.JSONField(
        'Detalle del estado',
        default=dict,
        blank=True
    )
    payment_data = models.JSONField(
        'Datos del pago',
        default=dict
    )
    error_detail = models.TextField(
        'Detalle del error',
        blank=True
    )
    signature = models.CharField(
        'Firma de integridad',
        max_length=255,
        null=True,
        blank=True
    )

    class Meta:
        verbose_name = 'Transacción'
        verbose_name_plural = 'Transacciones'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.reference} - {self.amount} - {self.status}"


class UserBalance(BaseModel):
    """Modelo para manejar el saldo de los usuarios"""
    user = models.OneToOneField(
        'users.User',
        on_delete=models.CASCADE,
        related_name='balance'
    )
    balance = models.DecimalField(
        'Saldo',
        max_digits=12,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)]
    )
    last_transaction = models.ForeignKey(
        Transaction,
        on_delete=models.SET_NULL,
        null=True,
        related_name='+'
    )

    class Meta:
        verbose_name = 'Saldo de usuario'
        verbose_name_plural = 'Saldos de usuarios'

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.balance}"
