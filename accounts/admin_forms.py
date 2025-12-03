# accounts/admin_forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.utils.crypto import get_random_string
from .models import CustomUser
from dashboard.models import Program
import random

class AdminAddTeacherForm(forms.Form):
    """Form for school admins to add teachers"""
    full_name = forms.CharField(max_length=90, required=True, help_text="Full name of the teacher")
    email = forms.EmailField(required=True, help_text="School email address")
    school_id = forms.CharField(max_length=10, required=True, help_text="Employee/Staff ID number")
    education_level = forms.ChoiceField(
        choices=[
            ('high_senior', 'High/Senior High'),
            ('university_college', 'University/College')
        ],
        required=True,
        help_text="Education level"
    )
    school_name = forms.CharField(max_length=200, required=False, help_text="School name (auto-filled from admin)")
    program = forms.ModelChoiceField(
        queryset=Program.objects.none(),
        required=False,
        help_text="Program/Department (required for University/College)"
    )
    department = forms.CharField(max_length=200, required=True, help_text="Department")
    
    def __init__(self, *args, **kwargs):
        admin_user = kwargs.pop('admin_user', None)
        super().__init__(*args, **kwargs)
        
        # Set school name from admin if available
        if admin_user and admin_user.school_name:
            self.fields['school_name'].initial = admin_user.school_name
            self.fields['school_name'].widget = forms.HiddenInput()
        
        # Filter education level choices based on admin's education level
        if admin_user and admin_user.education_level:
            # Admin has a specific education level - restrict to that only
            if admin_user.education_level == 'university_college':
                self.fields['education_level'].choices = [('university_college', 'University/College')]
                self.fields['education_level'].initial = 'university_college'
            elif admin_user.education_level == 'high_senior':
                self.fields['education_level'].choices = [('high_senior', 'High/Senior High')]
                self.fields['education_level'].initial = 'high_senior'
        else:
            # Admin doesn't have a specific level - show all options
            self.fields['education_level'].choices = [
                ('high_senior', 'High/Senior High'),
                ('university_college', 'University/College')
            ]
        
        # Filter programs by school and education level
        if admin_user and admin_user.school_name:
            programs = Program.objects.filter(
                school_name=admin_user.school_name,
                is_active=True
            )
            # If admin has specific education level, filter programs by that too
            if admin_user.education_level:
                programs = programs.filter(education_level=admin_user.education_level)
        else:
            programs = Program.objects.filter(is_active=True)
        
        self.fields['program'].queryset = programs
        
        # Make program required for university/college
        if 'education_level' in self.data:
            if self.data['education_level'] == 'university_college':
                self.fields['program'].required = True
        elif admin_user and admin_user.education_level == 'university_college':
            # If admin is college-only, program is always required
            self.fields['program'].required = True
    
    def clean_email(self):
        email = self.cleaned_data['email']
        if CustomUser.objects.filter(email=email).exists():
            raise forms.ValidationError('This email is already registered.')
        return email
    
    def clean_school_id(self):
        school_id = self.cleaned_data['school_id']
        if CustomUser.objects.filter(school_id=school_id).exists():
            raise forms.ValidationError('This ID is already registered.')
        return school_id
    
    def clean_department(self):
        """Convert department to uppercase"""
        department = self.cleaned_data.get('department', '').strip()
        if department:
            return department.upper()
        return department
    
    def clean(self):
        cleaned_data = super().clean()
        education_level = cleaned_data.get('education_level')
        program = cleaned_data.get('program')
        
        # Program is required for University/College
        if education_level == 'university_college' and not program:
            self.add_error('program', 'Program/Department is required for University/College level.')
        elif program:
            # Verify program matches education level
            if program.education_level != education_level:
                self.add_error('program', 'Selected program does not match the education level.')
        
        return cleaned_data
    
    def save(self, admin_user):
        """Create a teacher user"""
        user = CustomUser()
        user.full_name = self.cleaned_data['full_name']
        user.email = self.cleaned_data['email']
        user.school_id = self.cleaned_data['school_id']
        user.education_level = self.cleaned_data['education_level']
        user.school_name = self.cleaned_data.get('school_name') or admin_user.school_name
        user.program = self.cleaned_data.get('program')
        user.department = self.cleaned_data.get('department', '').strip()
        
        # Generate username
        base_username = user.full_name.replace(' ', '_').lower() if user.full_name else 'teacher'
        while True:
            random_num = random.randint(100, 999)
            username = f"{base_username}_{random_num}"
            if not CustomUser.objects.filter(username=username).exists():
                user.username = username
                break
        
        # Generate temporary password (exactly 8 characters)
        # Use uppercase alphanumeric characters for password
        temp_password = get_random_string(length=8, allowed_chars='ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789').upper()
        user.set_password(temp_password)
        
        user.is_teacher = True
        user.is_student = False
        user.is_admin = False
        user.is_approved = True  # Auto-approve teachers added by admin
        user.is_staff = False
        user.is_superuser = False
        
        user.save()
        
        # Store the temporary password for later retrieval
        from dashboard.models import UserTemporaryPassword
        UserTemporaryPassword.objects.update_or_create(
            user=user,
            defaults={'password': temp_password, 'is_used': False}
        )
        
        return user, temp_password

