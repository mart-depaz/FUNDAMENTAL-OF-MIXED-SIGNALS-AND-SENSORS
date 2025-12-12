# Notification Delete System - Troubleshooting Guide

## 🚀 Quick Start: Using the Debug Tools

### In Browser Console (F12 → Console Tab)

**Show available debug commands:**
```javascript
window.NotificationDebug.help()
```

**Get system inspection:**
```javascript
window.NotificationDebug.inspect()
```

**List all notifications:**
```javascript
window.NotificationDebug.listNotifications()
```

**Check event listeners:**
```javascript
window.NotificationDebug.checkListeners()
```

**Test delete for notification ID 5:**
```javascript
window.NotificationDebug.testDelete(5)
```

---

## 🔍 Diagnostic Flowchart

```
Delete button clicked
      ↓
[A] Event listener fires?
   YES → [B] JavaScript error?
         YES → Fix error in console
         NO  → [C] CSRF token found?
               YES → [D] API call sent?
                     YES → [E] Response 200?
                           YES → [F] success: true?
                                 YES → ✅ WORKING!
                                 NO  → Django view issue
                           NO  → Status code issue
                     NO  → Network blocked
               NO  → CSRF token missing
   NO  → Listener not attached
```

---

## ❌ Common Issues & Fixes

### Issue 1: Delete Button Doesn't Respond

**Symptoms:**
- Click delete button → nothing happens
- No errors in console
- No API request in Network tab

**Diagnosis:**
```javascript
// In console:
document.querySelectorAll('.deleteNotificationBtn').length  // Should be > 0
window.NotificationDebug.checkListeners()  // Check if attached
```

**Fix:**
```javascript
// Reattach listeners
window.NotificationDebug.reattachListeners()

// Or manually:
window.attachNotificationListeners()
```

**Root Cause:**
- Notifications loaded before JavaScript initialized
- Dynamic content not triggering event attachment
- Listeners removed by other code

---

### Issue 2: "Notification element not found"

**Symptoms:**
```
Notification element found: ✗
```

**Diagnosis:**
```javascript
// Check if element exists
document.querySelector('[data-notification-id="1"]')  // Replace 1 with actual ID

// List all notification IDs
window.NotificationDebug.listNotifications()
```

**Fixes:**

1. **Element was deleted already:**
   ```javascript
   // Check what notifications exist
   document.querySelectorAll('[data-notification-id]').length
   ```

2. **Wrong selector:**
   - Check HTML has `data-notification-id` attribute
   - Check attribute value matches: `{{ notification.id }}`

3. **Element is in shadow DOM:**
   ```javascript
   // Use alternate selector
   document.querySelector('[data-notification-id*="5"]')  // Contains "5"
   ```

---

### Issue 3: CSRF Token Not Found

**Symptoms:**
```
CSRF Token obtained: ✗
```

**Console Error:**
```
Error deleting notification: TypeError: Cannot read property 'value' of null
```

**Diagnosis:**
```javascript
// Check for CSRF token
window.NotificationDebug.findCSRFToken()

// Or manually check both sources:
document.querySelector('[name=csrfmiddlewaretoken]')?.value  // Hidden input
document.cookie.split(';').find(c => c.includes('csrftoken'))  // Cookie
```

**Fixes:**

1. **Add CSRF token to page:**
   ```html
   <!-- In template -->
   {% csrf_token %}
   ```

2. **Check Django CSRF middleware:**
   ```python
   # In settings.py - should be present:
   MIDDLEWARE = [
       'django.middleware.csrf.CsrfViewMiddleware',
   ]
   ```

3. **Enable CSRF in response:**
   ```python
   # In views.py
   from django.middleware.csrf import get_token
   
   def your_view(request):
       get_token(request)  # Ensure token is set
       return render(request, 'template.html')
   ```

---

### Issue 4: API Returns 403 Forbidden

**Symptoms:**
```
Delete response status: 403
```

**Causes:**
- CSRF token invalid or missing
- Token sent with wrong header name
- Token expired

**Fixes:**

1. **Verify header name (case-sensitive!):**
   ```javascript
   // ✅ Correct:
   'X-CSRFToken': csrfToken
   
   // ❌ Wrong:
   'X-csrf-token': csrfToken
   'X-CSRF-TOKEN': csrfToken
   ```

2. **Get fresh token:**
   ```javascript
   // Force new token
   location.reload()
   ```

3. **Check token is actually being sent:**
   ```javascript
   // In Network tab, check Request Headers:
   // Should have: X-CSRFToken: [token-value]
   ```

---

### Issue 5: API Returns 404 Not Found

**Symptoms:**
```
Delete response status: 404
```

**Causes:**
- Notification ID doesn't exist
- Wrong URL path
- Notification already deleted
- User doesn't own the notification

**Fixes:**

1. **Verify notification exists:**
   ```javascript
   // Check database
   window.NotificationDebug.listNotifications()
   
   // Or in Django shell:
   # python manage.py shell
   from dashboard.models import UserNotification
   UserNotification.objects.filter(id=1)
   ```

2. **Verify correct ID:**
   ```javascript
   // Get ID from element
   const btn = document.querySelector('.deleteNotificationBtn');
   console.log('ID:', btn.dataset.notificationId)
   ```

3. **Check user owns notification:**
   ```python
   # In Django shell:
   from django.contrib.auth import get_user_model
   from dashboard.models import UserNotification
   
   notif = UserNotification.objects.get(id=1)
   notif.user  # Should match current request.user
   ```

---

