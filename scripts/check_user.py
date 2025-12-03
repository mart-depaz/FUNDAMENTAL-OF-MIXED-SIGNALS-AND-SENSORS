"""
Quick script to check a specific user's status
Usage: python manage.py shell
Then: exec(open('check_user.py').read())
Or modify the username below and run directly
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'library_root.settings')
django.setup()

from accounts.models import CustomUser

# CHANGE THIS TO YOUR USERNAME
USERNAME = 'ADMIN'  # Change this to your actual username

try:
    user = CustomUser.objects.get(username=USERNAME)
    print(f"\n{'='*60}")
    print(f"Account Status for: {user.username}")
    print(f"{'='*60}")
    print(f"Email: {user.email}")
    print(f"Full Name: {user.full_name or 'N/A'}")
    print(f"\nStatus Flags:")
    print(f"  is_superuser: {user.is_superuser} {'✓' if user.is_superuser else '❌'}")
    print(f"  is_staff: {user.is_staff} {'✓' if user.is_staff else '❌ (REQUIRED FOR DJANGO ADMIN)'}")
    print(f"  is_active: {user.is_active} {'✓' if user.is_active else '❌ (ACCOUNT INACTIVE)'}")
    print(f"  is_admin (school): {user.is_admin}")
    print(f"  is_teacher: {user.is_teacher}")
    print(f"  is_student: {user.is_student}")
    
    if not user.is_staff:
        print(f"\n⚠️  FIXING: Setting is_staff=True...")
        user.is_staff = True
        user.save()
        print("✅ Fixed! You can now log into Django admin.")
    
    if not user.is_active:
        print(f"\n⚠️  FIXING: Setting is_active=True...")
        user.is_active = True
        user.save()
        print("✅ Fixed! Account is now active.")
    
    if user.is_staff and user.is_active and user.is_superuser:
        print(f"\n✅ Account is ready! You can log into Django admin.")
        print(f"   URL: http://127.0.0.1:8000/admin/")
        print(f"   Username: {user.username}")
    
except CustomUser.DoesNotExist:
    print(f"\n❌ User '{USERNAME}' not found!")
    print("\nAvailable superusers:")
    for su in CustomUser.objects.filter(is_superuser=True):
        print(f"  - {su.username} ({su.email})")

