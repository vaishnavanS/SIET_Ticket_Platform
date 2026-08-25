from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.models import User
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_protect
from django.contrib.auth.views import PasswordResetView, PasswordResetConfirmView
from django.db.models import Count
from .forms import AdminUserCreationForm, TechnicianGroupForm, CategoryForm
from .models import UserProfile, UserRole, TechnicianGroup
from tickets.models import Category, Ticket, TicketStatus


def admin_required(view_func):
    """Allow only active users with the application admin role."""
    @login_required(login_url='accounts:login')
    def wrapped_view(request, *args, **kwargs):
        if not request.user.is_staff or request.user.profile.role != UserRole.ADMIN:
            return redirect('accounts:dashboard')
        return view_func(request, *args, **kwargs)
    return wrapped_view

@require_http_methods(["GET", "POST"])
@csrf_protect
def login_view(request):
    """User login view"""
    if request.user.is_authenticated:
        return redirect('accounts:dashboard')
    
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        
        # Try to authenticate with username or email
        user = None
        if '@' in username:
            try:
                user_obj = User.objects.get(email=username)
                user = authenticate(request, username=user_obj.username, password=password)
            except User.DoesNotExist:
                user = None
        else:
            user = authenticate(request, username=username, password=password)
        
        if user is not None:
            # Check if user is active and not suspended
            try:
                profile = user.profile
                if not profile.is_active or profile.is_suspended:
                    messages.error(request, 'Your account is inactive or suspended. Please contact admin.')
                    return redirect('accounts:login')
            except UserProfile.DoesNotExist:
                messages.error(request, 'User profile not found. Please contact admin.')
                return redirect('accounts:login')
            
            login(request, user)
            
            # Handle remember me
            remember_me = request.POST.get('remember_me', False)
            if not remember_me:
                request.session.set_expiry(0)
            
            return redirect('accounts:dashboard')
        else:
            messages.error(request, 'Invalid username/email or password. Please try again.')
    
    return render(request, 'accounts/login.html')


@login_required(login_url='accounts:login')
def logout_view(request):
    """User logout view"""
    logout(request)
    return redirect('accounts:login')


@login_required(login_url='accounts:login')
def dashboard_view(request):
    """Send each authenticated user to their role dashboard."""
    role = request.user.profile.role
    if role == UserRole.ADMIN:
        return redirect('accounts:admin_dashboard')
    if role == UserRole.TECHNICIAN:
        return redirect('accounts:technician_dashboard')
    return redirect('accounts:user_dashboard')


@admin_required
def admin_dashboard(request):
    status_counts = [
        {'label': 'Open', 'value': Ticket.objects.filter(status=TicketStatus.OPEN).count(), 'class': 'open'},
        {'label': 'In progress', 'value': Ticket.objects.filter(status=TicketStatus.IN_PROGRESS).count(), 'class': 'progress'},
        {'label': 'Resolved', 'value': Ticket.objects.filter(status=TicketStatus.RESOLVED).count(), 'class': 'resolved'},
        {'label': 'Closed', 'value': Ticket.objects.filter(status=TicketStatus.CLOSED).count(), 'class': 'closed'},
    ]
    urgency_counts = [
        {'label': 'Low', 'value': Ticket.objects.filter(urgency='low').count(), 'class': 'low'},
        {'label': 'Medium', 'value': Ticket.objects.filter(urgency='medium').count(), 'class': 'medium'},
        {'label': 'High', 'value': Ticket.objects.filter(urgency='high').count(), 'class': 'high'},
        {'label': 'Critical', 'value': Ticket.objects.filter(urgency='critical').count(), 'class': 'critical'},
    ]
    context = {
        'user_count': User.objects.count(),
        'technician_count': UserProfile.objects.filter(role=UserRole.TECHNICIAN).count(),
        'open_count': Ticket.objects.filter(status=TicketStatus.OPEN).count(),
        'breached_count': Ticket.objects.filter(is_sla_breached=True).count(),
        'recent_users': User.objects.select_related('profile').order_by('-date_joined')[:8],
        'recent_tickets': Ticket.objects.select_related('reporter', 'assigned_technician').order_by('-created_at')[:8],
        'status_counts': status_counts,
        'urgency_counts': urgency_counts,
        'total_tickets': Ticket.objects.count(),
    }
    return render(request, 'accounts/admin_dashboard.html', context)


@admin_required
@require_http_methods(['GET', 'POST'])
def admin_create_user(request):
    form = AdminUserCreationForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('accounts:admin_users')
    return render(request, 'accounts/admin_create_user.html', {'form': form})


@admin_required
def admin_users(request):
    users = User.objects.select_related('profile').order_by('username')
    return render(request, 'accounts/admin_users.html', {'users': users})


