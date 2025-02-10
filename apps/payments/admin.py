# admin.py
from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html
from .models.transaction import Transaction, UserBalance
from .models.withdrawal import PrizeWithdrawal
from .models.bank_account import BankDestinationAccount


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = [
        'reference', 'user', 'amount', 'status',
        'payment_method', 'created_at'
    ]
    list_filter = ['status', 'payment_method', 'created_at']
    search_fields = [
        'reference', 'wompi_id', 'user__email',
        'user__first_name', 'user__last_name'
    ]
    readonly_fields = ['wompi_id', 'reference', 'signature']
    fieldsets = (
        ('Información básica', {
            'fields': (
                'user', 'amount', 'reference', 'status',
                'payment_method'
            )
        }),
        ('Información adicional', {
            'fields': (
                'wompi_id', 'signature', 'payment_data',
                'status_detail', 'error_detail'
            )
        }),
    )


@admin.register(UserBalance)
class UserBalanceAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'balance', 'last_transaction_date',
        'created_at', 'updated_at'
    ]
    search_fields = ['user__email', 'user__first_name', 'user__last_name']
    readonly_fields = ['balance', 'last_transaction']
    
    def last_transaction_date(self, obj):
        return obj.last_transaction.created_at if obj.last_transaction else '-'
    last_transaction_date.short_description = 'Última transacción'


@admin.register(PrizeWithdrawal)
class PrizeWithdrawalAdmin(admin.ModelAdmin):
    list_display = [
        'withdrawal_code', 'user', 'amount', 'status_colored',
        'bank_info', 'created_at', 'expiration_status', 'destination_account'
    ]
    list_filter = ['status', 'bank', 'account_type', 'created_at']
    search_fields = [
        'withdrawal_code', 'user__email', 'user__first_name',
        'user__last_name', 'account_number'
    ]
    readonly_fields = ['withdrawal_code', 'expiration_date', 'destination_account']
    actions = ['approve_withdrawals', 'reject_withdrawals']
    fieldsets = (
        ('Información básica', {
            'fields': (
                'user', 'amount', 'withdrawal_code', 'status',
                'expiration_date'
            )
        }),
        ('Información bancaria', {
            'fields': (
                'bank', 'account_type', 'account_number'
            )
        }),
        ('Notas y procesamiento', {
            'fields': (
                'admin_notes', 'processed_date'
            )
        }),
    )

    def status_colored(self, obj):
        colors = {
            'PENDING': 'orange',
            'APPROVED': 'green',
            'REJECTED': 'red',
            'EXPIRED': 'gray',
            'REVERSED': 'purple'
        }
        return format_html(
            '<span style="color: {};">{}</span>',
            colors[obj.status],
            obj.get_status_display()
        )
    status_colored.short_description = 'Estado'

    def bank_info(self, obj):
        return f"{obj.get_bank_display()} - {obj.get_account_type_display()}"
    bank_info.short_description = 'Información bancaria'

    def expiration_status(self, obj):
        if obj.status not in ['PENDING']:
            return '-'
        if obj.expiration_date and obj.expiration_date < timezone.now():
            return format_html(
                '<span style="color: red;">Expirado</span>'
            )
        return format_html(
            '<span style="color: green;">Vigente</span>'
        )
    expiration_status.short_description = 'Estado de expiración'

    def approve_withdrawals(self, request, queryset):
        for withdrawal in queryset.filter(status='PENDING'):
            withdrawal.status = 'APPROVED'
            withdrawal.processed_date = timezone.now()
            withdrawal.save()
    approve_withdrawals.short_description = "Aprobar retiros seleccionados"

    def reject_withdrawals(self, request, queryset):
        for withdrawal in queryset.filter(status='PENDING'):
            withdrawal.status = 'REJECTED'
            withdrawal.processed_date = timezone.now()
            # Revertir el balance
            balance = withdrawal.user.balance
            balance.balance += withdrawal.amount
            balance.save()
            withdrawal.save()
    reject_withdrawals.short_description = "Rechazar retiros seleccionados"

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(BankDestinationAccount)
class BankDestinationAccountAdmin(admin.ModelAdmin):
    list_display = [
        'bank', 'account_type', 'account_number',
        'account_owner', 'is_active', 'description'
    ]
    list_filter = ['bank', 'account_type', 'is_active']
    search_fields = [
        'account_number', 'account_owner',
        'identification_number', 'description'
    ]
    fieldsets = (
        ('Información bancaria', {
            'fields': (
                'bank', 'account_type', 'account_number',
                'description', 'is_active'
            )
        }),
        ('Información del titular', {
            'fields': (
                'account_owner', 'identification_type',
                'identification_number'
            )
        })
    )
