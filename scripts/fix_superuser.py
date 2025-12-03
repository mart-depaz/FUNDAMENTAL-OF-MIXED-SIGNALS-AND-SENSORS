"""
Script to check and fix Django superuser account
Run this with: python manage.py shell < fix_superuser.py
Or: python -c "exec(open('fix_superuser.py').read())"
"""
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'library_root.settings')
django.setup()

from accounts.models import CustomUser

print("=" * 60)
print("Django Superuser Account Checker & Fixer")
print("=" * 60)

# Get all superusers
superusers = CustomUser.objects.filter(is_superuser=True)
print(f"\nFound {superusers.count()} superuser account(s):\n")

if superusers.count() == 0:
    print("❌ No superuser accounts found!")
    print("\nTo create a new superuser, run:")
    print("   python manage.py createsuperuser")
else:
    for user in superusers:
        print(f"Username: {user.username}")
        print(f"Email: {user.email}")
        print(f"Full Name: {user.full_name or 'N/A'}")
        print(f"is_superuser: {user.is_superuser} ✓")
        print(f"is_staff: {user.is_staff} {'✓' if user.is_staff else '❌ (NEEDS FIX)'}")
        print(f"is_active: {user.is_active} {'✓' if user.is_active else '❌ (NEEDS FIX)'}")
        print(f"is_admin (school): {user.is_admin}")
        
        # Check if needs fixing
        needs_fix = False
        if not user.is_staff:
            print("\n⚠️  FIXING: Setting is_staff=True...")
            user.is_staff = True
            needs_fix = True
        
        if not user.is_active:
            print("⚠️  FIXING: Setting is_active=True...")
            user.is_active = True
            needs_fix = True
        
        if needs_fix:
            user.save()
            print("✅ Fixed! This account can now log into Django admin.")
        else:
            print("\n✅ Account is properly configured!")
        
        print("-" * 60)

print("\n" + "=" * 60)
print("Done! Try logging into Django admin now.")
print("=" * 60)

