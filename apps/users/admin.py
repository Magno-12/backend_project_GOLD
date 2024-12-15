from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.db import models
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('phone_number', 'get_full_name', 'email', 'is_active', 'get_bet_count', 'get_total_won')
    list_filter = ('is_active', 'is_staff', 'date_joined')
    search_fields = ('phone_number', 'email', 'first_name', 'last_name', 'identification')
    ordering = ('-date_joined',)
    
    fieldsets = (
        (None, {'fields': ('phone_number', 'pin')}),
        (_('Personal info'), {'fields': ('first_name', 'last_name', 'email', 'identification', 'birth_date')}),
        (_('Documents'), {'fields': ('document_front', 'document_back')}),
        (_('Permissions'), {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('phone_number', 'pin', 'email', 'first_name', 'last_name', 'identification', 'birth_date'),
        }),
    )

    def get_bet_count(self, obj):
        return obj.bets.count()
    get_bet_count.short_description = 'Total Apuestas'

    def get_total_won(self, obj):
        return obj.bets.filter(status='WON').aggregate(
            total=models.Sum('won_amount')
        )['total'] or 0
    get_total_won.short_description = 'Total Ganado'