class AdminAddStudentForm(forms.Form):
    """Form for school admins to add students"""
    full_name = forms.CharField(max_length=90, required=True, help_text="Full name of the student")
    email = forms.EmailField(required=True, help_text="School email address")
    school_id = forms.CharField(max_length=10, required=True, help_text="Student ID number")
    education_level = forms.ChoiceField(
        choices=[],
        required=True,
        help_text="Education level"
    )
    school_name = forms.CharField(max_length=200, required=False, help_text="School name (auto-filled from admin)")
    program = forms.ModelChoiceField(
        queryset=Program.objects.none(),
        required=False,
        help_text="Program/Major (required for University/College)"
    )
    year_level = forms.ChoiceField(
        choices=[
            ('1', '1st Year'),
            ('2', '2nd Year'),
            ('3', '3rd Year'),
            ('4', '4th Year'),
            ('5', '5th Year'),
        ],
        required=False,
        help_text="Year level"
    )
    section = forms.CharField(max_length=50, required=False, help_text="Section (e.g., A, B, 1, 2)")
    department = forms.CharField(max_length=200, required=True, help_text="Department")
    
    def __init__(self, *args, **kwargs):
        admin_user = kwargs.pop('admin_user', None)
        super().__init__(*args, **kwargs)
        
        # Set school name from admin if available
        if admin_user and admin_user.school_name:
            self.fields['school_name'].initial = admin_user.school_name
            self.fields['school_name'].widget = forms.HiddenInput()
        
        # Filter education level choices based on admin's education level
        if admin_user and admin_user.education_level:
            # Admin has a specific education level - restrict to that only
            if admin_user.education_level == 'university_college':
                self.fields['education_level'].choices = [('university_college', 'University/College')]
                self.fields['education_level'].initial = 'university_college'
            elif admin_user.education_level == 'high_senior':
                self.fields['education_level'].choices = [('high_senior', 'High/Senior High')]
                self.fields['education_level'].initial = 'high_senior'
        else:
            # Admin doesn't have a specific level - show all options
            self.fields['education_level'].choices = [
                ('high_senior', 'High/Senior High'),
                ('university_college', 'University/College')
            ]
        
        # Filter programs by school and education level
        if admin_user and admin_user.school_name:
            programs = Program.objects.filter(
                school_name=admin_user.school_name,
                is_active=True
            )
            # If admin has specific education level, filter programs by that too
            if admin_user.education_level:
                programs = programs.filter(education_level=admin_user.education_level)
        else:
            programs = Program.objects.filter(is_active=True)
        
        self.fields['program'].queryset = programs
        
        # Make program and year_level required for university/college
        if 'education_level' in self.data:
            if self.data['education_level'] == 'university_college':
                self.fields['program'].required = True
                self.fields['year_level'].required = True
                self.fields['section'].required = True
        elif admin_user and admin_user.education_level == 'university_college':
            # If admin is college-only, these fields are always required
            self.fields['program'].required = True
            self.fields['year_level'].required = True
            self.fields['section'].required = True
    
    def clean_email(self):
        email = self.cleaned_data['email']
        if CustomUser.objects.filter(email=email).exists():
            raise forms.ValidationError('This email is already registered.')
        return email
    
    def clean_school_id(self):
        school_id = self.cleaned_data['school_id']
        if CustomUser.objects.filter(school_id=school_id).exists():
            raise forms.ValidationError('This ID is already registered.')
        return school_id
    
    def clean_department(self):
        """Convert department to uppercase"""
        department = self.cleaned_data.get('department', '').strip()
        if department:
            return department.upper()
        return department
    
    def clean(self):
        cleaned_data = super().clean()
        education_level = cleaned_data.get('education_level')
        program = cleaned_data.get('program')
        year_level = cleaned_data.get('year_level')
        section = cleaned_data.get('section')
        
        # Program, year_level, and section are required for University/College
        if education_level == 'university_college':
            if not program:
                self.add_error('program', 'Program/Major is required for University/College level.')
            if not year_level:
                self.add_error('year_level', 'Year level is required for University/College level.')
            if not section:
                self.add_error('section', 'Section is required for University/College level.')
        elif program:
            # Verify program matches education level
            if program.education_level != education_level:
                self.add_error('program', 'Selected program does not match the education level.')
        
        return cleaned_data
    
    def save(self, admin_user):
        """Create a student user"""
        user = CustomUser()
        user.full_name = self.cleaned_data['full_name']
        user.email = self.cleaned_data['email']
        user.school_id = self.cleaned_data['school_id']
        user.education_level = self.cleaned_data['education_level']
        user.school_name = self.cleaned_data.get('school_name') or admin_user.school_name
        user.program = self.cleaned_data.get('program')
        year_level = self.cleaned_data.get('year_level')
        user.year_level = int(year_level) if year_level else None
        user.section = self.cleaned_data.get('section')
        user.department = self.cleaned_data.get('department', '').strip()
        
        # Generate username
        base_username = user.full_name.replace(' ', '_').lower() if user.full_name else 'student'
        while True:
            random_num = random.randint(100, 999)
            username = f"{base_username}_{random_num}"
            if not CustomUser.objects.filter(username=username).exists():
                user.username = username
                break
        
        # Generate temporary password (exactly 8 characters)
        # Use uppercase alphanumeric characters for password
        temp_password = get_random_string(length=8, allowed_chars='ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789').upper()
        user.set_password(temp_password)
        
        user.is_teacher = False
        user.is_student = True
        user.is_admin = False
        user.is_approved = True  # Students are auto-approved
        user.is_staff = False
        user.is_superuser = False
        
        user.save()
        
        # Store the temporary password for later retrieval
        from dashboard.models import UserTemporaryPassword
        UserTemporaryPassword.objects.update_or_create(
            user=user,
            defaults={'password': temp_password, 'is_used': False}
        )
        
        return user, temp_password

