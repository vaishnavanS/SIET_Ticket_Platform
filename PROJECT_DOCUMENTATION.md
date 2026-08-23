# SIET Helpdesk Ticket Platform

## 1. Project Overview

SIET Helpdesk is a Django-based campus IT service-desk platform for reporting, assigning, tracking, and resolving technical issues.

The platform is designed around three account roles:

- **Admin**: manages users, issue categories, technician groups, configurable issue forms, tickets, assignments, SLA status, and reports.
- **Technician**: sees tickets assigned to them and the complete issue details submitted by the reporter.
- **Normal User**: submits issues, tracks their own tickets, and receives a form tailored by the administrator.

The project follows a GLPI-inspired helpdesk workflow. It intentionally does **not** include asset management at this stage.

## 2. Technology Stack

- Python 3.14.6
- Django 5.2.17
- SQLite for development
- MySQL-ready configuration for production
- HTML5 and CSS3 server-rendered interface
- Pillow for image validation and logo/file handling
- django-cors-headers
- Django authentication, sessions, CSRF protection, ORM, and admin framework

`requirements.txt` uses Django `>=5.2,<5.3` because the project runs on Python 3.14.

## 3. Design Pattern and Visual Direction

### Login page

The login interface was based on the supplied SIET reference images:

- Pale green page background with a subtle dot pattern
- Centered light-green login card
- Dark-green header bar
- Small SIET college logo
- Rounded/circular logo presentation
- Green Sign in button
- Readable labels, fields, and Forgot Password link
- Responsive behavior for smaller screens
- No welcome-back or logout-success message shown on the login page

The current login logo is loaded from:

`static/images/logo.jpg`

### Admin interface

The admin interface uses a custom site-format UI rather than sending users to raw Django Administration pages:

- SIET Helpdesk branding in the header
- Small circular college logo beside the brand
- Right-side navigation tabs
- No visible Django Admin link in the custom admin UI
- No underlined browser-style navigation links
- Overview, Users, Issue reports, Technician groups, Categories, and Issue form sections
- Green operational color palette
- Summary cards, status bars, urgency bars, tables, forms, and filter controls
- Responsive layout for desktop and mobile screens

### GLPI-inspired behavior

The workflow takes inspiration from GLPI concepts:

- Central issue-reporting entry point
- Configurable service/report form
- Categories and technician groups
- Assignment queue
- Status tracking
- Urgency levels
- SLA monitoring
- Technician workload awareness
- Audit history models
- Separate user and technician experiences

The implementation is a custom Django application, not a copy of GLPI and not a GLPI installation.

## 4. Project Structure

```text
SIET_Ticket_Platform/
├── accounts/
│   ├── models.py
│   ├── forms.py
│   ├── views.py
│   ├── urls.py
│   ├── admin.py
│   ├── signals.py
│   └── management/commands/create_admin.py
├── tickets/
│   ├── models.py
│   ├── forms.py
│   ├── views.py
│   ├── urls.py
│   ├── admin.py
│   └── migrations/
├── siet_helpdesk/
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── templates/
│   ├── accounts/
│   │   ├── login.html
│   │   ├── admin_dashboard.html
│   │   ├── admin_users.html
│   │   ├── admin_create_user.html
│   │   ├── admin_groups.html
│   │   ├── admin_categories.html
│   │   ├── admin_tickets.html
│   │   ├── technician_dashboard.html
│   │   ├── user_dashboard.html
│   │   └── password_reset*.html
│   └── tickets/
│       ├── ticket_create.html
│       ├── ticket_edit.html
│       └── form_builder.html
├── static/
│   ├── css/login.css
│   ├── css/dashboard.css
│   ├── css/role_dashboard.css
│   └── images/logo.jpg
├── media/
├── db.sqlite3
├── manage.py
├── requirements.txt
└── PROJECT_DOCUMENTATION.md
```

## 5. Authentication and Account Roles

### Login

The login page accepts either:

- Username
- Email address

The login view:

1. Reads username/email and password.
2. Resolves email to the related username when needed.
3. Authenticates through Django authentication.
4. Rejects inactive or suspended profiles.
5. Supports the Remember me checkbox.
6. Redirects according to the profile role.

### Role routing

`/accounts/dashboard/` acts as the role dispatcher:

- Admin → `/accounts/dashboard/admin/`
- Technician → `/accounts/dashboard/technician/`
- Normal user → `/accounts/dashboard/user/`

### User profile

Every Django user receives a `UserProfile` through a post-save signal. The profile contains:

- Role
- Active state
- Suspended state
- Maximum active ticket count
- Creation and update timestamps

## 6. Admin Features

### Admin Overview

The Overview screen shows live data:

