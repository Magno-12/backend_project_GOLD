from rest_framework import serializers

from apps.users.models import User
from apps.payments.models import UserBalance


class AuthenticationSerializer(serializers.Serializer):
    phone_number = serializers.CharField(required=True)
    pin = serializers.CharField(required=True, write_only=True)


class LogoutSerializer(serializers.Serializer):
    refresh_token = serializers.CharField(required=True)


class UserAuthResponseSerializer(serializers.ModelSerializer):
    balance = serializers.SerializerMethodField()
    class Meta:
        model = User
        fields = (
            'id',
            'email',
            'first_name',
            'last_name',
            'phone_number',
            'identification',
            'birth_date',
            'balance'
        )

    def get_balance(self, obj):
            balance = UserBalance.objects.filter(user=obj).first()
            if balance:
                return {
                    'amount': float(balance.balance),
                    'last_updated': balance.last_transaction.created_at if balance.last_transaction else None
                }
            return {
                'amount': 0,
                'last_updated': None
            }