@admin_required
@require_http_methods(['POST'])
def admin_user_action(request, user_id, action):
    user = get_object_or_404(User.objects.select_related('profile'), pk=user_id)
    if user == request.user:
        return redirect('accounts:admin_users')
    if action == 'delete':
        user.delete()
        messages.success(request, f"User '{user.username}' was deleted.")
    elif action == 'suspend':
        user.profile.is_suspended = True
        user.profile.save(update_fields=['is_suspended', 'updated_at'])
        messages.warning(request, f"User '{user.username}' has been suspended.")
    elif action == 'activate':
        user.profile.is_suspended = False
        user.profile.save(update_fields=['is_suspended', 'updated_at'])
        messages.success(request, f"User '{user.username}' has been activated.")
    elif action == 'reset_password':
        new_password = request.POST.get('new_password', '').strip()
        if len(new_password) < 8:
            messages.error(request, "Password must be at least 8 characters long.")
        else:
            user.set_password(new_password)
            user.save()
            messages.success(request, f"Password for user '{user.username}' has been updated.")
    return redirect('accounts:admin_users')


@admin_required
@require_http_methods(['GET', 'POST'])
def admin_groups(request):
    if request.method == 'POST':
        action = request.POST.get('action', 'create')
        if action == 'create':
            form = TechnicianGroupForm(request.POST)
            if form.is_valid():
                group = form.save()
                cat_ids = request.POST.getlist('categories')
                if cat_ids:
                    Category.objects.filter(id__in=cat_ids).update(assigned_group=group)
                messages.success(request, f"Technician group '{group.name}' created successfully.")
                return redirect('accounts:admin_groups')
            else:
                messages.error(request, "Please correct the errors in the create group form.")
        elif action == 'edit':
            group_id = request.POST.get('group_id')
            group = get_object_or_404(TechnicianGroup, pk=group_id)
            form = TechnicianGroupForm(request.POST, instance=group)
            if form.is_valid():
                form.save()
                cat_ids = request.POST.getlist('categories')
                Category.objects.filter(assigned_group=group).update(assigned_group=None)
                if cat_ids:
                    Category.objects.filter(id__in=cat_ids).update(assigned_group=group)
                messages.success(request, f"Technician group '{group.name}' updated successfully.")
                return redirect('accounts:admin_groups')
            else:
                messages.error(request, "Failed to update technician group.")
        elif action == 'delete':
            group_id = request.POST.get('group_id')
            group = get_object_or_404(TechnicianGroup, pk=group_id)
            name = group.name
            group.delete()
            messages.success(request, f"Technician group '{name}' deleted successfully.")
            return redirect('accounts:admin_groups')

    form = TechnicianGroupForm()
    groups = TechnicianGroup.objects.prefetch_related('technicians', 'categories').all()
    all_categories = Category.objects.all()
    all_technicians = User.objects.filter(profile__role=UserRole.TECHNICIAN, profile__is_active=True)
    return render(request, 'accounts/admin_groups.html', {
        'form': form,
        'groups': groups,
        'all_categories': all_categories,
        'all_technicians': all_technicians,
    })


@admin_required
@require_http_methods(['GET', 'POST'])
def admin_categories(request):
    form = CategoryForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('accounts:admin_categories')
    categories = Category.objects.select_related('assigned_group').annotate(ticket_count=Count('tickets'))
    return render(request, 'accounts/admin_categories.html', {'form': form, 'categories': categories})


@admin_required
@require_http_methods(['GET', 'POST'])
def admin_email_settings(request):
    """Admin configuration for site outgoing email and SMTP connection"""
    from .models import SiteEmailSetting
    from .utils import get_site_email_connection
    from django.core.mail import EmailMessage

    setting = SiteEmailSetting.get_setting()

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'save_settings':
            setting.site_name = request.POST.get('site_name', 'SIET Helpdesk').strip()
            setting.from_email = request.POST.get('from_email', 'helpdesk@siet.edu.in').strip()
            setting.site_url = request.POST.get('site_url', '').strip()
            setting.smtp_backend = request.POST.get('smtp_backend', 'console')
            setting.smtp_host = request.POST.get('smtp_host', '').strip()
            try:
                setting.smtp_port = int(request.POST.get('smtp_port', 587))
            except ValueError:
                setting.smtp_port = 587
            use_ssl = ('smtp_use_ssl' in request.POST)
            use_tls = ('smtp_use_tls' in request.POST)
            if use_ssl:
                use_tls = False

            setting.smtp_use_tls = use_tls
            setting.smtp_use_ssl = use_ssl
            setting.smtp_user = request.POST.get('smtp_user', '').strip()

            pwd = request.POST.get('smtp_password', '').replace(' ', '').strip()
            if pwd:
                setting.smtp_password = pwd

            setting.save()
            messages.success(request, "Site Email & SMTP settings have been updated successfully.")
            return redirect('accounts:admin_email_settings')

        elif action == 'test_email':
            test_recipient = request.POST.get('test_recipient', '').strip()
            if not test_recipient:
                messages.error(request, "Please specify a test recipient email address.")
            else:
                conn, from_str, site_title = get_site_email_connection()
                try:
                    msg = EmailMessage(
                        subject=f"[{site_title}] Outgoing Mail & SMTP Test",
                        body=f"Hello,\n\nThis is a live test notification from {site_title}.\n\nYour outgoing SMTP email configuration is functioning properly and ready for system notifications, email verification, and password resets!\n\nBest regards,\n{site_title} System",
                        from_email=from_str,
                        to=[test_recipient],
                        connection=conn,
                    )
                    msg.send(fail_silently=False)
                    messages.success(request, f"✔ Test email was successfully dispatched to '{test_recipient}'!")
                except Exception as e:
                    messages.error(request, f"❌ Failed to dispatch test email: {str(e)}")
            return redirect('accounts:admin_email_settings')

    return render(request, 'accounts/admin_email_settings.html', {'setting': setting})



