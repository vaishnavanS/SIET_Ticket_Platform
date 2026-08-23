from django.contrib import admin
from .models import UserProfile, TechnicianGroup

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

