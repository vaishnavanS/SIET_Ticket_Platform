from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinLengthValidator
from django.utils import timezone

class UserRole(models.TextChoices):
    """User role choices"""
    ADMIN = 'admin', 'Admin'
    TECHNICIAN = 'technician', 'Technician'
    NORMAL_USER = 'normal_user', 'Normal User'


class UserProfile(models.Model):
    """Extended user profile with role and metadata"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=UserRole.choices, default=UserRole.NORMAL_USER)
    is_active = models.BooleanField(default=True)
    is_suspended = models.BooleanField(default=False)
    max_active_tickets = models.IntegerField(default=8, help_text="Maximum active tickets allowed for technician")
    phone_number = models.CharField(max_length=20, blank=True, default='')
    department = models.CharField(max_length=100, blank=True, default='')
    is_email_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def get_initials(self):
        if self.user.first_name and self.user.last_name:
            return f"{self.user.first_name[0]}{self.user.last_name[0]}".upper()
        elif self.user.first_name:
            return self.user.first_name[:2].upper()
        return self.user.username[:2].upper()

    def __str__(self):
        return f"{self.user.username} ({self.get_role_display()})"
    
    class Meta:
        verbose_name_plural = "User Profiles"


class TechnicianGroup(models.Model):
    """Group of technicians for categorized issue assignment"""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    max_tickets_per_tech = models.IntegerField(default=8, help_text="Max tickets per technician in this group")
    technicians = models.ManyToManyField(User, related_name='technician_groups', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name
    
    def get_available_technician(self):
        """
        Get the technician in this group with the lowest active ticket count
        Returns None if all technicians are at max capacity
        """
        from tickets.models import Ticket
        
        available_techs = []
        for tech in self.technicians.filter(profile__is_active=True, profile__is_suspended=False):
            active_count = Ticket.objects.filter(
                assigned_technician=tech,
                status__in=['open', 'in_progress']
            ).count()
            
            max_allowed = tech.profile.max_active_tickets if hasattr(tech, 'profile') else self.max_tickets_per_tech
            
            if active_count < max_allowed:
                available_techs.append((tech, active_count))
        
        if available_techs:
            # Sort by active count and return the one with least tickets
            available_techs.sort(key=lambda x: x[1])
            return available_techs[0][0]
        
        return None
    
    class Meta:
        ordering = ['name']


class SiteEmailSetting(models.Model):
    """System-wide email and SMTP configuration managed by Administrator"""
    site_name = models.CharField(max_length=100, default='SIET Helpdesk')
    from_email = models.EmailField(default='helpdesk@siet.edu.in', help_text="Default From email address")
    site_url = models.CharField(max_length=255, blank=True, default='', help_text="LAN or Public Base URL (e.g. http://10.10.10.141:8000). Auto-detects LAN IP if left blank.")
    smtp_backend = models.CharField(
        max_length=50,
        choices=[
            ('smtp', 'Live SMTP (Sends real emails)'),
            ('console', 'Console / Development (Outputs to server log)'),
        ],
        default='console',
        help_text="Choose Live SMTP to send real emails to inboxes, or Console for dev/testing"
    )
    smtp_host = models.CharField(max_length=255, default='smtp.gmail.com', blank=True)
    smtp_port = models.IntegerField(default=587)
    smtp_use_tls = models.BooleanField(default=True, help_text="Use TLS (typically port 587)")
    smtp_use_ssl = models.BooleanField(default=False, help_text="Use SSL (typically port 465)")
    smtp_user = models.CharField(max_length=255, blank=True, default='')
    smtp_password = models.CharField(max_length=255, blank=True, default='', help_text="SMTP App Password")
    updated_at = models.DateTimeField(auto_now=True)

    @classmethod
    def get_setting(cls):
        obj, _ = cls.objects.get_or_create(id=1)
        return obj

    def __str__(self):
        return f"{self.site_name} Email Config ({self.from_email})"

    class Meta:
        verbose_name = "Site Email Configuration"


