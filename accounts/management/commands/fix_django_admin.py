"""
Django management command to fix Django admin login
Usage: python manage.py fix_django_admin ADMIN admin123
"""
from django.core.management.base import BaseCommand
from accounts.models import CustomUser
from django.contrib.auth import authenticate


class Command(BaseCommand):
    help = 'Fix Django admin login for a user account'

    def add_arguments(self, parser):
        parser.add_argument('username', type=str, help='Username to fix')
        parser.add_argument('password', type=str, help='Password to set')

    def handle(self, *args, **options):
        username = options['username']
        password = options['password']
        
        self.stdout.write("=" * 70)
        self.stdout.write(self.style.SUCCESS("Fixing Django Admin Login"))
        self.stdout.write("=" * 70)
        
        try:
            # Try to find user (case-insensitive search)
            user = None
            for u in CustomUser.objects.all():
                if u.username.lower() == username.lower():
                    user = u
                    break
            
            if not user:
                self.stdout.write(self.style.ERROR(f"\n[ERROR] User '{username}' not found!"))
                self.stdout.write("\nAvailable users:")
                for u in CustomUser.objects.all()[:10]:
                    self.stdout.write(f"  - {u.username}")
                return
            
            self.stdout.write(f"\n[SUCCESS] Found user: {user.username}")
            self.stdout.write(f"   Email: {user.email}")
            
            # Show current status
            self.stdout.write(f"\n[STATUS] Current Status:")
            self.stdout.write(f"   is_superuser: {user.is_superuser}")
            self.stdout.write(f"   is_staff: {user.is_staff}")
            self.stdout.write(f"   is_active: {user.is_active}")
            
            # Fix everything
            self.stdout.write(f"\n[FIX] Fixing account...")
            user.is_superuser = True
            user.is_staff = True
            user.is_active = True
            user.set_password(password)
            user.save()
            
            self.stdout.write(self.style.SUCCESS("   [OK] is_superuser = True"))
            self.stdout.write(self.style.SUCCESS("   [OK] is_staff = True"))
            self.stdout.write(self.style.SUCCESS("   [OK] is_active = True"))
            self.stdout.write(self.style.SUCCESS(f"   [OK] Password reset to: {password}"))
            
            # Test authentication
            self.stdout.write(f"\n[TEST] Testing authentication...")
            auth_user = authenticate(username=user.username, password=password)
            if auth_user:
                self.stdout.write(self.style.SUCCESS("   [SUCCESS] Authentication successful!"))
            else:
                self.stdout.write(self.style.ERROR("   [ERROR] Authentication failed - trying with exact username..."))
                # Try with exact username
                auth_user = authenticate(username=user.username, password=password)
                if auth_user:
                    self.stdout.write(self.style.SUCCESS("   [SUCCESS] Authentication works with exact username!"))
            
            self.stdout.write("\n" + "=" * 70)
            self.stdout.write(self.style.SUCCESS("[SUCCESS] ACCOUNT FIXED!"))
            self.stdout.write("=" * 70)
            self.stdout.write(f"\n[INFO] Login Information:")
            self.stdout.write(f"   URL: http://127.0.0.1:8000/admin/")
            self.stdout.write(self.style.WARNING(f"   Username: '{user.username}' (EXACT CASE - copy this!)"))
            self.stdout.write(f"   Password: {password}")
            self.stdout.write("=" * 70)
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"\n[ERROR] Error: {str(e)}"))

