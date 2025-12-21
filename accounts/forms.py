# accounts/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser
import re
import random

class CustomUserCreationForm(UserCreationForm):
    role = forms.ChoiceField(choices=[('student', 'Student'), ('teacher', 'Teacher')])
    full_name = forms.CharField(max_length=90, required=False, help_text="Enter your full name (e.g., John Michael Doe, or any part like John), optional")

    class Meta:
        model = CustomUser
        fields = ('full_name', 'email', 'password1', 'password2')

    def clean_email(self):
        email = self.cleaned_data['email']
        if CustomUser.objects.filter(email=email).exists():
            raise forms.ValidationError('This email is already registered.')
        return email

    def clean(self):
        cleaned_data = super().clean()
        role = cleaned_data.get('role')
        school_id = self.data.get('student_id' if role == 'student' else 'employee_id')
        
        # Construct full_name from first_name, middle_name, last_name
        first_name = self.data.get('first_name', '').strip()
        middle_name = self.data.get('middle_name', '').strip()
        last_name = self.data.get('last_name', '').strip()
        
        if not first_name or not last_name:
            self.add_error(None, 'First Name and Last Name are required.')
        
        full_name = ' '.join(filter(None, [first_name, middle_name, last_name]))
        cleaned_data['full_name'] = full_name

        if role == 'student' and not school_id:
            self.add_error(None, 'Student ID is required.')
        elif role == 'teacher' and not school_id:
            self.add_error(None, 'Employee ID is required.')
        elif school_id and CustomUser.objects.filter(school_id=school_id).exists():
            self.add_error(None, f'This ID is already registered by another user.')
        
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        role = self.cleaned_data.get('role')
        full_name = self.cleaned_data.get('full_name', '')
        user.full_name = full_name
        
        # Auto-generate username resembling full_name with a unique number
        base_username = full_name.replace(' ', '_').lower() if full_name else 'user'
        while True:
            random_num = random.randint(100, 999)  # Shorter range for readability
            username = f"{base_username}_{random_num}"
            if not CustomUser.objects.filter(username=username).exists():
                user.username = username
                break
        
        # Save department if provided
        department = self.data.get('department', '').strip()
        if department:
            user.department = department
        
        if role == 'student':
            user.is_student = True
            user.is_approved = True  # Students are auto-approved, no admin approval needed
            user.school_id = self.data.get('student_id')
        elif role == 'teacher':
            user.is_teacher = True
            user.is_approved = True  # Teachers are now auto-approved, no admin approval needed
            user.school_id = self.data.get('employee_id')
        
        if commit:
            user.save()
            # Set the custom password (the password they created during signup)
            password1 = self.cleaned_data.get('password1')
            if password1:
                user.set_custom_password(password1)
        
        return user

class LoginForm(forms.Form):
    email_or_id = forms.CharField(
        label="Email / ID Number",
        max_length=100,
        widget=forms.TextInput(attrs={'placeholder': 'Enter your registered email or ID'}),
        error_messages={
            'required': 'Please enter your email or ID.',
        }
    )
    password = forms.CharField(
        widget=forms.PasswordInput,
        error_messages={
            'required': 'Please enter your password.'
        }
    )

    def clean_email_or_id(self):
        email_or_id = self.cleaned_data['email_or_id'].strip()
        # Allow any email format (no format restriction) and any ID format
        # Just check it's not empty (already done by required=True)
        return email_or_id

    def clean(self):
        cleaned_data = super().clean()
        email_or_id = cleaned_data.get('email_or_id')
        password = cleaned_data.get('password')
        if email_or_id and password:
            try:
                # Try email first (look for @ symbol)
                if '@' in email_or_id:
                    user = CustomUser.objects.get(email=email_or_id.lower())
                else:
                    # Try as ID (school_id)
                    user = CustomUser.objects.get(school_id=email_or_id)
            except CustomUser.DoesNotExist:
                raise forms.ValidationError('No account found with this email or ID.')
        return cleaned_data