- Total users
- Technician count
- Open ticket count
- SLA breach count
- Ticket status distribution
- Urgency distribution
- Recent users
- Recent tickets

The graphs are lightweight CSS bar charts driven by database counts. Zero-ticket states still display numeric zero values and empty bars.

The Overview contains no Create User button. User creation exists only under Users, as requested.

### Users

The Users screen allows the admin to:

- View all users
- See username, name, email, role, and status
- Create a user and assign a role in one step
- Suspend active users
- Activate suspended users
- Delete users with confirmation

The currently logged-in admin cannot suspend or delete itself.

Supported roles:

- Admin
- Technician
- Normal User

### Technician groups

The Technician groups screen allows the admin to:

- Create a group
- Add a description
- Select active, non-suspended technicians
- Set the maximum tickets per technician
- View technician count
- View category count

Groups are used for category-based ticket routing.

### Categories

The Categories screen allows the admin to:

- Create issue categories
- Add category descriptions
- Assign a category to a technician group
- View the number of reports in each category
- See which group receives that category's tickets

Examples include Network, PC, Account Access, Hardware, and Other.

### Issue reports

The Issue Reports screen allows the admin to:

- View all submitted reports
- Filter by All, Open, In Progress, Resolved, or Closed
- See reporter, category, urgency, assigned technician, and SLA state
- Open a custom site-format edit screen
- Edit ticket title and description
- Change category and urgency
- Assign a technician group
- Assign a technician
- Change ticket status
- Mark SLA breach state

### Configurable Report an Issue form

The Form Builder is available at:

`/tickets/form-builder/`

The admin can add configurable fields with:

- Field label
- Field key
- Field type
- Options
- Required/optional state
- Display order
- Active/inactive state

Supported field types:

- Short text
- Long text
- Radio buttons
- Checkboxes
- Dropdown

Options are entered one per line. Example:

```text
Network issue
PC issue
SEB issue
Other
```

## 7. Normal User Workflow

A normal user opens their dashboard and selects:

**Report an issue**

The form includes the standard ticket fields:

- Title
- Description
- Category
- Urgency
- Location
- Attachment

It also includes every active custom field configured by the admin.

When a radio, checkbox, or dropdown option containing `Other` is selected, the page reveals:

**Describe the other issue**

The user can type the additional problem description and submit the report.

On submission:

1. The ticket is created for the logged-in user.
2. Custom answers are saved as JSON on the ticket.
3. The ticket is automatically assigned when an available technician exists.
4. The user returns to their dashboard.

## 8. Technician Workflow

Technicians see only tickets assigned to their account.

The technician dashboard shows:

- Active ticket count
- Resolved ticket count
- Ticket number
- Ticket title
- Category
- Reporter
- Status
- Submitted custom form answers

For example, the technician can see:

```text
Facing Issue In: Other
Other issue details: The projector is not working
```

This means the configurable form response is available as readable ticket context instead of being lost in the browser form.

## 9. Ticket Data Model

### Category

- Name
- Description
- Assigned technician group
- Creation and update timestamps

### IssueFormField

- Label
- Unique field key
- Field type
- JSON options list
- Required flag
- Display order
- Active flag

### Ticket

- Auto-generated ticket number
- Title
- Description
- Urgency
- Category
- Location
- Optional image attachment
- Reporter
- Assigned technician
- Assigned technician group
- Status
- Custom form answers stored as JSON
- Created, assigned, resolved, and updated timestamps
- Response SLA duration
- Resolution SLA duration
- SLA breach flag and breach type

### TicketComment

- Ticket
- Author
- Comment content
- Optional attachment
- Creation and update timestamps

### TicketHistory

- Ticket
- User who made the change
- Changed field
- Old value
- New value
- Change timestamp

### UserProfile

- Django user
- Role
- Active flag
- Suspended flag
- Maximum active tickets
- Timestamps

### TechnicianGroup

- Name
- Description
- Maximum tickets per technician
- Technician membership
- Timestamps

## 10. Automatic Assignment

Assignment uses workload-aware round-robin behavior:

1. If the category has a technician group, use that group.
2. Consider active technicians in the group.
3. Skip suspended or inactive technicians.
4. Skip technicians at their maximum active ticket limit.
5. Select the technician with the lowest active workload.
6. If no category group is configured, use the general active technician pool.
7. If no technician is available, leave the ticket unassigned for admin action.

## 11. Ticket Status and Urgency

Statuses:

- Open
- In Progress
- Resolved
- Closed

Urgency levels:

- Low
- Medium
- High
- Critical

Status and urgency are shown in admin reporting and on technician/user dashboards where relevant.

## 12. SLA Tracking

Default SLA values:

