from rest_framework import serializers

from apps.payments.models.transaction import Transaction, UserBalance
from apps.payments.models.withdrawal import PrizeWithdrawal
from apps.payments.config import WOMPI_SETTINGS


class CardTokenizationSerializer(serializers.Serializer):
    """Serializador para tokenización de tarjetas"""
    number = serializers.CharField(max_length=16)
    cvc = serializers.CharField(max_length=4)
    exp_month = serializers.CharField(max_length=2)
    exp_year = serializers.CharField(max_length=2)
    card_holder = serializers.CharField(max_length=100)

    def validate(self, data):
        # Validar formato de fecha
        if not (data['exp_month'].isdigit() and data['exp_year'].isdigit()):
            raise serializers.ValidationError("Mes y año deben ser números")
        if not (1 <= int(data['exp_month']) <= 12):
            raise serializers.ValidationError("Mes debe estar entre 1 y 12")
        return data


class TransactionSerializer(serializers.ModelSerializer):
    """Serializador para transacciones"""
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    payment_data = serializers.JSONField(required=False)
    acceptance_token = serializers.CharField(write_only=True, required=False)
    card_token = serializers.CharField(write_only=True, required=False)
    installments = serializers.IntegerField(write_only=True, required=False, default=1)

    class Meta:
        model = Transaction
        fields = [
            'id', 'user', 'user_name', 'amount', 'reference',
            'payment_method', 'status', 'status_display', 'created_at', 
            'updated_at', 'payment_data', 'acceptance_token', 
            'card_token', 'installments'
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
    last_transaction_detail = TransactionSerializer(source='last_transaction', read_only=True)

    class Meta:
        model = UserBalance
        fields = [
            'id', 'user', 'user_name', 'balance',
            'created_at', 'updated_at', 'last_transaction_detail'
        ]
        read_only_fields = ['balance']


class PrizeWithdrawalSerializer(serializers.ModelSerializer):
    """Serializador para retiros de premios"""
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    bank_display = serializers.CharField(source='get_bank_display', read_only=True)
    account_type_display = serializers.CharField(source='get_account_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = PrizeWithdrawal
        fields = [
            'id', 'user', 'user_name', 'amount', 'withdrawal_code',
            'status', 'status_display', 'bank', 'bank_display', 
            'account_type', 'account_type_display', 'account_number', 
            'created_at', 'expiration_date', 'processed_date'
        ]
        read_only_fields = [
            'withdrawal_code', 'status', 'expiration_date', 
            'processed_date'
        ]

    def validate_amount(self, value):
        """Validar monto del retiro"""
        if value <= 0:
            raise serializers.ValidationError("El monto debe ser mayor a 0")
        user = self.context['request'].user
        user_balance = UserBalance.objects.get(user=user).balance

        if value > user_balance:
            raise serializers.ValidationError(
                "No tienes suficiente saldo para realizar este retiro"
            )
        return value

    def validate(self, data):
        # Validación especial para billeteras digitales
        if data['bank'] in ['NEQUI', 'DAVIPLATA', 'DALE', 'MOVII', 'RAPPIPAY', 'IRIS', 'TPAGA']:
            if data['account_type'] != 'DIGITAL':
                raise serializers.ValidationError({
                    'account_type': 'Las billeteras digitales solo pueden tener cuenta tipo Digital'
                })

        # Validaciones específicas por tipo de banco
        if data['bank'] in ['NEQUI', 'DAVIPLATA']:
            if not data['account_number'].isdigit() or len(data['account_number']) != 10:
                raise serializers.ValidationError({
                    'account_number': 'Para Nequi y Daviplata, el número debe ser un celular de 10 dígitos'
                })
        elif data['bank'] in ['BANCOLOMBIA', 'BANCO_BOGOTA', 'DAVIVIENDA']:
            if not data['account_number'].isdigit():
                raise serializers.ValidationError({
                    'account_number': 'El número de cuenta debe contener solo dígitos'
                })
            if len(data['account_number']) < 8 or len(data['account_number']) > 20:
                raise serializers.ValidationError({
                    'account_number': 'Longitud inválida para el número de cuenta bancaria'
                })

        return data
