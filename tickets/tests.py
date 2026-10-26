from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from accounts.models import UserProfile, UserRole, TechnicianGroup
from tickets.models import Category, Ticket, TicketStatus, TicketUrgency, TicketComment, TicketHistory, SolutionArticle, TargetCategory, CampusLocation


class TechnicianDashboardAndTicketTests(TestCase):
    def setUp(self):
        self.client = Client()

        # Create Admin
        self.admin = User.objects.create_superuser(
            username='admin_user',
            email='admin@siet.edu.in',
            password='Password123!'
        )
        self.admin.profile.role = UserRole.ADMIN
        self.admin.profile.save()

        # Create Technician
        self.tech = User.objects.create_user(
            username='tech_user',
            email='tech@siet.edu.in',
            password='Password123!'
        )
        self.tech.profile.role = UserRole.TECHNICIAN
        self.tech.profile.save()

        # Create Reporter (Normal User)
        self.reporter = User.objects.create_user(
            username='normal_user',
            email='user@siet.edu.in',
            password='Password123!'
        )
        self.reporter.profile.role = UserRole.NORMAL_USER
        self.reporter.profile.save()


        # Category
        self.category = Category.objects.create(
            name='Network Issue',
            description='Wifi and lab network problems'
        )

        # Ticket
        self.ticket = Ticket.objects.create(
            title='Wifi not connecting in Lab 3',
            description='Laptops unable to acquire IP address.',
            urgency=TicketUrgency.HIGH,
            category=self.category,
            location='CS Lab 3',
            reporter=self.reporter,
            assigned_technician=self.tech,
            status=TicketStatus.OPEN,
            custom_answers={'Facing Issue In': 'Network Issue'}
        )

    def test_technician_dashboard_requires_login(self):
        response = self.client.get(reverse('accounts:technician_dashboard'))
        self.assertEqual(response.status_code, 302)

    def test_technician_dashboard_renders_assigned_ticket(self):
        self.client.login(username='tech_user', password='Password123!')
        response = self.client.get(reverse('accounts:technician_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Wifi not connecting in Lab 3')
        self.assertContains(response, '#1')

    def test_technician_dashboard_status_filtering(self):
        self.client.login(username='tech_user', password='Password123!')
        response = self.client.get(reverse('accounts:technician_dashboard') + '?status=resolved')
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Wifi not connecting in Lab 3')

    def test_technician_quick_status_update(self):
        self.client.login(username='tech_user', password='Password123!')
        update_url = reverse('tickets:update_status', kwargs={'pk': self.ticket.pk})
        
        response = self.client.post(update_url, {
            'status': TicketStatus.IN_PROGRESS,
            'comment': 'Investigating router configuration'
        })
        self.assertEqual(response.status_code, 302)

        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.status, TicketStatus.IN_PROGRESS)
        
        # Verify Audit History
        history = TicketHistory.objects.filter(ticket=self.ticket).first()
        self.assertIsNotNone(history)
        self.assertEqual(history.field_name, 'status')
        self.assertEqual(history.old_value, 'Open')
        self.assertEqual(history.new_value, 'In Progress')

        # Verify Comment Logged
        comment = TicketComment.objects.filter(ticket=self.ticket).first()
        self.assertIsNotNone(comment)
        self.assertEqual(comment.content, 'Investigating router configuration')

    def test_ticket_detail_view_permissions(self):
        detail_url = reverse('tickets:detail', kwargs={'pk': self.ticket.pk})
        
        # Reporter can view
        self.client.login(username='normal_user', password='Password123!')
        res_reporter = self.client.get(detail_url)
        self.assertEqual(res_reporter.status_code, 200)
        self.assertContains(res_reporter, 'Wifi not connecting in Lab 3')

        # Assigned technician can view
        self.client.login(username='tech_user', password='Password123!')
        res_tech = self.client.get(detail_url)
        self.assertEqual(res_tech.status_code, 200)

        # Unrelated user cannot view
        other_user = User.objects.create_user(username='other_user', password='Password123!')
        self.client.login(username='other_user', password='Password123!')
        res_other = self.client.get(detail_url)
        self.assertEqual(res_other.status_code, 302)

    def test_add_ticket_comment(self):
        self.client.login(username='normal_user', password='Password123!')
        comment_url = reverse('tickets:add_comment', kwargs={'pk': self.ticket.pk})

        response = self.client.post(comment_url, {
            'content': 'Problem resolved on my end, thank you!'
        })
        self.assertEqual(response.status_code, 302)

        self.assertEqual(TicketComment.objects.filter(ticket=self.ticket).count(), 1)
        comment = TicketComment.objects.get(ticket=self.ticket)
        self.assertEqual(comment.content, 'Problem resolved on my end, thank you!')
        self.assertEqual(comment.author, self.reporter)


class FormBuilderTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_superuser(
            username='admin_builder',
            email='admin@siet.edu.in',
            password='Password123!'
        )
        self.admin.profile.role = UserRole.ADMIN
        self.admin.profile.save()

    def test_admin_access_form_builder(self):
        self.client.login(username='admin_builder', password='Password123!')
        response = self.client.get(reverse('tickets:form_builder'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Dynamic Form Studio')

    def test_add_and_edit_form_field_with_glpi_conditions(self):
        from tickets.models import IssueFormField
        self.client.login(username='admin_builder', password='Password123!')

        # 1. Create primary question with options
        post_data = {
            'action': 'save_field',
            'label': 'Facing Issue In',
            'field_key': 'facing_issue_in',
            'field_type': 'radio',
            'options_text': 'Network Issue\nPC Issue\nOther',
            'condition_type': 'always',
            'required': True,
            'order': 0,
            'is_active': True,
        }
        res_create = self.client.post(reverse('tickets:form_builder'), post_data)
        self.assertEqual(res_create.status_code, 302)

        field1 = IssueFormField.objects.get(field_key='facing_issue_in')
        self.assertEqual(field1.options, ['Network Issue', 'PC Issue', 'Other'])
        self.assertEqual(field1.condition_type, 'always')

        # 2. Create sub-question with 'visible_if' condition
        post_sub = {
            'action': 'save_field',
            'label': 'Which Network Problem?',
            'field_key': 'network_problem_type',
            'field_type': 'checkbox',
            'options_text': 'LAN Problem\nWiFi Problem\nSlow Network\nOther',
            'condition_type': 'visible_if',
            'condition_field_key': 'facing_issue_in',
            'condition_operator': 'equals',
            'condition_value': 'Network Issue',
            'required': True,
            'order': 1,
            'is_active': True,
        }
        res_sub = self.client.post(reverse('tickets:form_builder'), post_sub)
        self.assertEqual(res_sub.status_code, 302)

        field2 = IssueFormField.objects.get(field_key='network_problem_type')
        self.assertEqual(field2.condition_type, 'visible_if')
        self.assertEqual(field2.condition_field_key, 'facing_issue_in')
        self.assertEqual(field2.condition_value, 'Network Issue')

        # 3. Edit field
        edit_url = reverse('tickets:field_edit', kwargs={'pk': field2.pk})
        edit_data = {
            'label': 'Select Network Problem',
            'field_key': 'network_problem_type',
            'field_type': 'select',
            'options_text': 'LAN Problem\nWiFi Problem\nSlow Network\nOther',
            'condition_type': 'visible_if',
            'condition_field_key': 'facing_issue_in',
            'condition_operator': 'contains',
            'condition_value': 'Network',
            'required': True,
            'order': 1,
            'is_active': True,
        }
        res_edit = self.client.post(edit_url, edit_data)
        self.assertEqual(res_edit.status_code, 302)

        field2.refresh_from_db()
        self.assertEqual(field2.label, 'Select Network Problem')
        self.assertEqual(field2.condition_operator, 'contains')

        # 4. Delete field
        delete_url = reverse('tickets:field_delete', kwargs={'pk': field2.pk})
        res_delete = self.client.post(delete_url)
        self.assertEqual(res_delete.status_code, 302)
        self.assertFalse(IssueFormField.objects.filter(pk=field2.pk).exists())

    def test_technician_group_routing_update(self):
        from accounts.models import TechnicianGroup
        self.client.login(username='admin_builder', password='Password123!')
        
        cat = Category.objects.create(name='Exam SEB Issue')
        grp = TechnicianGroup.objects.create(name='Exam Tech Support')

        post_routing = {
            'action': 'update_routing',
            'category_id': cat.id,
            'group_id': grp.id,
        }
        res = self.client.post(reverse('tickets:form_builder'), post_routing)
        self.assertEqual(res.status_code, 302)

        cat.refresh_from_db()
        self.assertEqual(cat.assigned_group, grp)

    def test_category_specific_field_and_service_catalog(self):
        from tickets.models import Category, IssueFormField, ServiceCatalogItem
        self.client.login(username='admin_builder', password='Password123!')

        cat = Category.objects.create(name='Wifi & Network', description='Campus network issues')

        # Create category specific field
        field = IssueFormField.objects.create(
            label='Router Location',
            field_key='router_location',
            field_type='text',
            category=cat,
            is_active=True
        )
        self.assertEqual(field.category, cat)

        # Service catalog manager access & create
        res_cat = self.client.get(reverse('tickets:catalog_manager'))
        self.assertEqual(res_cat.status_code, 200)

        res_post_cat = self.client.post(reverse('tickets:catalog_manager'), {
            'title': 'Wifi Troubleshooting',
            'description': 'Help with lab wifi',
            'icon': '🌐',
            'category': cat.pk,
            'show_on_homepage': True,
            'is_active': True,
            'order': 1
        })
        self.assertEqual(res_post_cat.status_code, 302)
        self.assertTrue(ServiceCatalogItem.objects.filter(title='Wifi Troubleshooting').exists())

    def test_seed_glpi_workflow_command(self):
        from django.core.management import call_command
        from tickets.models import IssueFormField, Category, ServiceCatalogItem
        from accounts.models import TechnicianGroup

        call_command('seed_glpi_workflow')
        self.assertTrue(TechnicianGroup.objects.filter(name='Network Support Group').exists())
        self.assertTrue(Category.objects.filter(name='Network Issue').exists())
        self.assertTrue(IssueFormField.objects.filter(field_key='facing_issue_in').exists())
        self.assertTrue(IssueFormField.objects.filter(field_key='network_problem_type').exists())
        self.assertTrue(ServiceCatalogItem.objects.filter(title='Campus WiFi & LAN Access').exists())

    def test_ticket_creation_with_dynamic_custom_answers_and_routing(self):
        from django.core.management import call_command
        from accounts.models import UserProfile
        call_command('seed_glpi_workflow')

        # Create normal user
        user = User.objects.create_user(username='student1', password='Password123!')
        user.profile.role = UserRole.NORMAL_USER
        user.profile.save()

        # Create technician in Network Support Group
        tech = User.objects.create_user(username='net_tech1', password='Password123!')
        tech.profile.role = UserRole.TECHNICIAN
        tech.profile.save()
        net_grp = TechnicianGroup.objects.get(name='Network Support Group')
        net_grp.technicians.add(tech)

        self.client.login(username='student1', password='Password123!')
        net_cat = Category.objects.get(name='Network Issue')

        # Submit ticket
        post_data = {
            'title': 'No internet on table 4',
            'description': 'DHCP fails to assign an IP address to laptop.',
            'category': net_cat.id,
            'urgency': TicketUrgency.HIGH,
            'location': 'Lab 2 - Table 4',
            'facing_issue_in': ['Network Issue'],
            'network_problem_type': ['LAN Problem', 'Other'],
            'network_problem_description': 'Error 105 DNS probe failed',
            'other_issue_details': 'Port light on wall plate is off',
        }
        response = self.client.post(reverse('tickets:create'), post_data)
        self.assertEqual(response.status_code, 302)

        created_ticket = Ticket.objects.filter(reporter=user).first()
        self.assertIsNotNone(created_ticket)
        self.assertEqual(created_ticket.category, net_cat)
        self.assertIn(created_ticket.assigned_technician, net_grp.technicians.all())
        self.assertEqual(created_ticket.assigned_group, net_grp)


        # Verify custom answers stored properly
        answers = created_ticket.custom_answers
        self.assertIn('Facing Issue In', answers)
        self.assertIn('Which Network Problem ?', answers)
        self.assertIn('Type Your Network Problem', answers)
        self.assertIn('Other Issue Details', answers)
        self.assertEqual(answers['Other Issue Details'], 'Port light on wall plate is off')

    def test_file_attachment_upload_and_admin_visibility(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        user = User.objects.create_user(username='file_student', password='Password123!')
        self.client.login(username='file_student', password='Password123!')

        fake_img = SimpleUploadedFile("screenshot.jpg", b"fake image bytes", content_type="image/jpeg")
        post_data = {
            'title': 'Projector flickering with photo proof',
            'facing_issue_in': ['Network Issue'],
            'problem_description': 'Screen turns magenta intermittently.',
            'urgency': TicketUrgency.MEDIUM,
            'location': 'Seminar Hall A',
            'attachment': fake_img,
        }

        res = self.client.post(reverse('tickets:create'), post_data)
        self.assertEqual(res.status_code, 302)

        ticket = Ticket.objects.filter(reporter=user).first()
        self.assertIsNotNone(ticket)
        self.assertTrue(bool(ticket.attachment))

        # Check Admin Tickets Page table renders attachment link
        self.client.login(username='admin_builder', password='Password123!')
        admin_res = self.client.get(reverse('accounts:admin_tickets'))
        self.assertEqual(admin_res.status_code, 200)
        self.assertContains(admin_res, 'Attached File')

        # Check Ticket Detail page renders preview and download button
        detail_res = self.client.get(reverse('tickets:detail', kwargs={'pk': ticket.pk}))
        self.assertEqual(detail_res.status_code, 200)
        self.assertContains(detail_res, 'Attached Screenshot / Document')
        self.assertContains(detail_res, 'Download File')

        # Check File Size Limit Enforcement (upload 6MB file against 5MB default limit)
        self.client.login(username='file_student', password='Password123!')
        oversized_img = SimpleUploadedFile("big_photo.jpg", b"x" * (6 * 1024 * 1024), content_type="image/jpeg")
        post_oversized = {
            'title': 'Oversized photo test',
            'facing_issue_in': ['Network Issue'],
            'problem_description': 'File is too large',
            'urgency': TicketUrgency.LOW,
            'location': 'Lab 1',
            'attachment': oversized_img,
        }
        res_oversized = self.client.post(reverse('tickets:create'), post_oversized)
        self.assertEqual(res_oversized.status_code, 200)
        self.assertContains(res_oversized, 'exceeds maximum allowed limit of 5 MB')


    def test_service_catalog_toggle(self):
        from tickets.models import ServiceCatalogItem
        self.client.login(username='admin_builder', password='Password123!')

        item = ServiceCatalogItem.objects.create(title='Test Service', show_on_homepage=True)

        toggle_url = reverse('tickets:catalog_toggle', kwargs={'pk': item.pk})
        res = self.client.post(toggle_url, {'action': 'toggle_homepage'})
        self.assertEqual(res.status_code, 302)

        item.refresh_from_db()
        self.assertFalse(item.show_on_homepage)

    def test_lan_configuration_and_command(self):
        from django.conf import settings
        from tickets.management.commands.runserver_lan import get_all_lan_ips

        # Verify ALLOWED_HOSTS allows all or dynamic hosts
        self.assertIn('*', settings.ALLOWED_HOSTS)

        # Verify CSRF_TRUSTED_ORIGINS contains localhost and standard origins
        self.assertIn('http://localhost:8000', settings.CSRF_TRUSTED_ORIGINS)
        self.assertIn('http://127.0.0.1:8000', settings.CSRF_TRUSTED_ORIGINS)

        # Verify get_all_lan_ips runs without error
        lan_ips = get_all_lan_ips()
        self.assertIsInstance(lan_ips, list)

    def test_ticket_deletion_is_blocked(self):
        from django.core.exceptions import PermissionDenied
        # Create a ticket
        cat = Category.objects.create(name='Audio Video')
        user = User.objects.create_user(username='av_user', password='Password123!')
        ticket = Ticket.objects.create(
            title='Projector HDMI no signal',
            description='Room 101 projector not displaying laptop.',
            category=cat,
            reporter=user,
            location='Room 101'
        )
        # Attempting deletion must raise PermissionDenied
        with self.assertRaises(PermissionDenied):
            ticket.delete()

    def test_my_tickets_portal_view_and_filtering(self):
        user = User.objects.create_user(username='portal_user', password='Password123!')
        cat = Category.objects.create(name='Hardware')
        t1 = Ticket.objects.create(
            title='Broken Keyboard',
            description='Spacebar stuck',
            category=cat,
            reporter=user,
            location='Lab 1',
            status=TicketStatus.OPEN
        )
        t2 = Ticket.objects.create(
            title='Monitor Flickering',
            description='Screen goes black intermittently',
            category=cat,
            reporter=user,
            location='Lab 1',
            status=TicketStatus.RESOLVED
        )

        self.client.login(username='portal_user', password='Password123!')
        res = self.client.get(reverse('tickets:my_tickets'))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'Broken Keyboard')
        self.assertContains(res, 'Monitor Flickering')
        self.assertContains(res, 'ticket-process-stepper')
        self.assertContains(res, 'Submitted')


        # Filter by status=open
        res_open = self.client.get(reverse('tickets:my_tickets') + '?status=open')
        self.assertEqual(res_open.status_code, 200)
        self.assertContains(res_open, 'Broken Keyboard')
        self.assertNotContains(res_open, 'Monitor Flickering')

    def test_admin_can_edit_ticket_location_and_details(self):
        self.client.login(username='admin_builder', password='Password123!')
        cat = Category.objects.create(name='Software')
        user = User.objects.create_user(username='sw_user', password='Password123!')
        ticket = Ticket.objects.create(
            title='Compiler error',
            description='GCC missing',
            category=cat,
            reporter=user,
            location='Lab 4'
        )
        # Admin can access edit form
        res = self.client.get(reverse('tickets:edit', kwargs={'pk': ticket.pk}))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'Edit Issue #')
        self.assertContains(res, 'Campus Location / Room / Lab')

        # Admin posts updated location and details
        post_data = {
            'title': 'Compiler error in Lab 2',
            'description': 'GCC compiler missing on Ubuntu machines',
            'category': cat.pk,
            'urgency': 'high',
            'location': 'Hostel Block B - Room 304',
            'status': 'in_progress',
        }
        res_post = self.client.post(reverse('tickets:edit', kwargs={'pk': ticket.pk}), post_data)
        self.assertEqual(res_post.status_code, 302)
        self.assertIn(reverse('tickets:detail', kwargs={'pk': ticket.pk}), res_post.url)

        # Verify ticket was updated in database
        ticket.refresh_from_db()
        self.assertEqual(ticket.location, 'Hostel Block B - Room 304')
        self.assertEqual(ticket.urgency, 'high')

        # Verify audit history was recorded for location change
        history_item = TicketHistory.objects.filter(ticket=ticket, field_name='Location').first()
        self.assertIsNotNone(history_item)
        self.assertEqual(history_item.old_value, 'Lab 4')
        self.assertEqual(history_item.new_value, 'Hostel Block B - Room 304')

    def test_normal_user_cannot_access_ticket_edit(self):
        user = User.objects.create_user(username='unauthorized_editor', password='Password123!')
        user.profile.role = UserRole.NORMAL_USER
        user.profile.save()
        cat = Category.objects.create(name='General')
        ticket = Ticket.objects.create(title='Net', reporter=user, category=cat, location='Lab 1')

        self.client.login(username='unauthorized_editor', password='Password123!')
        res = self.client.get(reverse('tickets:edit', kwargs={'pk': ticket.pk}))
        self.assertEqual(res.status_code, 302)
        self.assertIn(reverse('tickets:detail', kwargs={'pk': ticket.pk}), res.url)

    def test_user_home_portal_options(self):
        user = User.objects.create_user(username='homepage_user', password='Password123!')
        user.profile.role = UserRole.NORMAL_USER
        user.profile.save()

        self.client.login(username='homepage_user', password='Password123!')
        res = self.client.get(reverse('accounts:user_dashboard'))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'Report an Issue')
        self.assertContains(res, 'Service Catalog')
        self.assertContains(res, 'My Tickets & History')
        self.assertContains(res, 'portal-cards-grid')

    def test_user_service_catalog_view(self):
        user = User.objects.create_user(username='cat_user', password='Password123!')
        user.profile.role = UserRole.NORMAL_USER
        user.profile.save()

        self.client.login(username='cat_user', password='Password123!')
        res = self.client.get(reverse('tickets:user_catalog'))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'IT Service Catalog')


