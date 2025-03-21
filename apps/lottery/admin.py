from django.contrib import admin
from django.http import HttpResponse
from django.contrib import messages
from django.core.files.base import ContentFile
from django.utils.html import format_html
from django.forms import TextInput
from django.utils import timezone
from django.db.models import Sum, Count
from django.shortcuts import redirect
from django import forms
from django.template.response import TemplateResponse
from django.urls import path
import cloudinary
import cloudinary.uploader
import csv
import pytz
import pandas as pd
import uuid
import json
from datetime import datetime, time
from io import TextIOWrapper
from datetime import datetime
from django.db import transaction

from .models import Lottery, Bet, LotteryResult, Prize, PrizePlan, PrizeType, LotteryNumberCombination
from apps.lottery.services.combination_processor import CombinationProcessor


# Formulario para seleccionar lotería
class LotteryCombinationsForm(forms.Form):
    file = forms.FileField(label='Archivo CSV de combinaciones')
    lottery = forms.ChoiceField(label='Lotería', choices=[])
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Obtener todas las loterías activas
        lotteries = CombinationProcessor.get_all_lotteries()
        self.fields['lottery'].choices = [(lottery['id'], lottery['name']) for lottery in lotteries]


# Formulario para importar CSV
class CsvImportForm(forms.Form):
    csv_file = forms.FileField()


