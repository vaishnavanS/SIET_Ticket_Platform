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
    elif action == 'suspend':
        user.profile.is_suspended = True
        user.profile.save(update_fields=['is_suspended', 'updated_at'])
    elif action == 'activate':
        user.profile.is_suspended = False
        user.profile.save(update_fields=['is_suspended', 'updated_at'])
    return redirect('accounts:admin_users')


@admin_required
@require_http_methods(['GET', 'POST'])
def admin_groups(request):
    form = TechnicianGroupForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('accounts:admin_groups')
    groups = TechnicianGroup.objects.prefetch_related('technicians', 'categories').annotate(ticket_count=Count('ticket'))
    return render(request, 'accounts/admin_groups.html', {'form': form, 'groups': groups})


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
    status_filter = request.GET.get('status', '')
    all_tickets = Ticket.objects.filter(assigned_technician=request.user).select_related('category', 'reporter')
    
    # Check SLA breach for active tickets
    for ticket in all_tickets.filter(status__in=[TicketStatus.OPEN, TicketStatus.IN_PROGRESS]):
        ticket.check_sla_breach()

    filtered_tickets = all_tickets
    if status_filter in dict(TicketStatus.choices):
        filtered_tickets = filtered_tickets.filter(status=status_filter)

    context = {
        'tickets': filtered_tickets,
        'ticket_answers': [(ticket, ticket.custom_answers.items()) for ticket in filtered_tickets],
        'active_count': all_tickets.filter(status__in=[TicketStatus.OPEN, TicketStatus.IN_PROGRESS]).count(),
        'in_progress_count': all_tickets.filter(status=TicketStatus.IN_PROGRESS).count(),
        'resolved_count': all_tickets.filter(status=TicketStatus.RESOLVED).count(),
        'sla_breached_count': all_tickets.filter(is_sla_breached=True).count(),
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




class CustomPasswordResetView(PasswordResetView):
    """Custom password reset view"""
    template_name = 'accounts/password_reset.html'
    email_template_name = 'accounts/password_reset_email.html'
    subject_template_name = 'accounts/password_reset_subject.txt'
    success_url = '/accounts/password-reset-sent/'


class CustomPasswordResetConfirmView(PasswordResetConfirmView):
    """Custom password reset confirm view"""
    template_name = 'accounts/password_reset_confirm.html'
    success_url = '/accounts/password-reset-complete/'

