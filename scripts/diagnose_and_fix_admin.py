"""
Comprehensive script to diagnose and fix Django admin login issues
Run this with: python manage.py shell
Then: exec(open('diagnose_and_fix_admin.py').read())
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'library_root.settings')
django.setup()

from accounts.models import CustomUser
from django.contrib.auth import authenticate

print("=" * 70)
print("Django Admin Login Diagnostic & Fix Tool")
print("=" * 70)

# Try different username variations
USERNAME_VARIANTS = ['ADMIN', 'admin', 'Admin']
PASSWORD = 'admin123'

print("\n🔍 Searching for user account...")
print("-" * 70)

user = None
found_username = None

# Try to find the user
for username_variant in USERNAME_VARIANTS:
    try:
        user = CustomUser.objects.get(username=username_variant)
        found_username = username_variant
        print(f"✅ Found user with username: '{username_variant}'")
        break
    except CustomUser.DoesNotExist:
        print(f"❌ User '{username_variant}' not found")
        continue

if not user:
    print("\n❌ Could not find user with any of these usernames:", USERNAME_VARIANTS)
    print("\nAvailable users in database:")
    for u in CustomUser.objects.all()[:10]:
        print(f"  - Username: '{u.username}' | Email: {u.email} | Superuser: {u.is_superuser} | Staff: {u.is_staff}")
    exit()

print(f"\n📋 Account Details:")
print(f"   Username: '{user.username}'")
print(f"   Email: {user.email}")
print(f"   Full Name: {user.full_name or 'N/A'}")

print(f"\n📊 Current Status:")
print(f"   is_superuser: {user.is_superuser} {'✓' if user.is_superuser else '❌ NEEDS FIX'}")
print(f"   is_staff: {user.is_staff} {'✓' if user.is_staff else '❌ NEEDS FIX (REQUIRED!)'}")
print(f"   is_active: {user.is_active} {'✓' if user.is_active else '❌ NEEDS FIX'}")
print(f"   is_admin (school): {user.is_admin}")

# Test password authentication
print(f"\n🔐 Testing Password Authentication...")
print(f"   Testing password: '{PASSWORD}'")
authenticated = authenticate(username=user.username, password=PASSWORD)
if authenticated:
    print(f"   ✅ Password is CORRECT!")
else:
    print(f"   ❌ Password is INCORRECT or not set properly!")

# Fix all issues
print(f"\n🔧 Fixing Account...")
print("-" * 70)

needs_fix = False

if not user.is_superuser:
    print("   Setting is_superuser = True")
    user.is_superuser = True
    needs_fix = True

if not user.is_staff:
    print("   Setting is_staff = True (REQUIRED for Django admin!)")
    user.is_staff = True
    needs_fix = True

if not user.is_active:
    print("   Setting is_active = True")
    user.is_active = True
    needs_fix = True

# Always reset password to ensure it's correct
print(f"   Resetting password to '{PASSWORD}'")
user.set_password(PASSWORD)
needs_fix = True

if needs_fix:
    user.save()
    print(f"\n✅ Account fixed and saved!")
else:
    print(f"\n✅ Account was already correct!")

# Verify the fix
print(f"\n📊 Updated Status:")
print(f"   is_superuser: {user.is_superuser} ✓")
print(f"   is_staff: {user.is_staff} ✓")
print(f"   is_active: {user.is_active} ✓")

# Test authentication again
print(f"\n🔐 Testing Authentication Again...")
authenticated = authenticate(username=user.username, password=PASSWORD)
if authenticated:
    print(f"   ✅ Authentication SUCCESSFUL!")
    print(f"   ✅ All checks passed!")
else:
    print(f"   ❌ Authentication still failing - there may be a deeper issue")

print(f"\n" + "=" * 70)
print(f"📝 LOGIN INFORMATION:")
print(f"=" * 70)
print(f"   URL: http://127.0.0.1:8000/admin/")
print(f"   Username: '{user.username}' (EXACT CASE - copy this exactly)")
print(f"   Password: '{PASSWORD}'")
print(f"=" * 70)

print(f"\n💡 IMPORTANT NOTES:")
print(f"   1. Username is CASE-SENSITIVE: Use exactly '{user.username}'")
print(f"   2. Make sure there are no extra spaces before/after the username")
print(f"   3. Try clearing your browser cache/cookies if it still doesn't work")
print(f"   4. Make sure you're going to: http://127.0.0.1:8000/admin/ (not /admin-portal/)")
print(f"=" * 70)

