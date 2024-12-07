from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import MinLengthValidator, MaxLengthValidator
from default.models.base_model import BaseModel
from apps.users.utils.validators import validate_adult


class User(AbstractUser, BaseModel):
    username = None
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    identification = models.CharField(max_length=20, unique=True)
    phone_number = models.CharField(max_length=15, unique=True)
    pin = models.CharField(
        max_length=4,
        validators=[
            MinLengthValidator(4),
            MaxLengthValidator(4)
        ]
    )
    birth_date = models.DateField(validators=[validate_adult])
    document_front = models.ImageField(upload_to='documents/', null=True, blank=True)
    document_back = models.ImageField(upload_to='documents/', null=True, blank=True)

    USERNAME_FIELD = 'phone_number'
    REQUIRED_FIELDS = ['email', 'first_name', 'last_name', 'identification', 'birth_date']

    def __str__(self):
        return f"{self.first_name} {self.last_name}"
