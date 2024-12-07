from rest_framework import serializers

from apps.users.models import User


class AuthenticationSerializer(serializers.Serializer):
    phone_number = serializers.CharField(required=True)
    pin = serializers.CharField(required=True, write_only=True)


class LogoutSerializer(serializers.Serializer):
    refresh_token = serializers.CharField(required=True)


class UserAuthResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            'id',
            'email',
            'first_name',
            'last_name',
            'phone_number',
            'identification',
            'birth_date'
        )
