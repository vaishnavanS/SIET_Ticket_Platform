from django.contrib import admin
from .models import UserProfile, TechnicianGroup, SiteEmailSetting, EmailQueue

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'is_active', 'is_suspended', 'max_active_tickets', 'created_at')
    list_filter = ('role', 'is_active', 'is_suspended', 'created_at')
    search_fields = ('user__username', 'user__email', 'user__first_name', 'user__last_name')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('User Info', {'fields': ('user', 'role')}),
        ('Status', {'fields': ('is_active', 'is_suspended')}),
        ('Settings', {'fields': ('max_active_tickets',)}),
        ('Timestamps', {'fields': ('created_at', 'updated_at'), 'classes': ('collapse',)}),
    )

@admin.register(TechnicianGroup)
class TechnicianGroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'max_tickets_per_tech', 'get_technician_count', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('name', 'description')
    filter_horizontal = ('technicians',)
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('Group Info', {'fields': ('name', 'description')}),
        ('Settings', {'fields': ('max_tickets_per_tech', 'technicians')}),
        ('Timestamps', {'fields': ('created_at', 'updated_at'), 'classes': ('collapse',)}),
    )
    
    def get_technician_count(self, obj):
        return obj.technicians.count()
    get_technician_count.short_description = 'Number of Technicians'


@admin.register(SiteEmailSetting)
class SiteEmailSettingAdmin(admin.ModelAdmin):
    list_display = ('site_name', 'from_email', 'smtp_backend', 'smtp_host', 'smtp_port', 'smtp_use_tls', 'updated_at')
    readonly_fields = ('updated_at',)


@admin.register(EmailQueue)
class EmailQueueAdmin(admin.ModelAdmin):
    list_display = ('id', 'recipient_email', 'subject', 'status', 'attempts', 'notification_type', 'created_at', 'sent_at')
    list_filter = ('status', 'notification_type', 'created_at')
    search_fields = ('recipient_email', 'recipient_name', 'subject', 'body', 'error_message')
    readonly_fields = ('created_at', 'sent_at')
    actions = ['retry_failed_emails']

    def retry_failed_emails(self, request, queryset):
        count = queryset.filter(status='failed').update(status='pending', attempts=0)
        self.message_user(request, f"Marked {count} failed email(s) for retry.")
    retry_failed_emails.short_description = "Retry selected failed emails"


