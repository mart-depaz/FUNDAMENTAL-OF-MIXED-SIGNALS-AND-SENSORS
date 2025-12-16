# accounts/views.py
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.core.mail import send_mail
from django.http import JsonResponse
from .forms import CustomUserCreationForm, LoginForm
from .models import CustomUser
from dashboard.models import AdminNotification
from django.conf import settings
from django.template.loader import render_to_string
import re
import random
import logging

logger = logging.getLogger(__name__)

def login_signup_view(request):
    if request.method == 'POST':
        if 'login-form' in request.POST:
            form = LoginForm(request.POST)
            if form.is_valid():
                email_or_id = form.cleaned_data['email_or_id']
                password = form.cleaned_data['password']
                selected_role = request.POST.get('selected_role', '').strip()

                if selected_role not in ['teacher', 'student']:
                    logger.error(f"Invalid role selected: {selected_role}")
                    return JsonResponse({'success': False, 'message': 'Please select a valid role (Teacher or Student).'})

                try:
                    if re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email_or_id):
                        user = CustomUser.objects.get(email=email_or_id.lower())
                    else:
                        user = CustomUser.objects.get(school_id=email_or_id)
                    logger.debug(f"User found: {user.username}, email={user.email}, school_id={user.school_id}")
                except CustomUser.DoesNotExist:
                    logger.error(f"Login failed: No user found for email_or_id={email_or_id}")
                    return JsonResponse({'success': False, 'message': 'Invalid email, ID, or password.'})

                # Try authenticating with temporary password first
                authenticated_user = authenticate(request, username=user.username, password=password)
                
                # If that fails, try custom password
                if not authenticated_user and user.check_custom_password(password):
                    authenticated_user = user
                    logger.info(f"User {user.username} authenticated using custom password")
                
                if not authenticated_user:
                    logger.error(f"Login failed: Invalid password for user={user.username}")
                    return JsonResponse({'success': False, 'message': 'Invalid email, ID, or password.'})

                if selected_role == 'student' and user.is_student:
                    # Clear any existing messages before login
                    storage = messages.get_messages(request)
                    list(storage)  # Consume all existing messages
                    login(request, authenticated_user)
                    logger.info(f"Successful student login: {user.username}")
                    messages.success(request, f'Welcome to Attendance system, {user.full_name or user.username}!')
                    redirect_url = '/dashboard/student-dashboard/'
                    if user.education_level == 'high_senior':
                        redirect_url = '/dashboard/high-school-dashboard/'
                    elif user.education_level == 'university_college':
                        redirect_url = '/dashboard/university-college-dashboard/'
                    return JsonResponse({'success': True, 'redirect': redirect_url, 'message': f'Welcome back, {user.full_name or user.username}!'})
                elif selected_role == 'teacher' and user.is_teacher:
                    if user.is_approved:
                        # Clear any existing messages before login
                        storage = messages.get_messages(request)
                        list(storage)  # Consume all existing messages
                        login(request, authenticated_user)
                        logger.info(f"Successful teacher login: {user.username}")
                        messages.success(request, f'Welcome to Attendance system, {user.full_name or user.username}!')
                        redirect_url = '/dashboard/teacher-dashboard/'
                        if user.education_level == 'high_senior':
                            redirect_url = '/dashboard/high-school-teacher-dashboard/'
                        elif user.education_level == 'university_college':
                            redirect_url = '/dashboard/university-college-teacher-dashboard/'
                        return JsonResponse({'success': True, 'redirect': redirect_url, 'message': f'Welcome back, {user.full_name or user.username}!'})
                    else:
                        logger.warning(f"Login failed: Teacher {user.username} not approved")
                        return JsonResponse({'success': False, 'message': 'Your teacher account is pending admin approval.'})
                else:
                    logger.error(f"Login failed: Role mismatch for user={user.username}, selected_role={selected_role}")
                    return JsonResponse({
                        'success': False,
                        'message': f'This account is registered as a {"student" if user.is_student else "teacher"}. Please select the correct role.'
                    })

            else:
                logger.error(f"Login form invalid: {form.errors}")
                return JsonResponse({
                    'success': False,
                    'message': form.errors.as_text()
                })

        elif 'signup-form' in request.POST or 'signup-form-student' in request.POST:
            form = CustomUserCreationForm(request.POST)
            if form.is_valid():
                email = form.cleaned_data['email'].lower()
                full_name = form.cleaned_data.get('full_name', '')  # Optional, defaults to empty string
                password1 = form.cleaned_data['password1']
                password2 = form.cleaned_data['password2']
                role = request.POST.get('role')
                education_level = form.cleaned_data['education_level']

                if password1 != password2:
                    logger.error(f"Signup failed: Passwords do not match for {full_name or 'unnamed user'}")
                    return JsonResponse({'success': False, 'message': 'Passwords do not match.'})

                try:
                    user = form.save()
                    selected_school = request.POST.get('school_name', '').strip()
                    
                    # Notify only the admin(s) of the selected school
                    if selected_school:
                        # Find admins with matching school name and education level
                        admins = CustomUser.objects.filter(
                            is_admin=True,
                            school_name=selected_school,
                            education_level=education_level
                        )
                    else:
                        # If no school selected, notify all admins (fallback)
                        admins = CustomUser.objects.filter(is_admin=True)
                    
                    notification_type = 'new_student_signup' if role == 'student' else 'new_teacher_signup'
                    title = f"New {'Student' if role == 'student' else 'Teacher'} Signup"
                    school_text = f" from {selected_school}" if selected_school else ""
                    
                    # Different messages for students (auto-approved) vs teachers (needs approval)
                    if role == 'student':
                        message = f"{user.full_name or user.username} ({user.email}){school_text} has signed up and is now active."
                    else:
                        message = f"{user.full_name or user.username} ({user.email}){school_text} has signed up and is awaiting approval."
                    
                    for admin in admins:
                        AdminNotification.objects.create(
                            admin=admin,
                            notification_type=notification_type,
                            title=title,
                            message=message,
                            related_user=user
                        )
                    
                    if role == 'student':
                        # Students are auto-approved (already set in form.save())
                        # Automatically log in the student
                        authenticated_user = authenticate(request, username=user.username, password=password1)
                        if authenticated_user:
                            login(request, authenticated_user)
                            logger.info(f"Student signup completed and auto-logged in: {user.username}")
                            
                            # Determine redirect URL based on education level
                            redirect_url = '/dashboard/student-dashboard/'
                            if user.education_level == 'high_senior':
                                redirect_url = '/dashboard/high-school-dashboard/'
                            elif user.education_level == 'university_college':
                                redirect_url = '/dashboard/university-college-dashboard/'
                            
                            return JsonResponse({
                                'success': True,
                                'message': f'Your student account has been created successfully! Redirecting to dashboard...',
                                'redirect': redirect_url
                            })
                        else:
                            # If authentication fails, still return success but without redirect
                            logger.warning(f"Student signup completed but auto-login failed: {user.username}")
                            return JsonResponse({
                                'success': True,
                                'message': f'Your student account has been created successfully! Please log in.'
                            })
                    else:
                        logger.info(f"Teacher signup submitted: {user.username}")
                        return JsonResponse({
                            'success': True,
                            'message': f'Your teacher account request has been submitted. Await admin approval.'
                        })
                except Exception as e:
                    logger.error(f"Signup failed: {str(e)}")
                    return JsonResponse({'success': False, 'message': str(e)})
            else:
                logger.error(f"Signup form invalid: {form.errors}")
                return JsonResponse({'success': False, 'message': form.errors.as_text()})

        elif 'verify-form' in request.POST:
            email = request.POST.get('verify-email').lower()
            if re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email):
                try:
                    user = CustomUser.objects.get(email=email)
                    logger.info(f"User found for password reset: {user.username}, email={user.email}")
                    verification_code = ''.join([str(random.randint(0, 9)) for _ in range(6)])
                    request.session['reset_user_id'] = user.id
                    request.session['verification_code'] = verification_code
                    request.session['verified_email'] = email
                    try:
                        html_message = None
                        try:
                            html_message = render_to_string('accounts/email/verification_code.html', {'verification_code': verification_code})
                        except Exception as template_error:
                            logger.warning(f"Failed to render verification code template: {str(template_error)}. Using plain text.")
                        
                        send_mail(
                            'Password Reset Verification Code',
                            f'Your verification code is: {verification_code}\n\nThis code is valid for 10 minutes. Please do not share it with anyone.',
                            settings.DEFAULT_FROM_EMAIL,
                            [email],
                            fail_silently=False,
                            html_message=html_message,
                        )
                        logger.info(f"Verification code sent to {email}")
                        return JsonResponse({
                            'success': True,
                            'message': f'Verification code sent to {email}. Please check your inbox (and spam/junk folder).',
                            'email': email,
                            'step': 2
                        })
                    except Exception as e:
                        logger.error(f"Email sending failed for {email}: {str(e)}")
                        error_msg = str(e)
                        # Provide more helpful error messages
                        if 'BadCredentials' in error_msg or 'Username and Password not accepted' in error_msg or 'authentication failed' in error_msg.lower():
                            error_msg = 'Email server authentication failed. Please contact the administrator to configure email settings. The email password may need to be updated.'
                        elif 'Connection refused' in error_msg or 'timeout' in error_msg.lower():
                            error_msg = 'Unable to connect to email server. Please check your internet connection and try again.'
                        elif '535' in error_msg or '5.7.0' in error_msg:
                            error_msg = 'Email authentication failed. Please ensure the email password (App Password for Gmail) is correct and up to date.'
                        return JsonResponse({
                            'success': False,
                            'message': f'Failed to send verification code: {error_msg}. Please try again or contact support.'
                        })
                except CustomUser.DoesNotExist:
                    logger.error(f"Password reset failed: No user found for email={email}")
                    return JsonResponse({'success': False, 'message': 'Account not found. Please ensure your email is correct.'})
            else:
                logger.error(f"Invalid email format: {email}")
                return JsonResponse({'success': False, 'message': 'Use a valid email (e.g., user@example.com).'})

        elif 'code-verification-form' in request.POST:
            user_id = request.session.get('reset_user_id')
            if user_id:
                input_code = request.POST.get('verification-code')
                stored_code = request.session.get('verification_code')
                if input_code == stored_code:
                    logger.info(f"Code verified for user_id={user_id}")
                    return JsonResponse({
                        'success': True,
                        'message': 'Code verified. Please set your new password.',
                        'step': 3,
                        'email': request.session.get('verified_email')
                    })
                else:
                    logger.error(f"Code verification failed: input_code={input_code}, stored_code={stored_code}")
                    return JsonResponse({
                        'success': False,
                        'message': 'Incorrect code. Please check your email and try again.',
                        'step': 2,
                        'email': request.session.get('verified_email')
                    })
            else:
                logger.error("Code verification failed: Session expired")
                return JsonResponse({'success': False, 'message': 'Session expired. Please start the reset process again.'})

        elif 'reset-password-form' in request.POST:
            user_id = request.session.get('reset_user_id')
            if user_id:
                try:
                    user = CustomUser.objects.get(id=user_id)
                    new_password = request.POST.get('new-password')
                    confirm_password = request.POST.get('confirm-new-password')
                    if new_password and confirm_password and new_password == confirm_password:
                        if len(new_password) >= 6:
                            # Set custom password (user's personal password)
                            user.set_custom_password(new_password)
                            # Clear OTP after successful reset
                            user.otp_code = None
                            user.otp_expires_at = None
                            user.save()
                            del request.session['reset_user_id']
                            del request.session['verification_code']
                            del request.session['verified_email']
                            logger.info(f"Custom password reset successful for user={user.username}")
                            return JsonResponse({
                                'success': True,
                                'message': 'Your password has been successfully reset! You can now log in with your new password.'
                            })
                        else:
                            logger.error(f"Password reset failed: Password too short for user={user.username}")
                            return JsonResponse({
                                'success': False,
                                'message': 'Password must be at least 6 characters long.',
                                'step': 3,
                                'email': request.session.get('verified_email')
                            })
                    else:
                        logger.error(f"Password reset failed: Passwords do not match for user={user.username}")
                        return JsonResponse({
                            'success': False,
                            'message': 'Passwords do not match. Please re-enter.',
                            'step': 3,
                            'email': request.session.get('verified_email')
                        })
                except CustomUser.DoesNotExist:
                    logger.error(f"Password reset failed: No user found for user_id={user_id}")
                    return JsonResponse({'success': False, 'message': 'Session expired. Please start the reset process again.'})
            else:
                logger.error("Password reset failed: Session expired")
                return JsonResponse({'success': False, 'message': 'Session expired. Please start the reset process again.'})

        elif 'resend_code' in request.POST:
            email = request.POST.get('verify-email').lower()
            if email and re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email):
                try:
                    user = CustomUser.objects.get(email=email)
                    logger.info(f"User found for resend code: {user.username}, email={user.email}")
                    verification_code = ''.join([str(random.randint(0, 9)) for _ in range(6)])
                    request.session['reset_user_id'] = user.id
                    request.session['verification_code'] = verification_code
                    request.session['verified_email'] = email
                    try:
                        html_message = None
                        try:
                            html_message = render_to_string('accounts/email/verification_code.html', {'verification_code': verification_code})
                        except Exception as template_error:
                            logger.warning(f"Failed to render verification code template: {str(template_error)}. Using plain text.")
                        
                        send_mail(
                            'Password Reset Verification Code',
                            f'Your verification code is: {verification_code}\n\nThis code is valid for 10 minutes. Please do not share it with anyone.',
                            settings.DEFAULT_FROM_EMAIL,
                            [email],
                            fail_silently=False,
                            html_message=html_message,
                        )
                        logger.info(f"Verification code resent to {email}")
                        return JsonResponse({
                            'success': True,
                            'message': f'Code resent to {email}. Please check your inbox (and spam/junk folder).',
                            'email': email
                        })
                    except Exception as e:
                        logger.error(f"Resend code failed for {email}: {str(e)}")
                        return JsonResponse({
                            'success': False,
                            'message': f'Failed to resend code: {str(e)}. Please try again or contact support.'
                        })
                except CustomUser.DoesNotExist:
                    logger.error(f"Resend code failed: No user found for email={email}")
                    return JsonResponse({'success': False, 'message': 'Account not found. Please ensure your email is correct.'})
            else:
                logger.error(f"Invalid email format for resend: {email}")
                return JsonResponse({'success': False, 'message': 'Use a valid email (e.g., user@example.com).'})

    return render(request, 'accounts/login_signup.html', {'messages': messages.get_messages(request)})

