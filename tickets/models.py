from django.db import models, transaction, IntegrityError
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
class CampusLocation(models.Model):
    """Admin-managed campus locations / buildings / blocks"""
    name = models.CharField(max_length=100, unique=True, help_text="e.g. Admin Block, Tech Park, Academic Block, Boys Hostel")
    code = models.CharField(max_length=30, blank=True, default='', help_text="Short identifier e.g. TECH_PARK, ADMIN_BLOCK")
    description = models.TextField(blank=True, default='', help_text="Description of this campus zone")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Campus Locations"
        ordering = ['name']

    def __str__(self):
        return self.name


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
    description = models.TextField(blank=True, default='')
    icon = models.CharField(max_length=50, default='📌', blank=True, help_text='Emoji or icon representation')
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



def get_admin_max_upload_size_bytes():
    """Returns max upload size in bytes configured by admin in IssueFormField or settings"""
    try:
        field = IssueFormField.objects.filter(field_key__in=['attachment', 'problem_attachment', 'file_upload'], is_active=True).first()
        if field and field.max_file_size_mb:
            return field.max_file_size_mb * 1024 * 1024
    except Exception:
        pass
    from django.conf import settings
    return getattr(settings, 'MAX_UPLOAD_SIZE', 5 * 1024 * 1024)


class Ticket(models.Model):
    """Main ticket model for issue tracking"""
    ticket_number = models.PositiveIntegerField(unique=True, editable=False, blank=True)
    title = models.CharField(max_length=200)
    description = models.TextField()
    urgency = models.CharField(max_length=20, choices=TicketUrgency.choices, default=TicketUrgency.MEDIUM)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name='tickets')
    campus_location = models.ForeignKey(CampusLocation, on_delete=models.SET_NULL, null=True, blank=True, related_name='tickets')
    location_details = models.CharField(max_length=200, blank=True, default='', help_text="Room / Lab / Specific location e.g. VLSI Lab")
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
            max_size = get_admin_max_upload_size_bytes()
            max_mb = max_size / (1024 * 1024)
            if hasattr(self.attachment, 'size') and self.attachment.size > max_size:
                raise ValidationError(f"File size exceeds {max_mb:.0f}MB limit configured by administrator.")
            
            allowed_extensions = ['jpg', 'jpeg', 'png', 'gif']
            ext = os.path.splitext(self.attachment.name)[1].lstrip('.').lower()
            if ext not in allowed_extensions:
                raise ValidationError(f"File type not allowed. Allowed: {', '.join(allowed_extensions)}")

    
    def save(self, *args, **kwargs):
        # Auto-compose location string from campus_location + location_details
        if self.campus_location:
            if self.location_details:
                self.location = f"{self.campus_location.name} - {self.location_details}"
            elif not self.location:
                self.location = self.campus_location.name

        self.clean()
        
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
        
        # Generate ticket_number atomically with retry to prevent concurrent collision
        if not self.ticket_number:
            for attempt in range(5):
                try:
                    with transaction.atomic():
                        max_ticket = Ticket.objects.select_for_update().order_by('-ticket_number').first()
                        self.ticket_number = (max_ticket.ticket_number + 1) if (max_ticket and max_ticket.ticket_number) else 1
                        super().save(*args, **kwargs)
                        return
                except IntegrityError:
                    if attempt == 4:
                        raise
                    self.ticket_number = None
                    continue
        else:
            super().save(*args, **kwargs)

    
    def delete(self, *args, **kwargs):
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied("Tickets cannot be deleted. All ticket records must be preserved for audit and compliance integrity.")
    
    def assign_to_technician(self):
        """Auto-assign ticket to technician using location routing, category group routing, or round-robin method"""
        if self.assigned_technician:
            return self.assigned_technician  # Already assigned
        
        tech = None
        target_group = None

        # 1. Location-based group routing (e.g. Tech Park -> Tech Park tech, Hostel -> Hostel tech)
        if self.campus_location or self.location:
            from accounts.models import TechnicianGroup
            groups_with_loc = list(TechnicianGroup.objects.prefetch_related('campus_locations', 'categories', 'technicians'))
            matching_groups = []
            for g in groups_with_loc:
                if self.campus_location and g.campus_locations.filter(pk=self.campus_location.pk).exists():
                    matching_groups.append(g)
                elif self.location and g.matches_location(self.location, self.campus_location):
                    matching_groups.append(g)

            if matching_groups:
                # Prioritize group that also matches ticket's category if one exists
                if self.category:
                    cat_match = next((g for g in matching_groups if self.category in g.categories.all()), None)
                    if cat_match:
                        candidate = cat_match.get_available_technician()
                        if candidate:
                            tech = candidate
                            target_group = cat_match

                if not tech:
                    for g in matching_groups:
                        candidate = g.get_available_technician()
                        if candidate:
                            tech = candidate
                            target_group = g
                            break

                if not target_group:
                    target_group = matching_groups[0]

        # 2. Category-based group routing fallback
        if not tech and self.category and self.category.assigned_group:
            target_group = self.category.assigned_group
            tech = target_group.get_available_technician()
        
        # 3. Fallback to general round-robin if group has no available technician or no group configured
        if not tech:
            tech = self._get_available_technician_roundrobin()
        
        if tech:
            self.assigned_technician = tech
            if target_group:
                self.assigned_group = target_group
            elif not self.assigned_group and self.category and self.category.assigned_group:
                self.assigned_group = self.category.assigned_group
            self.assigned_at = timezone.now()
            self.save(update_fields=['assigned_technician', 'assigned_group', 'assigned_at', 'updated_at'])
            try:
                from .services import send_ticket_assigned_email
                send_ticket_assigned_email(self, tech)
            except Exception:
                pass
            return tech
        elif target_group or self.assigned_group:
            if target_group and not self.assigned_group:
                self.assigned_group = target_group
            self.save(update_fields=['assigned_group', 'updated_at'])
        
        return None
    
    def _get_available_technician_roundrobin(self):
        """Get available technician using round-robin from all technicians with row locking"""
        from accounts.models import UserProfile
        
        with transaction.atomic():
            tech_profiles = UserProfile.objects.select_for_update().filter(
                role='technician', is_active=True, is_suspended=False
            ).select_related('user')
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

    def clean(self):
        """Validate comment attachment file size and allowed extensions"""
        if self.attachment:
            max_size = get_admin_max_upload_size_bytes()
            max_mb = max_size / (1024 * 1024)
            if hasattr(self.attachment, 'size') and self.attachment.size > max_size:
                raise ValidationError(f"Attachment exceeds {max_mb:.0f}MB limit configured by administrator.")
            
            allowed_extensions = ['jpg', 'jpeg', 'png', 'gif']
            ext = os.path.splitext(self.attachment.name)[1].lstrip('.').lower()
            if ext not in allowed_extensions:
                raise ValidationError(f"File type not allowed. Allowed: {', '.join(allowed_extensions)}")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)



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


