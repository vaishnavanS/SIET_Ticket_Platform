from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta
from PIL import Image
import os

class TicketStatus(models.TextChoices):
    """Status choices for tickets"""
    OPEN = 'open', 'Open'
    IN_PROGRESS = 'in_progress', 'In Progress'
    RESOLVED = 'resolved', 'Resolved'
    CLOSED = 'closed', 'Closed'


class TicketUrgency(models.TextChoices):
    """Urgency level choices"""
    LOW = 'low', 'Low'
    MEDIUM = 'medium', 'Medium'
    HIGH = 'high', 'High'
    CRITICAL = 'critical', 'Critical'


class Category(models.Model):
    """Issue categories (admin-editable)"""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    assigned_group = models.ForeignKey('accounts.TechnicianGroup', on_delete=models.SET_NULL, 
                                       null=True, blank=True, related_name='categories')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name_plural = "Categories"
        ordering = ['name']


class IssueFormField(models.Model):
    class FieldType(models.TextChoices):
        TEXT = 'text', 'Short text'
        TEXTAREA = 'textarea', 'Long text'
        RADIO = 'radio', 'Radio buttons'
        CHECKBOX = 'checkbox', 'Checkboxes'
        SELECT = 'select', 'Dropdown'
        FILE = 'file', 'File upload'


    class ConditionType(models.TextChoices):
        ALWAYS = 'always', 'Always visible'
        VISIBLE_IF = 'visible_if', 'Visible if...'
        HIDDEN_IF = 'hidden_if', 'Hidden if...'

    class ConditionOperator(models.TextChoices):
        EQUALS = 'equals', 'Equals / Matches'
        CONTAINS = 'contains', 'Contains'
        IN = 'in', 'Is one of'
        NOT_EQUALS = 'not_equals', 'Does not equal'

    label = models.CharField(max_length=150)
    field_key = models.SlugField(max_length=80, unique=True)
    field_type = models.CharField(max_length=20, choices=FieldType.choices, default=FieldType.TEXT)
    help_text = models.CharField(max_length=255, blank=True, help_text="Short guidance or description under question")
    category = models.ForeignKey(Category, on_delete=models.CASCADE, null=True, blank=True,
                                related_name='custom_fields', help_text="Category for category-specific questions. Leave empty to apply globally.")
    options = models.JSONField(default=list, blank=True, help_text='One option per line for radio, checkbox, or dropdown fields')
    required = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    max_file_size_mb = models.PositiveIntegerField(default=5, help_text="Maximum allowed file size in Megabytes (MB)")


    # GLPI-grade conditional logic fields
    condition_type = models.CharField(max_length=20, choices=ConditionType.choices, default=ConditionType.ALWAYS, blank=True)
    condition_field_key = models.CharField(max_length=80, blank=True, help_text="Parent question field key to check")
    condition_operator = models.CharField(max_length=20, choices=ConditionOperator.choices, default=ConditionOperator.EQUALS, blank=True)
    condition_value = models.CharField(max_length=200, blank=True, help_text="Value that triggers this question (e.g. Network Issue, Other)")

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        cat_str = f" [{self.category.name}]" if self.category else " [Global]"
        return f"{self.label}{cat_str}"


class ServiceCatalogItem(models.Model):
    """Catalog items/services displayed to normal users"""
    title = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, default='📌', help_text='Emoji or icon representation')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True,
                                help_text='Optional category linked to this service')
    show_on_homepage = models.BooleanField(default=True, help_text='Display this item on user dashboard homepage')
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return self.title



