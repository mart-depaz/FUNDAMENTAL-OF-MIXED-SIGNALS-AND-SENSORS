"""
Script to create a Django superuser account
Run this with: python manage.py shell
Then copy and paste the code below, or run: exec(open('create_superuser.py').read())
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'library_root.settings')
django.setup()

from accounts.models import CustomUser

print("=" * 60)
print("Create Django Superuser Account")
print("=" * 60)

# CHANGE THESE VALUES
USERNAME = 'ADMIN'  # Change to your preferred username
EMAIL = 'johnmartdepaz77@gmail.com'  # Change to your email
PASSWORD = 'admin123'  # Change to your preferred password

# Check if username already exists
if CustomUser.objects.filter(username=USERNAME).exists():
    print(f"\n⚠️  Username '{USERNAME}' already exists!")
    print("Updating existing user to be a superuser...")
    
    user = CustomUser.objects.get(username=USERNAME)
    user.is_superuser = True
    user.is_staff = True
    user.is_active = True
    user.email = EMAIL  # Update email if different
    user.set_password(PASSWORD)  # Reset password
    user.save()
    
    print(f"\n✅ User updated successfully!")
    print(f"   Username: {user.username}")
    print(f"   Email: {user.email}")
    print(f"   is_superuser: {user.is_superuser} ✓")
    print(f"   is_staff: {user.is_staff} ✓")
    print(f"   is_active: {user.is_active} ✓")
else:
    # Create new superuser
    user = CustomUser.objects.create_user(
        username=USERNAME,
        email=EMAIL,
        password=PASSWORD,
        is_superuser=True,
        is_staff=True,
        is_active=True
    )
    
    print(f"\n✅ Superuser created successfully!")
    print(f"   Username: {user.username}")
    print(f"   Email: {user.email}")
    print(f"   is_superuser: {user.is_superuser} ✓")
    print(f"   is_staff: {user.is_staff} ✓")

print(f"\n" + "=" * 60)
print(f"You can now log into Django admin at:")
print(f"   http://127.0.0.1:8000/admin/")
print(f"   Username: {user.username}")
print(f"   Password: {PASSWORD}")
print(f"=" * 60)

