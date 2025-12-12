// Global notification functions - Available everywhere

// Helper function to get CSRF token from cookies
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

function markAsRead(notificationId) {
    const csrftoken = getCookie('csrftoken') || document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
    fetch('/dashboard/notifications/' + notificationId + '/read/', {
        method: 'POST',
        credentials: 'same-origin',
        headers: {
            'X-CSRFToken': csrftoken,
            'Content-Type': 'application/json',
        }
    }).then(() => {
        // Store that notification was read in localStorage
        localStorage.setItem('notification_read_' + notificationId, 'true');
        
        // Reload notifications if in dropdown
        if (typeof loadNotifications === 'function') {
            const dropdown = document.getElementById('notificationsDropdown');
            if (dropdown) {
                dropdown.dataset.loaded = 'false';
            }
            loadNotifications();
            // Update badge count
            if (typeof updateNotificationBadge === 'function') {
                updateNotificationBadge();
            }
        } else {
            location.reload();
        }
    }).catch(error => {
        console.error('Error marking notification as read:', error);
    });
}

function handleNotificationClick(notificationId, redirectUrl) {
    const csrftoken = getCookie('csrftoken') || document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
    
    fetch('/dashboard/notifications/' + notificationId + '/read/', {
        method: 'POST',
        credentials: 'same-origin',
        headers: {
            'X-CSRFToken': csrftoken,
            'Content-Type': 'application/json',
        }
    }).then(response => {
        if (!response.ok) {
            throw new Error('Failed to mark as read');
        }
        return response.json();
    }).then(data => {
        if (data.success) {
            // Update badge immediately and store in localStorage
            if (typeof updateNotificationBadge === 'function') {
                updateNotificationBadge();
            }
            // Store that notification was read
            localStorage.setItem('notification_read_' + notificationId, 'true');
            
            // Then redirect if URL is provided and valid
            if (redirectUrl && redirectUrl !== 'null' && redirectUrl !== '' && redirectUrl !== 'None') {
                window.location.href = redirectUrl;
            } else {
                // Reload notifications if in dropdown
                if (typeof loadNotifications === 'function') {
                    const dropdown = document.getElementById('notificationsDropdown');
                    if (dropdown) {
                        dropdown.dataset.loaded = 'false';
                    }
                    loadNotifications();
                }
            }
        } else {
            // Still redirect even if marking as read fails
            if (redirectUrl && redirectUrl !== 'null' && redirectUrl !== '' && redirectUrl !== 'None') {
                window.location.href = redirectUrl;
            }
        }
    }).catch(error => {
        console.error('Error marking notification as read:', error);
        // Still redirect even if marking as read fails
        if (redirectUrl && redirectUrl !== 'null' && redirectUrl !== '' && redirectUrl !== 'None') {
            window.location.href = redirectUrl;
        }
    });
}

function deleteNotification(notificationId, eventObj) {
    if (eventObj) {
        eventObj.stopPropagation();
        eventObj.preventDefault();
    }
    const notificationItem = eventObj ? eventObj.target.closest('.notification-item') : document.querySelector(`.notification-item[onclick*="${notificationId}"]`);
    if (notificationItem) {
        notificationItem.classList.add('animate-fade-out');
        setTimeout(() => {
            // Get CSRF token
            const csrftoken = getCookie('csrftoken') || document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
            
            fetch('/dashboard/notifications/' + notificationId + '/delete/', {
                method: 'POST',
                credentials: 'same-origin',
                headers: {
                    'X-CSRFToken': csrftoken,
                    'Content-Type': 'application/json',
                }
            }).then(response => response.json()).then(data => {
                if (data.success) {
                    if (typeof loadNotifications === 'function') {
                        const dropdown = document.getElementById('notificationsDropdown');
                        if (dropdown) {
                            dropdown.dataset.loaded = 'false';
                        }
                        loadNotifications();
                        if (typeof updateNotificationBadge === 'function') {
                            updateNotificationBadge();
                        }
                    } else {
                        location.reload();
                    }
                } else {
                    if (notificationItem) notificationItem.classList.remove('animate-fade-out');
                    if (typeof showNotification === 'function') {
                        showNotification(data.message || 'Error deleting notification', 'error');
                    } else {
                        alert(data.message || 'Error deleting notification');
                    }
                }
            }).catch(error => {
                console.error('Error:', error);
                if (notificationItem) notificationItem.classList.remove('animate-fade-out');
                if (typeof showNotification === 'function') {
                    showNotification('Error deleting notification', 'error');
                } else {
                    alert('Error deleting notification');
                }
            });
        }, 200);
    }
}

function showDeleteAllModal() {
    const modal = document.getElementById('deleteAllModal');
    if (modal) {
        modal.classList.remove('hidden');
    }
}

function closeDeleteAllModal() {
    const modal = document.getElementById('deleteAllModal');
    if (modal) {
        modal.classList.add('hidden');
    }
}

function confirmDeleteAll() {
    const csrftoken = getCookie('csrftoken') || document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
    fetch('/dashboard/notifications/delete-all/', {
        method: 'POST',
        credentials: 'same-origin',
        headers: {
            'X-CSRFToken': csrftoken,
            'Content-Type': 'application/json',
        }
    }).then(response => response.json()).then(data => {
        if (data.success) {
            closeDeleteAllModal();
            if (typeof loadNotifications === 'function') {
                document.getElementById('notificationsDropdown').dataset.loaded = 'false';
                loadNotifications();
                if (typeof updateNotificationBadge === 'function') {
                    updateNotificationBadge();
                }
            } else {
                location.reload();
            }
        } else {
            alert(data.message || 'Error deleting notifications');
        }
    }).catch(error => {
        console.error('Error:', error);
        alert('Error deleting notifications');
    });
}

function markAllAsRead() {
    const csrftoken = getCookie('csrftoken') || document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
    
    fetch('/dashboard/notifications/mark-all-read/', {
        method: 'POST',
        credentials: 'same-origin',
        headers: {
            'X-CSRFToken': csrftoken,
            'Content-Type': 'application/json',
        }
    }).then(response => response.json()).then(data => {
        if (data.success) {
            // Reload notifications
            if (typeof loadNotifications === 'function') {
                const dropdown = document.getElementById('notificationsDropdown');
                if (dropdown) {
                    dropdown.dataset.loaded = 'false';
                }
                loadNotifications();
                // Update badge - it should disappear
                if (typeof updateNotificationBadge === 'function') {
                    updateNotificationBadge();
                }
            } else {
                location.reload();
            }
        } else {
            if (typeof showNotification === 'function') {
                showNotification(data.message || 'Error marking notifications as read', 'error');
            } else {
                alert(data.message || 'Error marking notifications as read');
            }
        }
    }).catch(error => {
        console.error('Error:', error);
        if (typeof showNotification === 'function') {
            showNotification('Error marking notifications as read', 'error');
        } else {
            alert('Error marking notifications as read');
        }
    });
}

function filterNotificationsByCategory(category) {
    // This is a placeholder - categories can be implemented later
    // For now, just reload notifications
    if (typeof loadNotifications === 'function') {
        const dropdown = document.getElementById('notificationsDropdown');
        if (dropdown) {
            dropdown.dataset.loaded = 'false';
        }
        loadNotifications();
    }
}

// Close modal when clicking outside
document.addEventListener('DOMContentLoaded', function() {
    const modal = document.getElementById('deleteAllModal');
    if (modal) {
        modal.addEventListener('click', function(e) {
            if (e.target === this) {
                closeDeleteAllModal();
            }
        });
    }
});
