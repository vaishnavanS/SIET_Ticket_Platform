from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.core import mail
from accounts.models import UserRole, TechnicianGroup

class AdminUserFilterTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_superuser(
            username='admin_boss',
            email='admin@siet.edu.in',
            password='Password123!'
        )
        self.admin.profile.role = UserRole.ADMIN
        self.admin.profile.save()

        self.tech1 = User.objects.create_user(
            username='tech_network',
            email='tech.net@siet.edu.in',
            password='Password123!'
        )
        self.tech1.profile.role = UserRole.TECHNICIAN
        self.tech1.profile.save()

        self.tech2 = User.objects.create_user(
            username='tech_hardware',
            email='tech.hw@siet.edu.in',
            password='Password123!'
        )
        self.tech2.profile.role = UserRole.TECHNICIAN
        self.tech2.profile.save()

        self.student = User.objects.create_user(
            username='student_rahul',
            email='rahul@siet.edu.in',
            password='Password123!'
        )
        self.student.profile.role = UserRole.NORMAL_USER
        self.student.profile.save()

        self.suspended_user = User.objects.create_user(
            username='suspended_bad',
            email='bad@siet.edu.in',
            password='Password123!'
        )
        self.suspended_user.profile.role = UserRole.NORMAL_USER
        self.suspended_user.profile.is_suspended = True
        self.suspended_user.profile.save()

        self.group = TechnicianGroup.objects.create(name='Network Team')
        self.group.technicians.add(self.tech1)

    def test_admin_users_view_permission(self):
        res = self.client.get(reverse('accounts:admin_users'))
        self.assertEqual(res.status_code, 302)

        self.client.login(username='student_rahul', password='Password123!')
        res2 = self.client.get(reverse('accounts:admin_users'))
        self.assertEqual(res2.status_code, 302)

        self.client.login(username='admin_boss', password='Password123!')
        res3 = self.client.get(reverse('accounts:admin_users'))
        self.assertEqual(res3.status_code, 200)

    def test_filter_by_technician_role(self):
        self.client.login(username='admin_boss', password='Password123!')
        res = self.client.get(reverse('accounts:admin_users') + '?role=technician')
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'tech_network')
        self.assertContains(res, 'tech_hardware')
        self.assertNotContains(res, 'student_rahul')
        self.assertNotContains(res, 'admin_boss')

    def test_filter_by_normal_user_role(self):
        self.client.login(username='admin_boss', password='Password123!')
        res = self.client.get(reverse('accounts:admin_users') + '?role=normal_user')
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'student_rahul')
        self.assertNotContains(res, 'tech_network')
        self.assertNotContains(res, 'tech_hardware')

    def test_filter_by_status_suspended(self):
        self.client.login(username='admin_boss', password='Password123!')
        res = self.client.get(reverse('accounts:admin_users') + '?status=suspended')
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'suspended_bad')
        self.assertNotContains(res, 'student_rahul')
        self.assertNotContains(res, 'tech_network')

    def test_search_query_by_username_or_email(self):
        self.client.login(username='admin_boss', password='Password123!')
        res = self.client.get(reverse('accounts:admin_users') + '?q=rahul')
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'student_rahul')
        self.assertNotContains(res, 'tech_network')

        res_email = self.client.get(reverse('accounts:admin_users') + '?q=tech.hw')
        self.assertEqual(res_email.status_code, 200)
        self.assertContains(res_email, 'tech_hardware')
        self.assertNotContains(res_email, 'tech_network')