def get_schools_by_education_level(request):
    """API endpoint to get schools filtered by education level"""
    education_level = request.GET.get('education_level', '')
    
    if not education_level:
        return JsonResponse({'success': False, 'message': 'Education level is required.'})
    
    # Get unique school names from admins with matching education level
    schools = CustomUser.objects.filter(
        is_admin=True,
        education_level=education_level,
        school_name__isnull=False
    ).exclude(school_name='').values_list('school_name', flat=True).distinct().order_by('school_name')
    
    school_list = [{'name': school} for school in schools]
    
    return JsonResponse({'success': True, 'schools': school_list})

def get_programs_by_school(request):
    """API endpoint to get programs filtered by school and education level"""
    from dashboard.models import Program
    
    school_name = request.GET.get('school_name', '')
    education_level = request.GET.get('education_level', '')
    
    if not school_name or not education_level:
        return JsonResponse({'success': False, 'message': 'School name and education level are required.'})
    
    # Get programs for the selected school and education level
    programs = Program.objects.filter(
        school_name=school_name,
        education_level=education_level,
        is_active=True
    ).order_by('code')
    
    program_list = [{'id': program.id, 'code': program.code, 'name': program.name, 'department': program.department} for program in programs]
    
    return JsonResponse({'success': True, 'programs': program_list})

