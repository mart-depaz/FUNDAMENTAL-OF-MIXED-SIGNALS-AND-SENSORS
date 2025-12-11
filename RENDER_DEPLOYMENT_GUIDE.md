# Render Deployment Guide for Attendance System

## Quick Start

This guide will help you deploy your attendance system from Cloudflare Tunnel to **Render** (persistent, free tier).

### Why Render?
✅ **Free tier** - 750 hours/month (enough for a project)
✅ **Persistent URL** - `https://your-app.onrender.com` (doesn't change)
✅ **Auto HTTPS** - SSL certificate included
✅ **PostgreSQL database** - Free included
✅ **No credit card needed** - But can upgrade later

---

## Step 1: Push Code to GitHub

First, you need to push your code to a GitHub repository that Render can access.

### Option A: Create New GitHub Account (Recommended)
1. Go to https://github.com/signup
2. Create a new account (or use existing)
3. Create a new **public repository** named `attendance-system`
4. Clone it locally:
   ```powershell
   git clone https://github.com/YOUR-USERNAME/attendance-system.git
   cd attendance-system
   ```
5. Copy all files from your FUNDAMENTAL-OF-MIXED-SIGNALS-AND-SENSORS folder into this new repo
6. Commit and push:
   ```powershell
   git add -A
   git commit -m "Initial attendance system commit"
   git push origin main
   ```

### Option B: Use Existing Repo
If you already have write access to a repo, just push your changes.

---

## Step 2: Connect Render to GitHub

1. Go to https://render.com (no credit card needed)
2. Click **"Sign up"** → Select **"GitHub"** 
3. Authorize Render to access your GitHub
4. Click **"New +"** → Select **"Web Service"**
5. Search for your repository name
6. Select your **attendance-system** repo

---

## Step 3: Configure Render Settings

Fill in these settings:

| Setting | Value |
|---------|-------|
| **Name** | `attendance-system` (or any name you want) |
| **Environment** | `Python 3` |
| **Region** | Select closest to you (e.g., Singapore, Tokyo) |
| **Branch** | `main` |
| **Build Command** | `bash build.sh` |
| **Start Command** | `gunicorn library_root.wsgi:application` |
| **Plan** | `Free` |

### Add Environment Variables

Click **"Add Environment Variable"** and add these:

```
DEBUG=False
SECRET_KEY=django-insecure-x&rfo%c#sm@0leoa26c0gr_(5hd(gz26x$_v9d2m=i2*z2tb@c
PYTHON_VERSION=3.13.1
```

Render automatically provides `DATABASE_URL` for PostgreSQL - you don't need to set it!

---

## Step 4: Deploy!

1. Click **"Create Web Service"**
2. Render will:
   - Pull your code from GitHub
   - Install dependencies from `requirements.txt`
   - Run your `build.sh` (which runs migrations)
   - Start gunicorn server

3. Wait 5-10 minutes for deployment to complete
4. You'll see a green checkmark and a URL like: `https://attendance-system.onrender.com`

---

## Step 5: Access Your Site

Visit your Render URL:
```
https://attendance-system.onrender.com
```

✅ System is now **live and free**!
✅ URL is **persistent** (won't change on restart)
✅ HTTPS works **automatically**
✅ Database is **PostgreSQL** (automatic)

---

## Step 6: Create Admin Account (First Time Only)

Once deployed, create a superuser account by accessing Render's shell:

1. In Render dashboard, go to your service
2. Click **"Shell"** tab
3. Run:
   ```bash
   python manage.py createsuperuser
   ```
4. Follow prompts to create admin account
5. Access admin at: `https://attendance-system.onrender.com/admin`

---

## Important Notes

### Database Migration
- Your SQLite database (`db.sqlite3`) won't be used on Render
- Render automatically provides **PostgreSQL**
- `build.sh` runs `python manage.py migrate` automatically
- All your tables will be created fresh

### Media Files (Profile Pictures)
- On Render's free tier, files are ephemeral (reset on restart)
- To fix this, upgrade to paid tier and add persistent storage
- For now, you can still upload, but they'll be deleted after app restarts

### Static Files
- Your CSS/JS files are served via WhiteNoise
- No separate configuration needed

### Camera Access
- HTTPS works automatically on Render
- Camera will work fine with `https://attendance-system.onrender.com`

---

## Monitoring & Logs

To see what's happening:

1. Click your service in Render dashboard
2. Click **"Logs"** tab
3. Scroll to see real-time Django output

### Common Errors & Fixes

**Error: "No such table: dashboard_enrollment"**
- Solution: Run shell command → `python manage.py migrate`

**Error: "ProgrammingError in django_session"**
- Solution: Same as above

**Page loads slowly**
- Free tier spins down after 15 min of inactivity
- First request wakes it (takes ~30 sec)
- Subsequent requests are fast

---

## Update Your Code

To deploy new changes:

1. Make changes locally
2. Commit and push to GitHub:
   ```powershell
   git add -A
   git commit -m "Your message"
   git push origin main
   ```
3. Render **automatically redeploys** within 1 minute!

---

## Next Steps (Optional)

### 1. Custom Domain
- Buy a domain (e.g., godaddy.com, namecheap.com)
- Point it to Render (they provide DNS instructions)
- Cost: Usually $10-15/year

### 2. Upgrade Plan
- Free tier: 750 hours/month = ~24/7 if alone
- Starter plan: $5/month = guaranteed 24/7
- Render doesn't charge for database on free tier!

### 3. Backup Your Data
- Even though it's free, your production data is real
- Regularly export using:
  ```bash
  python manage.py dumpdata > backup.json
  ```

---

## Summary

✅ Code pushed to GitHub
✅ Render connected and configured
✅ Site deployed at `https://attendance-system.onrender.com`
✅ PostgreSQL database ready
✅ HTTPS enabled automatically
✅ System is now **live and free**!

**You've successfully moved from Cloudflare Tunnel to Render!**

Any questions? Render has excellent documentation at https://render.com/docs