@admin_required
def admin_tickets(request):
    status = request.GET.get('status', '')
    tickets = Ticket.objects.select_related('reporter', 'assigned_technician', 'category')
    if status in dict(TicketStatus.choices):
        tickets = tickets.filter(status=status)
    return render(request, 'accounts/admin_tickets.html', {
        'tickets': tickets,
        'selected_status': status,
        'status_choices': TicketStatus.choices,
    })


@login_required(login_url='accounts:login')
def technician_dashboard(request):
    scope = request.GET.get('scope', 'my_active')
    status_filter = request.GET.get('status', '')

    base_tickets = Ticket.objects.select_related('category', 'reporter', 'assigned_technician', 'assigned_group')

    # Check SLA breach for active tickets
    for ticket in base_tickets.filter(status__in=[TicketStatus.OPEN, TicketStatus.IN_PROGRESS])[:50]:
        ticket.check_sla_breach()

    my_all_tickets = base_tickets.filter(assigned_technician=request.user)
    my_active_tickets = my_all_tickets.filter(status__in=[TicketStatus.OPEN, TicketStatus.IN_PROGRESS])
    my_resolved_tickets = my_all_tickets.filter(status__in=[TicketStatus.RESOLVED, TicketStatus.CLOSED])
    unassigned_tickets = base_tickets.filter(assigned_technician__isnull=True)

    if scope == 'my_resolved':
        tickets = my_resolved_tickets
    elif scope == 'team':
        tickets = base_tickets.all()
    elif scope == 'unassigned':
        tickets = unassigned_tickets
    else:  # default 'my_active'
        scope = 'my_active'
        tickets = my_active_tickets

    if status_filter in dict(TicketStatus.choices):
        tickets = tickets.filter(status=status_filter)

    context = {
        'tickets': tickets,
        'scope': scope,
        'my_active_count': my_active_tickets.count(),
        'in_progress_count': my_all_tickets.filter(status=TicketStatus.IN_PROGRESS).count(),
        'my_resolved_count': my_resolved_tickets.count(),
        'team_total_count': base_tickets.count(),
        'unassigned_count': unassigned_tickets.count(),
        'sla_breached_count': my_all_tickets.filter(is_sla_breached=True).count(),
        'selected_status': status_filter,
        'status_choices': TicketStatus.choices,
    }
    return render(request, 'accounts/technician_dashboard.html', context)



@login_required(login_url='accounts:login')
def user_dashboard(request):
    from tickets.models import ServiceCatalogItem
    tickets = Ticket.objects.filter(reporter=request.user).select_related('category', 'assigned_technician')
    
    catalog_count = ServiceCatalogItem.objects.filter(is_active=True).count()
    open_count = tickets.filter(status__in=[TicketStatus.OPEN, TicketStatus.IN_PROGRESS]).count()
    closed_count = tickets.filter(status__in=[TicketStatus.RESOLVED, TicketStatus.CLOSED]).count()

    return render(request, 'accounts/user_dashboard.html', {
        'recent_tickets': tickets.order_by('-created_at')[:5],
        'total_count': tickets.count(),
        'open_count': open_count,
        'closed_count': closed_count,
        'catalog_count': catalog_count,
    })




from .utils import send_verification_email, verify_token
from django.conf import settings
from django.urls import reverse_lazy

