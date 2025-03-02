# Generated by Django 5.1.2 on 2025-01-14 22:30

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        (
            "lottery",
            "0012_remove_bet_unique_lottery_number_date_lottery_series_and_more",
        ),
    ]

    operations = [
        migrations.AlterField(
            model_name="lottery",
            name="series",
            field=models.CharField(
                blank=True,
                default="000",
                max_length=3,
                null=True,
                validators=[
                    django.core.validators.RegexValidator(
                        "^\\d{3}$", "Debe ser una serie de 3 dígitos"
                    )
                ],
                verbose_name="Serie por defecto",
            ),
        ),
    ]
