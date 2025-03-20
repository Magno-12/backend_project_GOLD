from rest_framework import serializers
from django.utils import timezone
from apps.users.models import User, PasswordResetCode
from apps.users.utils.validators import validate_pin


class RequestPasswordResetSerializer(serializers.Serializer):
    """Serializador para solicitar un código de recuperación de contraseña"""
    email = serializers.EmailField()
    
    def validate_email(self, value):
        """Valida que el correo exista en la base de datos"""
        if not User.objects.filter(email=value).exists():
            raise serializers.ValidationError("No existe un usuario con este correo electrónico.")
        return value


class VerifyPasswordResetCodeSerializer(serializers.Serializer):
    """Serializador para verificar el código de recuperación"""
    email = serializers.EmailField()
    code = serializers.CharField(max_length=8)
    
    def validate(self, data):
        """Valida que el código sea válido para el usuario"""
        email = data.get('email')
        code = data.get('code')
        
        try:
            user = User.objects.get(email=email)
            reset_code = PasswordResetCode.objects.filter(
                user=user,
                code=code,
                is_used=False,
                expires_at__gt=timezone.now()
            ).first()
            
            if not reset_code:
                raise serializers.ValidationError("Código inválido o expirado.")
            
            data['user'] = user
            data['reset_code'] = reset_code
            return data
        except User.DoesNotExist:
            raise serializers.ValidationError("No existe un usuario con este correo electrónico.")


class ResetPasswordSerializer(serializers.Serializer):
    """Serializador para cambiar la contraseña"""
    email = serializers.EmailField()
    code = serializers.CharField(max_length=8)
    new_pin = serializers.CharField(min_length=4, max_length=4)
    confirm_pin = serializers.CharField(min_length=4, max_length=4)
    
    def validate(self, data):
        """Valida que el código sea válido y que las contraseñas coincidan"""
        email = data.get('email')
        code = data.get('code')
        new_pin = data.get('new_pin')
        confirm_pin = data.get('confirm_pin')
        
        # Validar que las contraseñas coincidan
        if new_pin != confirm_pin:
            raise serializers.ValidationError({"confirm_pin": "Las contraseñas no coinciden."})
        
        # Validar formato de PIN
        try:
            validate_pin(new_pin)
        except Exception as e:
            raise serializers.ValidationError({"new_pin": str(e)})
            
        # Validar código
        try:
            user = User.objects.get(email=email)
            reset_code = PasswordResetCode.objects.filter(
                user=user,
                code=code,
                is_used=False,
                expires_at__gt=timezone.now()
            ).first()
            
            if not reset_code:
                raise serializers.ValidationError({"code": "Código inválido o expirado."})
            
            data['user'] = user
            data['reset_code'] = reset_code
            return data
        except User.DoesNotExist:
            raise serializers.ValidationError({"email": "No existe un usuario con este correo electrónico."})