from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.exceptions import ValidationError
from tickets.forms import TicketCreateForm

class SecurityAndConcurrencyTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='sec_user', password='Password123!')
        self.category = Category.objects.create(name='Hardware')
        self.ticket = Ticket.objects.create(
            title='Test Ticket',
            description='Testing security',
            category=self.category,
            reporter=self.user,
            location='Lab 1'
        )

    def test_comment_attachment_rejects_dangerous_extensions(self):
        """Comment attachment should reject executables and scripts"""
        bad_file = SimpleUploadedFile("malware.exe", b"binary content", content_type="application/octet-stream")
        comment = TicketComment(
            ticket=self.ticket,
            author=self.user,
            content="Check this tool",
            attachment=bad_file
        )
        with self.assertRaises(ValidationError):
            comment.clean()

    def test_comment_attachment_accepts_valid_extensions(self):
        """Comment attachment should allow safe images and documents"""
        good_img = SimpleUploadedFile("screenshot.png", b"fake image bytes", content_type="image/png")
        comment = TicketComment(
            ticket=self.ticket,
            author=self.user,
            content="Screenshot of error",
            attachment=good_img
        )
        comment.clean()  # Should not raise
        comment.save()
        self.assertIsNotNone(comment.pk)

    def test_ticket_form_rejects_non_image_extension_with_form_error(self):
        """Ticket creation form should reject non-image attachments gracefully without 500 error"""
        pdf_file = SimpleUploadedFile("doc.pdf", b"%PDF-1.4 dummy", content_type="application/pdf")
        form = TicketCreateForm(
            data={
                'title': 'Broken Printer',
                'description': 'Needs toner',
                'urgency': TicketUrgency.MEDIUM,
                'location': 'Staff room'
            },
            files={'attachment': pdf_file}
        )
        self.assertFalse(form.is_valid())
        self.assertIn('attachment', form.errors)
        self.assertIn('File type \'.pdf\' is not allowed', form.errors['attachment'][0])

    def test_ticket_number_generation_sequential_and_unique(self):
        """Sequential ticket number generation should produce unique incrementing numbers"""
        t1 = Ticket.objects.create(title='T1', category=self.category, reporter=self.user, location='L1')
        t2 = Ticket.objects.create(title='T2', category=self.category, reporter=self.user, location='L2')
        t3 = Ticket.objects.create(title='T3', category=self.category, reporter=self.user, location='L3')
        self.assertTrue(t1.ticket_number < t2.ticket_number < t3.ticket_number)
        self.assertEqual(len({t1.ticket_number, t2.ticket_number, t3.ticket_number}), 3)


