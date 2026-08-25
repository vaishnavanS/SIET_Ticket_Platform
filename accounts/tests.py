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
        res = self.client.post(reverse('accounts:password_reset'), {'identity': 'unknown_person'})
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "No account found with this username or email address")

    def test_reset_suspended_account(self):
        res = self.client.post(reverse('accounts:password_reset'), {'identity': 'user_suspended'})
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Your account is currently suspended")

    def test_reset_no_email_account(self):
        res = self.client.post(reverse('accounts:password_reset'), {'identity': 'user_no_email'})
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "no email address is registered")

    def test_reset_unverified_email_account(self):
        res = self.client.post(reverse('accounts:password_reset'), {'identity': 'user_unverified'})
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "your email is not verified")

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
