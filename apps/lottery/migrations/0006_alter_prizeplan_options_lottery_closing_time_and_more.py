# Generated by Django 5.1.2 on 2024-12-24 19:42

import cloudinary.models
import datetime
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("lottery", "0005_lottery_sales_file"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="prizeplan",
            options={
                "ordering": ["-start_date"],
                "verbose_name": "Plan de premios",
                "verbose_name_plural": "Planes de premios",
            },
        ),
        migrations.AddField(
            model_name="lottery",
            name="closing_time",
            field=models.TimeField(
                default=datetime.time(20, 0),
                help_text="Hora límite para realizar apuestas",
                verbose_name="Hora límite de compra",
            ),
        ),
        migrations.AddField(
            model_name="lottery",
            name="last_draw_number",
            field=models.PositiveIntegerField(
                default=0,
                help_text="Se incrementa automáticamente",
                verbose_name="Último número de sorteo",
            ),
        ),
        migrations.AddField(
            model_name="lottery",
            name="next_draw_date",
            field=models.DateField(
                blank=True,
                help_text="Se actualiza automáticamente",
                null=True,
                verbose_name="Próxima fecha de sorteo",
            ),
        ),
        migrations.AddField(
            model_name="prizeplan",
            name="last_updated",
            field=models.DateField(auto_now=True, verbose_name="Última actualización"),
        ),
        migrations.AddField(
            model_name="prizeplan",
            name="plan_file",
            field=cloudinary.models.CloudinaryField(
                blank=True,
                help_text="PDF o documento del plan de premios",
                max_length=255,
                null=True,
                verbose_name="Archivo del plan",
            ),
        ),
        migrations.AddField(
            model_name="prizeplan",
            name="total_prize_amount",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text="Suma total de todos los premios del plan",
                max_digits=20,
                null=True,
                verbose_name="Monto total en premios",
            ),
        ),
        migrations.AlterField(
            model_name="prizeplan",
            name="end_date",
            field=models.DateField(
                blank=True,
                help_text="Dejar en blanco si es el plan actual",
                null=True,
                verbose_name="Fecha fin",
            ),
        ),
        migrations.AlterField(
            model_name="prizeplan",
            name="lottery",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="prize_plans",
                to="lottery.lottery",
                verbose_name="Lotería",
            ),
        ),
        migrations.AlterField(
            model_name="prizeplan",
            name="name",
            field=models.CharField(
                help_text="Ejemplo: Plan de Premios 2024",
                max_length=150,
                verbose_name="Nombre",
            ),
        ),
        migrations.AddConstraint(
            model_name="prizeplan",
            constraint=models.UniqueConstraint(
                fields=("lottery", "start_date"), name="unique_lottery_plan_date"
            ),
        ),
    ]
