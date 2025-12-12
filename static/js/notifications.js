/**
 * Notifications System JavaScript
 * Handles loading, marking as read, and deleting notifications
 */

// Global notification functions
function loadNotifications() {
    console.log("loadNotifications() called");
    const dropdown = document.getElementById('notificationsDropdown');
    if (!dropdown) {
        console.warn("Notifications dropdown not found");
        return;
    }

    // Check if already loaded
    if (dropdown.dataset.loaded === 'true') {
        console.log("Notifications already loaded, toggling visibility");
        dropdown.classList.toggle('hidden');
        return;
    }

    // Mark as loading
    dropdown.dataset.loading = 'true';
    dropdown.innerHTML = '<div class="p-4 text-center text-gray-500">Loading notifications...</div>';

    // Determine which endpoint to use based on user type
    let endpoint = '/dashboard/student/notifications/';
    
    // Try to detect user type from page content
    if (document.body.classList.contains('admin-page') || window.location.href.includes('admin')) {
        endpoint = '/dashboard/instructor/notifications/';
    } else if (document.body.classList.contains('instructor-page') || window.location.href.includes('teacher')) {
        endpoint = '/dashboard/instructor/notifications/';
    }

    fetch(endpoint)
        .then(response => {
            console.log("Notifications response status:", response.status);
            if (!response.ok) throw new Error('Network response was not ok');
            return response.text();
        })
        .then(html => {
            console.log("Notifications loaded, updating DOM");
            dropdown.innerHTML = html;
            dropdown.dataset.loaded = 'true';
            dropdown.classList.remove('hidden');
            
            // Re-attach event listeners for newly loaded content
            if (typeof window.attachNotificationListeners === 'function') {
                console.log("Re-attaching notification listeners");
                window.attachNotificationListeners();
            }
        })
        .catch(error => {
            console.error('Error loading notifications:', error);
            dropdown.innerHTML = '<div class="p-4 text-center text-red-500">Error loading notifications</div>';
            dropdown.dataset.loading = 'false';
        });
}

function updateNotificationBadge() {
    console.log("updateNotificationBadge() called");
    
    // Determine which endpoint to use
    let endpoint = '/dashboard/student/notifications/';
    if (document.body.classList.contains('admin-page') || window.location.href.includes('admin')) {
        endpoint = '/dashboard/instructor/notifications/';
    } else if (document.body.classList.contains('instructor-page') || window.location.href.includes('teacher')) {
        endpoint = '/dashboard/instructor/notifications/';
    }

    fetch(endpoint)
        .then(response => response.text())
        .then(html => {
            // Count unread notifications
            const tempDiv = document.createElement('div');
            tempDiv.innerHTML = html;
            const unreadCount = tempDiv.querySelectorAll('[data-notification-id]').length;
            
            // Update badge
            const badge = document.querySelector('[data-notification-count]');
            if (badge && unreadCount > 0) {
                badge.textContent = unreadCount;
                badge.classList.remove('hidden');
            } else if (badge) {
                badge.classList.add('hidden');
            }
            
            console.log("Badge updated with count:", unreadCount);
        })
        .catch(error => console.error('Error updating badge:', error));
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    console.log("Notifications.js initialized");
    
    // Set up notification dropdown toggle
    const notificationBell = document.querySelector('[data-notification-bell]');
    if (notificationBell) {
        notificationBell.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            console.log("Notification bell clicked");
            loadNotifications();
            return false;
        });
    }

    // Close dropdown when clicking outside
    document.addEventListener('click', function(e) {
        const dropdown = document.getElementById('notificationsDropdown');
        const bell = document.querySelector('[data-notification-bell]');
        
        if (dropdown && bell && !dropdown.contains(e.target) && !bell.contains(e.target)) {
            dropdown.classList.add('hidden');
        }
    });

    // Update badge on page load
    updateNotificationBadge();
    
    // Update badge periodically (every 30 seconds)
    setInterval(updateNotificationBadge, 30000);
});

// Export functions for global use
window.loadNotifications = loadNotifications;
window.updateNotificationBadge = updateNotificationBadge;
