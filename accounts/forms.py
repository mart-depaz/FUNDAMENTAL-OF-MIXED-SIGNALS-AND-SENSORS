# accounts/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser
import re
import random

class CustomUserCreationForm(UserCreationForm):
    role = forms.ChoiceField(choices=[('student', 'Student'), ('teacher', 'Teacher')])
    full_name = forms.CharField(max_length=90, required=False, help_text="Enter your full name (e.g., John Michael Doe, or any part like John), optional")
    education_level = forms.ChoiceField(
        choices=[
            ('high_senior', 'High/Senior High'),
            ('university_college', 'University/College')
        ],
        required=True,
        help_text="Select your education level."
    )

    class Meta:
        model = CustomUser
        fields = ('full_name', 'email', 'password1', 'password2', 'education_level')

    def clean_email(self):
        email = self.cleaned_data['email']
        if CustomUser.objects.filter(email=email).exists():
            raise forms.ValidationError('This email is already registered.')
        return email

    def clean(self):
        from dashboard.models import Program
        
        cleaned_data = super().clean()
        role = cleaned_data.get('role')
        school_id = self.data.get('student_id' if role == 'student' else 'employee_id')
        education_level = cleaned_data.get('education_level')

        if role == 'student' and not school_id:
            self.add_error(None, 'Student ID is required.')
        elif role == 'teacher' and not school_id:
            self.add_error(None, 'Employee ID is required.')
        elif school_id and CustomUser.objects.filter(school_id=school_id).exists():
            self.add_error(None, f'This ID is already registered by another user.')
        
        # Program is required for University/College
        if education_level == 'university_college':
            program_id = self.data.get('program_id', '').strip()
            if not program_id:
                self.add_error(None, 'Program/Major is required for University/College level.')
            else:
                try:
                    program = Program.objects.get(id=int(program_id))
                    # Verify program matches school and education level
                    school_name = self.data.get('school_name', '').strip()
                    if program.school_name and program.school_name != school_name:
                        self.add_error(None, 'Selected program does not belong to the selected school.')
                    if program.education_level != education_level:
                        self.add_error(None, 'Selected program does not match the education level.')
                except (Program.DoesNotExist, ValueError):
                    self.add_error(None, 'Invalid program selected.')
        
        # Department is only required for University/College
        if education_level in ['high_senior']:
            if 'department' in self.data and self.data['department']:
                self.add_error('department', 'Department is not required for High/Senior High.')
        return cleaned_data

    def save(self, commit=True):
        from dashboard.models import Program
        
        user = super().save(commit=False)
        role = self.cleaned_data.get('role')
        user.full_name = self.cleaned_data.get('full_name', '')  # Optional, defaults to empty string if not provided
        # Auto-generate username resembling full_name with a unique number
        base_username = user.full_name.replace(' ', '_').lower() if user.full_name else 'user'
        while True:
            random_num = random.randint(100, 999)  # Shorter range for readability
            username = f"{base_username}_{random_num}"
            if not CustomUser.objects.filter(username=username).exists():
                user.username = username
                break
        user.education_level = self.cleaned_data.get('education_level')
        # Save selected school name
        user.school_name = self.data.get('school_name', '').strip() or None
        
        # Save program if provided (for university/college students and teachers)
        program_id = self.data.get('program_id', '').strip()
        if program_id:
            try:
                program = Program.objects.get(id=int(program_id))
                user.program = program
            except (Program.DoesNotExist, ValueError):
                pass  # If program doesn't exist, leave it as None
        
        if role == 'student':
            user.is_student = True
            user.is_approved = True  # Students are auto-approved, no admin approval needed
            user.school_id = self.data.get('student_id')
        elif role == 'teacher':
            user.is_teacher = True
            user.is_approved = False  # Teachers still need admin approval
            user.school_id = self.data.get('employee_id')
        if commit:
            user.save()
        return user

class LoginForm(forms.Form):
    email_or_id = forms.CharField(
        label="Email / ID Number",
        max_length=100,
        widget=forms.TextInput(attrs={'placeholder': 'Enter your registered email or ID'}),
        error_messages={
            'required': 'Please enter your email or ID.',
            'invalid': 'Invalid email or ID format. Use email (e.g., user@example.com) or ID (e.g., 2023-00225).'
        }
    )
    password = forms.CharField(
        widget=forms.PasswordInput,
        error_messages={
            'required': 'Please enter your password.'
        }
    )

    def clean_email_or_id(self):
        email_or_id = self.cleaned_data['email_or_id']
        if not (re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email_or_id) or re.match(r'^\d{4}-\d{5}$', email_or_id)):
            raise forms.ValidationError('Invalid email or ID format. Use email (e.g., user@example.com) or ID (e.g., 2023-00225).')
        return email_or_id

    def clean(self):
        cleaned_data = super().clean()
        email_or_id = cleaned_data.get('email_or_id')
        password = cleaned_data.get('password')
        if email_or_id and password:
            try:
                user = CustomUser.objects.get(email=email_or_id) if re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email_or_id) else CustomUser.objects.get(school_id=email_or_id)
            except CustomUser.DoesNotExist:
                raise forms.ValidationError('No account found with this email or ID.')
        return cleaned_data