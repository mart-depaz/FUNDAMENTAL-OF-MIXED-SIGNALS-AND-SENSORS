# accounts/models.py
from django.contrib.auth.models import AbstractUser
from django.db import models

class CustomUser(AbstractUser):
    is_teacher = models.BooleanField(default=False)
    is_student = models.BooleanField(default=False)
    is_admin = models.BooleanField(default=False)  # For admin accounts
    is_approved = models.BooleanField(default=False)  # For teacher approval
    email = models.EmailField(unique=True)  # Ensure email is unique
    school_id = models.CharField(max_length=10, unique=True, blank=True, null=True)  # Unique ID for all users
    full_name = models.CharField(max_length=90, blank=True, null=True)  # Optional full name (e.g., John, Michael, or John Michael Doe)
    school_name = models.CharField(max_length=200, blank=True, null=True)  # School name to separate different schools
    education_level = models.CharField(
        max_length=20,
        choices=[
            ('high_senior', 'High/Senior High'),
            ('university_college', 'University/College')
        ],
        blank=True,
        null=True
    )
    # Program field - will be set after migration
    program = models.ForeignKey('dashboard.Program', on_delete=models.SET_NULL, null=True, blank=True, related_name='users', help_text="Program/Major for university/college students and teachers")
    year_level = models.IntegerField(null=True, blank=True, help_text="Year level (1, 2, 3, 4, etc.)")
    section = models.CharField(max_length=50, blank=True, null=True, help_text="Section (e.g., A, B, 1, 2)")
    department = models.CharField(max_length=200, blank=True, null=True, help_text="Department")
    profile_picture = models.ImageField(upload_to='profile_pictures/', blank=True, null=True, help_text="Profile picture")
    deleted_at = models.DateTimeField(null=True, blank=True, help_text="Soft delete timestamp - item will be permanently deleted after 30 days")
    custom_password = models.CharField(max_length=128, blank=True, null=True, help_text="User's custom password (hashed)")
    otp_code = models.CharField(max_length=6, blank=True, null=True, help_text="OTP code for password reset")
    otp_expires_at = models.DateTimeField(null=True, blank=True, help_text="OTP expiration timestamp")

    def __str__(self):
        return f"{self.full_name or self.username}"
    
    def set_custom_password(self, raw_password):
        """Set the custom password (hashed) and store plain text for display"""
        from django.contrib.auth.hashers import make_password
        self.custom_password = make_password(raw_password)
        self.save(update_fields=['custom_password'])
        
        # Store plain text password for display (similar to temporary password)
        try:
            from dashboard.models import UserCustomPassword
            UserCustomPassword.objects.update_or_create(
                user=self,
                defaults={'password': raw_password}
            )
        except Exception:
            pass  # Silently fail if model doesn't exist yet (migration pending)
    
    def check_custom_password(self, raw_password):
        """Check if the provided password matches the custom password"""
        from django.contrib.auth.hashers import check_password
        if not self.custom_password:
            return False
        return check_password(raw_password, self.custom_password)