class TicketNotification(models.Model):
    """In-app notifications for ticket status changes and comments"""
    class NotificationType(models.TextChoices):
        RESOLVED = 'resolved', 'Issue Resolved'
        COMMENT = 'comment', 'New Comment'
        REOPENED = 'reopened', 'Ticket Reopened'
        CLOSED = 'closed', 'Ticket Closed'
        ASSIGNED = 'assigned', 'Ticket Assigned'

    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ticket_notifications')
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, null=True, blank=True, related_name='notifications')
    title = models.CharField(max_length=200)
    message = models.TextField()
    notification_type = models.CharField(max_length=30, choices=NotificationType.choices, default=NotificationType.COMMENT)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Notification for {self.recipient.username}: {self.title}"


class SolutionArticle(models.Model):
    """Self-help diagnostic & resolution guide for common campus issues (Wi-Fi, LAN, SEB, etc.)"""
    class TargetCategory(models.TextChoices):
        WIFI_LAN = 'wifi_lan', 'Wi-Fi & LAN Network'
        SEB = 'seb', 'Safe Exam Browser (SEB)'
        HARDWARE = 'hardware', 'PC & Hardware'
        HOSTEL = 'hostel', 'Hostel Facilities'
        GENERAL = 'general', 'General IT'

    title = models.CharField(max_length=200)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True,
                                related_name='solutions', help_text="Linked category for automated ticket pre-filling")
    target_category = models.CharField(max_length=30, choices=TargetCategory.choices, default=TargetCategory.WIFI_LAN)
    summary = models.CharField(max_length=300, help_text="Short 1-sentence summary of the symptom/problem")
    symptoms = models.TextField(blank=True, help_text="Key indicators to confirm this is the problem (one per line)")
    solution_steps = models.TextField(help_text="Step-by-step resolution instructions (one step per line)")
    verification_checklist = models.TextField(blank=True, help_text="Checklist items to verify before raising a ticket (one per line)")
    helpful_count = models.PositiveIntegerField(default=0, help_text="Times students confirmed this solved their issue (deflected tickets)")
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', 'id']
        verbose_name = "Solution Article"
        verbose_name_plural = "Solution Articles"

    def __str__(self):
        return self.title

    def get_symptoms_list(self):
        return [s.strip() for s in self.symptoms.splitlines() if s.strip()]

    def get_steps_list(self):
        return [s.strip() for s in self.solution_steps.splitlines() if s.strip()]

    def get_solution_steps_list(self):
        return self.get_steps_list()

    def get_checklist(self):
        return [s.strip() for s in self.verification_checklist.splitlines() if s.strip()]

    def get_checklist_list(self):
        return self.get_checklist()

    def category_badge_class(self):
        mapping = {
            self.TargetCategory.WIFI_LAN: 'badge-wifi',
            self.TargetCategory.SEB: 'badge-seb',
            self.TargetCategory.HARDWARE: 'badge-hw',
            self.TargetCategory.HOSTEL: 'badge-hostel',
            self.TargetCategory.GENERAL: 'badge-gen',
        }
        return mapping.get(self.target_category, 'badge-gen')


TargetCategory = SolutionArticle.TargetCategory