class SolutionHubTests(TestCase):
    def setUp(self):
        self.client = Client()

        # Admin user
        self.admin = User.objects.create_superuser(
            username='admin_solutions',
            email='admin_sol@siet.edu.in',
            password='Password123!'
        )
        self.admin.profile.role = UserRole.ADMIN
        self.admin.profile.save()

        # Normal user
        self.user = User.objects.create_user(
            username='student_user',
            email='student@siet.edu.in',
            password='Password123!'
        )
        self.user.profile.role = UserRole.NORMAL_USER
        self.user.profile.save()

        # Technician user
        self.tech = User.objects.create_user(
            username='tech_solutions',
            email='tech_sol@siet.edu.in',
            password='Password123!'
        )
        self.tech.profile.role = UserRole.TECHNICIAN
        self.tech.profile.save()

        # Seed test solutions
        self.wifi_sol = SolutionArticle.objects.create(
            title="Wi-Fi Reconnecting or Weak Signal",
            target_category=TargetCategory.WIFI_LAN,
            summary="Fix device repeatedly disconnecting from SIET_Campus_WiFi.",
            symptoms="Frequent disconnection\nRandomized MAC address issue\nObtaining IP address loop",
            solution_steps="1. Open Wi-Fi settings.\n2. Tap SIET_Campus_WiFi.\n3. Change MAC to Phone/Device MAC.",
            verification_checklist="Can you open siet.ac.in?\nDo you see a valid 10.10.x.x IP address?",
            helpful_count=5,
            is_active=True,
            order=1
        )

        self.seb_sol = SolutionArticle.objects.create(
            title="Safe Exam Browser (SEB) Red Screen Lockout",
            target_category=TargetCategory.SEB,
            summary="Resolve prohibited background process warnings during exams.",
            symptoms="Red screen with process warning\nAnyDesk or Discord detected",
            solution_steps="1. Press Ctrl+Alt+Del or Exit SEB.\n2. Open Task Manager.\n3. End Discord and AnyDesk.",
            verification_checklist="Task manager shows zero forbidden background tools\nSEB starts normally",
            helpful_count=2,
            is_active=True,
            order=2
        )

        self.inactive_sol = SolutionArticle.objects.create(
            title="Draft Solution Not Ready",
            target_category=TargetCategory.GENERAL,
            summary="Work in progress guide.",
            solution_steps="Under construction",
            is_active=False,
            order=99
        )

    def test_solution_article_helpers(self):
        """Model parsing methods should correctly split lines and return lists"""
        symptoms = self.wifi_sol.get_symptoms_list()
        self.assertEqual(len(symptoms), 3)
        self.assertIn("Randomized MAC address issue", symptoms)

        steps = self.wifi_sol.get_solution_steps_list()
        self.assertEqual(len(steps), 3)
        self.assertTrue(steps[0].startswith("1."))

        checklist = self.wifi_sol.get_checklist_list()
        self.assertEqual(len(checklist), 2)

        self.assertEqual(self.wifi_sol.category_badge_class(), "badge-wifi")
        self.assertEqual(self.seb_sol.category_badge_class(), "badge-seb")

    def test_solutions_list_view_displays_active_solutions(self):
        """Solutions list should show active guides and hide inactive ones for regular users"""
        self.client.login(username='student_user', password='Password123!')
        response = self.client.get(reverse('tickets:solutions'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Wi-Fi Reconnecting or Weak Signal")
        self.assertContains(response, "Safe Exam Browser (SEB) Red Screen Lockout")
        self.assertNotContains(response, "Draft Solution Not Ready")

    def test_solutions_list_category_filter(self):
        """Filtering by category=WIFI_LAN should only show Wi-Fi / LAN solutions"""
        self.client.login(username='student_user', password='Password123!')
        response = self.client.get(reverse('tickets:solutions') + '?category=WIFI_LAN')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Wi-Fi Reconnecting or Weak Signal")
        self.assertNotContains(response, "Safe Exam Browser (SEB) Red Screen Lockout")

        # Now test SEB filter
        response_seb = self.client.get(reverse('tickets:solutions') + '?category=SEB')
        self.assertEqual(response_seb.status_code, 200)
        self.assertContains(response_seb, "Safe Exam Browser (SEB) Red Screen Lockout")
        self.assertNotContains(response_seb, "Wi-Fi Reconnecting or Weak Signal")

    def test_solutions_list_search_query(self):
        """Search query should match title, summary, or symptoms"""
        self.client.login(username='student_user', password='Password123!')
        response = self.client.get(reverse('tickets:solutions') + '?q=Randomized')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Wi-Fi Reconnecting or Weak Signal")
        self.assertNotContains(response, "Safe Exam Browser (SEB) Red Screen Lockout")

    def test_solution_feedback_ajax(self):
        """POST to solution feedback should increment helpful_count and return JSON"""
        self.client.login(username='student_user', password='Password123!')
        url = reverse('tickets:solution_feedback', kwargs={'pk': self.wifi_sol.pk})
        response = self.client.post(url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data.get('success'))
        self.assertEqual(data.get('helpful_count'), 6)

        self.wifi_sol.refresh_from_db()
        self.assertEqual(self.wifi_sol.helpful_count, 6)

    def test_admin_solutions_access_control(self):
        """Regular user cannot access admin solutions manager"""
        self.client.login(username='student_user', password='Password123!')
        response = self.client.get(reverse('tickets:admin_solutions'))
        # Should redirect to user dashboard
        self.assertEqual(response.status_code, 302)

        # Admin user can access
        self.client.login(username='admin_solutions', password='Password123!')
        response_admin = self.client.get(reverse('tickets:admin_solutions'))
        self.assertEqual(response_admin.status_code, 200)
        self.assertContains(response_admin, "Solutions & Quick-Fixes Manager")

    def test_admin_solutions_crud(self):
        """Admin can create, toggle active state, and delete solution articles"""
        self.client.login(username='admin_solutions', password='Password123!')

        # 1. Create new article
        create_response = self.client.post(reverse('tickets:admin_solutions'), {
            'action': 'create',
            'title': 'Wired LAN Cable Loose Connection',
            'target_category': TargetCategory.WIFI_LAN,
            'summary': 'Fix RJ45 jack clip loose.',
            'symptoms': 'Network cable unplugged notification\nFlashing orange LED',
            'solution_steps': '1. Check RJ45 clip.\n2. Push firmly until click sound.',
            'verification_checklist': 'Link light turns solid green\nInternet connected',
            'order': 3,
            'is_active': 'on'
        })
        self.assertEqual(create_response.status_code, 302)
        new_article = SolutionArticle.objects.filter(title='Wired LAN Cable Loose Connection').first()
        self.assertIsNotNone(new_article)
        self.assertTrue(new_article.is_active)

        # 2. Toggle active state
        toggle_response = self.client.post(reverse('tickets:admin_solutions'), {
            'action': 'toggle_active',
            'solution_id': new_article.pk
        })
        self.assertEqual(toggle_response.status_code, 302)
        new_article.refresh_from_db()
        self.assertFalse(new_article.is_active)

        # 3. Edit article
        edit_url = reverse('tickets:admin_solution_edit', kwargs={'pk': new_article.pk})
        edit_response = self.client.post(edit_url, {
            'title': 'Wired LAN Cable Updated Guide',
            'target_category': TargetCategory.WIFI_LAN,
            'summary': 'Updated RJ45 guide.',
            'symptoms': 'New symptoms',
            'solution_steps': '1. Step one\n2. Step two',
            'verification_checklist': 'Check one',
            'order': 4,
            'is_active': 'on'
        })
        self.assertEqual(edit_response.status_code, 302)
        new_article.refresh_from_db()
        self.assertEqual(new_article.title, 'Wired LAN Cable Updated Guide')
        self.assertTrue(new_article.is_active)

        # 4. Delete article
        del_response = self.client.post(reverse('tickets:admin_solutions'), {
            'action': 'delete',
            'solution_id': new_article.pk
        })
        self.assertEqual(del_response.status_code, 302)
        self.assertFalse(SolutionArticle.objects.filter(pk=new_article.pk).exists())

    def test_technician_can_access_solutions_manager(self):
        """Technician account can access Solutions Manager dashboard"""
        self.client.login(username='tech_solutions', password='Password123!')
        response = self.client.get(reverse('tickets:admin_solutions'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Solutions & Quick-Fixes Manager")
        self.assertContains(response, "Publish New Solution Guide")

    def test_technician_can_create_and_edit_solution(self):
        """Technician account can publish a new solution and edit existing solutions"""
        self.client.login(username='tech_solutions', password='Password123!')

        # Create solution as technician
        create_resp = self.client.post(reverse('tickets:admin_solutions'), {
            'action': 'create',
            'title': 'Technician Fixed Wi-Fi Roaming Guide',
            'target_category': TargetCategory.WIFI_LAN,
            'summary': 'AP roaming configuration instructions.',
            'symptoms': 'Device sticks to far away AP',
            'solution_steps': '1. Turn Wi-Fi off and on.\n2. Reconnect to nearest AP.',
            'verification_checklist': 'Connected to AP with > -65 dBm signal',
            'order': 5,
            'is_active': 'on'
        })
        self.assertEqual(create_resp.status_code, 302)
        article = SolutionArticle.objects.filter(title='Technician Fixed Wi-Fi Roaming Guide').first()
        self.assertIsNotNone(article)

        # Edit solution as technician
        edit_url = reverse('tickets:admin_solution_edit', kwargs={'pk': article.pk})
        edit_resp = self.client.post(edit_url, {
            'title': 'Technician Fixed Wi-Fi Roaming Guide (Updated)',
            'target_category': TargetCategory.WIFI_LAN,
            'summary': 'Updated roaming guide.',
            'symptoms': 'Device sticks to far away AP',
            'solution_steps': '1. Turn Wi-Fi off and on.\n2. Reconnect to nearest AP.\n3. Forget other SSIDs.',
            'verification_checklist': 'Signal is strong',
            'order': 5,
            'is_active': 'on'
        })
        self.assertEqual(edit_resp.status_code, 302)
        article.refresh_from_db()
        self.assertEqual(article.title, 'Technician Fixed Wi-Fi Roaming Guide (Updated)')

    def test_solutions_list_management_buttons_visibility(self):
        """Technicians and admins see the '+ Create & Manage Solutions' button and 'Edit' button; normal users do not"""
        # 1. Normal user does NOT see management buttons
        self.client.login(username='student_user', password='Password123!')
        user_resp = self.client.get(reverse('tickets:solutions'))
        self.assertEqual(user_resp.status_code, 200)
        self.assertNotContains(user_resp, "+ Create & Manage Solutions")
        self.assertNotContains(user_resp, reverse('tickets:admin_solutions'))

        # 2. Technician sees management button and edit action
        self.client.login(username='tech_solutions', password='Password123!')
        tech_resp = self.client.get(reverse('tickets:solutions'))
        self.assertEqual(tech_resp.status_code, 200)
        self.assertContains(tech_resp, "+ Create & Manage Solutions")
        self.assertContains(tech_resp, reverse('tickets:admin_solution_edit', kwargs={'pk': self.wifi_sol.pk}))

        # 3. Admin sees management button and edit action
        self.client.login(username='admin_solutions', password='Password123!')
        admin_resp = self.client.get(reverse('tickets:solutions'))
        self.assertEqual(admin_resp.status_code, 200)
        self.assertContains(admin_resp, "+ Create & Manage Solutions")
        self.assertContains(admin_resp, reverse('tickets:admin_solution_edit', kwargs={'pk': self.wifi_sol.pk}))

    def test_location_condition_technician_group_routing(self):
        """Tickets matching a location condition route to the dedicated location technician"""
        from accounts.models import TechnicianGroup

        # 1. Create Hostel Tech & Group
        hostel_tech = User.objects.create_user(username='hostel_tech_specialist', password='Password123!')
        hostel_tech.profile.role = UserRole.TECHNICIAN
        hostel_tech.profile.save()
        hostel_grp = TechnicianGroup.objects.create(
            name='Hostel Support Team Alpha',
            location_condition='Hostel, Boys Hostel',
            max_tickets_per_tech=5
        )
        hostel_grp.technicians.add(hostel_tech)

        # 2. Create Tech Park Tech & Group
        techpark_tech = User.objects.create_user(username='techpark_tech_specialist', password='Password123!')
        techpark_tech.profile.role = UserRole.TECHNICIAN
        techpark_tech.profile.save()
        techpark_grp = TechnicianGroup.objects.create(
            name='Tech Park Team Beta',
            location_condition='Tech Park, CS Lab',
            max_tickets_per_tech=5
        )
        techpark_grp.technicians.add(techpark_tech)

        cat = Category.objects.create(name='General Hardware')
        student = User.objects.create_user(username='campus_resident', password='Password123!')

        # 3. Ticket with Hostel location
        ticket_hostel = Ticket.objects.create(
            title='Fan and LAN socket broken',
            description='Room socket not powering up',
            category=cat,
            reporter=student,
            location='Hostel Block C - Room 204'
        )
        assigned_tech_1 = ticket_hostel.assign_to_technician()
        ticket_hostel.refresh_from_db()
        self.assertEqual(assigned_tech_1, hostel_tech)
        self.assertEqual(ticket_hostel.assigned_technician, hostel_tech)
        self.assertEqual(ticket_hostel.assigned_group, hostel_grp)

        # 4. Ticket with Tech Park location
        ticket_tp = Ticket.objects.create(
            title='Projector HDMI cable faulty',
            description='Projector flickering in Lab 3',
            category=cat,
            reporter=student,
            location='Tech Park 2nd Floor - CS Lab 3'
        )
        assigned_tech_2 = ticket_tp.assign_to_technician()
        ticket_tp.refresh_from_db()
        self.assertEqual(assigned_tech_2, techpark_tech)
        self.assertEqual(ticket_tp.assigned_technician, techpark_tech)
        self.assertEqual(ticket_tp.assigned_group, techpark_grp)


class CampusLocationAndRoutingTests(TestCase):
    def setUp(self):
        self.client = Client()

        # Admin user
        self.admin = User.objects.create_superuser(username='admin_loc', email='admin@siet.edu.in', password='Password123!')
        self.admin.profile.role = UserRole.ADMIN
        self.admin.profile.save()

        # Technicians
        self.tech_park_tech = User.objects.create_user(username='techpark_lead', password='Password123!')
        self.tech_park_tech.profile.role = UserRole.TECHNICIAN
        self.tech_park_tech.profile.save()

        self.hostel_tech = User.objects.create_user(username='hostel_lead', password='Password123!')
        self.hostel_tech.profile.role = UserRole.TECHNICIAN
        self.hostel_tech.profile.save()

        # Normal User
        self.student = User.objects.create_user(username='vlsi_student', password='Password123!')
        self.student.profile.role = UserRole.NORMAL_USER
        self.student.profile.save()

        # Campus Locations
        self.loc_tech_park = CampusLocation.objects.create(name='Tech Park', code='TECH_PARK', is_active=True)
        self.loc_hostel = CampusLocation.objects.create(name='Boys Hostel', code='BOYS_HOSTEL', is_active=True)
        self.loc_admin_block = CampusLocation.objects.create(name='Admin Block', code='ADMIN_BLOCK', is_active=True)

        # Groups with structured campus locations
        self.tp_group = TechnicianGroup.objects.create(name='Tech Park Hardware Group', max_tickets_per_tech=10)
        self.tp_group.campus_locations.add(self.loc_tech_park)
        self.tp_group.technicians.add(self.tech_park_tech)

        self.hostel_group = TechnicianGroup.objects.create(name='Hostel Facilities Group', max_tickets_per_tech=10)
        self.hostel_group.campus_locations.add(self.loc_hostel)
        self.hostel_group.technicians.add(self.hostel_tech)

        self.category = Category.objects.create(name='Lab Hardware')

    def test_admin_locations_manager_access(self):
        # Normal user cannot access locations manager
        self.client.login(username='vlsi_student', password='Password123!')
        res_user = self.client.get(reverse('tickets:admin_locations'))
        self.assertEqual(res_user.status_code, 302)

        # Admin can access
        self.client.login(username='admin_loc', password='Password123!')
        res_admin = self.client.get(reverse('tickets:admin_locations'))
        self.assertEqual(res_admin.status_code, 200)
        self.assertContains(res_admin, 'Campus Locations & Blocks')
        self.assertContains(res_admin, 'Tech Park')
        self.assertContains(res_admin, 'Boys Hostel')

    def test_admin_can_create_and_edit_campus_location(self):
        self.client.login(username='admin_loc', password='Password123!')
        
        # Create new location
        create_res = self.client.post(reverse('tickets:admin_locations'), {
            'action': 'create',
            'name': 'Mechanical Workshop Block',
            'code': 'MECH_BLOCK',
            'description': 'CNC and welding labs',
            'is_active': 'on'
        })
        self.assertEqual(create_res.status_code, 302)
        new_loc = CampusLocation.objects.filter(code='MECH_BLOCK').first()
        self.assertIsNotNone(new_loc)
        self.assertEqual(new_loc.name, 'Mechanical Workshop Block')

        # Edit location
        edit_res = self.client.post(reverse('tickets:admin_locations'), {
            'action': 'edit',
            'location_id': new_loc.id,
            'name': 'Robotics & Mechanical Block',
            'code': 'ROBOTICS_MECH',
            'description': 'Upgraded robotics hub',
            'is_active': 'on'
        })
        self.assertEqual(edit_res.status_code, 302)
        new_loc.refresh_from_db()
        self.assertEqual(new_loc.name, 'Robotics & Mechanical Block')

        # Toggle active
        toggle_res = self.client.post(reverse('tickets:admin_locations'), {
            'action': 'toggle_active',
            'location_id': new_loc.id
        })
        self.assertEqual(toggle_res.status_code, 302)
        new_loc.refresh_from_db()
        self.assertFalse(new_loc.is_active)

    def test_ticket_creation_with_campus_location_and_details_routing(self):
        self.client.login(username='vlsi_student', password='Password123!')
        
        # User reports issue at Tech Park + VLSI Lab
        post_data = {
            'title': 'Oscilloscope probe not reading',
            'description': 'Probe channel 2 is faulty',
            'category': self.category.pk,
            'urgency': 'high',
            'campus_location': self.loc_tech_park.pk,
            'location_details': 'VLSI Lab - Workbench 3',
            'facing_issue_in': ['Network Issue'],
            'problem_description': 'Probe channel 2 is faulty',
        }
        res = self.client.post(reverse('tickets:create'), post_data)
        self.assertEqual(res.status_code, 302)

        ticket = Ticket.objects.filter(reporter=self.student, title='Oscilloscope probe not reading').first()
        self.assertIsNotNone(ticket)
        self.assertEqual(ticket.campus_location, self.loc_tech_park)
        self.assertEqual(ticket.location_details, 'VLSI Lab - Workbench 3')
        self.assertEqual(ticket.location, 'Tech Park - VLSI Lab - Workbench 3')

        # Verify routed directly to Tech Park Technician Group and Lead
        self.assertEqual(ticket.assigned_group, self.tp_group)
        self.assertEqual(ticket.assigned_technician, self.tech_park_tech)

    def test_ticket_creation_in_hostel_routes_to_hostel_group(self):
        ticket = Ticket.objects.create(
            title='Hostel LAN dead',
            description='Port dead in room',
            category=self.category,
            reporter=self.student,
            campus_location=self.loc_hostel,
            location_details='Room 205',
        )
        ticket.assign_to_technician()
        ticket.refresh_from_db()

        self.assertEqual(ticket.location, 'Boys Hostel - Room 205')
        self.assertEqual(ticket.assigned_group, self.hostel_group)
        self.assertEqual(ticket.assigned_technician, self.hostel_tech)

    def test_admin_edit_ticket_updates_campus_location(self):
        self.client.login(username='admin_loc', password='Password123!')
        ticket = Ticket.objects.create(
            title='Dean office printer jammed',
            description='Paper jam',
            category=self.category,
            reporter=self.student,
            location='Old Location',
        )

        res = self.client.post(reverse('tickets:edit', kwargs={'pk': ticket.pk}), {
            'title': 'Dean office printer jammed',
            'description': 'Paper jam',
            'category': self.category.pk,
            'urgency': 'critical',
            'campus_location': self.loc_admin_block.pk,
            'location_details': '1st Floor - Dean Chamber',
            'status': 'open',
        })
        self.assertEqual(res.status_code, 302)
        ticket.refresh_from_db()

        self.assertEqual(ticket.campus_location, self.loc_admin_block)
        self.assertEqual(ticket.location_details, '1st Floor - Dean Chamber')
        self.assertEqual(ticket.location, 'Admin Block - 1st Floor - Dean Chamber')