@admin.register(Lottery)
class LotteryAdmin(admin.ModelAdmin):
    list_display = (
        'name', 
        'code', 
        'draw_day', 
        'draw_time', 
        'is_active', 
        'fraction_count', 
        'fraction_price',
        'betting_status', 
        'next_draw_info'
    )
    list_filter = ('is_active', 'draw_day')
    search_fields = ('name', 'code')
    
    fieldsets = (
        ('Información Básica', {
            'fields': (
                'name', 'code', 'draw_day', 'draw_time', 'is_active', 
                'requires_series', 'available_series', 'logo_url'
            )
        }),
        ('Configuración de Fracciones', {
            'fields': (
                'fraction_count', 'fraction_price', 'major_prize_amount',
                'max_fractions_per_bet'
            )
        }),
        ('Límites de Apuestas', {
            'fields': (
                'min_bet_amount', 'max_bet_amount'
            )
        }),
        ('Configuración de Sorteos', {
            'fields': (
                'closing_time', 'last_draw_number', 'next_draw_date',
                'prize_plan_file'
            )
        }),
        ('Configuración de Números', {
            'fields': (
                'number_range_start', 'number_range_end', 'allow_duplicate_numbers',
                'series'
            ),
            'classes': ('collapse',),
        }),
        ('Archivos de Sistema', {
            'fields': (
                'number_ranges_file', 'unsold_tickets_file', 'sales_file', 'combinations_file'
            ),
            'classes': ('collapse',),
        }),
    )

    actions = [
        'generate_sales_file',
        'generate_unsold_file', 
        'generate_type_204_report',
        'process_combinations_csv',
        'upload_combinations_file'
    ]
    
    # Añadir URL personalizada para el formulario
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('upload-combinations/', self.admin_site.admin_view(self.upload_combinations_view), name='lottery_upload_combinations'),
        ]
        return custom_urls + urls
    
    def upload_combinations_view(self, request):
        """Vista para subir archivo de combinaciones y seleccionar lotería"""
        context = {
            'title': 'Subir Combinaciones',
            'opts': self.model._meta,
            'app_label': self.model._meta.app_label,
        }
        
        if request.method == 'POST':
            form = LotteryCombinationsForm(request.POST, request.FILES)
            if form.is_valid():
                # Subir archivo a Cloudinary
                csv_file = request.FILES['file']
                lottery_id = form.cleaned_data['lottery']
                
                try:
                    upload_result = cloudinary.uploader.upload(
                        csv_file,
                        resource_type='raw',
                        folder=f'lottery/combinations/',
                        public_id=f'combinations_{lottery_id}_{timezone.now().strftime("%Y%m%d_%H%M%S")}'
                    )
                    
                    # Procesar el archivo
                    processor = CombinationProcessor(lottery_id=lottery_id)
                    result = processor.process_cloudinary_file(upload_result['secure_url'])
                    
                    if 'error' in result:
                        self.message_user(request, f"Error: {result['error']}", level=messages.ERROR)
                    else:
                        # Actualizar el campo combinations_file de la lotería
                        lottery = Lottery.objects.get(id=lottery_id)
                        lottery.combinations_file = upload_result['secure_url']
                        lottery.save(update_fields=['combinations_file'])
                        
                        self.message_user(
                            request, 
                            f"Se procesaron {result['combinations_count']} combinaciones para {result['lottery_name']}. "
                            f"Se añadieron {result['series_count']} series únicas."
                        )
                        
                        # Redirigir a la página de detalle de la lotería
                        return redirect(f'../change/{lottery_id}')
                
                except Exception as e:
                    self.message_user(request, f"Error: {str(e)}", level=messages.ERROR)
        else:
            form = LotteryCombinationsForm()
        
        context['form'] = form
        return TemplateResponse(request, 'admin/lottery/upload_combinations.html', context)
    
    def upload_combinations_file(self, request, queryset):
        """Acción para subir archivo de combinaciones"""
        if len(queryset) != 1:
            self.message_user(request, "Seleccione una sola lotería", level=messages.ERROR)
            return
            
        return redirect('admin:lottery_upload_combinations')
    
    upload_combinations_file.short_description = "Subir archivo de combinaciones"

    def betting_status(self, obj):
        """Estado actual de las apuestas"""
        bogota_tz = pytz.timezone('America/Bogota')
        now = timezone.now().astimezone(bogota_tz)
        
        if not obj.is_active:
            status = 'Inactiva'
            color = 'red'
        elif now > bogota_tz.localize(datetime.combine(now.date(), obj.closing_time)):
            status = 'Cerrada'
            color = 'red'
        else:
            status = 'Abierta'
            color = 'green'
            
        return format_html(
            '<span style="color: {};">{}</span>',
            color,
            status
        )
    betting_status.short_description = 'Estado Apuestas'

    def next_draw_info(self, obj):
        return f"Sorteo #{obj.last_draw_number + 1} - {obj.next_draw_date}"
    next_draw_info.short_description = 'Próximo Sorteo'

    def generate_sales_file(self, request, queryset):
        """Genera archivo de ventas"""
        if len(queryset) != 1:
            self.message_user(request, "Seleccione una sola lotería", level=messages.ERROR)
            return

        lottery = queryset[0]
        try:
            # Obtener apuestas vendidas
            sold_bets = Bet.objects.filter(
                lottery=lottery,
                draw_date=lottery.next_draw_date,
                status='PENDING'
            ).select_related('user')

            # Crear contenido del archivo
            content = []
            # Encabezado
            content.append("VENTA06")  # Código de lotería
            content.append("0993")     # Código distribuidor
            content.append(f"{lottery.last_draw_number + 1:04d}")  # Número sorteo (formato: 4 dígitos)
            content.append(f"{len(sold_bets):07d}")  # Total ventas (formato: 7 dígitos)

            # Detalle de ventas
            for bet in sold_bets:
                # Asegurar que tenemos enteros para conversiones
                number = int(bet.number) if isinstance(bet.number, str) and bet.number.isdigit() else 0
                series = int(bet.series) if isinstance(bet.series, str) and bet.series.isdigit() else 0
                
                # Calcular fracciones
                fractions = int(bet.amount/lottery.fraction_price)
                
                # Convertir UUID a string y formatear para el campo de consecutivo
                # Eliminamos guiones y tomamos solo los primeros 10 caracteres
                bet_id_str = str(bet.id).replace('-', '')[:10]
                
                line = (
                    f"{number:04d}"           # Número (formato: 4 dígitos)
                    f"{series:03d}"           # Serie (formato: 3 dígitos)
                    f"{fractions:03d}"        # Fracciones (formato: 3 dígitos)
                    f"19"                     # Código departamento
                    f"{'BBC':>5}"             # Serie tiquete (justificado a derecha, 5 caracteres)
                    f"{bet_id_str:0>10}"      # Consecutivo (10 dígitos, rellenado con ceros)
                    f"GOLD{bet_id_str[:14]}"  # Código seguridad (fijo + hasta 14 caracteres del ID)
                )
                content.append(line)

            # Generar archivo
            filename = f"V_0993{lottery.last_draw_number + 1}.txt"
            response = HttpResponse(
                '\n'.join(content),
                content_type='text/plain'
            )
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response

        except Exception as e:
            self.message_user(request, f'Error: {str(e)}', level=messages.ERROR)
            import traceback
            self.message_user(request, f'Detalles: {traceback.format_exc()}', level=messages.ERROR)

    generate_sales_file.short_description = "Generar archivo de ventas"

    def generate_unsold_file(self, request, queryset):
        """Genera archivo de billetes no vendidos"""
        if len(queryset) != 1:
            self.message_user(request, "Seleccione una sola lotería", level=messages.ERROR)
            return

        lottery = queryset[0]
        try:
            content = []
            # Encabezado según formato
            content.append("06")  # Código lotería
            content.append("0993") # Código distribuidor Coinjuegos
            content.append(f"{lottery.last_draw_number + 1:04d}") # Aseguramos 4 dígitos
            
            # Obtener billetes no vendidos
            unsold_tickets = lottery.bets.filter(
                status='PENDING',
                draw_date=lottery.next_draw_date
            )
            
            # Total fracciones devueltas 
            total_fractions = sum(
                int(ticket.amount/lottery.fraction_price) 
                for ticket in unsold_tickets
            )
            content.append(f"{total_fractions:07d}") # Aseguramos 7 dígitos

            # Detalle de billetes
            for ticket in unsold_tickets:
                # Asegurar que tenemos enteros para conversiones
                number = int(ticket.number) if isinstance(ticket.number, str) and ticket.number.isdigit() else 0
                series = int(ticket.series) if isinstance(ticket.series, str) and ticket.series.isdigit() else 0
                
                fractions = int(ticket.amount/lottery.fraction_price)
                line = (
                    f"{number:04d}"     # NNNN - aseguramos 4 dígitos
                    f"{series:03d}"     # SSS - aseguramos 3 dígitos
                    f"{fractions:03d}"         # FFF
                    f"{fractions:02d}"         # ##
                    f"001"                     # QQQ
                    f"01"                      # PP
                )
                content.append(line)

            # Generar archivo
            filename = f"D_0993{lottery.last_draw_number + 1}.txt"
            response = HttpResponse(
                '\n'.join(content),
                content_type='text/plain'
            )
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response

        except Exception as e:
            self.message_user(request, f'Error: {str(e)}', level=messages.ERROR)
            import traceback
            self.message_user(request, f'Detalles: {traceback.format_exc()}', level=messages.ERROR)

    generate_unsold_file.short_description = "Generar archivo no vendidos"

    def generate_type_204_report(self, request, queryset):
        """Genera el archivo tipo 204 para SuperSalud"""
        if len(queryset) != 1:
            self.message_user(request, "Seleccione una sola lotería", level=messages.ERROR)
            return

        lottery = queryset[0]
        allowed, message = self.is_betting_allowed(lottery)
        if allowed:
            self.message_user(
                request, 
                "Aún no es hora de generar el reporte 204", 
                level=messages.ERROR
            )
            return

        try:
            # Generar contenido archivo tipo 204
            content = []
            # Líneas de encabezado
            content.append(f"{lottery.code[:2]:0>2}")  # Código lotería
            content.append("0993")  # Código distribuidor
            content.append(f"{lottery.last_draw_number + 1:04d}")  # Número sorteo

            # Obtener billetes vendidos
            sold_tickets = Bet.objects.filter(
                lottery=lottery,
                draw_date=lottery.next_draw_date,
                status='PENDING'
            ).select_related('user')

            # Total fracciones vendidas
            total_fractions = sum(
                int(bet.amount/lottery.fraction_price) 
                for bet in sold_tickets
            )
            content.append(f"{total_fractions:07d}")

            # Detalle billetes vendidos
            for bet in sold_tickets:
                # Asegurar que tenemos enteros para conversiones
                number = int(bet.number) if isinstance(bet.number, str) and bet.number.isdigit() else 0
                series = int(bet.series) if isinstance(bet.series, str) and bet.series.isdigit() else 0
                
                fractions = int(bet.amount/lottery.fraction_price)
                bet_id_str = str(bet.id).replace('-', '')[:10]
                
                line = (
                    f"{number:04d}{series:03d}"  # Número y serie
                    f"{fractions:03d}19"         # Fracciones y código departamento
                    f"{'BBC'}{bet_id_str:0>10}"  # Serie tiquete y consecutivo
                    f"GOLD{bet_id_str[:14]}"     # Código seguridad
                )
                content.append(line)

            # Generar archivo
            filename = f"204_{lottery.code}_{lottery.last_draw_number + 1}.txt"
            response = HttpResponse(
                '\n'.join(content),
                content_type='text/plain'
            )
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response

        except Exception as e:
            self.message_user(
                request, 
                f'Error generando archivo tipo 204: {str(e)}',
                level=messages.ERROR
            )
            import traceback
            self.message_user(request, f'Detalles: {traceback.format_exc()}', level=messages.ERROR)

    generate_type_204_report.short_description = "Generar reporte tipo 204"

    def process_combinations_csv(self, request, queryset):
        """Procesa archivo CSV de combinaciones válidas"""
        if len(queryset) != 1:
            self.message_user(request, "Seleccione una sola lotería", level=messages.ERROR)
            return

        lottery = queryset[0]

        # Si el formulario fue enviado
        if request.POST.get('_process_csv'):
            if 'csv_file' not in request.FILES:
                self.message_user(request, 'Debe seleccionar un archivo CSV', level=messages.ERROR)
                return
                
            csv_file = request.FILES['csv_file']
            if not csv_file.name.endswith('.csv'):
                self.message_user(request, 'El archivo debe ser CSV', level=messages.ERROR)
                return

            try:
                # Procesar CSV usando pandas
                df = pd.read_csv(csv_file, dtype={
                    '5100': str,  # número
                    '001': str,   # serie
                    '175': int,   # fracciones (opcional)
                    '0000': str   # otro campo si existe
                })
                
                processed = 0
                errors = []
                
                with transaction.atomic():
                    # Desactivar combinaciones anteriores
                    LotteryNumberCombination.objects.filter(
                        lottery=lottery,
                        draw_date=lottery.next_draw_date
                    ).update(is_active=False)
                    
                    for index, row in df.iterrows():
                        try:
                            number = str(row['5100']).zfill(4)
                            series = str(row['001']).zfill(3)
                            
                            if not (number.isdigit() and len(number) == 4):
                                errors.append(f"Fila {index + 2}: Número inválido {number}")
                                continue
                                
                            if not (series.isdigit() and len(series) == 3):
                                errors.append(f"Fila {index + 2}: Serie inválida {series}")
                                continue
                            
                            combination, created = LotteryNumberCombination.objects.update_or_create(
                                lottery=lottery,
                                number=number,
                                series=series,
                                draw_date=lottery.next_draw_date,
                                defaults={
                                    'total_fractions': lottery.fraction_count,
                                    'used_fractions': 0,
                                    'is_active': True
                                }
                            )
                            processed += 1
                            
                        except Exception as e:
                            errors.append(f"Error en fila {index + 2}: {str(e)}")
                
                if errors:
                    self.message_user(
                        request,
                        f'Proceso completado con {len(errors)} errores. '
                        f'Se procesaron {processed} combinaciones correctamente.',
                        level=messages.WARNING
                    )
                else:
                    self.message_user(
                        request,
                        f'Se procesaron {processed} combinaciones correctamente.',
                        level=messages.SUCCESS
                    )
                    
            except Exception as e:
                self.message_user(request, f'Error procesando archivo: {str(e)}', level=messages.ERROR)
            return

        # Mostrar formulario de carga usando el intermediario de Django
        form = CsvImportForm()
        return self.admin_site.admin_view(lambda r: HttpResponse('''
            <form method="post" enctype="multipart/form-data">
                <input type="hidden" name="_process_csv" value="1">
                <input type="file" name="csv_file" accept=".csv" required>
                <input type="submit" value="Procesar CSV">
                <input type="hidden" name="csrfmiddlewaretoken" value="{}">
            </form>
        '''.format(request.CSRF_TOKEN)))(request)

    process_combinations_csv.short_description = "Procesar CSV de combinaciones"

    def is_betting_allowed(self, lottery):
        """Verifica si se permite apostar en este momento"""
        bogota_tz = pytz.timezone('America/Bogota')
        now = timezone.now().astimezone(bogota_tz)
        
        if not lottery.is_active:
            return False, "Lotería inactiva"

        # Validar día
        day_map = {
            'MONDAY': 0, 'TUESDAY': 1, 'WEDNESDAY': 2,
            'THURSDAY': 3, 'FRIDAY': 4, 'SATURDAY': 5
        }
        if now.weekday() != day_map.get(lottery.draw_day):
            return False, "No es día de sorteo"

        # Validar hora de cierre
        closing_datetime = bogota_tz.localize(
            datetime.combine(now.date(), lottery.closing_time)
        )
        if now > closing_datetime:
            return False, "Fuera de horario de apuestas"

        return True, "Apuestas permitidas"

    def save_model(self, request, obj, form, change):
        # Procesar series disponibles
        if isinstance(obj.available_series, str):
            obj.available_series = [
                s.strip() for s in obj.available_series.split(',') 
                if s.strip()
            ]
        
        # Validar series
        if obj.available_series:
            invalid_series = [
                s for s in obj.available_series 
                if not (s.isdigit() and len(s) == 3)
            ]
            if invalid_series:
                messages.error(
                    request,
                    f"Series inválidas: {', '.join(invalid_series)}. "
                    "Deben ser números de 3 dígitos."
                )
                return
            
            obj.available_series = list(set(obj.available_series))

        super().save_model(request, obj, form, change)


