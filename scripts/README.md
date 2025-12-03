# 🔧 Utility Scripts

This directory contains utility scripts for managing the Attendance System.

## 📋 Available Scripts

### 1. `create_superuser.py`
**Purpose**: Create or update a Django superuser account

**Usage**:
```powershell
python manage.py shell
exec(open('scripts/create_superuser.py').read())
```

**Before running**: Edit the script to set:
- `USERNAME` - Your desired username
- `EMAIL` - Your email address
- `PASSWORD` - Your desired password

**What it does**:
- Creates a new superuser if username doesn't exist
- Updates existing user to be superuser if username exists
- Sets `is_superuser`, `is_staff`, and `is_active` flags

---

### 2. `check_user.py`
**Purpose**: Check the status of a specific user account

**Usage**:
```powershell
python manage.py shell
exec(open('scripts/check_user.py').read())
```

**Before running**: Edit the script to set:
- `USERNAME` - The username to check

**What it does**:
- Displays user account information
- Shows status flags (is_superuser, is_staff, is_active)
- Automatically fixes missing `is_staff` or `is_active` flags

---

### 3. `fix_admin_login.py`
**Purpose**: Fix Django admin login issues for a specific user

**Usage**:
```powershell
python manage.py shell
exec(open('scripts/fix_admin_login.py').read())
```

**Before running**: Edit the script to set:
- `USERNAME` - The username to fix
- `NEW_PASSWORD` - New password to set

**What it does**:
- Sets `is_superuser = True`
- Sets `is_staff = True`
- Sets `is_active = True`
- Resets password

---

### 4. `fix_superuser.py`
**Purpose**: Check and fix all superuser accounts

**Usage**:
```powershell
python manage.py shell
exec(open('scripts/fix_superuser.py').read())
```

**What it does**:
- Lists all superuser accounts
- Checks their status flags
- Automatically fixes missing `is_staff` or `is_active` flags

---

### 5. `diagnose_and_fix_admin.py`
**Purpose**: Comprehensive diagnostic tool for Django admin login issues

**Usage**:
```powershell
python manage.py shell
exec(open('scripts/diagnose_and_fix_admin.py').read())
```

**What it does**:
- Searches for user accounts with various username formats
- Tests authentication
- Checks all status flags
- Provides detailed diagnostic information
- Automatically fixes common issues

**Best for**: When you're not sure what's wrong with admin login

---

## 🚀 Quick Reference

| Script | When to Use |
|--------|-------------|
| `create_superuser.py` | Need to create a new admin account |
| `check_user.py` | Want to check a specific user's status |
| `fix_admin_login.py` | Know the username but can't log in |
| `fix_superuser.py` | Want to check/fix all superusers |
| `diagnose_and_fix_admin.py` | Not sure what's wrong, need comprehensive check |

## ⚠️ Important Notes

1. **Always edit the script first** - Most scripts require you to set variables like `USERNAME` and `PASSWORD` before running

2. **Use Django shell** - All scripts must be run through `python manage.py shell`

3. **Backup first** - These scripts modify user accounts, so make sure you have a backup if needed

4. **Check the output** - Scripts provide detailed output about what they're doing

## 💡 Tips

- If you're unsure which script to use, start with `diagnose_and_fix_admin.py`
- For quick fixes, use `fix_admin_login.py` if you know the username
- Use `check_user.py` to verify changes after running other scripts

---

**Location**: All scripts are in `library_system/scripts/`

