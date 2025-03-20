# apps/users/models/password_reset.py
import random
import string
from django.db import models
from django.utils import timezone
from datetime import timedelta

from apps.default.models.base_model import BaseModel

def generate_verification_code():
    """Genera un código alfanumérico de 8 caracteres"""
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(8))


class PasswordResetCode(BaseModel):
    """Modelo para almacenar códigos de verificación para cambio de contraseña"""
    user = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='password_reset_codes')
    code = models.CharField(max_length=8, default=generate_verification_code)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(minutes=5)
        super().save(*args, **kwargs)

    def is_valid(self):
        """Verifica si el código es válido (no usado y no expirado)"""
        return (not self.is_used and 
                timezone.now() <= self.expires_at)

    class Meta:
        verbose_name = 'Código de recuperación'
        verbose_name_plural = 'Códigos de recuperación'
        ordering = ['-created_at']
