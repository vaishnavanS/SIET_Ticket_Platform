from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = 'accounts'

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('dashboard/admin/', views.admin_dashboard, name='admin_dashboard'),
    path('dashboard/technician/', views.technician_dashboard, name='technician_dashboard'),
    path('dashboard/user/', views.user_dashboard, name='user_dashboard'),
    path('profile/', views.profile_view, name='profile'),
    path('verify-email/<str:token>/', views.verify_email_view, name='verify_email'),
    path('admin/users/', views.admin_users, name='admin_users'),
    path('admin/users/create/', views.admin_create_user, name='admin_create_user'),
    path('admin/users/<int:user_id>/<str:action>/', views.admin_user_action, name='admin_user_action'),
    path('admin/groups/', views.admin_groups, name='admin_groups'),
    path('admin/categories/', views.admin_categories, name='admin_categories'),
    path('admin/email-settings/', views.admin_email_settings, name='admin_email_settings'),
    path('admin/tickets/', views.admin_tickets, name='admin_tickets'),
    path('password-reset/', views.CustomPasswordResetView.as_view(), name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='accounts/password_reset_done.html'
    ), name='password_reset_done'),
    path('password-reset/<uidb64>/<token>/', views.CustomPasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('password-reset-complete/', auth_views.PasswordResetCompleteView.as_view(
        template_name='accounts/password_reset_complete.html'
    ), name='password_reset_complete'),
]
