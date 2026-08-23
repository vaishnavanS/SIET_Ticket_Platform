# SIET Helpdesk Ticketing Platform

A professional Django-based helpdesk ticketing system for SIET (Srinivas Institute of Engineering and Technology) to manage IT service requests and issues.

## Features

- **User Roles**: Admin, Technician, and Normal User
- **Ticket Management**: Create, track, and resolve support tickets
- **Smart Assignment**: Round-robin ticket assignment to technicians or groups
- **Technician Groups**: Organize technicians by department (Network, Electrical, etc.)
- **SLA Tracking**: Monitor response and resolution times
- **File Attachments**: Securely upload images and documents
- **Dashboard**: Real-time ticket status and analytics
- **Admin Panel**: Django admin interface for complete control
- **Email Notifications**: Automatic notifications for ticket updates

## Project Structure

```
SIET_Ticket_Platform/
├── accounts/                    # User authentication and profiles
│   ├── models.py              # UserProfile, TechnicianGroup models
│   ├── admin.py               # Django admin configuration
│   ├── views.py               # Login, logout, dashboard views
│   ├── urls.py                # Account-related URLs
│   ├── signals.py             # Auto-create UserProfile signals
│   └── management/
│       └── commands/
│           └── create_admin.py # Management command for creating admin
├── tickets/                     # Ticket management app
│   ├── models.py              # Ticket, Category, TicketComment models
│   ├── admin.py               # Ticket admin interface
│   ├── views.py               # Ticket views (to be implemented)
│   └── urls.py                # Ticket-related URLs
├── siet_helpdesk/              # Project settings and main configuration
│   ├── settings.py            # Django settings
│   ├── urls.py                # Main URL configuration
│   └── wsgi.py                # WSGI configuration
├── templates/                  # HTML templates
│   └── accounts/
│       ├── login.html         # Login page
│       ├── dashboard.html     # Dashboard template
│       └── password_reset*.html # Password reset templates
├── static/                     # Static files
│   ├── css/
│   │   ├── login.css          # Login page styles
│   │   └── dashboard.css      # Dashboard styles
│   ├── js/                    # JavaScript files
│   └── images/
│       └── logo.png           # SIET Logo
├── media/                      # User-uploaded files
│   └── uploads/               # Ticket attachments
├── manage.py                   # Django management script
├── requirements.txt            # Python dependencies
└── .env.example               # Environment configuration template
```

## Installation

### Prerequisites
- Python 3.8+
- pip (Python package manager)
- Virtual environment (recommended)

### Setup Steps

1. **Create Virtual Environment**
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. **Install Dependencies**
```bash
pip install -r requirements.txt
```

3. **Create Environment File**
```bash
cp .env.example .env
# Edit .env with your database configuration
```

4. **Run Migrations**
```bash
python manage.py migrate
```

5. **Create Admin User**
```bash
python manage.py create_admin <username> <email> <password>
# Example:
python manage.py create_admin admin admin@siet.edu.in admin123
```

6. **Collect Static Files** (for production)
```bash
python manage.py collectstatic --noinput
```

7. **Run Development Server**
```bash
python manage.py runserver
```

Access the application at: `http://localhost:8000/accounts/login/`

## Database Models

### UserProfile
- Extended user model with roles (Admin, Technician, Normal User)
- Activity tracking and suspension status
- Max ticket allocation limit for technicians

### TechnicianGroup
- Group technicians by department
- Assign specific issue categories to groups
- Track group-level SLA settings

### Ticket
- Main ticket model with full tracking
- Auto-incrementing ticket number (Ticket #1, #2, etc.)
- SLA response and resolution times
- Status tracking (Open, In Progress, Resolved, Closed)

### Category
- Issue types (Network, Electrical, Facility, etc.)
- Admin-editable list of categories
- Optional assignment to technician groups

### TicketComment
- Track all communication on tickets
- Support for file attachments
- Audit trail of updates

### TicketHistory
- Complete audit trail of all changes
- Track who changed what and when
- Read-only for compliance

## Auto-Assignment Logic

The system uses intelligent round-robin assignment:

1. **Group-Based**: If category has an assigned technician group:
   - Assign to technician in group with lowest active tickets
   - Skip technicians at max capacity

2. **General Pool**: If no group assigned:
   - Assign to any available technician
   - Prioritize by workload (lowest active tickets)

3. **Unassigned Queue**: If all technicians at capacity:
   - Ticket stays unassigned
   - Admin receives alert
   - Manual assignment by admin

## File Upload Security

- **Max File Size**: 5MB per file
- **Allowed Formats**: JPG, JPEG, PNG, GIF (images only)
- **Storage**: Sandboxed in `/media/` directory
- **Access**: Only authenticated users can download
- **Validation**: Server-side validation with MIME type checking

## SLA Tracking

### Response SLA
- Default: 1 hour from ticket creation
- Triggered when technician assigned

### Resolution SLA
- Default: 24 hours from ticket creation
- Checked on ticket status change

### Breach Alerts
- Admin notified if SLA breached
- Dashboard highlights overdue tickets
- Escalation workflow available

## Admin Interface

Access Django admin at: `http://localhost:8000/admin/`

Features:
- User and profile management
- Technician group configuration
- Category management
- Ticket status updates (bulk actions available)
- View complete audit trail

## Configuration

### Database Setup (Optional MySQL)

For MySQL production deployment:

```bash
pip install mysqlclient
```

Update `settings.py`:
```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'siet_helpdesk',
        'USER': 'root',
        'PASSWORD': 'your_password',
        'HOST': 'localhost',
        'PORT': '3306',
    }
}
```

### Email Configuration

Update `settings.py` for email notifications:
```python
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'your_email@gmail.com'
EMAIL_HOST_PASSWORD = 'your_app_password'
```

## API Endpoints (Future)

- `POST /api/tickets/` - Create ticket
- `GET /api/tickets/` - List tickets
- `GET /api/tickets/{id}/` - Ticket details
- `PATCH /api/tickets/{id}/` - Update ticket
- `GET /api/tickets/{id}/comments/` - Ticket comments

## Security Considerations

- ✅ CSRF protection on all forms
- ✅ SQL injection prevention (ORM)
- ✅ XSS protection
- ✅ File upload validation
- ✅ User authentication required
- ✅ Role-based access control
- ✅ Audit trail for compliance

### Recommended for Production
- Enable HTTPS/SSL
- Set `DEBUG = False`
- Use strong `SECRET_KEY`
- Configure allowed hosts
- Use environment variables for secrets
- Regular database backups
- Log rotation setup

## Troubleshooting

### Migration Errors
```bash
python manage.py showmigrations
python manage.py migrate --fake accounts 0001  # If needed
```

### Port Already in Use
```bash
python manage.py runserver 8001
```

### Static Files Not Loading
```bash
python manage.py collectstatic --clear --noinput
```

## Development Notes

### Creating Test Data
```bash
python manage.py shell
# In Django shell:
>>> from accounts.models import UserProfile
>>> from django.contrib.auth.models import User
>>> user = User.objects.create_user('techuser', 'tech@siet.edu.in', 'pass123')
>>> user.first_name = 'John'
>>> user.save()
>>> profile = user.profile
>>> profile.role = 'technician'
>>> profile.save()
```

### Database Reset (Development Only)
```bash
# Delete db.sqlite3
# Remove migration files (keep __init__.py)
python manage.py makemigrations
python manage.py migrate
```

## Support

For issues or feature requests, contact the development team.

## License

This project is proprietary to SIET.
