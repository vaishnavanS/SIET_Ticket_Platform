# SIET IT Helpdesk & Issue Ticketing Platform

A centralized, enterprise-grade IT Service Management (ITSM) and helpdesk ticketing platform engineered for the Sri Shakthi Institute of Engineering and Technology (SIET) campus community. The platform streamlines campus IT operations, lab hardware diagnostics, network troubleshooting, and online examination technical support through dynamic form workflows and intelligent automated routing.

---

## 1. Overview & Purpose

In a modern educational institution, technical disruptions—such as lab workstation failures, campus Wi-Fi dropouts, classroom projector glitches, and Safe Exam Browser (SEB) lockups—require prompt, structured resolution.

The SIET Helpdesk Platform replaces manual, unorganized communication channels with an automated, transparent, and auditable IT ticketing system. It empowers students and faculty to submit detailed issue reports while providing IT technicians and administrators with real-time tracking, workload balancing, and SLA compliance monitoring.

---

## 2. Core Functional Modules

### 2.1. Campus User Portal (Students & Faculty)
- **Interactive Issue Reporting**: Submit support requests with category selection, urgency indicators, campus location/lab details, dynamic questionnaires, and screenshot/document attachments.
- **Visual Lifecycle Stepper**: Real-time 4-stage tracking pipeline (Submitted -> Assigned -> In Progress -> Resolved) showing exact timestamps and technician assignments.
- **Ticket History & Discussion**: View open and past tickets with threaded technician communication and audit logs.
- **Service Catalog**: Browse self-service catalog tiles for common issues (Campus Wi-Fi, Lab Hardware, SEB Exam Support, General IT) with pre-filled routing metadata.

### 2.2. GLPI-Grade Dynamic Form Studio
- **Dynamic Question Builder**: System administrators can create, reorder, edit, and delete dynamic questions on the ticket submission canvas without modifying codebase files.
- **Conditional Branching Rules**: Configure visual visibility conditions (`Visible If...`, `Hidden If...`) where sub-questions dynamically appear based on user selections (e.g. choosing "Network Issue" reveals network-specific sub-questions).
- **Dynamic Question Types**:
  - Single-choice radio button pills with highlighted active states
  - Multi-select checkboxes
  - Dropdown select menus
  - Single-line text boxes
  - Multiline text areas (including Problem Description)
  - File upload inputs with admin-configurable upload size limits (MB)
- **Auto-Expanding "Other" Details**: Selecting "Other" on any choice dynamically reveals a dedicated detail specification area.
- **Live In-Studio Form Preview**: Real-time modal matching 100% of the live user form to test branching logic before deploying to campus users.

### 2.3. Intelligent Auto-Routing & Workload Balancing
- **Technician Support Groups**: Specialized teams organized by expertise (Network Support Group, Hardware Maintenance Group, Online Exam & SEB Tech Support).
- **Round-Robin Workload Distribution**: Automatically assigns incoming tickets to the technician within the designated group who has the lowest active workload.
- **Capacity Throttling**: Technicians have a configurable active ticket ceiling to prevent assignment bottlenecks.
- **General Support Fallback**: Tickets with unmapped categories or full technician queues route safely to the administrative holding queue.

### 2.4. Technician Workspace
- **Assigned Queue Dashboard**: Live workbench listing active assignments filtered by status (Open, In Progress, Resolved, Closed).
- **SLA Countdown & Breach Badges**: Visual indicators highlighting on-track and breached response/resolution milestones.
- **Direct Processing & Diagnostics**: Single-click status transitions, technical resolution notes, and direct communication timeline.
- **Attachment Viewer**: Inline thumbnail preview and download links for user-submitted diagnostic photos and screenshots.

### 2.5. Administrative Control Center
- **Global Ticket Oversight**: Comprehensive table of all campus issue reports with location, category, urgency, SLA status, and attachment links.
- **User & Role Management**: Administrative interface to manage user accounts, assign roles (Admin, Technician, Normal User), and control account suspension.
- **Technician Group Management**: Create departments, adjust workload limits, and allocate technicians to groups.
- **Form Studio & Routing Matrix**: Visual interface to map issue categories directly to technician groups.
- **Non-Destructive Audit Compliance**: Enforces an institutional policy where submitted tickets cannot be deleted, preserving a permanent audit trail.

---

## 3. User Roles & Access Hierarchy

| Role | Primary Responsibilities & Access Permissions |
| :--- | :--- |
| **Normal User** (Students / Faculty / Staff) | Report IT issues, track ticket progress via interactive stepper, reply to technician comments, and access the campus service catalog. |
| **Technician** (IT Support Staff) | View assigned support queue, update diagnostics, communicate with reporters, upload resolution notes, and close tickets. |
| **Administrator** (IT Directorate / System Admins) | Complete platform governance: configure dynamic forms, assign technician groups, monitor campus-wide SLAs, manage user roles, and oversee all tickets. |

---

## 4. System Architecture & Data Schema

### 4.1. Entity Relationship Overview
- **`User` & `UserProfile`**: Extends standard authentication with campus role definitions, suspension states, and capacity limits.
- **`TechnicianGroup`**: Departmental containers grouping technician accounts with workload quotas.
- **`Category`**: Root issue classifications linked directly to technician groups for automated routing.
- **`IssueFormField`**: Schema definition model for dynamic questions, options, field types, conditional branching rules, and max file upload limits.
- **`Ticket`**: Central entity capturing ticket number, reporter, category, urgency, location, custom dynamic form answers (JSON), problem description, attachment, SLA deadlines, status, and assigned technician/group.
- **`TicketComment`**: Collaborative communication stream between reporters, technicians, and administrators.
- **`TicketHistory`**: Read-only timeline recording all status transitions, reassignments, and modifications.
- **`ServiceCatalogItem`**: Self-service showcase tiles presented on the student/staff home portal.

### 4.2. Security & Integrity Standards
- **Role-Based Access Control (RBAC)**: Strict view-level and object-level permission enforcement across all endpoints.
- **Data Protection**: Zero raw secret exposure, encrypted password storage, and environment-based configuration.
- **Cross-Site Request Forgery (CSRF) Protection**: Strict CSRF token validation across all dynamic and standard form submissions.
- **SQL Injection & XSS Defense**: Standardized Django ORM query abstraction and template HTML escaping.
- **Attachment Sandboxing**: Client and server-side file size enforcement with isolated media storage.
