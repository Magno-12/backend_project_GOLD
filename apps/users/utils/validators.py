from django.core.exceptions import ValidationError
from datetime import date

def validate_adult(birth_date):
    today = date.today()
    age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
    if age < 18:
        raise ValidationError('Debes ser mayor de 18 años para registrarte.')

def validate_pin(value):
    if not value.isdigit() or len(value) != 4:
        raise ValidationError('El PIN debe ser un número de 4 dígitos.')
    return value