@admin.register(LotteryNumberCombination)
class LotteryNumberCombinationAdmin(admin.ModelAdmin):
    list_display = ('lottery', 'number', 'series', 'available_fractions', 'is_active', 'draw_date', 'winner_status')
    list_filter = ('lottery', 'is_active', 'draw_date', 'is_winner')
    search_fields = ('number', 'series')
    readonly_fields = ('used_fractions', 'prize_detail')
    
    fieldsets = (
        ('Información básica', {
            'fields': ('lottery', 'number', 'series', 'draw_date', 'is_active')
        }),
        ('Fracciones', {
            'fields': ('total_fractions', 'used_fractions')
        }),
        ('Premios', {
            'fields': ('is_winner', 'prize_type', 'prize_amount', 'prize_detail')
        }),
    )
    
    def available_fractions(self, obj):
        return obj.total_fractions - obj.used_fractions
    available_fractions.short_description = 'Fracciones Disponibles'
    
    def winner_status(self, obj):
        if obj.is_winner:
            return format_html(
                '<span style="color: green; font-weight: bold;">⭐ GANADORA: {}</span>',
                obj.prize_type or 'Premio'
            )
        return ''
    winner_status.short_description = 'Estatus Ganador'


@admin.register(Bet)
class BetAdmin(admin.ModelAdmin):
    list_display = ('lottery', 'user', 'number', 'series', 'amount', 'status', 'draw_date', 'won_amount')
    list_filter = ('status', 'draw_date', 'lottery')
    search_fields = ('user__phone_number', 'number', 'series')
    readonly_fields = ('won_amount', 'winning_details')