def reset_password_view(request):
    if request.method == 'POST':
        user_id = request.session.get('reset_user_id')
        if user_id:
            try:
                user = CustomUser.objects.get(id=user_id)
                new_password = request.POST.get('new-password')
                confirm_password = request.POST.get('confirm-new-password')
                if new_password and confirm_password and new_password == confirm_password:
                    if len(new_password) >= 6:
                        # Set custom password (user's personal password)
                        user.set_custom_password(new_password)
                        # Clear OTP after successful reset
                        user.otp_code = None
                        user.otp_expires_at = None
                        user.save()
                        del request.session['reset_user_id']
                        del request.session['verification_code']
                        del request.session['verified_email']
                        logger.info(f"Custom password reset successful for user={user.username}")
                        return JsonResponse({
                            'success': True,
                            'message': 'Your password has been successfully reset! You can now log in with your new password.'
                        })
                    else:
                        logger.error(f"Password reset failed: Password too short for user={user.username}")
                        return JsonResponse({
                            'success': False,
                            'message': 'Password must be at least 6 characters long.'
                        })
                else:
                    logger.error(f"Password reset failed: Passwords do not match for user={user.username}")
                    return JsonResponse({'success': False, 'message': 'Passwords do not match. Please re-enter.'})
            except CustomUser.DoesNotExist:
                logger.error(f"Password reset failed: No user found for user_id={user_id}")
                return JsonResponse({'success': False, 'message': 'Session expired. Please start the reset process again.'})
        else:
            logger.error("Password reset failed: Session expired")
            return JsonResponse({'success': False, 'message': 'Session expired. Please start the reset process again.'})
    elif request.session.get('reset_user_id'):
        return render(request, 'accounts/reset_password.html')
    else:
        logger.error("Password reset failed: Invalid session")
        messages.error(request, 'Invalid session. Please verify your email or ID first.')
        return redirect('login_signup')

