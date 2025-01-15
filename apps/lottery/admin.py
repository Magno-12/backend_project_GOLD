from django.contrib import admin
from django.http import HttpResponse
from django.contrib import messages
from django.core.files.base import ContentFile
from django.utils.html import format_html
from django.forms import TextInput
from django.utils import timezone
from django.db.models import Sum, Count
import cloudinary
import cloudinary.uploader
import csv
import pytz
from datetime import datetime, time
from io import TextIOWrapper
from datetime import datetime
from .models import Lottery, Bet, LotteryResult, Prize, PrizePlan, PrizeType


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
                'requires_series', 'available_series'
            )
        }),
        ('Configuración de Fracciones', {
            'fields': (
                'fraction_count', 'fraction_price', 'major_prize_amount',
                'max_fractions_per_combination'
            )
        }),
        ('Límites de Apuestas', {
            'fields': (
                'min_bet_amount', 'max_bet_amount'
            )
        }),
        ('Configuración de Sorteos', {
            'fields': (
                'closing_time', 'last_draw_number', 'next_draw_date'
            )
        }),
    )

    actions = [
        'generate_sales_file',
        'generate_unsold_file', 
        'generate_type_204_report'
    ]

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
            content.append(f"{lottery.last_draw_number + 1:04d}")  # Número sorteo
            content.append(f"{len(sold_bets):07d}")  # Total ventas

            # Detalle de ventas
            for bet in sold_bets:
                line = (
                    f"{bet.number:04d}"           # Número
                    f"{bet.series:03d}"           # Serie
                    f"{int(bet.amount/lottery.fraction_price):03d}"  # Fracciones
                    f"19"                         # Código departamento
                    f"{'BBC':>5}"                 # Serie tiquete
                    f"{bet.id:0>10}"              # Consecutivo
                    f"GOLD{bet.id:014}"           # Código seguridad
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
            content.append(f"{str(lottery.last_draw_number + 1):0>4}") # Aseguramos 4 dígitos
            
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
            content.append(f"{total_fractions:0>7}") # Aseguramos 7 dígitos

            # Detalle de billetes
            for ticket in unsold_tickets:
                fractions = int(ticket.amount/lottery.fraction_price)
                line = (
                    f"{ticket.number:0>4}"     # NNNN
                    f"{ticket.series:0>3}"     # SSS
                    f"{fractions:0>3}"         # FFF
                    f"{fractions:0>2}"         # ##
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
                line = (
                    f"{bet.number:04d}{bet.series:03d}"
                    f"{int(bet.amount/lottery.fraction_price):03d}19"
                    f"{'BBC'}{bet.id:0>10}"
                    f"GOLD{bet.id:014}"
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

    generate_type_204_report.short_description = "Generar reporte tipo 204"

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

@admin.register(PrizePlan)  # Registrar el modelo correcto
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