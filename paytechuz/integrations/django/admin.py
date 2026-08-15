"""
Django admin configuration for PayTechUZ.
"""
from django.contrib import admin
from django.utils.html import format_html

from .models import PaymentTransaction


@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
    """
    Admin configuration for PaymentTransaction model.
    """
    list_display = (
        'id',
        'gateway',
        'transaction_id',
        'account_id',
        'amount',
        'state_display',
        'created_at',
        'updated_at',
    )
    list_filter = ('gateway', 'state', 'created_at')
    search_fields = ('transaction_id', 'account_id')
    readonly_fields = (
        'gateway',
        'transaction_id',
        'account_id',
        'amount',
        'state',
        'extra_data',
        'created_at',
        'updated_at',
        'performed_at',
        'cancelled_at',
    )
    fieldsets = (
        ('Transaction Information', {
            'fields': (
                'gateway',
                'transaction_id',
                'account_id',
                'amount',
                'state',
            )
        }),
        ('Timestamps', {
            'fields': (
                'created_at',
                'updated_at',
                'performed_at',
                'cancelled_at',
            )
        }),
        ('Additional Data', {
            'fields': ('extra_data',),
            'classes': ('collapse',),
        }),
    )

    def state_display(self, obj):
        """
        Display the state with a colored badge.
        """
        states = {
            PaymentTransaction.CREATED: ('#f8f9fa', '#212529', 'Created'),
            PaymentTransaction.INITIATING: ('#fff3cd', '#856404', 'Initiating'),
            PaymentTransaction.SUCCESSFULLY: ('#d4edda', '#155724', 'Successfully'),
            PaymentTransaction.CANCELLED: ('#f8d7da', '#721c24', 'Cancelled'),
            PaymentTransaction.CANCELLED_DURING_INIT: ('#f8d7da', '#721c24', 'Cancelled (Init)'),
        }
        if obj.state in states:
            bg, color, label = states[obj.state]
            return format_html(
                '<span style="background-color: {}; color: {}; padding: 3px 8px; border-radius: 4px;">{}</span>',
                bg, color, label
            )
        return format_html('<span>{}</span>', obj.get_state_display())

    state_display.short_description = 'State'
