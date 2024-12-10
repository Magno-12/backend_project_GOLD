from rest_framework import serializers

from apps.payments.models.transaction import Transaction, UserBalance
from apps.payments.config import WOMPI_SETTINGS


class CardTokenizationSerializer(serializers.Serializer):
    """Serializador para tokenización de tarjetas"""
    number = serializers.CharField(max_length=16)
    cvc = serializers.CharField(max_length=4)
    exp_month = serializers.CharField(max_length=2)
    exp_year = serializers.CharField(max_length=2)
    card_holder = serializers.CharField(max_length=100)


class TransactionSerializer(serializers.ModelSerializer):
    """Serializador para transacciones"""
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)

    class Meta:
        model = Transaction
        fields = [
            'id', 'user', 'user_name', 'amount', 'reference',
            'payment_method', 'status', 'status_display',
            'created_at', 'updated_at', 'payment_data'
        ]
        read_only_fields = ['status', 'wompi_id', 'reference']

    def validate_amount(self, value):
        """Validar monto de la transacción"""
        if value < WOMPI_SETTINGS['MIN_AMOUNT']:
            raise serializers.ValidationError(
                f"El monto mínimo es {WOMPI_SETTINGS['MIN_AMOUNT']}"
            )
        if value > WOMPI_SETTINGS['MAX_AMOUNT']:
            raise serializers.ValidationError(
                f"El monto máximo es {WOMPI_SETTINGS['MAX_AMOUNT']}"
            )
        return value


class UserBalanceSerializer(serializers.ModelSerializer):
    """Serializador para saldo de usuario"""
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)

    class Meta:
        model = UserBalance
        fields = [
            'id', 'user', 'user_name', 'balance',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['balance']
