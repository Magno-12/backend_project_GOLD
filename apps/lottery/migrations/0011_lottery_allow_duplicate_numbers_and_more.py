# Generated by Django 5.1.2 on 2025-01-12 16:45

import django.core.validators
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("lottery", "0010_remove_bet_unique_lottery_number_date_and_more"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="lottery",
            name="allow_duplicate_numbers",
            field=models.BooleanField(
                default=False,
                help_text="Si está activo, permite el mismo número en diferentes series",
                verbose_name="Permitir números duplicados en series",
            ),
        ),
        migrations.AddField(
            model_name="lottery",
            name="max_fractions_per_combination",
            field=models.PositiveIntegerField(
                default=1,
                help_text="Máximo de fracciones por combinación número-serie",
                verbose_name="Máximo fracciones por combinación",
            ),
        ),
        migrations.AddField(
            model_name="lottery",
            name="number_range_end",
            field=models.CharField(
                default=1,
                help_text="Número final del rango válido",
                max_length=4,
                validators=[
                    django.core.validators.RegexValidator(
                        "^\\d{4}$", "Debe ser un número de 4 dígitos"
                    )
                ],
                verbose_name="Rango final",
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="lottery",
            name="number_range_start",
            field=models.CharField(
                default=1,
                help_text="Número inicial del rango válido",
                max_length=4,
                validators=[
                    django.core.validators.RegexValidator(
                        "^\\d{4}$", "Debe ser un número de 4 dígitos"
                    )
                ],
                verbose_name="Rango inicial",
            ),
            preserve_default=False,
        ),
        migrations.AddConstraint(
            model_name="lottery",
            constraint=models.UniqueConstraint(
                fields=("code", "name"), name="unique_lottery_code_name"
            ),
        ),
        migrations.AddConstraint(
            model_name="lottery",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    ("number_range_start__lte", models.F("number_range_end"))
                ),
                name="valid_number_range",
            ),
        ),
    ]
