from django.contrib import admin
from django.utils.html import format_html
from .models import Department, Program, Course, CourseSchedule, AdminNotification, UserTemporaryPassword


# ============================================
# INSTITUTIONAL SETUP CATEGORY
# ============================================

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    """Admin interface for Department model"""
    list_display = ['code', 'name', 'school_name', 'education_level', 'is_active', 'program_count', 'created_at']
    list_filter = ['is_active', 'education_level', 'school_name', 'created_at']
    search_fields = ['name', 'code', 'school_name']
    readonly_fields = ['created_at', 'updated_at', 'icon_preview']
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'code', 'school_name', 'education_level')
        }),
        ('Visual', {
            'fields': ('icon', 'icon_preview')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def icon_preview(self, obj):
        """Display icon preview in admin"""
        if obj.icon:
            return format_html('<img src="{}" style="max-width: 100px; max-height: 100px;" />', obj.icon.url)
        return "No icon"
    icon_preview.short_description = 'Icon Preview'
    
    def program_count(self, obj):
        """Display count of programs in this department"""
        count = Program.objects.filter(department=obj.name, school_name=obj.school_name).count()
        return count
    program_count.short_description = 'Programs'
    program_count.admin_order_field = 'program__count'
    
    class Meta:
        verbose_name = 'Department'
        verbose_name_plural = 'Departments'


@admin.register(Program)
class ProgramAdmin(admin.ModelAdmin):
    """Admin interface for Program model"""
    list_display = ['code', 'name', 'department_display', 'school_name', 'education_level', 'is_active', 'user_count', 'course_count', 'created_at']
    list_filter = ['is_active', 'education_level', 'school_name', 'department', 'created_at']
    search_fields = ['code', 'name', 'department', 'school_name']
    readonly_fields = ['created_at', 'updated_at', 'icon_preview']
    fieldsets = (
        ('Basic Information', {
            'fields': ('code', 'name', 'department', 'department_code', 'school_name', 'education_level')
        }),
        ('Visual', {
            'fields': ('icon', 'icon_preview')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def icon_preview(self, obj):
        """Display icon preview in admin"""
        if obj.icon:
            return format_html('<img src="{}" style="max-width: 100px; max-height: 100px;" />', obj.icon.url)
        return "No icon"
    icon_preview.short_description = 'Icon Preview'
    
    def department_display(self, obj):
        """Display department with code if available"""
        if obj.department_code:
            return f"{obj.department_code} - {obj.department}"
        return obj.department
    department_display.short_description = 'Department'
    department_display.admin_order_field = 'department'
    
    def user_count(self, obj):
        """Display count of users in this program"""
        from accounts.models import CustomUser
        count = CustomUser.objects.filter(program=obj).count()
        return count
    user_count.short_description = 'Users'
    
    def course_count(self, obj):
        """Display count of courses in this program"""
        count = obj.courses.count()
        return count
    course_count.short_description = 'Courses'
    
    class Meta:
        verbose_name = 'Program'
        verbose_name_plural = 'Programs'


# ============================================
# ACADEMIC MANAGEMENT CATEGORY
# ============================================

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    """Admin interface for Course model"""
    list_display = ['code', 'name', 'program', 'year_level', 'section', 'semester', 'school_year', 'instructor', 'days_display', 'time_display', 'is_active', 'created_at']
    list_filter = ['is_active', 'semester', 'school_year', 'year_level', 'program', 'program__department', 'created_at']
    search_fields = ['code', 'name', 'program__code', 'program__name', 'instructor__full_name', 'instructor__username', 'room']
    readonly_fields = ['created_at', 'updated_at', 'color_preview']
    fieldsets = (
        ('Course Information', {
            'fields': ('code', 'name', 'program', 'year_level', 'section', 'semester', 'school_year')
        }),
        ('Instructor & Location', {
            'fields': ('instructor', 'room')
        }),
        ('Schedule', {
            'fields': ('days', 'start_time', 'end_time')
        }),
        ('Attendance Settings', {
            'fields': ('attendance_start', 'attendance_end'),
            'description': 'These times are set by the instructor, not the admin.'
        }),
        ('Display', {
            'fields': ('color', 'color_preview')
        }),
        ('Metadata', {
            'fields': ('school_name', 'is_active'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def days_display(self, obj):
        """Display days in a readable format"""
        return obj.days.replace(',', ', ')
    days_display.short_description = 'Days'
    
    def time_display(self, obj):
        """Display time range"""
        return f"{obj.start_time.strftime('%I:%M %p')} - {obj.end_time.strftime('%I:%M %p')}"
    time_display.short_description = 'Time'
    
    def color_preview(self, obj):
        """Display color preview"""
        return format_html(
            '<div style="width: 50px; height: 30px; background-color: {}; border: 1px solid #ccc; border-radius: 4px;"></div>',
            obj.color
        )
    color_preview.short_description = 'Color Preview'
    
    class Meta:
        verbose_name = 'Course'
        verbose_name_plural = 'Courses'


@admin.register(CourseSchedule)
class CourseScheduleAdmin(admin.ModelAdmin):
    """Admin interface for CourseSchedule model (day-specific schedules)"""
    list_display = ['course', 'day', 'start_time', 'end_time', 'room', 'day_order', 'attendance_start', 'attendance_end']
    list_filter = ['day', 'course__program', 'course__semester', 'course__school_year']
    search_fields = ['course__code', 'course__name', 'room', 'day']
    fieldsets = (
        ('Course Information', {
            'fields': ('course',)
        }),
        ('Schedule Details', {
            'fields': ('day', 'day_order', 'start_time', 'end_time', 'room')
        }),
        ('Attendance Window', {
            'fields': ('attendance_start', 'attendance_end'),
            'description': 'Attendance window for this specific day schedule.'
        }),
    )
    
    class Meta:
        verbose_name = 'Course Schedule (Day-Specific)'
        verbose_name_plural = 'Course Schedules (Day-Specific)'


# ============================================
# SYSTEM MANAGEMENT CATEGORY
# ============================================

@admin.register(AdminNotification)
class AdminNotificationAdmin(admin.ModelAdmin):
    """Admin interface for AdminNotification model"""
    list_display = ['title', 'notification_type', 'admin', 'related_user', 'is_read', 'created_at']
    list_filter = ['is_read', 'notification_type', 'created_at']
    search_fields = ['title', 'message', 'admin__username', 'admin__full_name', 'related_user__username', 'related_user__full_name']
    readonly_fields = ['created_at']
    fieldsets = (
        ('Notification Details', {
            'fields': ('admin', 'notification_type', 'title', 'message')
        }),
        ('Related Information', {
            'fields': ('related_user', 'is_read')
        }),
        ('Timestamp', {
            'fields': ('created_at',)
        }),
    )
    
    def get_queryset(self, request):
        """Optimize queryset"""
        qs = super().get_queryset(request)
        return qs.select_related('admin', 'related_user')
    
    class Meta:
        verbose_name = 'Admin Notification'
        verbose_name_plural = 'Admin Notifications'


@admin.register(UserTemporaryPassword)
class UserTemporaryPasswordAdmin(admin.ModelAdmin):
    """Admin interface for UserTemporaryPassword model"""
    list_display = ['user', 'is_used', 'created_at', 'updated_at']
    list_filter = ['is_used', 'created_at', 'updated_at']
    search_fields = ['user__username', 'user__full_name', 'user__email', 'user__school_id']
    readonly_fields = ['created_at', 'updated_at', 'password_display']
    fieldsets = (
        ('User Information', {
            'fields': ('user',)
        }),
        ('Password Information', {
            'fields': ('password', 'password_display', 'is_used')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def password_display(self, obj):
        """Display masked password"""
        if obj.password:
            return '•' * min(len(obj.password), 20)
        return "No password set"
    password_display.short_description = 'Password (masked)'
    
    def get_queryset(self, request):
        """Optimize queryset"""
        qs = super().get_queryset(request)
        return qs.select_related('user')
    
    class Meta:
        verbose_name = 'User Temporary Password'
        verbose_name_plural = 'User Temporary Passwords'


# ============================================
# CUSTOMIZE ADMIN SITE
# ============================================

# Customize admin site header and title
admin.site.site_header = "Attendance System Administration"
admin.site.site_title = "Attendance System Admin"
admin.site.index_title = "Welcome to Attendance System Administration"

# Note: Models are organized in the admin interface as follows:
# 1. Institutional Setup (Dashboard app):
#    - Departments
#    - Programs  
#    - Courses
#    - Admin Notifications
#    - User Temporary Passwords
# 2. User Management (Accounts app):
#    - Custom Users
#
# The ordering is controlled by the model Meta classes and admin registration order.
