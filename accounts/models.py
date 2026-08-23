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
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
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
        for tech in self.technicians.all():
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

