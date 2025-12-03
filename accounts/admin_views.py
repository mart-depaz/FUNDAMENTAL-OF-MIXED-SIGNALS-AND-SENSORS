# accounts/admin_views.py
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from .models import CustomUser
import re
import random
import logging

logger = logging.getLogger(__name__)

def admin_login_signup_view(request):
    """
    School admin login and signup view.
    This is completely separate from Django admin.
    Django superusers can also use this to create school admin accounts.
    """
    # If already logged in as school admin, redirect to their dashboard
    if request.user.is_authenticated and request.user.is_admin:
        return redirect('dashboard:admin_dashboard')
    
    # Django superusers can access this page to create school admin accounts
    # No need to block them - the systems are independent
    
    if request.method == 'POST':
        if 'admin-login-form' in request.POST:
            email_or_id = request.POST.get('email_or_id', '').strip()
            password = request.POST.get('password', '').strip()

            if not email_or_id or not password:
                return JsonResponse({'success': False, 'message': 'Please fill in all fields.'})

            try:
                if re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email_or_id):
                    user = CustomUser.objects.get(email=email_or_id.lower())
                else:
                    user = CustomUser.objects.get(school_id=email_or_id)
                
                if not user.is_admin:
                    return JsonResponse({'success': False, 'message': 'This account is not an admin account.'})
                
                authenticated_user = authenticate(request, username=user.username, password=password)
                
                # If that fails, try custom password
                if not authenticated_user and user.check_custom_password(password):
                    authenticated_user = user
                    logger.info(f"Admin {user.username} authenticated using custom password")
                
                if not authenticated_user:
                    return JsonResponse({'success': False, 'message': 'Invalid email, ID, or password.'})
                
                if authenticated_user.is_admin:
                    # Clear any existing messages before login
                    from django.contrib import messages
                    storage = messages.get_messages(request)
                    list(storage)  # Consume all existing messages
                    login(request, authenticated_user)
                    logger.info(f"Successful admin login: {user.username}")
                    messages.success(request, f'Welcome back, {user.username}!')
                    return JsonResponse({'success': True, 'redirect': '/dashboard/admin-dashboard/', 'message': f'Welcome back, {user.username}!'})
                else:
                    return JsonResponse({'success': False, 'message': 'This account is not an admin account.'})
                    
            except CustomUser.DoesNotExist:
                return JsonResponse({'success': False, 'message': 'Invalid email, ID, or password.'})

        elif 'admin-signup-form' in request.POST:
            email = request.POST.get('email', '').strip().lower()
            school_name = request.POST.get('school_name', '').strip()
            education_level = request.POST.get('education_level', 'university_college').strip()  # Default to university_college
            admin_id = request.POST.get('admin_id', '').strip()
            password1 = request.POST.get('password1', '').strip()
            password2 = request.POST.get('password2', '').strip()

            if not all([email, school_name, admin_id, password1, password2]):
                return JsonResponse({'success': False, 'message': 'Please fill in all fields.'})

            if password1 != password2:
                return JsonResponse({'success': False, 'message': 'Passwords do not match.'})

            if len(password1) < 6:
                return JsonResponse({'success': False, 'message': 'Password must be at least 6 characters.'})

            if CustomUser.objects.filter(email=email).exists():
                return JsonResponse({'success': False, 'message': 'This email is already registered.'})

            if CustomUser.objects.filter(school_id=admin_id).exists():
                return JsonResponse({'success': False, 'message': 'This admin ID is already registered.'})

            try:
                # Generate username from email or admin_id
                base_username = email.split('@')[0] if '@' in email else admin_id.lower()
                username = base_username
                counter = 1
                while CustomUser.objects.filter(username=username).exists():
                    username = f"{base_username}_{counter}"
                    counter += 1

                user = CustomUser.objects.create_user(
                    username=username,
                    email=email,
                    password=password1,
                    full_name='',  # No full name for school admins
                    school_name=school_name,
                    education_level=education_level,
                    school_id=admin_id,
                    is_admin=True,  # School admin - separate from Django admin
                    is_teacher=False,
                    is_student=False,
                    is_approved=True,
                    is_staff=False,  # School admins should NOT access Django admin
                    is_superuser=False  # Only Django superuser (ADMIN) has this
                )
                
                # Store password in plain text for display (similar to temporary password)
                try:
                    from dashboard.models import UserTemporaryPassword
                    UserTemporaryPassword.objects.update_or_create(
                        user=user,
                        defaults={'password': password1, 'is_used': False}
                    )
                except Exception as e:
                    logger.error(f"Failed to store admin password: {str(e)}")
                
                # Clear any existing messages before login
                from django.contrib import messages
                storage = messages.get_messages(request)
                list(storage)  # Consume all existing messages
                login(request, user)
                logger.info(f"Successful admin signup and login: {user.username}")
                messages.success(request, f'Welcome, {user.username}! Your admin account has been created successfully.')
                return JsonResponse({
                    'success': True,
                    'message': f'Welcome, {user.username}! Your admin account has been created successfully.',
                    'redirect': '/dashboard/admin-dashboard/'
                })
            except Exception as e:
                logger.error(f"Admin signup failed: {str(e)}")
                return JsonResponse({'success': False, 'message': f'Error creating account: {str(e)}'})

    return render(request, 'accounts/admin_login_signup.html')

@login_required
def admin_logout_view(request):
    """Admin logout view"""
    if request.user.is_admin:
        username = request.user.username
        # Clear any existing messages before logout
        storage = messages.get_messages(request)
        list(storage)  # Consume all existing messages
        logout(request)
        # Set logout message after logout
        messages.success(request, f'Goodbye, {username}! You have been successfully logged out.')
    return redirect('admin_login_signup')

