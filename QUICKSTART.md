# SIET Helpdesk - Quick Start Guide

## Getting Started in 5 Minutes

### Prerequisites
- Python 3.8+ installed
- Virtual environment created and activated

### 1. Initial Setup (First Time)
```bash
cd /run/media/vaishnavan/ACER/Users/Vaishnavan\ S/project/SIET_Ticket_Platform
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Create admin user (if not already created)
python manage.py create_admin admin admin@siet.edu.in admin123
```

### 2. Run the Server

#### Option A: Run across LAN (Wi-Fi / Multi-Device Access)
To make the platform accessible to other computers, phones, or tablets connected to your Wi-Fi/LAN (even if your IP changes dynamically):
```bash
# Linux / macOS
./run_lan.sh

# Or using Django management command
./venv/bin/python manage.py runserver_lan

# Windows
run_lan.bat
```
This automatically detects your machine's active LAN IP (e.g. `http://192.168.1.2:8000/`) and prints direct URLs for both local and LAN access.

#### Option B: Standard Localhost Only
```bash
source venv/bin/activate
python manage.py runserver
```

### 3. Access the Application

- **Local Machine**: http://127.0.0.1:8000/ or http://localhost:8000/
- **Other LAN / Wi-Fi Devices**: `http://<YOUR_LOCAL_IP>:8000/` (printed in terminal banner)
- **Login Page**: http://localhost:8000/accounts/login/
- **Django Admin**: http://localhost:8000/admin/


## 📋 What's Been Built

### ✅ Core Features Implemented

1. **User Authentication System**
   - Login/Logout functionality
   - Role-based access (Admin, Technician, Normal User)
   - Remember me option
   - Password reset capability
   - User suspension and deactivation

2. **Database Models**
   - UserProfile with roles and status
   - TechnicianGroup for organizing by department
   - Ticket with full tracking (ticket_number, urgency, status)
   - Category for issue types
   - TicketComment for communication
   - TicketHistory for audit trail

3. **Smart Assignment System**
   - Round-robin ticket assignment
   - Group-based routing (Network, Electrical, etc.)
   - Workload balancing
   - Max ticket limit per technician
   - Automatic unassigned queue management

4. **SLA Tracking**
   - Response SLA (1 hour)
   - Resolution SLA (24 hours)
   - Breach detection and alerts
   - Dashboard compliance tracking

5. **File Upload Security**
   - Image validation (JPG, PNG, GIF only)
   - 5MB file size limit
   - Sandboxed storage
   - Authenticated access only

6. **Admin Interface**
   - Full Django admin integration
   - User and profile management
   - Technician group configuration
   - Category CRUD operations
   - Bulk ticket status updates
   - Complete audit trail viewing

7. **Professional Login Page**
   - SIET logo and branding
   - Responsive design
   - Light green theme (matching mockup)
   - Error messages
   - Password reset link

## 🗂️ Directory Structure Created

```
static/
├── css/
│   └── login.css              # Login page styling
├── images/
│   └── logo.png               # SIET logo (200x200 PNG)
└── js/

templates/
└── accounts/
    ├── login.html             # Login form
    └── dashboard.html         # User dashboard

accounts/
├── models.py                  # UserProfile, TechnicianGroup
├── views.py                   # Login, logout views
├── urls.py                    # Auth URLs
├── admin.py                   # Admin configuration
├── signals.py                 # Auto-create profile
└── management/
    └── commands/
        └── create_admin.py    # Create admin command

tickets/
├── models.py                  # Ticket, Category, Comment models
├── admin.py                   # Ticket admin interface
├── views.py                   # Ticket views (scaffolding)
└── urls.py                    # Ticket URLs

media/                         # User uploads directory
db.sqlite3                     # Database file
```

## 🔐 Test Credentials

```yaml
Admin Account:
  Username: admin
  Email: admin@siet.edu.in
  Password: Password123!

Technician Account:
  Username: tech
  Email: tech@siet.edu.in
  Password: Password123!

Student / User Account:
  Username: student
  Email: student@siet.edu.in
  Password: Password123!
```

## 📱 Key Admin Features

### 1. Create New Users
- Go to Admin Panel → Auth → Users → Add User
- Set username and password
- The system automatically creates a UserProfile
- Edit profile to set role (Admin/Technician/Normal User)

### 2. Create Technician Group
- Admin Panel → Accounts → Technician Groups → Add
- Name: "Network Team"
- Max Tickets per Tech: 8
- Add technicians to the group

### 3. Set Up Categories
- Admin Panel → Tickets → Categories → Add
- Name: "Network Issue"
- Assign to group: "Network Team" (optional)

### 4. Monitor Tickets
- All tickets visible in Admin Panel
- Bulk actions: Mark In Progress, Resolved, Closed
- View complete history of changes

## 🛠️ Development Commands

```bash
# Create additional test users
python manage.py shell
>>> from django.contrib.auth.models import User
>>> user = User.objects.create_user('tech1', 'tech1@siet.edu.in', 'pass123')
>>> user.first_name = 'John'
>>> user.save()
>>> profile = user.profile
>>> profile.role = 'technician'
>>> profile.save()

# Check migrations status
python manage.py showmigrations

# Create new models (after changes)
python manage.py makemigrations
python manage.py migrate

# Collect static files (production)
python manage.py collectstatic --noinput
```

## 🔄 Next Steps - Frontend Features to Implement

1. **Dashboard**
   - Ticket statistics and charts
   - Quick ticket creation
   - My tickets view
   - Admin quick actions

2. **Ticket Management**
   - Create new ticket form
   - List view with filters
   - Detail view with comments
   - Status update forms
   - Reassign functionality

3. **Technician Views**
   - Assigned tickets list
   - Quick status update
   - Comment and resolution form
   - Workload dashboard

4. **Admin Dashboard**
   - SLA compliance chart
   - Technician utilization
   - Category statistics
   - Unassigned ticket queue
   - User management interface

## 🚢 Production Deployment Checklist

- [ ] Change DEBUG = False in settings.py
- [ ] Configure MySQL database
- [ ] Set up HTTPS/SSL
- [ ] Configure email backend
- [ ] Set strong SECRET_KEY
- [ ] Configure ALLOWED_HOSTS
- [ ] Set up environment variables
- [ ] Run collectstatic
- [ ] Set up scheduled tasks (SLA checks)
- [ ] Configure logging
- [ ] Set up database backups
- [ ] Test password reset email
- [ ] Configure CORS if needed

## 📞 Support

The application is fully functional as a base system. The Django admin panel provides complete control over all data and configurations.

For any issues or to add features:
1. Check Django logs
2. Use Django shell for debugging
3. Review model definitions for data structure
4. Refer to Django documentation

---

**Status**: ✅ Ready for development and testing
**Last Updated**: August 23, 2026