- Response SLA: 1 hour
- Resolution SLA: 24 hours

The system supports:

- Assignment/response breach detection
- Resolution breach detection
- Overdue checks
- SLA state on admin issue reports
- SLA breach counts on the admin Overview

## 13. File Upload Rules

Ticket attachments are validated server-side:

- Maximum size: 5 MB
- Allowed formats: JPG, JPEG, PNG, GIF
- Stored under the media directory
- Validation is performed by the Ticket model before saving

## 14. URL Routes

### Authentication

- `/accounts/login/`
- `/accounts/logout/`
- `/accounts/password-reset/`
- `/accounts/password-reset/done/`
- `/accounts/password-reset/<uidb64>/<token>/`
- `/accounts/password-reset-complete/`

### Role dashboards

- `/accounts/dashboard/`
- `/accounts/dashboard/admin/`
- `/accounts/dashboard/technician/`
- `/accounts/dashboard/user/`

### Custom admin workspace

- `/accounts/admin/users/`
- `/accounts/admin/users/create/`
- `/accounts/admin/users/<id>/<action>/`
- `/accounts/admin/groups/`
- `/accounts/admin/categories/`
- `/accounts/admin/tickets/`

### Configurable form and tickets

- `/tickets/create/`
- `/tickets/form-builder/`
- `/tickets/<id>/edit/`

### Project root

- `/` redirects to the login page.

## 15. Security and Permissions

Implemented:

- Django authentication
- Login-required access for private pages
- Admin-role and staff checks for admin features
- CSRF tokens on POST forms
- POST-only user suspend/delete actions
- Current-admin self-protection
- ORM-based database access
- Server-side file validation
- Django password hashing
- Suspended/inactive login rejection

## 16. Settings and Static Files

Important settings:

- `DEBUG = True` for development
- `TIME_ZONE = Asia/Kolkata`
- SQLite database for local development
- `STATIC_URL = /static/`
- `STATIC_ROOT = staticfiles/`
- `STATICFILES_DIRS = [BASE_DIR / 'static']`
- `MEDIA_URL = /media/`
- `MEDIA_ROOT = media/`
- Upload limit: 5 MB
- Allowed image formats configured in settings

The `STATICFILES_DIRS` configuration was added so the top-level `static` folder is served correctly during development.

## 17. Database Migration History

The current tickets migrations include:

- `0001_initial.py`: initial ticket/category/comment/history schema
- `0002_issueformfield_ticket_custom_answers.py`: configurable form fields and ticket answer storage

Migration commands:

```bash
python manage.py makemigrations
python manage.py migrate
```

## 18. Setup and Run Instructions

```bash
cd "/run/media/vaishnavan/ACER/Users/Vaishnavan S/project/SIET_Ticket_Platform"
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Open:

`http://localhost:8000/accounts/login/`

Create an admin if necessary:

```bash
python manage.py create_admin admin admin@siet.edu.in admin123
```

Development admin credentials used during testing:

```text
Username: admin
Email: admin@siet.edu.in
Password: admin123
```

## 19. Validation Completed

The following checks were performed successfully:

- `python manage.py check`
- Login page returned HTTP 200
- Password reset page returned HTTP 200
- Admin Overview returned HTTP 200
- Users page returned HTTP 200
- Create User page returned HTTP 200
- Technician Groups page returned HTTP 200
- Categories page returned HTTP 200
- Issue Reports page returned HTTP 200
- Form Builder returned HTTP 200
- Normal user Report an Issue page returned HTTP 200
- Admin ticket editor returned HTTP 200
- Static CSS returned HTTP 200
- College logo asset returned HTTP 200
- Admin user suspend action tested
- Admin user activate action tested
- Admin user delete action tested with a temporary account
- Other-option ticket submission tested
- Custom answers were confirmed in the saved ticket
- Admin/technician/normal-user role routing was confirmed

## 20. Current Limitations and Next Work

The following work is still suitable for the next development phase:

- Add edit/delete controls for already-created form fields in the Form Builder
- Add drag-and-drop field ordering
- Add ticket detail pages with full comment timeline
- Add technician status-update actions from the technician dashboard
- Add user-facing ticket detail view
- Add ticket comments and comment attachments to the custom site UI
- Add pagination and search to users and issue reports
- Add notification emails using SMTP configuration
- Add richer time-series charts for Grafana-like historical reporting
- Add scheduled SLA checking and escalation jobs
- Add automated unit and integration test files
- Add production database and deployment configuration

Asset management is intentionally excluded from the current scope.

## 21. Important Operational Note

At least one Category must exist before a normal user can submit a ticket because the Ticket model requires a category. The admin should first create categories such as Network Issue, PC Issue, or Account Access and optionally map them to technician groups.
