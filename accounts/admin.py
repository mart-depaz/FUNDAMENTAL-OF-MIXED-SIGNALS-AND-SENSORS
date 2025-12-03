# accounts/admin.py
from django.contrib import admin
from .models import CustomUser
from django.urls import reverse
from django.utils.html import format_html
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.http import HttpResponseRedirect
import logging

logger = logging.getLogger(__name__)

@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    """
    Django Admin interface for managing all users.
    This is for Django superusers (system administrators) only.
    School admins use the custom admin portal at /admin-portal/
    """
    list_display = ['username', 'full_name', 'email', 'user_type', 'is_approved', 'is_staff', 'is_superuser', 'school_name', 'education_level', 'school_id', 'password_info', 'date_joined']
    list_editable = ['is_approved', 'is_staff']  # Allow editing is_approved and is_staff directly in the list view
    list_filter = ['is_admin', 'is_teacher', 'is_student', 'is_approved', 'is_staff', 'is_superuser', 'education_level', 'school_name']
    search_fields = ['username', 'full_name', 'email', 'school_id', 'school_name']
    actions = ['approve_teachers']
    ordering = ['-date_joined']
    
    def user_type(self, obj):
        """Display user type clearly"""
        types = []
        if obj.is_superuser:
            types.append('Django Admin')
        if obj.is_admin:
            types.append('School Admin')
        if obj.is_teacher:
            types.append('Teacher')
        if obj.is_student:
            types.append('Student')
        return ', '.join(types) if types else 'Regular User'
    user_type.short_description = 'User Type'
    
    def password_info(self, obj):
        """Show password status"""
        if obj.password:
            return format_html('<span style="color: green;">✓ Set</span> <a href="../{}/password/">(Change)</a>', obj.id)
        return format_html('<span style="color: red;">Not Set</span>')
    password_info.short_description = 'Password'
    
    fieldsets = (
        ('Account Information (ALL DATA VISIBLE)', {
            'fields': ('username', 'email', 'full_name', 'password'),
            'description': 'All account information including password (can be changed here).'
        }),
        ('Django Admin Status (ONLY FOR DJANGO SUPERUSER)', {
            'fields': ('is_superuser', 'is_staff', 'is_active'),
            'description': '⚠️ ONLY Django superuser (ADMIN) should have is_superuser=True and is_staff=True. School admins should have BOTH set to False.'
        }),
        ('School Admin Status (SEPARATE FROM DJANGO ADMIN)', {
            'fields': ('is_admin',),
            'description': 'School admins (is_admin=True) manage their school through /admin-portal/. They CANNOT access Django admin (/admin/). Only Django superuser can access Django admin.'
        }),
        ('User Roles', {
            'fields': ('is_teacher', 'is_student', 'is_approved'),
            'description': 'Regular users: teachers and students managed by school admins.'
        }),
        ('School Information', {
            'fields': ('school_name', 'school_id', 'education_level'),
            'description': 'School assignment for school admins, teachers, and students.'
        }),
        ('Permissions', {
            'fields': ('groups', 'user_permissions'),
            'classes': ('collapse',)
        }),
        ('Important Dates', {
            'fields': ('date_joined', 'last_login'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['date_joined', 'last_login']
    
    def get_readonly_fields(self, request, obj=None):
        """Make password field editable"""
        readonly = list(self.readonly_fields)
        if obj:  # Editing an existing object
            # Password can be changed
            return readonly
        return readonly

    def approve_link(self, obj):
        if obj.is_teacher and not obj.is_approved:
            return format_html('<a href="{}">Approve</a>', reverse('approve_teacher', args=[obj.id]))
        return "-"
    approve_link.short_description = "Approve Teacher"

    def approve_teachers(self, request, queryset):
        for user in queryset.filter(is_teacher=True, is_approved=False):
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
                self.message_user(request, f'Approved {user.full_name or user.username} and sent email.')
            except Exception as e:
                logger.error(f"Failed to send teacher approval email to {user.email}: {str(e)}")
                self.message_user(request, f'Approved {user.full_name or user.username}, but failed to send email: {str(e)}', level='warning')
    approve_teachers.short_description = "Approve selected teachers"
    

    def save_model(self, request, obj, form, change):
        old_approved = CustomUser.objects.get(id=obj.id).is_approved if change else False
        if change and 'is_approved' in form.changed_data and obj.is_teacher and not old_approved and obj.is_approved:
            try:
                html_message = None
                try:
                    html_message = render_to_string('accounts/email/teacher_approval.html', {
                        'username': obj.username,
                        'login_url': request.build_absolute_uri('/')
                    })
                    logger.debug(f"Rendered teacher approval HTML for {obj.email}: {html_message[:100]}...")
                except Exception as template_error:
                    logger.error(f"Failed to render teacher approval template for {obj.email}: {str(template_error)}")
                
                send_mail(
                    'Teacher Account Approved',
                    f'Dear {obj.full_name or obj.username},\n\nYour teacher account has been approved by the school admin. You can now log in at {request.build_absolute_uri("/")}.',
                    settings.DEFAULT_FROM_EMAIL,
                    [obj.email],
                    fail_silently=False,
                    html_message=html_message,
                )
                logger.info(f"Teacher approved and email sent to: {obj.email}")
                self.message_user(request, f'Approved {obj.full_name or obj.username} and sent email notification.')
            except Exception as e:
                logger.error(f"Failed to send teacher approval email to {obj.email}: {str(e)}")
                self.message_user(request, f'Approved {obj.full_name or obj.username}, but failed to send email: {str(e)}', level='warning')
        super().save_model(request, obj, form, change)

    def response_change(self, request, obj):
        if obj.is_teacher and 'is_approved' in request.POST and obj.is_approved:
            self.message_user(request, f'Teacher {obj.full_name or obj.username} has been approved. An email notification has been sent.')
            return HttpResponseRedirect(reverse('admin:accounts_customuser_changelist'))
        return super().response_change(request, obj)