### Issue 6: API Returns 500 Internal Server Error

**Symptoms:**
```
Delete response status: 500
```

**Diagnosis:**
- Check Django logs: `tail -f logs/debug.log`
- Look for exception in error output

**Common Django Errors:**

1. **Model not found:**
   ```
   django.core.exceptions.ImproperlyConfigured: Model dashboard.UserNotification doesn't exist
   ```
   **Fix:** Run migrations
   ```bash
   python manage.py migrate
   ```

2. **User not authenticated:**
   ```
   AttributeError: 'AnonymousUser' object has no attribute 'id'
   ```
   **Fix:** Make sure user is logged in, check `@login_required` decorator

3. **Database locked:**
   ```
   sqlite3.OperationalError: database is locked
   ```
   **Fix:** Close other connections, restart server

---

### Issue 7: Delete Succeeds but Notification Still Visible

**Symptoms:**
```
Delete response data: {success: true}
BUT notification still shows
```

**Causes:**
- Reload function not working
- Element not actually removed from DOM
- Cache issue

**Fixes:**

1. **Check reload function:**
   ```javascript
   typeof window.loadNotifications  // Should be 'function'
   
   // Try manually:
   window.NotificationDebug.reloadNow()
   ```

2. **Manual refresh:**
   ```javascript
   // Force page reload
   location.reload()
   ```

3. **Clear browser cache:**
   ```
   Ctrl+Shift+Delete (or Cmd+Shift+Delete on Mac)
   ```

4. **Check for duplicate notifications:**
   ```javascript
   const id = 1;  // Notification ID
   document.querySelectorAll(`[data-notification-id="${id}"]`).length
   // Should return 0 if deleted
   ```

---

### Issue 8: Multiple Delete Requests at Once

**Symptoms:**
- Clicking delete multiple times quickly
- Multiple API requests sent
- Unpredictable behavior

**Fix:**
```javascript
// Add debouncing to delete function
// Current code already waits 300ms, but can add:

NotificationSystem.deleteNotification = (function() {
    let pending = {};
    
    return function(notificationId) {
        // Prevent duplicate requests
        if (pending[notificationId]) {
            console.log('Delete already in progress for:', notificationId);
            return;
        }
        
        pending[notificationId] = true;
        
        // ... existing code ...
        
        // Clear pending flag when done
        setTimeout(() => {
            delete pending[notificationId];
        }, 500);
    };
})();
```

---

## 📊 Testing Checklist

Before assuming there's a bug, test in order:

- [ ] **Test 1: Check notification exists**
  ```javascript
  window.NotificationDebug.listNotifications()
  ```

- [ ] **Test 2: Check element exists**
  ```javascript
  document.querySelector('[data-notification-id="1"]')  // Replace 1
  ```

- [ ] **Test 3: Check delete button attached**
  ```javascript
  window.NotificationDebug.checkListeners()
  ```

- [ ] **Test 4: Test API directly**
  ```javascript
  window.NotificationDebug.testDelete(1)  // Replace 1
  ```

- [ ] **Test 5: Check reload function**
  ```javascript
  typeof window.loadNotifications
  ```

- [ ] **Test 6: Manual delete + reload**
  ```javascript
  window.NotificationDebug.deleteNow(1)
  ```

---

## 🛠️ Advanced Debugging

### Enable Request Logging
```javascript
// In console, before testing:
const origFetch = fetch;
window.fetch = function(...args) {
    const [url, opts] = args;
    console.log('➡️  REQUEST:', opts?.method || 'GET', url);
    return origFetch.apply(this, args)
        .then(r => {
            console.log('⬅️  RESPONSE:', r.status, url);
            return r;
        });
};
```

### Monitor Storage
```javascript
// Check localStorage (if used)
console.log('localStorage:', JSON.stringify(localStorage, null, 2))

// Check sessionStorage
console.log('sessionStorage:', JSON.stringify(sessionStorage, null, 2))

// Check IndexedDB (if used)
// More complex, requires IDB API
```

### Check Network Security Policy
```javascript
// View Content Security Policy
document.currentScript.getAttribute('nonce')  // Check for nonce
// Or check headers in Network tab → Response Headers
```

---

## 🚨 When to Check Backend Logs

If all client-side debugging shows requests being sent correctly, but API returns error:

1. **Start Django development server with verbose logging:**
   ```bash
   python manage.py runserver --verbosity=3 2>&1 | tee debug.log
   ```

2. **Add logging to view:**
   ```python
   import logging
   logger = logging.getLogger(__name__)
   
   def delete_notification_view(request, notification_id):
       logger.debug(f"Delete request: user={request.user}, notif_id={notification_id}")
       # ... rest of code
   ```

3. **Check database directly:**
   ```bash
   python manage.py dbshell
   SELECT * FROM dashboard_usernotification WHERE id=1 AND user_id=5;
   ```

---

## 📞 Support Information

When reporting issues, include:

1. **Exact error message from console**
2. **Output of `NotificationDebug.inspect()`**
3. **Network tab screenshot showing POST request**
4. **Django server logs**
5. **Browser version**: 
   ```javascript
   navigator.userAgent
   ```

---

## ✅ Verification Checklist for Production

- [ ] All console.log statements are for debugging only
- [ ] No sensitive data in error messages
- [ ] Error messages are user-friendly
- [ ] Timeout handling for slow connections
- [ ] Rate limiting to prevent abuse
- [ ] Database cleanup of orphaned notifications
- [ ] Performance monitoring in place
- [ ] User permissions validated on backend

