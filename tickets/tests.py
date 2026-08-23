from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from accounts.models import UserProfile, UserRole, TechnicianGroup
from tickets.models import Category, Ticket, TicketStatus, TicketUrgency, TicketComment, TicketHistory


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

    def test_admin_ticket_edit_redirects_to_detail(self):
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
        # Accessing edit redirects to detail view
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






