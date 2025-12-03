"""
Script to fix Django admin login for a specific user
Run this with: python manage.py shell
Then: exec(open('fix_admin_login.py').read())
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'library_root.settings')
django.setup()

from accounts.models import CustomUser

print("=" * 60)
print("Fix Django Admin Login")
print("=" * 60)

# CHANGE THIS TO YOUR USERNAME
USERNAME = 'ADMIN'  # Your username
NEW_PASSWORD = 'admin123'  # Your desired password

try:
    user = CustomUser.objects.get(username=USERNAME)
    
    print(f"\nFound user: {user.username}")
    print(f"Email: {user.email}")
    print(f"\nCurrent Status:")
    print(f"  is_superuser: {user.is_superuser}")
    print(f"  is_staff: {user.is_staff}")
    print(f"  is_active: {user.is_active}")
    
    # Fix all required flags
    print(f"\n🔧 Fixing account...")
    
    user.is_superuser = True
    user.is_staff = True
    user.is_active = True
    
    # Reset password
    user.set_password(NEW_PASSWORD)
    user.save()
    
    print(f"✅ Account fixed!")
    print(f"\nUpdated Status:")
    print(f"  is_superuser: {user.is_superuser} ✓")
    print(f"  is_staff: {user.is_staff} ✓")
    print(f"  is_active: {user.is_active} ✓")
    print(f"  Password: Reset to '{NEW_PASSWORD}'")
    
    print(f"\n" + "=" * 60)
    print(f"✅ You can now log in to Django admin:")
    print(f"   URL: http://127.0.0.1:8000/admin/")
    print(f"   Username: {user.username}")
    print(f"   Password: {NEW_PASSWORD}")
    print(f"=" * 60)
    
except CustomUser.DoesNotExist:
    print(f"\n❌ User '{USERNAME}' not found!")
    print("\nAvailable users:")
    for u in CustomUser.objects.all()[:10]:
        print(f"  - {u.username} (email: {u.email}, superuser: {u.is_superuser}, staff: {u.is_staff})")
    
    print(f"\n💡 To create a new superuser, run:")
    print(f"   python manage.py createsuperuser")
    print(f"   Or use the create_superuser.py script")

