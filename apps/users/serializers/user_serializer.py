from rest_framework import serializers

from apps.users.utils.validators import validate_pin
from apps.users.models.user import User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            'id', 
            'email', 
            'first_name', 
            'last_name', 
            'identification', 
            'phone_number', 
            'pin', 
            'birth_date', 
            'document_front', 
            'document_back'
        )
        extra_kwargs = {
            'pin': {'write_only': True}
        }

    def validate_pin(self, value):
        return validate_pin(value)
