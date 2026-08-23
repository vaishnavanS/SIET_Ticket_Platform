from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from accounts.models import UserProfile, UserRole

class Command(BaseCommand):
    help = 'Create an admin user'

    def add_arguments(self, parser):
        parser.add_argument('username', type=str, help='Username for admin account')
        parser.add_argument('email', type=str, help='Email for admin account')
        parser.add_argument('password', type=str, help='Password for admin account')

    def handle(self, *args, **options):
        username = options['username']
        email = options['email']
        password = options['password']
        
        # Check if user already exists
        if User.objects.filter(username=username).exists():
            self.stdout.write(self.style.WARNING(f'User {username} already exists'))
            return
        
        # Create user
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            is_staff=True,
            is_superuser=True
        )
        
        # Create profile
        profile = UserProfile.objects.get(user=user)
        profile.role = UserRole.ADMIN
        profile.is_active = True
        profile.save()
        
        self.stdout.write(self.style.SUCCESS(f'Admin user {username} created successfully'))
