# Generated by Django 5.1.2 on 2024-12-27 00:09

import django.contrib.postgres.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("lottery", "0006_alter_prizeplan_options_lottery_closing_time_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="lottery",
            name="available_series",
            field=django.contrib.postgres.fields.ArrayField(
                base_field=models.CharField(max_length=3),
                blank=True,
                default=list,
                help_text="Series disponibles para esta lotería",
                size=None,
                verbose_name="Series disponibles",
            ),
        ),
    ]