def verify_email_view(request, token):
    """Verify user's email address from token link"""
    user_id, email = verify_token(token)
    if not user_id or not email:
        messages.error(request, "The email verification link is invalid or has expired. Please request a new verification link from your profile.")
        if request.user.is_authenticated:
            return redirect('accounts:profile')
        return redirect('accounts:login')

    try:
        target_user = User.objects.get(pk=user_id, email=email)
        profile, _ = UserProfile.objects.get_or_create(user=target_user)
        profile.is_email_verified = True
        profile.save(update_fields=['is_email_verified', 'updated_at'])
        messages.success(request, f"✔ Your email address '{email}' has been successfully verified!")
    except User.DoesNotExist:
        messages.error(request, "User account associated with this verification link could not be found.")

    if request.user.is_authenticated:
        return redirect('accounts:profile')
    return redirect('accounts:login')


@login_required(login_url='accounts:login')
def profile_view(request):
    """User profile view with role-specific data and email verification"""
    user = request.user
    profile, created = UserProfile.objects.get_or_create(user=user)

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'update_profile':
            first_name = request.POST.get('first_name', '').strip()
            last_name = request.POST.get('last_name', '').strip()
            email = request.POST.get('email', '').strip()
            phone_number = request.POST.get('phone_number', '').strip()
            department = request.POST.get('department', '').strip()

            email_changed = (email.lower() != user.email.lower())

            user.first_name = first_name
            user.last_name = last_name
            user.email = email
            user.save()

            profile.phone_number = phone_number
            profile.department = department
            if email_changed:
                profile.is_email_verified = False
            profile.save()

            if email_changed and email:
                success, msg = send_verification_email(request, user)
                if success:
                    messages.warning(request, f"Profile updated! A verification link was sent to '{email}'. Please check your inbox to verify.")
                else:
                    messages.warning(request, f"Profile updated, but we could not dispatch verification email: {msg}")
            else:
                messages.success(request, "Your profile details have been updated successfully.")
            return redirect('accounts:profile')

        elif action == 'send_verification':
            if not user.email:
                messages.error(request, "Please configure your email address in Edit Profile first.")
            else:
                success, msg = send_verification_email(request, user)
                if success:
                    messages.success(request, f"A fresh verification link was sent to '{user.email}'. Please check your inbox.")
                else:
                    messages.error(request, f"Failed to dispatch verification email: {msg}")
            return redirect('accounts:profile')

    context = {
        'profile': profile,
        'user_role': profile.role,
    }

    if profile.role == UserRole.NORMAL_USER:
        user_tickets = Ticket.objects.filter(reporter=user)
        context.update({
            'total_tickets': user_tickets.count(),
            'open_tickets': user_tickets.filter(status__in=[TicketStatus.OPEN, TicketStatus.IN_PROGRESS]).count(),
            'resolved_tickets': user_tickets.filter(status__in=[TicketStatus.RESOLVED, TicketStatus.CLOSED]).count(),
            'recent_tickets': user_tickets.order_by('-created_at')[:4],
        })
    elif profile.role == UserRole.TECHNICIAN:
        tech_tickets = Ticket.objects.filter(assigned_technician=user)
        assigned_groups = user.technician_groups.all()
        context.update({
            'total_assigned': tech_tickets.count(),
            'active_assigned': tech_tickets.filter(status__in=[TicketStatus.OPEN, TicketStatus.IN_PROGRESS]).count(),
            'resolved_assigned': tech_tickets.filter(status__in=[TicketStatus.RESOLVED, TicketStatus.CLOSED]).count(),
            'sla_breached_count': tech_tickets.filter(is_sla_breached=True).count(),
            'assigned_groups': assigned_groups,
            'recent_tickets': tech_tickets.order_by('-created_at')[:4],
        })
    elif profile.role == UserRole.ADMIN or user.is_staff:
        context.update({
            'total_system_users': User.objects.count(),
            'total_categories': Category.objects.count(),
            'total_system_tickets': Ticket.objects.count(),
            'total_groups': TechnicianGroup.objects.count(),
            'recent_tickets': Ticket.objects.order_by('-created_at')[:4],
        })

    return render(request, 'accounts/profile.html', context)


class CustomPasswordResetView(PasswordResetView):
    """Custom password reset view that dispatches reset link to user email with LAN IP resolution"""
    template_name = 'accounts/password_reset.html'
    email_template_name = 'accounts/password_reset_email.html'
    subject_template_name = 'accounts/password_reset_subject.txt'
    from_email = settings.DEFAULT_FROM_EMAIL
    success_url = reverse_lazy('accounts:password_reset_done')

    def get_extra_email_context(self):
        from .utils import get_site_base_url
        from urllib.parse import urlparse
        base_url = get_site_base_url(self.request)
        parsed = urlparse(base_url)
        return {
            'protocol': parsed.scheme or 'http',
            'domain': parsed.netloc or parsed.path or 'localhost:8000',
        }


class CustomPasswordResetConfirmView(PasswordResetConfirmView):
    """Custom password reset confirm view that updates user password in DB"""
    template_name = 'accounts/password_reset_confirm.html'
    success_url = reverse_lazy('accounts:password_reset_complete')



