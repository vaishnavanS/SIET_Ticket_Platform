from django.urls import path
from . import views

app_name = 'tickets'

urlpatterns = [
    path('my-tickets/', views.my_tickets, name='my_tickets'),
    path('catalog/', views.user_service_catalog, name='user_catalog'),
    path('create/', views.ticket_create, name='create'),

    path('form-builder/', views.issue_form_builder, name='form_builder'),
    path('form-builder/<int:pk>/edit/', views.issue_form_field_edit, name='field_edit'),
    path('form-builder/<int:pk>/delete/', views.issue_form_field_delete, name='field_delete'),
    path('service-catalog/', views.service_catalog_manager, name='catalog_manager'),
    path('service-catalog/<int:pk>/toggle/', views.service_catalog_toggle, name='catalog_toggle'),
    path('<int:pk>/', views.ticket_detail, name='detail'),
    path('<int:pk>/edit/', views.ticket_edit, name='edit'),
    path('<int:pk>/status/', views.ticket_update_status, name='update_status'),
    path('<int:pk>/comment/', views.ticket_add_comment, name='add_comment'),
    path('solutions/', views.solutions_list, name='solutions'),
    path('solutions/list/', views.solutions_list, name='solutions_list'),
    path('solutions/<int:pk>/feedback/', views.solution_feedback, name='solution_feedback'),
    path('solutions-admin/', views.admin_solutions_manager, name='admin_solutions'),
    path('solutions-admin/<int:pk>/edit/', views.admin_solution_edit, name='admin_solution_edit'),
    path('locations/', views.admin_locations, name='admin_locations'),
    path('notifications/<int:pk>/read/', views.notification_mark_read, name='notification_read'),
    path('notifications/clear-all/', views.notifications_clear_all, name='notifications_clear'),
]