def approve_teacher(request, user_id):
    if request.user.is_superuser:
        try:
            user = CustomUser.objects.get(id=user_id)
            if not user.is_teacher:
                logger.error(f"Teacher approval failed: User {user.username} is not a teacher")
                messages.error(request, f'{user.full_name or user.username} is not a teacher account.')
                return redirect('admin:accounts_customuser_changelist')
            if user.is_approved:
                logger.warning(f"Teacher approval skipped: User {user.username} is already approved")
                messages.warning(request, f'{user.full_name or user.username} is already approved.')
                return redirect('admin:accounts_customuser_changelist')
            
            user.is_approved = True
            user.save()
            try:
                html_message = None
                try:
                    html_message = render_to_string('accounts/email/teacher_approval.html', {
                        'username': user.username,
                        'login_url': request.build_absolute_uri('/')
                    })
                    logger.debug(f"Rendered teacher approval HTML for {user.email}: {html_message[:100]}...")
                except Exception as template_error:
                    logger.error(f"Failed to render teacher approval template for {user.email}: {str(template_error)}")
                
                send_mail(
                    'Teacher Account Approved',
                    f'Dear {user.full_name or user.username},\n\nYour teacher account has been approved by the school admin. You can now log in at {request.build_absolute_uri("/")}.',
                    settings.DEFAULT_FROM_EMAIL,
                    [user.email],
                    fail_silently=False,
                    html_message=html_message,
                )
                logger.info(f"Teacher approved and email sent to: {user.email}")
                messages.success(request, f'Approved {user.full_name or user.username} and sent email notification.')
            except Exception as e:
                logger.error(f"Failed to send teacher approval email to {user.email}: {str(e)}")
                messages.warning(request, f'Approved {user.full_name or user.username}, but failed to send email: {str(e)}.')
            
            login(request, user)
            redirect_url = '/dashboard/teacher-dashboard/'
            if user.education_level == 'high_senior':
                redirect_url = '/dashboard/high-school-teacher-dashboard/'
            elif user.education_level == 'university_college':
                redirect_url = '/dashboard/university-college-teacher-dashboard/'
            return redirect(redirect_url)
        except CustomUser.DoesNotExist:
            logger.error(f"Teacher approval failed: No user found for user_id={user_id}")
            messages.error(request, 'User not found.')
            return redirect('admin:accounts_customuser_changelist')
    else:
        logger.error(f"Teacher approval failed: User {request.user.username} is not superuser")
        messages.error(request, 'Only superusers can approve teachers.')
        return redirect('admin:accounts_customuser_changelist')

def logout_view(request):
    """Logout view - redirects to appropriate login page based on user type"""
    # Check user type BEFORE logging out (after logout, user won't be accessible)
    user = request.user
    is_admin = False
    username = 'User'
    if user.is_authenticated:
        is_admin = (user.is_admin or user.is_superuser)
        username = user.full_name or user.username
    
    # Clear any existing messages before logout
    storage = messages.get_messages(request)
    list(storage)  # Consume all existing messages
    logout(request)
    # Set logout message after logout
    messages.success(request, f'Come again, {username}! You have been successfully logged out.')
    
    # Redirect admin to admin login, others to regular login
    if is_admin:
        return redirect('admin_login_signup')
    else:
        return redirect('login_signup')