@admin.register(LotteryResult)
class LotteryResultAdmin(admin.ModelAdmin):
    list_display = ('lottery', 'fecha', 'numero', 'numero_serie')
    list_filter = ('lottery', 'fecha')
    search_fields = ('numero', 'numero_serie')
    readonly_fields = ('premios_secos',)

@admin.register(Prize)
class PrizeAdmin(admin.ModelAdmin):
    list_display = ('prize_plan', 'prize_type', 'name', 'amount', 'fraction_amount', 'quantity')
    list_filter = ('prize_plan__lottery', 'prize_type')
    search_fields = ('name', 'prize_plan__name')
    readonly_fields = ('fraction_amount',)

    def save_model(self, request, obj, form, change):
        if obj.amount and obj.prize_plan.lottery.fraction_count:
            obj.fraction_amount = obj.amount / obj.prize_plan.lottery.fraction_count
        super().save_model(request, obj, form, change)

@admin.register(PrizePlan)
class PrizePlanAdmin(admin.ModelAdmin):
    list_display = ['lottery', 'name', 'start_date', 'is_active', 'last_updated']
    actions = ['upload_plan_file']
    
    def upload_plan_file(self, request, queryset):
        if 'file' not in request.FILES:
            self.message_user(request, "No se ha seleccionado archivo", level=messages.ERROR)
            return
            
        for plan in queryset:
            try:
                result = cloudinary.uploader.upload(
                    request.FILES['file'],
                    resource_type='raw',
                    folder=f'lottery/plans/',
                    public_id=f'plan_{plan.lottery.code}_{timezone.now().strftime("%Y%m%d")}'
                )
                plan.plan_file = result['secure_url']
                plan.save()

                self.message_user(request, f"Plan actualizado para {plan.lottery.name}")
            except Exception as e:
                self.message_user(request, f"Error: {str(e)}", level=messages.ERROR)

@admin.register(PrizeType)
class PrizeTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'requires_series', 'requires_exact_match')
    list_filter = ('requires_series', 'requires_exact_match', 'is_special')
    search_fields = ('name', 'code')