class PasswordResetTests(TestCase):
    def setUp(self):
        self.client = Client()
        
        # Valid user with verified email
        self.valid_user = User.objects.create_user(
            username='user_verified',
            email='verified@siet.edu.in',
            password='OldPassword123!'
        )
        self.valid_user.profile.is_email_verified = True
        self.valid_user.profile.save()

        # User with unverified email
        self.unverified_user = User.objects.create_user(
            username='user_unverified',
            email='unverified@siet.edu.in',
            password='OldPassword123!'
        )
        self.unverified_user.profile.is_email_verified = False
        self.unverified_user.profile.save()

        # User with no email
        self.no_email_user = User.objects.create_user(
            username='user_no_email',
            email='',
            password='OldPassword123!'
        )
        self.no_email_user.profile.is_email_verified = False
        self.no_email_user.profile.save()

        # Suspended user
        self.suspended_user = User.objects.create_user(
            username='user_suspended',
            email='suspended@siet.edu.in',
            password='OldPassword123!'
        )
        self.suspended_user.profile.is_suspended = True
        self.suspended_user.profile.save()

    def test_reset_empty_input(self):
        res = self.client.post(reverse('accounts:password_reset'), {'identity': ''})
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Please enter your username or registered email address")

    def test_reset_non_existent_account(self):
        mail.outbox = []
        res = self.client.post(reverse('accounts:password_reset'), {'identity': 'unknown_person'}, follow=True)
        self.assertEqual(res.status_code, 200)
        self.assertTemplateUsed(res, 'accounts/password_reset_done.html')
        self.assertEqual(len(mail.outbox), 0)

    def test_reset_suspended_account(self):
        mail.outbox = []
        res = self.client.post(reverse('accounts:password_reset'), {'identity': 'user_suspended'}, follow=True)
        self.assertEqual(res.status_code, 200)
        self.assertTemplateUsed(res, 'accounts/password_reset_done.html')
        self.assertEqual(len(mail.outbox), 0)

    def test_reset_no_email_account(self):
        mail.outbox = []
        res = self.client.post(reverse('accounts:password_reset'), {'identity': 'user_no_email'}, follow=True)
        self.assertEqual(res.status_code, 200)
        self.assertTemplateUsed(res, 'accounts/password_reset_done.html')
        self.assertEqual(len(mail.outbox), 0)

    def test_reset_unverified_email_account(self):
        mail.outbox = []
        res = self.client.post(reverse('accounts:password_reset'), {'identity': 'user_unverified'}, follow=True)
        self.assertEqual(res.status_code, 200)
        self.assertTemplateUsed(res, 'accounts/password_reset_done.html')
        self.assertEqual(len(mail.outbox), 0)

    def test_reset_valid_username_success(self):
        mail.outbox = []
        res = self.client.post(reverse('accounts:password_reset'), {'identity': 'user_verified'}, follow=True)
        self.assertEqual(res.status_code, 200)
        self.assertTemplateUsed(res, 'accounts/password_reset_done.html')
        self.assertContains(res, "ve****ed@siet.edu.in")
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Password Reset Request', mail.outbox[0].subject)
        self.assertIn('user_verified', mail.outbox[0].body)
        self.assertEqual(mail.outbox[0].to, ['verified@siet.edu.in'])

    def test_reset_valid_email_success(self):
        mail.outbox = []
        res = self.client.post(reverse('accounts:password_reset'), {'identity': 'verified@siet.edu.in'}, follow=True)
        self.assertEqual(res.status_code, 200)
        self.assertTemplateUsed(res, 'accounts/password_reset_done.html')
        self.assertContains(res, "ve****ed@siet.edu.in")
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['verified@siet.edu.in'])

    def test_password_reset_confirm_redirects_to_login(self):
        from django.utils.http import urlsafe_base64_encode
        from django.utils.encoding import force_bytes
        from django.contrib.auth.tokens import default_token_generator
        
        uid = urlsafe_base64_encode(force_bytes(self.valid_user.pk))
        token = default_token_generator.make_token(self.valid_user)
        
        confirm_url = reverse('accounts:password_reset_confirm', kwargs={'uidb64': uid, 'token': token})
        
        # GET confirm page
        get_res = self.client.get(confirm_url, follow=True)
        self.assertEqual(get_res.status_code, 200)
        self.assertContains(get_res, "Set New Password")
        
        # POST valid new password to the active URL
        post_url = get_res.request['PATH_INFO']
        post_res = self.client.post(post_url, {
            'new_password1': 'BrandNewPass123!',
            'new_password2': 'BrandNewPass123!'
        }, follow=True)
        
        # Should redirect directly to login page
        self.assertEqual(post_res.status_code, 200)
        self.assertTemplateUsed(post_res, 'accounts/login.html')
        self.assertContains(post_res, "Your password has been successfully reset")
        
        # Verify user can log in with new password
        login_success = self.client.login(username='user_verified', password='BrandNewPass123!')
        self.assertTrue(login_success)


class AdminUserActionTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_superuser(
            username='admin_test',
            email='admin@siet.edu.in',
            password='Password123!'
        )
        self.admin.profile.role = UserRole.ADMIN
        self.admin.profile.save()

        self.clean_user = User.objects.create_user(
            username='clean_user',
            email='clean@siet.edu.in',
            password='Password123!'
        )

        self.protected_user = User.objects.create_user(
            username='protected_user',
            email='protected@siet.edu.in',
            password='Password123!'
        )

        from tickets.models import Category, Ticket, TicketComment, TicketHistory
        self.category = Category.objects.create(name='Hardware Test')
        self.ticket = Ticket.objects.create(
            title='Test Ticket',
            description='Test Desc',
            category=self.category,
            location='Lab 1',
            reporter=self.protected_user
        )
        self.comment = TicketComment.objects.create(
            ticket=self.ticket,
            author=self.protected_user,
            content='User comment'
        )
        self.history = TicketHistory.objects.create(
            ticket=self.ticket,
            changed_by=self.protected_user,
            field_name='status',
            old_value='Open',
            new_value='In Progress'
        )

    def test_delete_user_without_tickets_deletes_permanently(self):
        self.client.login(username='admin_test', password='Password123!')
        url = reverse('accounts:admin_user_action', kwargs={'user_id': self.clean_user.id, 'action': 'delete'})
        res = self.client.post(url, {'delete_mode': 'archive'}, follow=True)
        self.assertEqual(res.status_code, 200)
        self.assertFalse(User.objects.filter(id=self.clean_user.id).exists())
        self.assertContains(res, "was permanently deleted")

    def test_delete_user_with_tickets_archive_mode(self):
        self.client.login(username='admin_test', password='Password123!')
        url = reverse('accounts:admin_user_action', kwargs={'user_id': self.protected_user.id, 'action': 'delete'})
        res = self.client.post(url, {'delete_mode': 'archive'}, follow=True)
        self.assertEqual(res.status_code, 200)

        # User is permanently deleted from auth_user
        self.assertFalse(User.objects.filter(id=self.protected_user.id).exists())

        # Ticket and comment are preserved under system archive 'deleted_user'
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.reporter.username, 'deleted_user')
        self.comment.refresh_from_db()
        self.assertEqual(self.comment.author.username, 'deleted_user')
        self.history.refresh_from_db()
        self.assertEqual(self.history.changed_by.username, 'deleted_user')

        self.assertContains(res, "archived under")
        self.assertContains(res, "[Deleted User]")

    def test_delete_user_with_tickets_purge_mode(self):
        from tickets.models import Ticket, TicketComment, TicketHistory
        self.client.login(username='admin_test', password='Password123!')
        url = reverse('accounts:admin_user_action', kwargs={'user_id': self.protected_user.id, 'action': 'delete'})
        res = self.client.post(url, {'delete_mode': 'purge'}, follow=True)
        self.assertEqual(res.status_code, 200)

        # User and tickets are completely wiped
        self.assertFalse(User.objects.filter(id=self.protected_user.id).exists())
        self.assertFalse(Ticket.objects.filter(id=self.ticket.id).exists())
        self.assertFalse(TicketComment.objects.filter(id=self.comment.id).exists())
        self.assertFalse(TicketHistory.objects.filter(id=self.history.id).exists())
        self.assertContains(res, "permanently purged")

    def test_delete_technician_unassigns_tickets(self):
        from tickets.models import Ticket
        tech = User.objects.create_user(
            username='tech_to_delete',
            email='tech.del@siet.edu.in',
            password='Password123!'
        )
        tech.profile.role = UserRole.TECHNICIAN
        tech.profile.save()

        assigned_ticket = Ticket.objects.create(
            title='Assigned Tech Ticket',
            description='Testing technician deletion',
            category=self.category,
            location='Lab 2',
            reporter=self.clean_user,
            assigned_technician=tech
        )

        self.client.login(username='admin_test', password='Password123!')
        url = reverse('accounts:admin_user_action', kwargs={'user_id': tech.id, 'action': 'delete'})
        res = self.client.post(url, {'delete_mode': 'archive'}, follow=True)
        self.assertEqual(res.status_code, 200)

        # Technician deleted
        self.assertFalse(User.objects.filter(id=tech.id).exists())

        # Ticket still exists and assigned_technician is set to None
        assigned_ticket.refresh_from_db()
        self.assertIsNone(assigned_ticket.assigned_technician)

    def test_admin_cannot_delete_self(self):
        self.client.login(username='admin_test', password='Password123!')
        url = reverse('accounts:admin_user_action', kwargs={'user_id': self.admin.id, 'action': 'delete'})
        res = self.client.post(url, {'delete_mode': 'purge'}, follow=True)
        self.assertEqual(res.status_code, 200)
        self.assertTrue(User.objects.filter(id=self.admin.id).exists())
        self.assertContains(res, "cannot delete or modify your own active admin account")
