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
]