class Ticket(models.Model):
    """Main ticket model for issue tracking"""
    ticket_number = models.PositiveIntegerField(unique=True, editable=False, blank=True)
    title = models.CharField(max_length=200)
    description = models.TextField()
    urgency = models.CharField(max_length=20, choices=TicketUrgency.choices, default=TicketUrgency.MEDIUM)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name='tickets')
    location = models.CharField(max_length=200)
    attachment = models.FileField(upload_to='ticket_attachments/%Y/%m/%d/', blank=True, null=True)
    custom_answers = models.JSONField(default=dict, blank=True)
    
    # Relationships
    reporter = models.ForeignKey(User, on_delete=models.PROTECT, related_name='reported_tickets')
    assigned_technician = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                           related_name='assigned_tickets', limit_choices_to={'profile__role': 'technician'})
    assigned_group = models.ForeignKey('accounts.TechnicianGroup', on_delete=models.SET_NULL, null=True, blank=True)
    
    # Status tracking
    status = models.CharField(max_length=20, choices=TicketStatus.choices, default=TicketStatus.OPEN)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    assigned_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # SLA Tracking
    sla_response_time = models.DurationField(default=timedelta(hours=1), 
                                            help_text="Time to assign technician")
    sla_resolution_time = models.DurationField(default=timedelta(hours=24),
                                              help_text="Time to resolve ticket")
    is_sla_breached = models.BooleanField(default=False)
    sla_breach_type = models.CharField(max_length=50, blank=True, 
                                      choices=[('response', 'Response SLA'), ('resolution', 'Resolution SLA')])
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['assigned_technician', 'status']),
            models.Index(fields=['reporter', 'status']),
        ]
    
    def __str__(self):
        return f"Ticket #{self.ticket_number} - {self.title}"
    
    def clean(self):
        """Validate attachment file"""
        if self.attachment:
            # Check file size
            max_size = 5 * 1024 * 1024  # 5MB
            if self.attachment.size > max_size:
                raise ValidationError(f"File size exceeds {max_size / (1024*1024)}MB limit")
            
            # Check file extension
            allowed_extensions = ['jpg', 'jpeg', 'png', 'gif']
            ext = os.path.splitext(self.attachment.name)[1][1:].lower()
            if ext not in allowed_extensions:
                raise ValidationError(f"File type not allowed. Allowed: {', '.join(allowed_extensions)}")
    
    def save(self, *args, **kwargs):
        self.clean()
        
        # Generate ticket_number if not set
        if not self.ticket_number:
            last_ticket = Ticket.objects.all().order_by('-ticket_number').first()
            self.ticket_number = (last_ticket.ticket_number + 1) if last_ticket else 1
        
        # Set assigned_at when status changes to in_progress
        if self.status == TicketStatus.IN_PROGRESS and not self.assigned_at:
            self.assigned_at = timezone.now()
        
        # Set resolved_at when status changes to resolved
        if self.status == TicketStatus.RESOLVED and not self.resolved_at:
            self.resolved_at = timezone.now()
            # Check if SLA was breached
            if self.created_at and (self.resolved_at > self.created_at + self.sla_resolution_time):
                self.is_sla_breached = True
                self.sla_breach_type = 'resolution'
        
        super().save(*args, **kwargs)


    
    def delete(self, *args, **kwargs):
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied("Tickets cannot be deleted. All ticket records must be preserved for audit and compliance integrity.")
    
    def assign_to_technician(self):

        """Auto-assign ticket to technician using round-robin method"""
        if self.assigned_technician:
            return  # Already assigned
        
        # Check if category has an assigned group
        if self.category.assigned_group:
            tech = self.category.assigned_group.get_available_technician()
        else:
            # Get all active technicians with lowest workload
            from accounts.models import UserProfile
            tech = self._get_available_technician_roundrobin()
        
        if tech:
            self.assigned_technician = tech
            self.assigned_group = self.category.assigned_group
            self.assigned_at = timezone.now()
            self.save()
            return tech
        
        return None
    
    def _get_available_technician_roundrobin(self):
        """Get available technician using round-robin from all technicians"""
        from accounts.models import UserProfile
        
        tech_profiles = UserProfile.objects.filter(role='technician', is_active=True, is_suspended=False)
        available_techs = []
        
        for profile in tech_profiles:
            user = profile.user
            active_count = Ticket.objects.filter(
                assigned_technician=user,
                status__in=['open', 'in_progress']
            ).count()
            
            if active_count < profile.max_active_tickets:
                available_techs.append((user, active_count))
        
        if available_techs:
            # Sort by active count and return the one with least tickets
            available_techs.sort(key=lambda x: x[1])
            return available_techs[0][0]
        
        return None
    
    def check_sla_breach(self):
        """Check if ticket has breached SLA"""
        now = timezone.now()
        
        # Check response SLA (if not yet assigned)
        if not self.assigned_at and now > self.created_at + self.sla_response_time:
            self.is_sla_breached = True
            self.sla_breach_type = 'response'
            self.save()
        
        # Check resolution SLA (if not yet resolved)
        elif self.status not in [TicketStatus.RESOLVED, TicketStatus.CLOSED]:
            if now > self.created_at + self.sla_resolution_time:
                self.is_sla_breached = True
                self.sla_breach_type = 'resolution'
                self.save()
    
    @property
    def time_to_resolution(self):
        """Get time taken to resolve"""
        if self.resolved_at and self.created_at:
            return self.resolved_at - self.created_at
        return None
    
    @property
    def is_overdue(self):
        """Check if ticket is overdue"""
        if self.status not in [TicketStatus.RESOLVED, TicketStatus.CLOSED]:
            return timezone.now() > self.created_at + self.sla_resolution_time
        return False


class TicketComment(models.Model):
    """Comments/updates on tickets"""
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(User, on_delete=models.PROTECT, related_name='ticket_comments')
    content = models.TextField()
    attachment = models.FileField(upload_to='comment_attachments/%Y/%m/%d/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Comment by {self.author.username} on Ticket #{self.ticket.ticket_number}"


class TicketHistory(models.Model):
    """Audit trail for ticket changes"""
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='history')
    changed_by = models.ForeignKey(User, on_delete=models.PROTECT)
    field_name = models.CharField(max_length=50)
    old_value = models.TextField(blank=True)
    new_value = models.TextField(blank=True)
    changed_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-changed_at']
        verbose_name_plural = "Ticket Histories"
    
    def __str__(self):
        return f"Ticket #{self.ticket.ticket_number} - {self.field_name} changed"

