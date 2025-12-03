# 🎯 Django Admin Guide

## Overview

All important models are now registered in Django Admin and organized into logical categories for easy navigation.

## 📋 Registered Models

### 📚 Institutional Setup Category

#### 🏢 Departments
- **Model**: `Department`
- **Features**:
  - List view shows: Code, Name, School, Education Level, Status, Program Count
  - Filters: Active Status, Education Level, School Name, Created Date
  - Search: Name, Code, School Name
  - Icon preview in detail view
  - Shows program count for each department

#### 🎓 Programs
- **Model**: `Program`
- **Features**:
  - List view shows: Code, Name, Department, School, Education Level, Status, User Count, Course Count
  - Filters: Active Status, Education Level, School Name, Department, Created Date
  - Search: Code, Name, Department, School Name
  - Icon preview in detail view
  - Shows user count and course count for each program

#### 📖 Courses
- **Model**: `Course`
- **Features**:
  - List view shows: Code, Name, Program, Year Level, Section, Semester, School Year, Instructor, Days, Time, Status
  - Filters: Active Status, Semester, School Year, Year Level, Program, Department, Created Date
  - Search: Code, Name, Program, Instructor, Room
  - Color preview for timetable display
  - Time display in readable format (e.g., "08:00 AM - 10:00 AM")

### 🔔 System Management Category

#### 🔔 Admin Notifications
- **Model**: `AdminNotification`
- **Features**:
  - List view shows: Title, Type, Admin, Related User, Read Status, Created Date
  - Filters: Read Status, Notification Type, Created Date
  - Search: Title, Message, Admin, Related User

#### 🔑 User Temporary Passwords
- **Model**: `UserTemporaryPassword`
- **Features**:
  - List view shows: User, Used Status, Created Date, Updated Date
  - Filters: Used Status, Created Date, Updated Date
  - Search: Username, Full Name, Email, School ID
  - Password is masked for security

### 👥 User Management Category

#### 👤 Users (CustomUser)
- **Model**: `CustomUser`
- **Features**:
  - List view shows: Username, Full Name, Email, User Type, Approval Status, Staff Status, Superuser Status, School, Education Level, School ID, Password Status, Date Joined
  - Filters: Admin, Teacher, Student, Approval Status, Staff, Superuser, Education Level, School Name
  - Search: Username, Full Name, Email, School ID, School Name
  - Bulk actions: Approve Teachers
  - Password management

## 🎨 Organization

Models are organized in the Django Admin interface as follows:

1. **📚 Institutional Setup** (Dashboard app)
   - 🏢 Departments
   - 🎓 Programs
   - 📖 Courses
   - 🔔 Notifications
   - 🔑 Temporary Passwords

2. **👥 User Management** (Accounts app)
   - 👤 Users

## 🔍 Key Features

### List Views
- **Sortable columns**: Click column headers to sort
- **Inline editing**: Some fields can be edited directly in the list view
- **Quick filters**: Use sidebar filters to narrow down results
- **Search**: Use the search box to find specific records

### Detail Views
- **Organized fieldsets**: Fields are grouped logically
- **Read-only timestamps**: Created/Updated dates are automatically tracked
- **Image previews**: Icons and profile pictures show previews
- **Color previews**: Course colors display visually

### Filters
- **Active Status**: Filter by active/inactive records
- **School Name**: Filter by school (for multi-school setups)
- **Education Level**: Filter by High/Senior High or University/College
- **Date Ranges**: Filter by creation/update dates

### Search
- **Multi-field search**: Search across multiple fields simultaneously
- **Case-insensitive**: Search works regardless of case
- **Partial matching**: Find records with partial matches

## 📝 Common Tasks

### Adding a Department
1. Go to **📚 Institutional Setup** → **🏢 Departments**
2. Click **"Add Department"**
3. Fill in:
   - Name (required)
   - Code (optional but recommended)
   - School Name
   - Education Level
   - Upload icon (optional)
4. Click **"Save"**

### Adding a Program
1. Go to **📚 Institutional Setup** → **🎓 Programs**
2. Click **"Add Program"**
3. Fill in:
   - Code (required)
   - Name (required)
   - Department (required)
   - School Name
   - Education Level
   - Upload icon (optional)
4. Click **"Save"**

### Adding a Course
1. Go to **📚 Institutional Setup** → **📖 Courses**
2. Click **"Add Course"**
3. Fill in all required fields
4. Click **"Save"**

### Managing Users
1. Go to **👥 User Management** → **👤 Users**
2. Use filters to find specific users
3. Click on a user to edit
4. Use bulk actions to approve multiple teachers at once

## ⚠️ Important Notes

1. **Django Admin vs Custom Portal**:
   - Django Admin (`/admin/`) is for Django superusers only
   - School admins use the custom portal (`/dashboard/admin-dashboard/`)

2. **Permissions**:
   - Only Django superusers can access `/admin/`
   - School admins cannot access Django admin

3. **Data Integrity**:
   - Deleting a Department will affect Programs
   - Deleting a Program will affect Courses and Users
   - Always check relationships before deleting

4. **School Separation**:
   - All models support `school_name` for multi-school setups
   - Use filters to view data for specific schools

## 🚀 Quick Access

- **Django Admin**: `http://127.0.0.1:8000/admin/`
- **Custom Admin Portal**: `http://127.0.0.1:8000/dashboard/admin-dashboard/`

---

**Note**: All models are fully searchable, filterable, and organized for easy navigation!

