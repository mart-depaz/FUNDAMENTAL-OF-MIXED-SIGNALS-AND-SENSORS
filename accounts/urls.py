# for accounts app urls.py


from django.urls import path
from . import views
from . import admin_views

urlpatterns = [
    path('', views.login_signup_view, name='login_signup'),
    path('logout/', views.logout_view, name='logout'),
    path('reset-password/', views.reset_password_view, name='reset_password'),
    path('approve_teacher/<int:user_id>/', views.approve_teacher, name='approve_teacher'),
    path('api/get-schools/', views.get_schools_by_education_level, name='get_schools'),
    path('api/get-programs/', views.get_programs_by_school, name='get_programs'),
    # Admin routes (custom admin portal - separate from Django admin)
    path('admin-portal/', admin_views.admin_login_signup_view, name='admin_login_signup'),
    path('admin-portal/logout/', admin_views.admin_logout_view, name='admin_logout'),
]