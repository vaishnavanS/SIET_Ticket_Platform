from django.contrib import admin
from .models import Category, Ticket, TicketComment, TicketHistory

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'assigned_group', 'get_ticket_count', 'created_at')
    list_filter = ('assigned_group', 'created_at')
    search_fields = ('name', 'description')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('Category Info', {'fields': ('name', 'description', 'assigned_group')}),
        ('Timestamps', {'fields': ('created_at', 'updated_at'), 'classes': ('collapse',)}),
    )
    
    def get_ticket_count(self, obj):
        return obj.tickets.count()
    get_ticket_count.short_description = 'Tickets'


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ('ticket_number', 'title', 'urgency', 'status', 'assigned_technician', 'is_sla_breached', 'created_at')
    list_filter = ('status', 'urgency', 'category', 'is_sla_breached', 'created_at')
    search_fields = ('ticket_number', 'title', 'description', 'location')
    readonly_fields = ('ticket_number', 'created_at', 'assigned_at', 'resolved_at', 'updated_at')
    filter_horizontal = ()
    
    fieldsets = (
        ('Ticket Info', {'fields': ('ticket_number', 'title', 'description', 'location')}),
        ('Classification', {'fields': ('category', 'urgency')}),
        ('Assignment', {'fields': ('reporter', 'assigned_technician', 'assigned_group')}),
        ('Status & Tracking', {'fields': ('status', 'created_at', 'assigned_at', 'resolved_at', 'updated_at')}),
        ('SLA & Compliance', {'fields': ('sla_response_time', 'sla_resolution_time', 'is_sla_breached', 'sla_breach_type')}),
        ('Attachments', {'fields': ('attachment',)}),
    )
    
    def get_readonly_fields(self, request, obj=None):
        if obj:  # Viewing an existing object
            return self.readonly_fields + ('title', 'description', 'location', 'category', 'reporter', 'custom_answers')
        return self.readonly_fields
    
    def has_delete_permission(self, request, obj=None):
        return False
    
    actions = ['mark_in_progress', 'mark_resolved', 'mark_closed']

    
    def mark_in_progress(self, request, queryset):
        updated = queryset.update(status='in_progress')
        self.message_user(request, f'{updated} ticket(s) marked as In Progress')
    mark_in_progress.short_description = 'Mark selected as In Progress'
    
    def mark_resolved(self, request, queryset):
        updated = queryset.update(status='resolved')
        self.message_user(request, f'{updated} ticket(s) marked as Resolved')
    mark_resolved.short_description = 'Mark selected as Resolved'
    
    def mark_closed(self, request, queryset):
        updated = queryset.update(status='closed')
        self.message_user(request, f'{updated} ticket(s) marked as Closed')
    mark_closed.short_description = 'Mark selected as Closed'


@admin.register(TicketComment)
class TicketCommentAdmin(admin.ModelAdmin):
    list_display = ('ticket', 'author', 'created_at')
    list_filter = ('ticket', 'author', 'created_at')
    search_fields = ('ticket__title', 'author__username', 'content')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Comment Info', {'fields': ('ticket', 'author', 'content')}),
        ('Attachments', {'fields': ('attachment',)}),
        ('Timestamps', {'fields': ('created_at', 'updated_at'), 'classes': ('collapse',)}),
    )


@admin.register(TicketHistory)
class TicketHistoryAdmin(admin.ModelAdmin):
    list_display = ('ticket', 'field_name', 'changed_by', 'changed_at')
    list_filter = ('field_name', 'changed_by', 'changed_at')
    search_fields = ('ticket__title', 'field_name', 'changed_by__username')
    readonly_fields = ('ticket', 'changed_by', 'field_name', 'old_value', 'new_value', 'changed_at')
    
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False

