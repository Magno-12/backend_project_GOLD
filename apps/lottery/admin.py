from django.contrib import admin
from django.http import HttpResponse
from django.contrib import messages
from django.core.files.base import ContentFile
from django.utils.html import format_html
from django.utils import timezone
from django.db.models import Sum, Count
import cloudinary
import cloudinary.uploader
import csv
from io import TextIOWrapper
from datetime import datetime
from .models import Lottery, Bet, LotteryResult, Prize, PrizePlan, PrizeType

@admin.register(Lottery)
class LotteryAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'draw_day', 'draw_time', 'is_active', 
                   'fraction_count', 'fraction_price', 'get_ranges_file', 
                   'get_unsold_file', 'get_sales_file')
    list_filter = ('is_active', 'draw_day')
    search_fields = ('name', 'code')
    readonly_fields = ('number_ranges_file', 'unsold_tickets_file', 'sales_file')
    
    fieldsets = (
        ('Información Básica', {
            'fields': (
                'name', 'code', 'draw_day', 'draw_time', 'is_active', 
                'requires_series'
            )
        }),
        ('Configuración de Fracciones', {
            'fields': (
                'fraction_count', 'fraction_price', 'major_prize_amount'
            )
        }),
        ('Límites de Apuestas', {
            'fields': (
                'min_bet_amount', 'max_bet_amount'
            )
        }),
        ('Archivos', {
            'fields': (
                'number_ranges_file', 'unsold_tickets_file', 'sales_file'
            )
        })
    )
    
    actions = ['process_ranges_file', 'generate_unsold_report', 'generate_sales_report']

    def get_ranges_file(self, obj):
        if obj.number_ranges_file:
            return format_html('<a href="{}" target="_blank">Ver archivo</a>', obj.number_ranges_file)
        return '-'
    get_ranges_file.short_description = 'Archivo de Rangos'

    def get_unsold_file(self, obj):
        if obj.unsold_tickets_file:
            return format_html('<a href="{}" target="_blank">Ver archivo</a>', obj.unsold_tickets_file)
        return '-'
    get_unsold_file.short_description = 'Billetes No Vendidos'

    def get_sales_file(self, obj):
        if obj.sales_file:
            return format_html('<a href="{}" target="_blank">Ver archivo</a>', obj.sales_file)
        return '-'
    get_sales_file.short_description = 'Archivo de Ventas'

    def process_ranges_file(self, request, queryset):
        if len(queryset) != 1:
            self.message_user(request, "Seleccione una sola lotería", level=messages.ERROR)
            return

        if 'file' not in request.FILES:
            self.message_user(request, "No se ha seleccionado ningún archivo", level=messages.ERROR)
            return

        try:
            lottery = queryset[0]
            csv_file = request.FILES['file']
            file_data = TextIOWrapper(csv_file, encoding='utf-8')
            reader = csv.reader(file_data)
            valid_rows = []
            
            for row in reader:
                if len(row) == 1:
                    number = row[0].split(',')
                    if len(number) == 4:
                        valid_rows.append(row[0])

            if not valid_rows:
                self.message_user(request, "El archivo no contiene datos válidos", level=messages.ERROR)
                return

            result = cloudinary.uploader.upload(
                csv_file,
                resource_type='raw',
                folder=f'lottery/ranges/',
                public_id=f'ranges_{lottery.code}_{datetime.now().strftime("%Y%m%d_%H%M%S")}',
            )

            lottery.number_ranges_file = result['secure_url']
            lottery.save()

            self.message_user(
                request, 
                f'Archivo procesado exitosamente. {len(valid_rows)} rangos válidos.',
                level=messages.SUCCESS
            )

        except Exception as e:
            self.message_user(request, f'Error procesando archivo: {str(e)}', level=messages.ERROR)

    process_ranges_file.short_description = "Procesar archivo de rangos"

    def generate_unsold_report(self, request, queryset):
        if len(queryset) != 1:
            self.message_user(request, "Seleccione una sola lotería", level=messages.ERROR)
            return

        lottery = queryset[0]
        try:
            content = []
            content.append("06")
            content.append("0993")
            content.append(str(lottery.sorteo_number))
            
            unsold_tickets = lottery.bets.filter(status='PENDING')
            content.append(str(unsold_tickets.count()))
            
            for ticket in unsold_tickets:
                line = (
                    f"{ticket.number:04d}"
                    f"{ticket.series:03d}"
                    f"{lottery.fraction_count:03d}"
                    f"{lottery.fraction_count:02d}"
                    f"001"
                    f"01"
                )
                content.append(line)

            file_content = '\n'.join(content)
            result = cloudinary.uploader.upload(
                ContentFile(file_content.encode()),
                resource_type='raw',
                folder=f'lottery/unsold/',
                public_id=f'unsold_{lottery.code}_{datetime.now().strftime("%Y%m%d_%H%M%S")}',
            )

            lottery.unsold_tickets_file = result['secure_url']
            lottery.save()

            response = HttpResponse(file_content, content_type='text/plain')
            response['Content-Disposition'] = f'attachment; filename="devoluciones_{lottery.code}.txt"'
            return response

        except Exception as e:
            self.message_user(request, f'Error generando reporte: {str(e)}', level=messages.ERROR)

    generate_unsold_report.short_description = "Generar reporte no vendidos"

    def generate_sales_report(self, request, queryset):
        if len(queryset) != 1:
            self.message_user(request, "Seleccione una sola lotería", level=messages.ERROR)
            return

        lottery = queryset[0]
        try:
            content = []
            content.append("VENTA06")
            content.append("0993")
            content.append(str(lottery.sorteo_number))

            sold_tickets = lottery.bets.filter(status='PENDING')
            content.append(str(sold_tickets.count()))

            for ticket in sold_tickets:
                line = (
                    f"{ticket.number:04d}"
                    f"{ticket.series:03d}"
                    f"{ticket.fraction:03d}"
                    f"{ticket.department_code:02d}"
                    f"{ticket.ticket_series:>5}"
                    f"{ticket.ticket_number:0>10}"
                    f"{ticket.security_code:14}"
                )
                content.append(line)

            file_content = '\n'.join(content)
            result = cloudinary.uploader.upload(
                ContentFile(file_content.encode()),
                resource_type='raw',
                folder=f'lottery/sales/',
                public_id=f'sales_{lottery.code}_{datetime.now().strftime("%Y%m%d_%H%M%S")}',
            )

            lottery.sales_file = result['secure_url']
            lottery.save()

            filename = f"V_discoin{lottery.sorteo_number}.06"
            response = HttpResponse(file_content, content_type='text/plain')
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response

        except Exception as e:
            self.message_user(
                request, 
                f'Error generando archivo de ventas: {str(e)}',
                level=messages.ERROR
            )

    generate_sales_report.short_description = "Generar reporte de ventas"

    def save_model(self, request, obj, form, change):
        if change and 'is_active' in form.changed_data and not obj.is_active:
            # Lógica adicional al desactivar lotería
            pass
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