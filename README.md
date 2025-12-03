# 📚 Attendance System

A comprehensive Django-based attendance management system for schools, supporting multiple education levels (High School, Senior High, University/College).

## 📁 Project Structure

```
library_system/
├── accounts/              # User authentication and account management
│   ├── models.py          # CustomUser model
│   ├── views.py           # Authentication views
│   ├── admin_views.py     # Admin-specific views
│   ├── forms.py           # User forms
│   └── templates/         # Account-related templates
│
├── dashboard/            # Main application dashboard
│   ├── models.py         # Program, Course, Department models
│   ├── views.py          # Student/Instructor views
│   ├── admin_views.py     # Admin dashboard views
│   └── templates/        # Dashboard templates
│
├── library_root/         # Django project configuration
│   ├── settings.py      # Project settings
│   ├── urls.py          # URL routing
│   ├── middleware.py    # Custom middleware (no-cache in dev)
│   └── wsgi.py          # WSGI configuration
│
├── templates/            # Shared templates
│   ├── dashboard/       # Dashboard templates
│   └── partials/        # Reusable template components
│
├── media/                # User-uploaded files (profile pictures, etc.)
├── scripts/              # Utility scripts (see scripts/README.md)
├── docs/                 # Documentation files
│
├── manage.py            # Django management script
├── requirements.txt     # Python dependencies
├── COMPLETE_CACHE_FIX.ps1  # Cache clearing script (use this!)
└── README.md            # This file
```

## 🚀 Quick Start

### 1. Activate Virtual Environment
```powershell
..\library_env\Scripts\Activate.ps1
```

### 2. Install Dependencies
```powershell
pip install -r requirements.txt
```

### 3. Run Migrations
```powershell
python manage.py makemigrations
python manage.py migrate
```

### 4. Create Admin Account
```powershell
python manage.py createsuperuser
```
Or use the utility script:
```powershell
python manage.py shell
exec(open('scripts/create_superuser.py').read())
```

### 5. Start Development Server
```powershell
python manage.py runserver
```

Or use the cache fix script (recommended):
```powershell
.\COMPLETE_CACHE_FIX.ps1
```

## 🔧 Development Workflow

### Making Changes

1. **Stop the server** (`Ctrl + C`)

2. **Run the cache fix script**:
   ```powershell
   .\COMPLETE_CACHE_FIX.ps1
   ```

3. **Clear browser cache**:
   - Press `Ctrl + Shift + Delete`
   - Select "Cached images and files" → "All time" → "Clear data"

4. **Open Developer Tools** (`F12`):
   - Go to Network tab
   - Check "Disable cache"

5. **Hard refresh** (`Ctrl + F5`)

### Why Changes Don't Appear?

See `docs/WHY_CHANGES_NOT_UPDATING.md` for a complete explanation of caching issues and solutions.

## 📝 Key Features

### For School Admins
- ✅ User Management (Students, Instructors)
- ✅ Program & Department Management
- ✅ Course/Subject Management
- ✅ Attendance Reports
- ✅ Profile Management

### For Instructors
- ✅ Course Management
- ✅ Attendance Tracking
- ✅ Student Management
- ✅ Timetable View

### For Students
- ✅ View Schedule
- ✅ View Courses
- ✅ Attendance History

## 🛠️ Utility Scripts

See `scripts/README.md` for details on available utility scripts:
- `create_superuser.py` - Create Django superuser
- `check_user.py` - Check user account status
- `fix_admin_login.py` - Fix admin login issues
- `diagnose_and_fix_admin.py` - Comprehensive admin diagnostic tool

## 📚 Documentation

- **Cache Issues**: `docs/WHY_CHANGES_NOT_UPDATING.md`
- **Cache Fix Guide**: `docs/README_CACHE_FIX.md`

## 🔐 User Types

1. **School Admin** (`is_admin=True`)
   - Full system access
   - Manages users, programs, courses
   - Access: `/dashboard/admin-dashboard/`

2. **Instructor** (`is_teacher=True`)
   - Manages courses and attendance
   - Access: `/dashboard/teacher-dashboard/`

3. **Student** (`is_student=True`)
   - Views schedule and attendance
   - Access: `/dashboard/student-dashboard/`

4. **Django Superuser** (`is_superuser=True`)
   - Django admin access
   - Access: `/admin/`

## 🗄️ Database

- **Default**: SQLite (`db.sqlite3`)
- **Migrations**: Located in `accounts/migrations/` and `dashboard/migrations/`

## 📦 Dependencies

See `requirements.txt` for complete list. Key dependencies:
- Django 5.2.7
- Pillow (for image handling)
- python-docx (for document generation)

## 🐛 Troubleshooting

### Changes Not Appearing?
1. Run `.\COMPLETE_CACHE_FIX.ps1`
2. Clear browser cache
3. Hard refresh (`Ctrl + F5`)
4. Check `docs/WHY_CHANGES_NOT_UPDATING.md`

### Admin Login Issues?
Use the diagnostic script:
```powershell
python manage.py shell
exec(open('scripts/diagnose_and_fix_admin.py').read())
```

### Database Issues?
```powershell
python manage.py makemigrations
python manage.py migrate
```

## 📞 Support

For issues or questions, check:
1. `docs/` directory for documentation
2. `scripts/` directory for utility tools
3. Django server console for error messages

---

**Remember**: Always use `COMPLETE_CACHE_FIX.ps1` when restarting the server to ensure changes are reflected!

