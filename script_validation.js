
// ============================================================
// SOUND EFFECTS - Defined first at global scope
// ============================================================
function playScanCaptureSound() {
    try {
        const audio = new Audio('/static/sounds/success-sound-effect.mp3');
        audio.volume = 0.5; // Set volume to 50%
        audio.play().catch(err => console.log('Could not play capture sound:', err));
    } catch (e) {
        console.log('Could not play capture sound:', e);
    }
}

function playConfirmationSound() {
    return new Promise((resolve) => {
        try {
            const audio = new Audio('/static/sounds/registration-success-beep.mp3');
            audio.volume = 1.0; // Full volume
            
            // Resolve when audio ends or after timeout
            const audioEndedHandler = () => {
                console.log('[SOUND] Confirmation sound finished playing');
                audio.removeEventListener('ended', audioEndedHandler);
                resolve();
            };
            
            // Fallback timeout in case 'ended' event doesn't fire (3 seconds max)
            const timeoutId = setTimeout(() => {
                console.log('[SOUND] Confirmation sound timeout - proceeding anyway');
                audio.removeEventListener('ended', audioEndedHandler);
                resolve();
            }, 3000);
            
            audio.addEventListener('ended', audioEndedHandler);
            
            audio.play().catch(err => {
                console.log('Could not play confirmation sound:', err);
                clearTimeout(timeoutId);
                resolve(); // Resolve immediately if play fails
            });
        } catch (e) {
            console.log('Could not play confirmation sound:', e);
            resolve(); // Resolve immediately if exception occurs
        }
    });
}

function playEnrollmentSuccessSound() {
    try {
        const audio = new Audio('/static/sounds/success-sound-effect.mp3');
        audio.volume = 0.5; // Set volume to 50%
        audio.play().catch(err => console.log('Could not play success sound:', err));
    } catch (e) {
        console.log('Could not play success sound:', e);
    }
}

function playEnrollmentErrorSound() {
    try {
        const audio = new Audio('/static/sounds/error-sound-effect.mp3');
        audio.volume = 0.5; // Set volume to 50%
        audio.play().catch(err => console.log('Could not play error sound:', err));
    } catch (e) {
        console.log('Could not play error sound:', e);
    }
}
// ============================================================

function openRegistrationInstructorsModal() {
    const modal = document.getElementById('registrationInstructorsModal');
    const content = document.getElementById('registrationInstructorsContent');
    
    if (!modal) {
        console.error('Registration modal not found');
        return;
    }
    
    // Show loading state
    content.innerHTML = '<div class="text-center py-8 text-gray-500"><i class="fas fa-spinner fa-spin text-2xl mb-2"></i><p>Loading registration data...</p></div>';
    modal.classList.remove('hidden');
    
    // Fetch registration data
    fetch('{% url "dashboard:student_get_registration_instructors" %}')
        .then(r => r.json())
        .then(data => {
            if (!data.success) {
                content.innerHTML = `<div class="text-red-600 p-4 text-center">${data.message || 'Failed to load registration data.'}</div>`;
                return;
            }
            
            if (!data.instructors || data.instructors.length === 0) {
                content.innerHTML = '<div class="text-center py-8 text-gray-500"><i class="fas fa-inbox text-3xl mb-2"></i><p>No instructors have registration enabled for your courses.</p></div>';
                return;
            }
            
            // Build instructor cards
            let html = '<div class="space-y-3">';
            data.instructors.forEach(instructor => {
                const profilePic = instructor.profile_picture ? `<img src="${instructor.profile_picture}" alt="${instructor.name}" class="w-12 h-12 rounded-full object-cover">` : `<div class="w-12 h-12 rounded-full bg-blue-600 flex items-center justify-center text-white font-bold">${instructor.name.charAt(0)}</div>`;
                html += `
                    <div class="p-4 rounded-lg border-2 border-blue-200 bg-blue-50 hover:bg-blue-100 transition">
                        <div class="flex justify-between items-start mb-2">
                            <div class="flex items-center gap-3">
                                ${profilePic}
                                <div>
                                    <h4 class="font-bold text-lg text-gray-900">${instructor.name}</h4>
                                    <p class="text-xs text-gray-600">${instructor.courses.length} course(s)</p>
                                </div>
                            </div>
                            <button class="px-3 py-1 bg-blue-600 text-white rounded text-sm font-semibold hover:bg-blue-700 transition register-btn" data-instructor-id="${instructor.id}" data-instructor-name="${instructor.name}" data-instructor-picture="${instructor.profile_picture || ''}">
                                Register
                            </button>
                        </div>
                        <div class="space-y-1 ml-15">
                            ${instructor.courses.map(course => `
                                <div class="text-sm text-gray-700 flex items-center gap-2">
                                    <i class="fas fa-book text-blue-600"></i>
                                    <span class="font-medium">${course.code}</span> - ${course.name}
                                </div>
                            `).join('')}
                        </div>
                    </div>
                `;
            });
            html += '</div>';
            content.innerHTML = html;
            
            // CRITICAL FIX: Attach event listeners to register buttons instead of using onclick attributes
            // This prevents malformed onclick handlers with complex objects
            // Store instructors data globally for access in event handlers
            window.instructorsData = data.instructors;
            
            const registerButtons = content.querySelectorAll('.register-btn');
            if (registerButtons.length > 0) {
                registerButtons.forEach(btn => {
                    btn.addEventListener('click', function(e) {
                        e.preventDefault();
                        const instructorId = parseInt(this.getAttribute('data-instructor-id'));
                        const instructorName = this.getAttribute('data-instructor-name');
                        const instructorPicture = this.getAttribute('data-instructor-picture');
                        
                        // Find courses from global data
                        if (window.instructorsData && window.instructorsData.length > 0) {
                            const instructor = window.instructorsData.find(i => i.id === instructorId);
                            if (instructor && instructor.courses) {
                                openInstructorRegistration(instructorId, instructorName, instructorPicture, instructor.courses);
                            } else {
                                console.error('Instructor or courses not found');
                            }
                        }
                    });
                });
            }
        })
        .catch(err => {
            console.error('Error loading registration data:', err);
            content.innerHTML = '<div class="text-red-600 p-4 text-center">Error loading registration data.</div>';
        });
}

function closeRegistrationInstructorsModal() {
    const modal = document.getElementById('registrationInstructorsModal');
    if (modal) {
        modal.classList.add('hidden');
    }
}

function openInstructorRegistration(instructorId, instructorName, profilePicture, courses) {
    // Create a modal for this specific instructor showing their courses
    let modal = document.getElementById('instructorRegistrationDetailsModal');
    if (!modal) {
        modal = document.createElement('div');
        modal.id = 'instructorRegistrationDetailsModal';
        modal.className = 'fixed inset-0 bg-black bg-opacity-50 hidden z-[120] flex items-center justify-center p-4 backdrop-blur-sm';
        document.body.appendChild(modal);
    }
    
    const profilePic = profilePicture ? `<img src="${profilePicture}" alt="${instructorName}" class="w-16 h-16 rounded-full object-cover border-2 border-blue-300">` : `<div class="w-16 h-16 rounded-full bg-blue-600 flex items-center justify-center text-white font-bold text-2xl">${instructorName.charAt(0)}</div>`;
    
    let coursesHtml = courses.map(course => `
        <div class="p-3 rounded-lg border border-gray-200 bg-gray-50">
            <div class="font-semibold text-gray-900">${course.code} - ${course.name}</div>
        </div>
    `).join('');
    
    modal.innerHTML = `
        <div class="bg-white rounded-2xl shadow-2xl max-w-md w-full p-6">
            <div class="flex justify-between items-start mb-6">
                <div class="flex items-center gap-3">
                    ${profilePic}
                    <div>
                        <h3 class="text-xl font-bold text-gray-900">Register with</h3>
                        <p class="text-lg font-semibold text-blue-600">${instructorName}</p>
                    </div>
                </div>
                <button onclick="closeInstructorRegistrationModal()" class="text-gray-400 hover:text-gray-600">
                    <i class="fas fa-times text-lg"></i>
                </button>
            </div>
            
            <div class="space-y-3 mb-6">
                <h4 class="font-semibold text-gray-800 text-sm">Your courses with this instructor:</h4>
                ${coursesHtml}
            </div>
            
            <div class="space-y-3">
                <div class="grid grid-cols-2 gap-3">
                    <button onclick="openQRCodeRegistration(${instructorId}, '${instructorName.replace(/'/g, "\\'")}')" class="px-4 py-3 bg-blue-600 text-white rounded-lg font-semibold hover:bg-blue-700 transition flex items-center justify-center gap-2">
                        <i class="fas fa-qrcode"></i> QR Code
                    </button>
                    <button onclick="openBiometricRegistration(${instructorId}, '${instructorName.replace(/'/g, "\\'")}')" class="px-4 py-3 bg-purple-600 text-white rounded-lg font-semibold hover:bg-purple-700 transition flex items-center justify-center gap-2">
                        <i class="fas fa-fingerprint"></i> Biometric
                    </button>
                </div>
                <p class="text-xs text-gray-500 text-center">Choose registration method or use both</p>
            </div>
            <button onclick="closeInstructorRegistrationModal()" class="w-full mt-2 px-4 py-2 bg-gray-200 text-gray-700 rounded-lg font-semibold hover:bg-gray-300 transition">
                Close
            </button>
        </div>
    `;
    
    modal.classList.remove('hidden');
    modal.addEventListener('click', function(e) {
        if (e.target === modal) {
            closeInstructorRegistrationModal();
        }
    });
}

function closeInstructorRegistrationModal() {
    const modal = document.getElementById('instructorRegistrationDetailsModal');
    if (modal) {
        modal.classList.add('hidden');
    }
}

function openRegistrationMethods(instructorId, instructorName) {
    // Close modals first
    closeInstructorRegistrationModal();
    closeRegistrationInstructorsModal();
    
    // Set the registration mode to student self-registration
    window.isStudentRegisterMode = true;
    
    // Store instructor ID for backend reference
    window.currentInstructorId = instructorId;
    
    // Set student ID prefill from page data if available
    const studentIdPrefill = document.querySelector('[data-student-id]')?.getAttribute('data-student-id') || '';
    
    // Get all courses from the current registration modal (before we close it)
    // In the QR scanner, we'll use courseId 0 as a special marker for multi-course registration
    console.log('Opening QR Scanner in student registration mode for instructor:', instructorId);
    
    // Open QR Scanner - courseId of 0 indicates student registering with instructor (multi-course)
    if (typeof window.openQRScanner === 'function') {
        window.openQRScanner(0, studentIdPrefill, '');
    } else {
        console.error('QR Scanner function not available');
        alert('QR Scanner is not available. Please refresh the page and try again.');
    }
}

// Open QR Code Registration
function openQRCodeRegistration(instructorId, instructorName) {
    // Close modals first
    closeInstructorRegistrationModal();
    closeRegistrationInstructorsModal();
    
    // Set the registration mode to student self-registration
    window.isStudentRegisterMode = true;
    
    // Store instructor ID for backend reference
    window.currentInstructorId = instructorId;
    
    // Set student ID prefill from page data if available
    const studentIdPrefill = document.querySelector('[data-student-id]')?.getAttribute('data-student-id') || '';
    
    console.log('Opening QR Scanner for instructor:', instructorId);
    
    // Open QR Scanner - courseId of 0 indicates student registering with instructor (multi-course)
    if (typeof window.openQRScanner === 'function') {
        window.openQRScanner(0, studentIdPrefill, '');
    } else {
        console.error('QR Scanner function not available');
        alert('QR Scanner is not available. Please refresh the page and try again.');
    }
}

// Open Biometric Registration
function openBiometricRegistration(instructorId, instructorName) {
    console.log('Opening biometric registration for instructor:', instructorId, instructorName);
    
    // Close modals first
    closeInstructorRegistrationModal();
    closeRegistrationInstructorsModal();
    
    // Fetch enrolled courses for this student with this instructor
    console.log(`Fetching enrolled courses from: /dashboard/api/student/enrolled-courses/?instructor_id=${instructorId}`);
    
    fetch(`/dashboard/api/student/enrolled-courses/?instructor_id=${instructorId}`)
        .then(response => {
            console.log('API response status:', response.status);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            console.log('API response data:', data);
            
            if (!data.success) {
                console.error('API error:', data.message);
                showNotification(`Error loading courses: ${data.message}`, 'error');
                return;
            }
            
            if (!data.courses || data.courses.length === 0) {
                console.warn('No enrolled courses found with this instructor', instructorId);
                showNotification('You are not enrolled in any courses with this instructor', 'warning');
                return;
            }
            
            console.log(`Found ${data.courses.length} enrolled courses`);
            
            // Store course IDs for enrollment
            window.enrollmentCourseIds = data.courses.map(c => c.id);
            
            // Create biometric registration modal (simplified without course selection)
            let modal = document.getElementById('biometricRegistrationModal');
            if (!modal) {
                modal = document.createElement('div');
                modal.id = 'biometricRegistrationModal';
                modal.className = 'fixed inset-0 bg-black bg-opacity-50 hidden z-[120] flex items-center justify-center p-4 backdrop-blur-sm overflow-y-auto';
                document.body.appendChild(modal);
            }
            
            // Build course list display
            let coursesListHtml = data.courses.map(course => `
                <div class="p-3 rounded-lg border border-green-200 bg-green-50">
                    <div class="font-semibold text-gray-900">${course.code}</div>
                    <div class="text-sm text-gray-600">${course.name}</div>
                </div>
            `).join('');
            
            modal.innerHTML = `
                <div class="bg-white rounded-xl shadow-xl max-w-sm w-full p-6">
                    <!-- Header -->
                    <div class="flex justify-between items-center mb-6">
                        <h3 class="text-xl font-bold text-gray-900 flex items-center gap-2">
                            <i class="fas fa-fingerprint text-purple-600"></i> Fingerprint
                        </h3>
                        <button onclick="closeBiometricRegistrationModal()" class="text-gray-400 hover:text-gray-600">
                            <i class="fas fa-times text-lg"></i>
                        </button>
                    </div>
                    
                    <!-- Scan Icon and Status -->
                    <div class="flex flex-col items-center justify-center py-6 mb-4 bg-purple-50 rounded-lg">
                        <i id="scanIcon" class="fas fa-fingerprint text-5xl text-purple-600 mb-3"></i>
                        <p id="scanTitle" class="text-base font-semibold text-gray-800">Ready to Scan</p>
                          <p id="scanSubtitle" class="text-xs text-gray-600 mt-1">0/3</p>
                    <div class="mb-4">
                        <div class="flex flex-col items-center justify-center p-6 bg-purple-50 rounded-lg" id="progressContainer">
                            <!-- Progress Bar -->
                            <div class="w-full mb-4">
                                <div class="flex justify-between items-center mb-2">
                                    <span class="text-xs font-semibold text-gray-700">Scan Progress</span>
                                    <span id="progressPercent" class="text-xs font-bold text-purple-600">0%</span>
                                </div>
                                <div class="w-full bg-gray-200 rounded-full h-3 overflow-hidden">
                                    <div id="progressBar" class="bg-gradient-to-r from-purple-500 to-purple-600 h-full rounded-full transition-all duration-300" style="width: 0%"></div>
                                </div>
                            </div>
                            
                            <div class="text-6xl font-bold text-purple-600 mb-2" id="percentageDisplay" style="display: none;">0%</div>
                            <div class="text-sm text-gray-600 text-center mb-2">
                                <span id="enrollmentCounter" class="text-lg font-semibold text-purple-600">0/3</span> scans completed
                            </div>
                            <div id="enrollmentStatus" class="text-xs text-gray-600 text-center">
                                Ready to start
                            </div>
                        </div>
                    </div>
                    
                    <!-- Results -->
                    <div id="confirmationsList" class="space-y-1 mb-4 max-h-24 overflow-y-auto hidden">
                        <!-- Results appear here -->
                    </div>
                    
                    <!-- Buttons -->
                    <div class="space-y-2">
                        <button id="startEnrollBtn" onclick="startBiometricEnrollment('${instructorName.replace(/'/g, "\\'")}')" class="w-full px-4 py-2.5 bg-purple-600 hover:bg-purple-700 text-white font-semibold text-sm rounded-lg transition">
                            <i class="fas fa-fingerprint mr-1"></i> Start 3-Capture Enrollment
                        </button>
                        <button onclick="closeBiometricRegistrationModal()" class="w-full px-4 py-2 bg-gray-100 text-gray-700 font-medium text-sm rounded-lg hover:bg-gray-200 transition">
                            Cancel
                        </button>
                    </div>
                </div>
            `;
            
            modal.classList.remove('hidden');
            modal.addEventListener('click', function(e) {
                if (e.target === modal) {
                    closeBiometricRegistrationModal();
                }
            });
        })
        .catch(error => {
            console.error('Error fetching courses:', error);
            showNotification(`Error loading courses: ${error.message}`, 'error');
        });
}

// Close Biometric Registration Modal
function closeBiometricRegistrationModal() {
    console.log('[ENROLLMENT] ===== CLOSING BIOMETRIC MODAL =====');
    const modal = document.getElementById('biometricRegistrationModal');
    if (modal) {
        modal.classList.add('hidden');
    }
    
    // CRITICAL: Reset ALL enrollment state variables IMMEDIATELY
    console.log('[ENROLLMENT] Resetting frontend state variables');
    window.enrollmentCompleted = false;
    window.fingerDetectedShown = false;
    window.isProcessing = false;
    window.enrollmentInErrorState = false;
    window.enrollmentInProgress = false;
    window.enrollmentConfirmedSuccessfully = false;
    confirmations = 0;
    lastEnrollmentCancelTime = Date.now();  // Track cancel time to allow retry after delay
    
    // CRITICAL: Close WebSocket IMMEDIATELY to stop any further UI updates
    if (currentWebSocket) {
        try {
            console.log('[ENROLLMENT] Closing WebSocket connection');
            currentWebSocket.close();
            currentWebSocket = null;
        } catch (e) {
            console.warn('[ENROLLMENT] Error closing WebSocket:', e);
        }
    }
    
    // SIMPLIFIED: No longer send cancel to ESP32
    // Just close the modal and reset frontend state
    // ESP32 will naturally timeout and return to waiting state
    console.log('[ENROLLMENT] Modal closed - ESP32 will timeout and reset automatically');
    
    // Reset enrollment lock for this instructor
    setInstructorEnrollmentInProgress(false);
    console.log('[ENROLLMENT] ===== MODAL CLOSED - FRONTEND RESET =====');
}


// Global flag to prevent simultaneous enrollments (per instructor)
let currentWebSocket = null;  // Track current WebSocket connection
let confirmations = 0;  // Track number of successful fingerprint captures
let lastEnrollmentCancelTime = 0;  // Track when last enrollment was cancelled to allow retry after delay
let enrollmentConfirmedSuccessfully = false;  // Flag to track if confirmation succeeded
window.enrollmentInProgress = false;  // CRITICAL: Prevent multiple simultaneous enrollment requests

// Helper function to get instructor ID from page
function getInstructorId() {
    // First try: look for instructor ID in the enrollment context (most reliable)
    if (window.currentInstructorId) {
        console.log('[INSTRUCTOR] Using cached instructor ID:', window.currentInstructorId);
        return window.currentInstructorId;
    }
    
    // Second try: look for data attribute on body
    if (document.body.dataset.instructorId) {
        window.currentInstructorId = document.body.dataset.instructorId;
        console.log('[INSTRUCTOR] Found instructor ID from body data:', window.currentInstructorId);
        return window.currentInstructorId;
    }
    
    // Third try: look for element with instructor ID
    const instructorIdElement = document.getElementById('instructorId');
    if (instructorIdElement) {
        const id = instructorIdElement.textContent || instructorIdElement.value;
        if (id) {
            window.currentInstructorId = id;
            console.log('[INSTRUCTOR] Found instructor ID from element:', window.currentInstructorId);
            return window.currentInstructorId;
        }
    }
    
    // Fourth try: from URL parameters
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.has('instructor_id')) {
        window.currentInstructorId = urlParams.get('instructor_id');
        console.log('[INSTRUCTOR] Found instructor ID from URL:', window.currentInstructorId);
        return window.currentInstructorId;
    }
    
    // Fifth try: from page title or heading
    const heading = document.querySelector('h1, h2, h3');
    if (heading && heading.textContent) {
        const text = heading.textContent;
        const match = text.match(/(\d+)/);
        if (match) {
            window.currentInstructorId = 'instructor_' + match[1];
            console.log('[INSTRUCTOR] Extracted instructor ID from heading:', window.currentInstructorId);
            return window.currentInstructorId;
        }
    }
    
    // Fallback
    console.warn('[INSTRUCTOR] Could not detect instructor ID - using fallback');
    window.currentInstructorId = 'default_instructor';
    return window.currentInstructorId;
}

// Get current student ID from page data
function getCurrentStudentId() {
    const studentId = document.querySelector('[data-student-id]')?.getAttribute('data-student-id');
    return studentId || 'unknown_student';
}

// Helper function to get unique enrollment state key for this instructor
function getEnrollmentStateKey() {
    const instructorId = getInstructorId();
    return `enrollment_in_progress_instructor_${instructorId}`;
}

// Helper function to check if ANOTHER STUDENT is currently enrolling
// Returns true only if a DIFFERENT student is enrolling
// Returns false if THIS student is enrolling or no one is (allows same user through)
function isInstructorEnrollmentInProgress() {
    const key = getEnrollmentStateKey();
    const enrollingStudentId = sessionStorage.getItem(key);
    const currentStudentId = getCurrentStudentId();
    
    // If no one is enrolling, allow through
    if (!enrollingStudentId) {
        return false;
    }
    
    // CRITICAL: If THE SAME student is enrolling, allow them through
    // This prevents blocking a user's own confirmation
    if (enrollingStudentId === currentStudentId) {
        console.log('[ENROLLMENT] Same student enrolling - allowing. Student:', currentStudentId);
        return false;
    }
    
    // A DIFFERENT student is enrolling - block
    console.log('[ENROLLMENT] Different student enrolling! Current:', currentStudentId, 'Enrolling:', enrollingStudentId);
    return true;
}

// Helper function to set enrollment status for THIS instructor
function setInstructorEnrollmentInProgress(status) {
    const key = getEnrollmentStateKey();
    const currentStudentId = getCurrentStudentId();
    
    if (status) {
        console.log('[ENROLLMENT] SETTING lock - Student:', currentStudentId);
        sessionStorage.setItem(key, currentStudentId);
    } else {
        console.log('[ENROLLMENT] CLEARING lock - Student:', currentStudentId);
        sessionStorage.removeItem(key);
    }
}

// Clear enrollment lock if page unloads (only for the student who initiated it)
window.addEventListener('beforeunload', () => {
    const key = getEnrollmentStateKey();
    const enrollingStudentId = sessionStorage.getItem(key);
    const currentStudentId = getCurrentStudentId();
    if (enrollingStudentId === currentStudentId) {
        setInstructorEnrollmentInProgress(false);
    }
});

// Also clear old stale locks on page load (older than 30 minutes)
window.addEventListener('load', () => {
    const key = getEnrollmentStateKey();
    const timestamp = sessionStorage.getItem(key + '_timestamp');
    if (timestamp) {
        const ageMinutes = (Date.now() - parseInt(timestamp)) / 60000;
        if (ageMinutes > 30) {
            console.log('[ENROLLMENT] Stale lock detected (age:', ageMinutes.toFixed(1), 'min) - clearing');
            setInstructorEnrollmentInProgress(false);
        }
    }
});

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

// Start Biometric Enrollment - Main entry point for Start button
async function startBiometricEnrollment(instructorName) {
    console.log('[ENROLLMENT] Starting biometric enrollment');
    
    // CRITICAL: Only check lock if NOT confirming an existing enrollment
    // When confirming, we're already in the middle of enrollment, so lock should be bypassed
    if (!window.isConfirmingEnrollment && isInstructorEnrollmentInProgress()) {
        const instructorId = getInstructorId();
        const key = getEnrollmentStateKey();
        console.warn('[ENROLLMENT] Enrollment is in progress for instructor:', instructorId, 'Key:', key);
        showNotification('Another student is currently registering under this instructor. Please wait for them to finish.', 'warning');
        console.log('[ENROLLMENT] Enrollment blocked - another student under same instructor is in progress');
        return;
    }
    
    // Reset confirmation flag if we're starting a new enrollment
    window.isConfirmingEnrollment = false;
    
    // Get pre-stored enrolled course IDs
    const courseIds = window.enrollmentCourseIds;
    if (!courseIds || courseIds.length === 0) {
        showNotification('No courses found for enrollment', 'warning');
        return;
    }
    
    console.log(`[ENROLLMENT] Enrolling in ${courseIds.length} courses:`, courseIds);
    
    // Check for existing fingerprints
    checkExistingFingerprints(courseIds);
}

// Check for existing fingerprints for this student-instructor combination
function checkExistingFingerprints(courseIds) {
    const studentId = document.querySelector('[data-student-id]')?.getAttribute('data-student-id') || '';
    
    if (!studentId || !courseIds || courseIds.length === 0) {
        // Proceed without checking if no student ID or courses
        proceedWithEnrollment(courseIds);
        return;
    }
    
    console.log('[FINGERPRINT CHECK] Checking for existing fingerprints for student:', studentId);
    
    // Check if student has existing biometric enrollment
    fetch('{% url "dashboard:api_check_biometric" %}', {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCookie('csrftoken'),
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            student_id: studentId,
            course_ids: courseIds
        })
    })
    .then(response => response.json())
    .then(data => {
        console.log('[FINGERPRINT CHECK] Response:', data);
        
        if (data.has_existing_registration) {
            // Show warning that they can re-register and old fingerprint will be replaced
            showExistingFingerprintWarning(courseIds, data.instructor_name || 'this instructor');
        } else {
            // No existing fingerprint, proceed normally
            proceedWithEnrollment(courseIds);
        }
    })
    .catch(error => {
        console.warn('[FINGERPRINT CHECK] Could not check existing fingerprints, proceeding anyway:', error);
        // Proceed even if check fails - don't block enrollment
        proceedWithEnrollment(courseIds);
    });
}

// Show warning if student already has a fingerprint registered
function showExistingFingerprintWarning(courseIds, instructorName) {
    const modal = document.createElement('div');
    modal.id = 'existingFingerprintWarningModal';
    modal.className = 'fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-[999]';
    modal.innerHTML = `
        <div class="bg-white rounded-lg shadow-2xl max-w-md w-full mx-4 p-6">
            <div class="text-center mb-4">
                <i class="fas fa-fingerprint text-5xl text-orange-500 mb-2 block"></i>
                <h2 class="text-xl font-bold text-gray-800">Existing Fingerprint Detected</h2>
            </div>
            
            <p class="text-gray-600 text-center mb-6">
                You have already registered a fingerprint for <strong>${instructorName}</strong>. 
                <br><br>
                If you register a different fingerprint now, your previous fingerprint will be <strong>automatically deleted</strong> and replaced with the new one.
            </p>
            
            <p class="text-sm text-gray-500 text-center mb-6 bg-blue-50 p-3 rounded">
                <i class="fas fa-info-circle mr-1"></i>
                The old fingerprint will be removed from the sensor, freeing up space for future registrations.
            </p>
            
            <div class="flex gap-3">
                <button onclick="closeExistingFingerprintWarning()" 
                        class="flex-1 px-4 py-2 bg-gray-300 hover:bg-gray-400 text-gray-800 font-semibold rounded-lg transition">
                    <i class="fas fa-arrow-left mr-1"></i> Go Back
                </button>
                <button onclick="proceedWithEnrollmentAfterWarning()" 
                        class="flex-1 px-4 py-2 bg-orange-600 hover:bg-orange-700 text-white font-semibold rounded-lg transition">
                    <i class="fas fa-fingerprint mr-1"></i> Continue
                </button>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
    console.log('[ENROLLMENT] Showing existing fingerprint warning');
}

function closeExistingFingerprintWarning() {
    const modal = document.getElementById('existingFingerprintWarningModal');
    if (modal) {
        modal.remove();
    }
}

function proceedWithEnrollmentAfterWarning() {
    closeExistingFingerprintWarning();
    const courseIds = window.enrollmentCourseIds;
    proceedWithEnrollment(courseIds);
}

// Proceed with actual enrollment
async function proceedWithEnrollment(courseIds) {
    const btn = document.getElementById('startEnrollBtn');
    // Get ESP32 IP from Django context, with fallback
    let R307_IP = '{{ esp32_ip|default:"192.168.1.9" }}';
    if (!R307_IP || R307_IP.includes('{{')) {
        // Fallback if template variable isn't available
        R307_IP = localStorage.getItem('esp32_ip') || '192.168.1.9';
    }
    console.log('[ENROLLMENT] Using ESP32 IP:', R307_IP);
    
    // Store in window context so submitBiometricEnrollment can access it
    window.ESP32_IP = R307_IP;
    
    // CRITICAL SAFETY CHECK: Prevent multiple simultaneous enrollments
    if (window.enrollmentInProgress === true) {
        console.warn('[ENROLLMENT] âš ï¸ Enrollment already in progress! Ignoring duplicate request');
        return;
    }
    
    // Set flag IMMEDIATELY to prevent re-entry
    window.enrollmentInProgress = true;
    console.log('[ENROLLMENT] ===== ENROLLMENT REQUEST STARTED =====');
    
    // CRITICAL: Check if enrollment was just cancelled - wait for ESP32 to reset (4 second minimum)
    // Increased from 2.5s to 4s to allow ESP32 enrollment loop to fully exit and reset
    const timeSinceCancel = Date.now() - lastEnrollmentCancelTime;
    const REQUIRED_RESET_TIME = 4000;  // 4 seconds for ESP32 to fully exit enrollment and reset state
    
    if (timeSinceCancel < REQUIRED_RESET_TIME) {
        const waitTime = REQUIRED_RESET_TIME - timeSinceCancel;
        console.log(`[ENROLLMENT] Last enrollment cancelled ${timeSinceCancel}ms ago. Waiting ${waitTime}ms for ESP32 to fully reset...`);
        
        // Reset the in-progress flag since we're waiting
        window.enrollmentInProgress = false;
        
        // Disable start button during reset
        if (btn) {
            btn.disabled = true;
            const originalText = btn.innerHTML;
            const remainSeconds = Math.ceil(waitTime / 1000);
            btn.innerHTML = `<i class="fas fa-spinner fa-spin mr-1"></i> Sensor resetting (${remainSeconds}s)...`;
            
            // Update countdown every 500ms
            const countdownInterval = setInterval(() => {
                const remaining = Date.now() - lastEnrollmentCancelTime;
                if (remaining >= REQUIRED_RESET_TIME) {
                    clearInterval(countdownInterval);
                    btn.disabled = false;
                    btn.innerHTML = originalText;
                } else {
                    const secs = Math.ceil((REQUIRED_RESET_TIME - remaining) / 1000);
                    btn.innerHTML = `<i class="fas fa-spinner fa-spin mr-1"></i> Sensor resetting (${secs}s)...`;
                }
            }, 500);
        }
        
        showNotification('Sensor is resetting. Please wait...', 'info');
        setTimeout(() => {
            proceedWithEnrollment(courseIds);
        }, waitTime);
        return;
    }
    
    // CRITICAL: Only check lock if NOT confirming an existing enrollment
    // When confirming, we're already in the middle of enrollment, so lock should be bypassed
    if (!window.isConfirmingEnrollment && isInstructorEnrollmentInProgress()) {
        console.warn('[ENROLLMENT] Enrollment already in progress for this instructor');
        window.enrollmentInProgress = false;
        showNotification('Enrollment is already in progress for your instructor. Please wait.', 'warning');
        return;
    }
    
    // Reset confirmation flag if we're starting a new enrollment
    window.isConfirmingEnrollment = false;
    
    // Mark enrollment as in progress for THIS instructor
    setInstructorEnrollmentInProgress(true);
    
    if (!courseIds || courseIds.length === 0) {
        console.error('[ENROLLMENT] No course IDs provided');
        window.enrollmentInProgress = false;
        setInstructorEnrollmentInProgress(false);
        showNotification('No courses found for enrollment', 'warning');
        return;
    }
    
    console.log(`[ENROLLMENT] Enrolling in ${courseIds.length} courses:`, courseIds);
    
    const statusEl = document.getElementById('enrollmentStatus');
    const percentageDisplay = document.getElementById('percentageDisplay');
    const counter = document.getElementById('enrollmentCounter');
    const scanIcon = document.getElementById('scanIcon');
    const scanTitle = document.getElementById('scanTitle');
    const scanSubtitle = document.getElementById('scanSubtitle');
    
    // Check if all required elements exist
    if (!btn || !statusEl || !percentageDisplay || !counter || !scanIcon || !scanTitle || !scanSubtitle) {
        console.error('[ENROLLMENT] Missing required modal elements');
        showNotification('Error: Modal elements missing', 'danger');
        setInstructorEnrollmentInProgress(false);
        return;
    }
    
    console.log('[ENROLLMENT] All modal elements found');
    
    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin mr-1"></i> Sending request...';
    
    // CRITICAL: Hide cancel button during active enrollment to prevent user interruption
    const cancelBtn = document.querySelector('button[onclick="closeBiometricRegistrationModal()"]');
    if (cancelBtn) {
        console.log('[ENROLLMENT] Hiding Cancel button during active enrollment');
        cancelBtn.style.display = 'none';
    }
    
    // Reset enrollment state flags
    window.fingerDetectedShown = false;
    window.enrollmentCompleted = false;  // Reset completion flag for new attempt
    window.enrollmentInErrorState = false;  // Reset error flag for new attempt
    window.isProcessing = false;  // Track if we're currently processing a fingerprint
    window.enrollmentConfirmedSuccessfully = false;  // Reset confirmation flag for new attempt
    confirmations = 0;  // Reset scan counter for new enrollment
    
    // Generate unique enrollment ID
    const enrollmentId = `enrollment_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    const biometricTemplate = `template_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    
    // Store biometric template globally for use in handleEnrollmentComplete
    window.biometricTemplate = biometricTemplate;
    
    console.log('[ENROLLMENT] Generated enrollment ID:', enrollmentId);
    console.log('[ENROLLMENT] Step 1: UI setup...');
    
    // Update UI to show waiting for finger
    scanIcon.innerHTML = '<i class="fas fa-fingerprint text-5xl text-blue-500 mb-3 animate-pulse"></i>';
    scanTitle.textContent = 'Ready to Scan';
    scanSubtitle.textContent = 'Place your finger on sensor';
    statusEl.innerHTML = '<i class="fas fa-fingerprint mr-2"></i> Waiting for finger...';
    percentageDisplay.style.display = 'none';
    counter.textContent = '0/3';
    console.log('[ENROLLMENT] Step 1: âœ“ UI setup complete');
    
    console.log('[ENROLLMENT] Step 2: Creating WebSocket URL...');
    // Create WebSocket connection for real-time updates
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    let wsHost = window.location.host;
    if (!wsHost.includes(':') && window.location.hostname === 'localhost') {
        wsHost = 'localhost:8000';
    }
    const wsUrl = `${protocol}//${wsHost}/ws/biometric/enrollment/${enrollmentId}/`;
    
    console.log(`[ENROLLMENT] Step 2: âœ“ WebSocket URL: ${wsUrl}`);
    console.log(`[ENROLLMENT] Step 3: Closing previous WebSocket...`);
    
    // Close any previous WebSocket connections
    if (currentWebSocket) {
        try {
            currentWebSocket.close();
        } catch (e) {
            console.warn('[ENROLLMENT] Could not close previous socket:', e);
        }
    }
    console.log('[ENROLLMENT] Step 3: âœ“ Previous WebSocket closed');
    
    console.log('[ENROLLMENT] Step 4: Skipping reset - no longer sending cancel to ESP32');
    
    console.log('[ENROLLMENT] Step 5: Now sending enrollment request directly...');
    console.log('[ENROLLMENT] ===== NOW SENDING ENROLLMENT REQUEST TO ESP32 =====');
    
    // CRITICAL: Send enrollment request to ESP32 FIRST before WebSocket
    // This ensures ESP32 knows about the enrollment before we try to get updates
    const enrollPayload = {
        slot: 1,
        template_id: enrollmentId
    };
    
    console.log('[ENROLLMENT] Sending enrollment request to ESP32 FIRST...');
    console.log('[ENROLLMENT] Target: http://' + R307_IP + '/enroll');
    console.log('[ENROLLMENT] Payload:', enrollPayload);
    
    try {
        // Use AbortController for proper timeout handling
        const controller = new AbortController();
        const timeoutId = setTimeout(() => {
            console.error('[ENROLLMENT] Request timeout - no response from ESP32 after 10 seconds');
            controller.abort();
        }, 10000);
        
        const response = await fetch(`http://${R307_IP}/enroll`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(enrollPayload),
            signal: controller.signal
        });
        
        clearTimeout(timeoutId);
        console.log('[ENROLLMENT] ESP32 responded with status:', response.status);
        
        if (!response.ok) {
            const errorText = await response.text();
            console.error('[ENROLLMENT] ESP32 error response:', errorText);
            throw new Error(`ESP32 returned ${response.status}: ${errorText}`);
        }
        
        const data = await response.json();
        console.log('[ENROLLMENT] âœ“ ESP32 accepted enrollment:', data);
    } catch (error) {
        console.error('[ENROLLMENT] âœ— FAILED to send enrollment to ESP32');
        console.error('[ENROLLMENT] Error type:', error.name);
        console.error('[ENROLLMENT] Error message:', error.message);
        console.error('[ENROLLMENT] Full error:', error);
        
        if (error.name === 'AbortError') {
            showNotification('ESP32 timeout - sensor not responding', 'danger');
        } else if (error.message.includes('Failed to fetch')) {
            showNotification('Cannot reach ESP32 at 192.168.1.9 - check WiFi', 'danger');
        } else {
            showNotification('ESP32 enrollment failed: ' + error.message, 'danger');
        }
        setInstructorEnrollmentInProgress(false);
        console.log('[ENROLLMENT] âœ— Enrollment request FAILED - exiting');
        return;
    }
    
    console.log('[ENROLLMENT] Step 6: âœ“ Enrollment request sent successfully');
    console.log('[ENROLLMENT] Step 7: Now creating WebSocket for real-time updates...');
    
    // NOW create the WebSocket connection
    const socket = new WebSocket(wsUrl);
    currentWebSocket = socket;  // Store reference globally
    
    // Track if this specific socket is ready to receive enrollment messages
    let socketReady = false;
    let espRequestSent = true;  // Already sent above!
    let enrollmentStartTime = Date.now();  // Track when enrollment started (to ignore early errors)
    
    console.log('[WEBSOCKET] Creating WebSocket connection to:', wsUrl);
    
    socket.onopen = (event) => {
        console.log('[WEBSOCKET] âœ“ Connection established');
        console.log('[WEBSOCKET] Socket ready state:', socket.readyState);
        btn.innerHTML = '<i class="fas fa-fingerprint mr-1"></i> Place finger now...';
        
        console.log('[ENROLLMENT] Enrollment request already sent to ESP32');
        console.log('[ENROLLMENT] Waiting for WebSocket updates from ESP32...');
        
        // Give Django a moment to set up the enrollment group
        setTimeout(() => {
            socketReady = true;
            console.log('[ENROLLMENT] WebSocket ready to receive enrollment messages');
        }, 500);
    };
    
    socket.onerror = (event) => {
        console.error('[WEBSOCKET] âœ— WebSocket error:', event);
        showNotification('WebSocket error - check browser console', 'danger');
    };
    
    socket.onclose = (event) => {
        console.log('[WEBSOCKET] Connection closed:', event.code, event.reason);
    };
    
    socket.onmessage = (event) => {
        try {
            console.log('[WEBSOCKET] Raw message data received:', event.data);
            const message = JSON.parse(event.data);
            console.log('[WEBSOCKET] Parsed message:', JSON.stringify(message));
            
            // CRITICAL: Wait for socket to be fully ready before processing messages
            // This prevents stale error messages from being shown immediately after start
            if (!socketReady) {
                console.log('[WEBSOCKET] Socket not ready yet, ignoring early message. Will process when ready.');
                return;
            }
            
            // CRITICAL: Ignore error messages that come in too early (first 1.5 seconds)
            // This filters out spurious/stale errors from ESP32 startup
            const timeSinceStart = Date.now() - enrollmentStartTime;
            if ((message.success === false || message.error) && timeSinceStart < 1500) {
                console.log(`[WEBSOCKET] Ignoring early error (${timeSinceStart}ms after start) - likely stale message:`, message);
                return;
            }
            
            // CRITICAL: Only process messages if this is the current active socket
            if (socket !== currentWebSocket) {
                console.log('[WEBSOCKET] Ignoring message from old socket connection');
                return;
            }
            
            // CRITICAL: Check if enrollment is already complete to prevent overwriting success state
            const btn = document.getElementById('startEnrollBtn');
            if (btn && btn.innerHTML.includes('Confirm') && btn.className.includes('green')) {
                console.log('[ENROLLMENT] Already at success state (Confirm button) - ignoring further messages');
                return;  // Don't process any more messages after success
            }
            
            // Track if we've shown the "Finger Detected" message to avoid duplicates
            window.fingerDetectedShown = window.fingerDetectedShown || false;
            
            // SIMPLIFIED MESSAGE FLOW - Only show 3 types of messages:
            // 1. "Finger Detected" - when finger is first placed
            // 2. "Processing" - while processing the fingerprint
            // 3. Error messages - if something goes wrong
            
            const statusEl = document.getElementById('enrollmentStatus');
            
            // If successful enrollment - CHECK THIS FIRST BEFORE ERROR CHECKS
            // CRITICAL: Only process enrollment_complete events, NOT scan_update events
            if (message.success === true && message.type === 'enrollment_complete') {
                console.log('[ENROLLMENT] âœ“âœ“âœ“ Fingerprint enrolled successfully! âœ“âœ“âœ“');
                console.log('[ENROLLMENT] WebSocket received enrollment_complete - calling handleEnrollmentComplete');
                
                // Call handleEnrollmentComplete which will call submitBiometricEnrollment
                // This saves the biometric data for all courses and reloads the page
                handleEnrollmentComplete(message);
                
                // LOCK THE STATE: Set a flag so retry handler won't override
                window.enrollmentCompleted = true;
                return;  // Stop processing any further messages
            }
            // Handle scan_update messages - individual fingerprint captures
            else if (message.type === 'scan_update') {
                console.log('[WEBSOCKET] Processing scan_update message:', message);
                handleScanUpdate(message);
                return;
            }
            // If enrollment failed - ONLY if not already successful
            // CRITICAL: Do NOT show error if we're currently processing a fingerprint
            // Also ignore errors that are just status messages (like quality warnings)
            // Only show errors that indicate actual failure (bad image, model creation failed, etc.)
            else if (!window.enrollmentCompleted && !window.isProcessing && (message.success === false || message.error)) {
                // CRITICAL: Filter out non-critical error messages that should be ignored during processing
                const msgLower = (message.message || '').toLowerCase();
                const isCriticalError = 
                    msgLower.includes('failed') || 
                    msgLower.includes('bad') || 
                    msgLower.includes('timeout') ||
                    msgLower.includes('error') ||
                    message.error_code; // Has explicit error code
                
                // If it's not a critical error, just log it and ignore
                if (!isCriticalError && message.message) {
                    console.log('[ENROLLMENT] Ignoring non-critical error/warning:', message);
                    return;
                }
                
                console.log('[ENROLLMENT] Fingerprint capture failed (critical error):', message);
                
                // CRITICAL: Mark that we're in error state (prevents retry from being shown prematurely)
                window.enrollmentInErrorState = true;
                
                // Only show error message - not intermediate messages
                // Update icon to error
                const scanIcon = document.getElementById('scanIcon');
                if (scanIcon) {
                    scanIcon.innerHTML = '<i class="fas fa-exclamation-circle text-5xl text-red-500 mb-3"></i>';
                }
                
                // Update status message with error
                if (statusEl) {
                    statusEl.innerHTML = `<i class="fas fa-exclamation mr-2"></i> ${message.message || 'Failed to create model'}`;
                }
                
                // Update counter
                const counter = document.getElementById('enrollmentCounter');
                if (counter) counter.textContent = '0/1';
                
                // Update title
                const scanTitle = document.getElementById('scanTitle');
                if (scanTitle) {
                    scanTitle.textContent = 'Capture Failed';
                }
                
                // Show error notification
                showNotification(`âœ— ${message.message || 'Failed to create fingerprint model'}`, 'danger');
                
                // Wait 2 seconds before enabling retry to give ESP32 time to reset
                setTimeout(() => {
                    // Double-check we haven't succeeded in the meantime
                    if (window.enrollmentCompleted) {
                        console.log('[ENROLLMENT] Enrollment already completed - skipping retry button');
                        return;
                    }
                    
                    // Update button to Retry (orange) - ONLY IF NOT ALREADY SUCCESSFUL
                    if (btn) {
                        btn.disabled = false;
                        btn.innerHTML = '<i class="fas fa-redo mr-1"></i> Retry';
                        btn.className = 'w-full px-4 py-2.5 bg-orange-600 hover:bg-orange-700 text-white font-semibold text-sm rounded-lg transition';
                        btn.onclick = function() {
                            // Disable button immediately to prevent double-clicks
                            btn.disabled = true;
                            btn.innerHTML = '<i class="fas fa-spinner fa-spin mr-1"></i> Restarting...';
                            
                            // Close old WebSocket connection completely
                            if (socket && socket.readyState === WebSocket.OPEN) {
                                socket.close();
                            }
                            if (currentWebSocket) {
                                try {
                                    currentWebSocket.close();
                                } catch (e) {
                                    console.warn('[ENROLLMENT] Could not close socket:', e);
                                }
                            }
                            
                            // Reset enrollment state for this instructor
                            setInstructorEnrollmentInProgress(false);
                            window.fingerDetectedShown = false;  // Reset for next attempt
                            window.enrollmentCompleted = false;  // Reset completion flag
                            window.enrollmentInErrorState = false;  // Clear error state
                            window.isProcessing = false;  // Clear processing flag
                            
                            // Notify ESP32 to cancel current enrollment
                            fetch(`http://${R307_IP}/enroll/cancel`, {
                                method: 'POST',
                                headers: {'Content-Type': 'application/json'},
                                body: JSON.stringify({})
                            }).catch(e => console.warn('[RETRY] Cancel request failed:', e));
                            
                            // Wait 3 seconds for ESP32 to fully reset before retry
                            setTimeout(() => {
                                console.log('[RETRY] Starting new enrollment attempt after ESP32 reset');
                                proceedWithEnrollment(window.enrollmentCourseIds);
                            }, 3000);
                        };
                        console.log('[ENROLLMENT] Button set to RETRY (orange) - FAILURE STATE');
                    }
                }, 2000);  // Give ESP32 2 seconds to reset before enabling retry
            }
            // For intermediate messages - only show "Finger Detected" and "Processing"
            // CRITICAL: Do NOT show retry button during processing - only on actual errors
            else if (!window.enrollmentCompleted && !window.enrollmentInErrorState && message.message) {
                const msgLower = message.message.toLowerCase();
                
                console.log('[ENROLLMENT] Processing intermediate message:', {
                    original: message.message,
                    lowercase: msgLower,
                    fingerDetectedShown: window.fingerDetectedShown,
                    isProcessing: window.isProcessing
                });
                
                // Only show "Finger Detected" once
                // Check for multiple variations: "detected", "finger", "placement", "ready"
                if ((msgLower.includes('detected') || msgLower.includes('finger') || msgLower.includes('placement')) && !window.fingerDetectedShown) {
                    console.log('[ENROLLMENT] âœ“ Finger Detected message identified:', message.message);
                    
                    if (statusEl) {
                        statusEl.innerHTML = '<i class="fas fa-check-circle mr-2 text-green-500"></i> Finger Detected';
                        console.log('[ENROLLMENT] Updated UI to show "Finger Detected"');
                    }
                    
                    // Show notification popup using fallback if needed
                    const notifyFunc = typeof showNotification === 'function' ? showNotification : window.showNotificationFallback;
                    notifyFunc('âœ“ Finger Detected - Processing...', 'success');
                    console.log('[ENROLLMENT] Notification triggered');
                    
                    window.fingerDetectedShown = true;
                    window.isProcessing = true;  // Mark that we're now processing a fingerprint
                    console.log('[ENROLLMENT] Finger detected - message shown, marking as processing');
                }
                // Show "Processing" for processing messages (but NOT if we're already at 100%)
                else if ((msgLower.includes('processing') || msgLower.includes('quality')) && !window.fingerDetectedShown) {
                    if (statusEl) {
                        statusEl.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i> Processing...';
                    }
                    window.isProcessing = true;  // Mark that we're processing
                    console.log('[ENROLLMENT] Processing - message shown, fingerprint in progress');
                }
                // Ignore other intermediate messages to avoid message clutter
            }
        } catch (error) {
            console.error('[WEBSOCKET] Error parsing message:', error, 'Raw:', event.data);
        }
    };
    
    socket.onerror = (error) => {
        console.error('[WEBSOCKET] ERROR:', error);
        console.error('[WEBSOCKET] Ready state:', socket.readyState);
        showNotification('WebSocket connection error', 'danger');
    };
    
    socket.onclose = (event) => {
        console.log('[WEBSOCKET] Connection closed');
        console.log('[WEBSOCKET] Close code:', event.code);
        console.log('[WEBSOCKET] Close reason:', event.reason);
    };
    
    // Handle scan update from server
    function handleScanUpdate(message) {
        console.log('[SCAN] Processing update with data:', message);
        
        // Extract fields from message
        const slot = message.slot || message.scan_step || 0;
        const success = message.success || false;
        const quality = message.quality || message.quality_score || 0;
        
        console.log(`[SCAN] Extracted: slot=${slot}, success=${success}, quality=${quality}`);
        
        // CRITICAL: Only process successful captures
        // success should be TRUE to increment the counter
        if (success === true) {
            // This is a confirmed successful capture
            confirmations++;
            console.log(`[SCAN] âœ“ Confirmed capture ${confirmations}/3`);
            
            // SOUND EFFECT: Play capture sound immediately when scan is confirmed
            playScanCaptureSound();
            
            // Show success notification
            const scanMessage = message.message || `Scan ${slot}/3 captured`;
            showNotification(`âœ“ ${scanMessage}`, 'success');
            console.log('[NOTIFICATION] Showing success for scan:', slot);
            
            // Update counter
            const counter = document.getElementById('enrollmentCounter');
            if (counter) {
                counter.textContent = `${confirmations}/3`;
                console.log('[PROGRESS] Updated counter to:', counter.textContent);
            }
            
            // Update progress bar
            const progressPercent = (confirmations / 3) * 100;
            const progressBar = document.getElementById('progressBar');
            const progressPercentEl = document.getElementById('progressPercent');
            if (progressBar) {
                progressBar.style.width = progressPercent + '%';
                console.log('[PROGRESS] Updated progress bar to:', progressPercent + '%');
            }
            if (progressPercentEl) {
                progressPercentEl.textContent = Math.round(progressPercent) + '%';
            }
            
            // Update percentage display
            const percentageDisplay = document.getElementById('percentageDisplay');
            if (percentageDisplay && confirmations > 0) {
                if (percentageDisplay.style.display === 'none') {
                    percentageDisplay.style.display = 'block';
                    console.log('[PROGRESS] Showing percentage display - capture detected');
                }
                percentageDisplay.textContent = Math.round(progressPercent) + '%';
                percentageDisplay.style.color = confirmations === 3 ? '#10b981' : '#9333ea';
                console.log('[PROGRESS] Updated percentage to:', Math.round(progressPercent) + '%');
            }
            
            // Check if all 3 captures are complete
            if (confirmations >= 3 && !window.enrollmentCompleted) {
                console.log('[SCAN] âœ“âœ“âœ“ ALL 3 CAPTURES COMPLETE! âœ“âœ“âœ“');
                console.log('[SCAN] Showing Confirm button - waiting for user confirmation');
                
                // Mark as enrollment complete so this code doesn't run multiple times
                window.enrollmentCompleted = true;
                
                // Update icon to success
                const scanIcon = document.getElementById('scanIcon');
                if (scanIcon) {
                    scanIcon.innerHTML = '<i class="fas fa-circle-check text-5xl text-green-500 mb-3"></i>';
                }
                
                // Update title
                const scanTitle = document.getElementById('scanTitle');
                if (scanTitle) {
                    scanTitle.textContent = '3 Scans Complete!';
                }
                
                // Update status
                const statusEl = document.getElementById('enrollmentStatus');
                if (statusEl) {
                    statusEl.innerHTML = '<i class="fas fa-check-circle mr-2"></i> Ready to confirm';
                }
                
                // Get course IDs and biometric template
                const courseIds = window.enrollmentCourseIds || [];
                const biometricTemplate = window.biometricTemplate || `template_${Date.now()}`;
                
                console.log('[SCAN] All 3 captures complete. Showing confirm button for user to click.');
                console.log('[SCAN] Courses to register:', courseIds);
                
                // Show confirm button
                const confirmBtn = document.getElementById('startEnrollBtn');
                const cancelBtn = document.querySelector('button[onclick="closeBiometricRegistrationModal()"]');
                
                if (confirmBtn) {
                    confirmBtn.disabled = false;
                    confirmBtn.innerHTML = '<i class="fas fa-check mr-1"></i> Confirm 3 Captures';
                    confirmBtn.className = 'w-full px-4 py-2.5 bg-green-600 hover:bg-green-700 text-white font-semibold text-sm rounded-lg transition';
                    
                    confirmBtn.onclick = async function() {
                        console.log('[CONFIRM] User clicked confirm button');
                        console.log('[CONFIRM] âš ï¸ CRITICAL: Setting enrollmentConfirmedSuccessfully flag IMMEDIATELY');
                        
                        // CRITICAL: Set flag IMMEDIATELY before any async operations
                        // This prevents closeBiometricRegistrationModal from sending cancel
                        window.enrollmentConfirmedSuccessfully = true;
                        
                        confirmBtn.disabled = true;
                        
                        // Hide cancel button so user can't interrupt
                        if (cancelBtn) {
                            cancelBtn.style.display = 'none';
                        }
                        
                        // SOUND EFFECT: Play confirmation sound and wait for it to complete
                        console.log('[CONFIRM] Waiting for confirmation sound to complete...');
                        await playConfirmationSound();
                        console.log('[CONFIRM] Confirmation sound completed - now submitting enrollment');
                        
                        console.log('[CONFIRM] Submitting biometric enrollment with courses:', courseIds);
                        console.log('[CONFIRM] Biometric template:', biometricTemplate);
                        
                        // Call submitBiometricEnrollment to save the biometric data
                        // Store reference to button for error handling
                        submitBiometricEnrollment(confirmations, biometricTemplate, courseIds).catch(err => {
                            console.error('[CONFIRM] Enrollment error:', err);
                            confirmBtn.disabled = false;
                            confirmBtn.innerHTML = '<i class="fas fa-check mr-1"></i> Confirm 3 Captures';
                            if (cancelBtn) {
                                cancelBtn.style.display = 'block';
                            }
                        });
                    };
                }
                
                // Hide cancel button during enrollment to prevent accidental clicks
                if (cancelBtn) {
                    console.log('[SCAN] Hiding Cancel button during enrollment');
                    cancelBtn.style.display = 'none';
                }
                
                return;
            }
        } else {
            // Failed capture - don't increment
            console.log('[SCAN] Capture failed or low quality:', message.message);
            
            // Show failure message if it's a critical error
            if (message.message && message.message.toLowerCase().includes('quality')) {
                showNotification(`Quality too low: ${quality}% - try again`, 'warning');
            }
        }
        
        // Update status - show current message from ESP32
        const statusEl = document.getElementById('enrollmentStatus');
        if (statusEl && message.message) {
            statusEl.innerHTML = `<i class="fas fa-fingerprint mr-2"></i> ${message.message}`;
        }
        
        // Update icon - show green check for successful scans, pulse for in-progress
        const scanIcon = document.getElementById('scanIcon');
        if (scanIcon && success !== true) {
            scanIcon.innerHTML = '<i class="fas fa-fingerprint text-5xl text-blue-500 mb-3 animate-pulse"></i>';
        }
        
        const scanTitle = document.getElementById('scanTitle');
        if (scanTitle && success !== true) {
            scanTitle.textContent = `Capture ${slot}/3`;
        }
        
        const scanSubtitle = document.getElementById('scanSubtitle');
        if (scanSubtitle) {
            scanSubtitle.textContent = quality > 0 ? `Quality: ${quality}%` : 'Waiting for finger...';
        }
        
        console.log('[SCAN] Update complete - confirmations:', confirmations, '/3');
    }
    
    function handleEnrollmentComplete(message) {
        console.log('[ENROLLMENT] Complete:', message);
        
        // Get DOM elements
        const statusEl = document.getElementById('enrollmentStatus');
        const scanTitle = document.getElementById('scanTitle');
        const scanSubtitle = document.getElementById('scanSubtitle');
        
        // Get course IDs from window - THIS IS THE KEY: We enroll ONE fingerprint for ALL courses
        const courseIds = window.enrollmentCourseIds || [];
        
        if (statusEl) statusEl.innerHTML = '<i class="fas fa-check mr-2"></i> Enrollment complete!';
        if (scanTitle) scanTitle.textContent = 'Success!';
        if (scanSubtitle) scanSubtitle.textContent = `${courseIds.length} course(s) enrolled`;
        
        // Submit enrollment to Django with ALL course IDs at once
        // The fingerprint slot (1) is used for all courses - one fingerprint per student
        submitBiometricEnrollment(1, window.biometricTemplate, courseIds);
    }
    
    function handleEnrollmentError(message) {
        console.error('[ENROLLMENT] Error:', message);
        showNotification(`Error: ${message.message}`, 'danger');
        scanIcon.innerHTML = '<i class="fas fa-exclamation-triangle text-5xl text-red-500 mb-3"></i>';
        scanTitle.textContent = 'Error';
        btn.disabled = false;
        btn.innerHTML = '<i class="fas fa-redo mr-1"></i> Retry';
        if (socket.readyState === WebSocket.OPEN) socket.close();
    }
    
    // Start scanning for next fingerprint
    async function startNextScan() {
        const nextScanNumber = confirmations + 1;
        console.log('[SCAN] Starting scan', nextScanNumber);
        
        scanIcon.innerHTML = '<i class="fas fa-fingerprint text-5xl text-blue-500 mb-3 animate-pulse"></i>';
        scanTitle.textContent = `Scan ${nextScanNumber} of 3`;
        scanSubtitle.textContent = 'Place your finger on sensor';
        statusEl.innerHTML = `<i class="fas fa-fingerprint mr-2"></i> Ready for scan ${nextScanNumber}...`;
        
        try {
            const enrollPayload = {
                slot: nextScanNumber,
                template_id: enrollmentId
            };
            
            console.log('[SCAN] Sending to Arduino:', JSON.stringify(enrollPayload));
            
            // Poll ESP32 for finger detection in real-time
            pollFingerDetection(nextScanNumber, enrollPayload);
            
        } catch (error) {
            console.error('[SCAN] Arduino error:', error);
            showNotification(`Cannot reach ESP32 at ${R307_IP}`, 'danger');
            scanIcon.innerHTML = '<i class="fas fa-exclamation-triangle text-5xl text-red-500 mb-3"></i>';
            scanTitle.textContent = 'Connection Error';
            btn.disabled = false;
            btn.innerHTML = '<i class="fas fa-redo mr-1"></i> Retry';
        }
    }
    
    // FALLBACK: Create simple notification if not available
    window.showNotificationFallback = function(message, type) {
        console.log(`[NOTIFICATION-FALLBACK] ${type.toUpperCase()}: ${message}`);
        
        // Create a simple alert-like notification
        const notifDiv = document.createElement('div');
        notifDiv.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 16px 24px;
            border-radius: 8px;
            font-weight: bold;
            z-index: 9999;
            animation: slideIn 0.3s ease;
            font-size: 16px;
        `;
        
        if (type === 'success') {
            notifDiv.style.backgroundColor = '#10b981';
            notifDiv.style.color = 'white';
        } else if (type === 'warning') {
            notifDiv.style.backgroundColor = '#f59e0b';
            notifDiv.style.color = 'white';
        } else if (type === 'info') {
            notifDiv.style.backgroundColor = '#3b82f6';
            notifDiv.style.color = 'white';
        } else {
            notifDiv.style.backgroundColor = '#ef4444';
            notifDiv.style.color = 'white';
        }
        
        notifDiv.textContent = message;
        document.body.appendChild(notifDiv);
        
        setTimeout(() => notifDiv.remove(), 3000);
    };
    
    // Poll ESP32 device for finger detection
    async function pollFingerDetection(scanNumber, enrollPayload) {
        let pollCount = 0;
        const maxPolls = 1200; // 120 seconds at 100ms intervals
        const pollInterval = 100; // milliseconds
        
        console.log(`[POLLING] ===== POLLING STARTED for scan ${scanNumber} =====`);
        console.log(`[POLLING] Envelope: ${JSON.stringify(enrollPayload)}`);
        
        const pollTimer = setInterval(async () => {
            pollCount++;
            
            // Log every 10 polls so we know polling is active
            if (pollCount % 10 === 1) {
                console.log(`[POLLING] Poll attempt ${pollCount}/1200...`);
            }
            
            try {
                // Send enrollment request to ESP32 - it will detect finger and return immediately if found
                const response = await fetch(`http://${R307_IP}/enroll`, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(enrollPayload),
                    timeout: 130000  // INCREASED: 130 seconds to match ESP32 timeout
                });
                
                if (response.ok) {
                    const r307Data = await response.json();
                    console.log(`[POLLING] Response ${pollCount}:`, r307Data);
                    
                    // CRITICAL: Handle ALL responses from ESP32 - show status in UI and notifications
                    if (r307Data.message) {
                        const msgLower = r307Data.message.toLowerCase();
                        const quality = r307Data.quality_score || 0;
                        
                        console.log(`[POLLING] Message received: "${r307Data.message}" (Quality: ${quality}%)`);
                        
                        // Update subtitle with quality score
                        const scanSubtitle = document.getElementById('scanSubtitle');
                        if (scanSubtitle && quality > 0) {
                            scanSubtitle.textContent = `Quality: ${quality}%`;
                        }
                        
                        // CRITICAL: Match ALL message types to ensure UI updates
                        let messageHandled = false;
                        
                        // Handle: "Finger detected - processing"
                        if (msgLower.includes('detected') && !window.fingerDetectedShown) {
                            console.log(`[POLLING] âœ“âœ“âœ“ FINGER DETECTED! âœ“âœ“âœ“`);
                            messageHandled = true;
                            
                            try {
                                const scanIcon = document.getElementById('scanIcon');
                                if (scanIcon) {
                                    scanIcon.innerHTML = '<i class="fas fa-check-circle text-5xl text-green-500 mb-3"></i>';
                                    console.log('[POLLING] Updated scanIcon to green checkmark');
                                }
                                
                                const statusEl = document.getElementById('enrollmentStatus');
                                if (statusEl) {
                                    statusEl.innerHTML = '<i class="fas fa-spinner fa-spin mr-2 text-green-600"></i> Finger Detected - Processing...';
                                    console.log('[POLLING] Updated status to "Finger Detected - Processing..."');
                                }
                            } catch(e) {
                                console.error('[POLLING] Error updating DOM:', e);
                            }
                            
                            // CRITICAL: Show popup notification for detection
                            const notifyFunc = typeof showNotification === 'function' ? showNotification : window.showNotificationFallback;
                            setTimeout(() => notifyFunc('âœ“ Fingerprint Detected! Processing...', 'success'), 50);
                            console.log('[POLLING] Notification triggered for detection');
                            
                            window.fingerDetectedShown = true;
                            window.isProcessing = true;
                            
                            try {
                                const percentageDisplay = document.getElementById('percentageDisplay');
                                if (percentageDisplay) {
                                    percentageDisplay.style.display = 'block';
                                    percentageDisplay.textContent = '25%';
                                    percentageDisplay.style.color = '#9333ea';
                                    console.log('[POLLING] Updated progress bar to 25% purple');
                                }
                            } catch(e) {
                                console.error('[POLLING] Error updating progress:', e);
                            }
                        } 
                        // Handle: "Image quality low - take second capture"
                        else if ((msgLower.includes('quality') || msgLower.includes('low')) && !messageHandled) {
                            console.log(`[POLLING] Image quality low (${quality}%) - requesting second capture`);
                            messageHandled = true;
                            
                            const scanIcon = document.getElementById('scanIcon');
                            if (scanIcon) {
                                scanIcon.innerHTML = '<i class="fas fa-exclamation-triangle text-5xl text-yellow-600 mb-3"></i>';
                            }
                            
                            const statusEl = document.getElementById('enrollmentStatus');
                            if (statusEl) {
                                statusEl.innerHTML = `<i class="fas fa-exclamation-triangle mr-2 text-yellow-600"></i> ${r307Data.message}`;
                            }
                            
                            // CRITICAL: Show popup notification for quality issue
                            const notifyFunc = typeof showNotification === 'function' ? showNotification : window.showNotificationFallback;
                            setTimeout(() => notifyFunc(`âš ï¸ Quality Low (${quality}%) - ${r307Data.message}`, 'warning'), 50);
                            
                            const percentageDisplay = document.getElementById('percentageDisplay');
                            if (percentageDisplay) {
                                percentageDisplay.style.display = 'block';
                                percentageDisplay.textContent = quality + '%';
                                percentageDisplay.style.color = '#eab308';
                            }
                        }
                        // Handle: "Place finger again - press firmly..."
                        else if ((msgLower.includes('again') || msgLower.includes('second')) && !messageHandled) {
                            console.log(`[POLLING] Requesting second finger placement`);
                            messageHandled = true;
                            
                            const scanIcon = document.getElementById('scanIcon');
                            if (scanIcon) {
                                scanIcon.innerHTML = '<i class="fas fa-hand-paper text-5xl text-blue-600 mb-3"></i>';
                            }
                            
                            const scanTitle = document.getElementById('scanTitle');
                            if (scanTitle) {
                                scanTitle.textContent = 'Dual Capture Mode';
                            }
                            
                            const statusEl = document.getElementById('enrollmentStatus');
                            if (statusEl) {
                                statusEl.innerHTML = `<i class="fas fa-hand-paper mr-2 text-blue-600"></i> ðŸ”„ ${r307Data.message}`;
                            }
                            
                            // CRITICAL: Show popup notification for second placement
                            const notifyFunc = typeof showNotification === 'function' ? showNotification : window.showNotificationFallback;
                            setTimeout(() => notifyFunc('ðŸ”„ Place Finger Again - Press firmly for 3-5 seconds', 'info'), 50);
                            
                            const percentageDisplay = document.getElementById('percentageDisplay');
                            if (percentageDisplay) {
                                percentageDisplay.style.display = 'block';
                                percentageDisplay.textContent = quality + '%';
                                percentageDisplay.style.color = '#3b82f6';
                            }
                        }
                        // Default handler: Show ANY message that hasn't been handled
                        // This catches "Ready to scan - place your finger on sensor" and similar messages
                        else if (!messageHandled && !r307Data.success) {
                            console.log(`[POLLING] Status message: ${r307Data.message}`);
                            messageHandled = true;
                            
                            const statusEl = document.getElementById('enrollmentStatus');
                            if (statusEl) {
                                statusEl.innerHTML = `<i class="fas fa-spinner fa-spin mr-2"></i> ${r307Data.message}`;
                            }
                            
                            // CRITICAL: Show notification for any status message
                            const notifyFunc = typeof showNotification === 'function' ? showNotification : window.showNotificationFallback;
                            setTimeout(() => notifyFunc(`ðŸ“ ${r307Data.message}`, 'info'), 50);
                            
                            const percentageDisplay = document.getElementById('percentageDisplay');
                            if (percentageDisplay && quality > 0) {
                                percentageDisplay.style.display = 'block';
                                percentageDisplay.textContent = quality + '%';
                            }
                        }
                    }
                    
                    // If finger was successfully enrolled - FINAL SUCCESS
                    if (r307Data.success) {
                        clearInterval(pollTimer);
                        confirmations++;
                        console.log(`[POLLING] âœ“âœ“âœ“ FINGERPRINT ENROLLMENT SUCCESSFUL âœ“âœ“âœ“`);
                        
                        // SOUND EFFECT: Play capture success sound
                        playScanCaptureSound();
                        
                        // Show final success notification
                        showNotification('âœ“âœ“âœ“ Fingerprint Enrolled Successfully! âœ“âœ“âœ“', 'success');
                        
                        // Update UI with final success
                        const scanIcon = document.getElementById('scanIcon');
                        const scanTitle = document.getElementById('scanTitle');
                        const scanSubtitle = document.getElementById('scanSubtitle');
                        const statusEl = document.getElementById('enrollmentStatus');
                        const percentageDisplay = document.getElementById('percentageDisplay');
                        
                        const quality = r307Data.quality_score || 85;
                        
                        if (scanIcon) {
                            scanIcon.innerHTML = '<i class="fas fa-check-circle text-5xl text-green-500 mb-3"></i>';
                        }
                        if (scanTitle) {
                            scanTitle.textContent = `Scan ${confirmations}/1`;
                        }
                        if (scanSubtitle) {
                            scanSubtitle.textContent = `Quality: ${quality}%`;
                        }
                        if (statusEl) {
                            statusEl.innerHTML = `<i class="fas fa-check mr-2 text-green-600"></i> ${r307Data.message || 'Fingerprint captured successfully'}`;
                        }
                        
                        // Update progress bar to 100%
                        if (percentageDisplay) {
                            percentageDisplay.style.display = 'block';
                            percentageDisplay.textContent = '100%';
                            percentageDisplay.style.color = '#10b981'; // green
                        }
                        
                        // Move to next scan or complete - single scan done
                        if (confirmations >= 1) {
                            handleEnrollmentComplete({success: true, courses_enrolled: courseIds.length});
                        }
                        return;
                    }
                }
            } catch (error) {
                console.log(`[POLLING] Attempt ${pollCount}: Waiting for finger...`);
            }
            
            // Timeout check
            if (pollCount >= maxPolls) {
                clearInterval(pollTimer);
                console.error(`[POLLING] Timeout: No finger detected on scan ${scanNumber}`);
                
                scanIcon.innerHTML = '<i class="fas fa-exclamation-circle text-5xl text-yellow-500 mb-3"></i>';
                scanTitle.textContent = 'Timeout';
                scanSubtitle.textContent = 'No finger detected';
                statusEl.innerHTML = '<i class="fas fa-exclamation mr-2"></i> Please try again';
                
                // Retry option
                btn.disabled = false;
                btn.innerHTML = `<i class="fas fa-redo mr-1"></i> Retry Scan`;
                btn.onclick = () => {
                    startNextScan(); // Retry same scan
                };
            }
        }, pollInterval);
    }
}

// Submit biometric enrollment to backend
async function submitBiometricEnrollment(confirmations, biometricTemplate, courseIds) {
    return new Promise(async (resolve, reject) => {
        console.log(`[SUBMIT] Starting enrollment submission for ${courseIds.length} courses:`, courseIds);
        
        // CRITICAL FIX: Send ALL course IDs in ONE request instead of multiple requests
        // This ensures the fingerprint is registered ONCE for ALL courses (like QR code)
        const enrollmentData = {
            course_ids: courseIds,  // Send ALL course IDs at once
            biometric_data: biometricTemplate,
            biometric_type: 'fingerprint',
            confirmations: confirmations
        };
        
        console.log(`[SUBMIT] Sending batch enrollment for ${courseIds.length} courses in single request:`, enrollmentData);
        
        // Create abort controller for timeout
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 15000); // 15 second timeout
        
        fetch('{% url "dashboard:api_biometric_enroll" %}', {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCookie('csrftoken'),
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(enrollmentData),
            signal: controller.signal
        })
        .then(response => {
            clearTimeout(timeoutId);
            console.log('[SUBMIT] Response status:', response.status);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            return response.json();
        })
        .then(data => {
            console.log('[SUBMIT] Batch enrollment response:', data);
        
        // Store fingerprint IDs for later use in confirmation
        window.enrollmentFingerprintId = data.fingerprint_id;
        window.enrollmentIsReplacement = data.is_replacement || false;
        window.enrollmentCourseIds = courseIds;  // Store course IDs
        
        // Log if this is a replacement
        if (data.is_replacement) {
            console.log('[SUBMIT] âš ï¸ FINGERPRINT REPLACEMENT MODE DETECTED:');
            console.log('[SUBMIT]    Fingerprint_id: ' + data.fingerprint_id + ' (reusing same ID)');
            console.log('[SUBMIT]    Biometric data will be updated on CONFIRM');
        }
        
        const statusEl = document.getElementById('enrollmentStatus');
        const scanTitle = document.getElementById('scanTitle');
        const scanSubtitle = document.getElementById('scanSubtitle');
        const scanIcon = document.getElementById('scanIcon');
        const btn = document.getElementById('startEnrollBtn');
        
        if (data.success) {
            // All courses enrolled successfully
            console.log('[SUBMIT] âœ“âœ“âœ“ ALL COURSES ENROLLED SUCCESSFULLY âœ“âœ“âœ“');
            console.log('[SUBMIT] Fingerprint ID from Django:', data.fingerprint_id);
            console.log('[SUBMIT] Biometric template:', window.biometricTemplate);
            
            // CRITICAL: Send confirmation to ESP32 to save fingerprint to sensor
            console.log('[SUBMIT] CRITICAL: Sending confirmation to ESP32...');
            
            // Get ESP32 IP from window context (set by proceedWithEnrollment)
            const espIP = window.ESP32_IP || '{{ esp32_ip|default:"192.168.1.9" }}';
            console.log('[SUBMIT] ESP32 IP:', espIP);
            
            // Prepare confirmation payload with the exact fingerprint_id Django assigned
            const confirmPayload = {
                fingerprint_id: data.fingerprint_id,  // CRITICAL: Use the ID that Django assigned
                template_id: window.biometricTemplate || ''
            };
            
            console.log('[SUBMIT] Confirmation payload:', JSON.stringify(confirmPayload));
            
            // Send confirmation to ESP32 and WAIT for response
            let confirmationSucceeded = false;
            try {
                console.log('[SUBMIT] Fetching ESP32 confirmation endpoint...');
                const confirmResponse = await fetch(`http://${espIP}/enroll/confirm`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(confirmPayload)
                });
                
                console.log('[SUBMIT] ESP32 confirmation response status:', confirmResponse.status);
                
                if (confirmResponse.ok) {
                    const confirmData = await confirmResponse.json();
                    console.log('[SUBMIT] âœ“âœ“âœ“ ESP32 CONFIRMATION SUCCESSFUL âœ“âœ“âœ“');
                    console.log('[SUBMIT] Response:', confirmData);
                    console.log('[SUBMIT] âœ“ Fingerprint SAVED to sensor slot:', data.fingerprint_id);
                    confirmationSucceeded = true;
                } else {
                    const responseText = await confirmResponse.text();
                    console.error('[SUBMIT] âœ— ESP32 confirmation failed with status:', confirmResponse.status);
                    console.error('[SUBMIT] âœ— Response body:', responseText);
                    console.error('[SUBMIT] âœ— Fingerprint may NOT have been saved to sensor!');
                }
            } catch (err) {
                console.error('[SUBMIT] âœ— Network error - Could not reach ESP32:');
                console.error('[SUBMIT] âœ— Error:', err.message);
                console.error('[SUBMIT] âœ— Tried to reach:', `http://${espIP}/enroll/confirm`);
                console.error('[SUBMIT] âœ— CRITICAL: Fingerprint may NOT be on sensor!');
            }
            
            if (!confirmationSucceeded) {
                console.warn('[SUBMIT] âš ï¸ WARNING: Enrollment saved to Django but fingerprint NOT confirmed to sensor');
                console.warn('[SUBMIT] âš ï¸ Instructor scanning will NOT find this fingerprint!');
            }
            
            scanIcon.innerHTML = '<i class="fas fa-check-circle text-6xl text-green-500 mb-4"></i>';
            
            // Show different message if replacement
            if (data.is_replacement) {
                scanTitle.textContent = 'Fingerprint Updated!';
                scanSubtitle.textContent = `Biometric for fingerprint_id ${data.fingerprint_id} updated`;
                statusEl.innerHTML = `<i class="fas fa-sync mr-2 text-blue-600"></i> <span class="text-blue-700">Fingerprint update confirmed!</span>`;
            } else {
                scanTitle.textContent = 'Enrollment Complete!';
                scanSubtitle.textContent = `Fingerprint registered in ${courseIds.length} course(s)`;
                statusEl.innerHTML = `<i class="fas fa-check mr-2 text-green-600"></i> <span class="text-green-700">Fingerprint enrolled in all ${courseIds.length} courses!</span>`;
            }
            
            // Show notification first
            showNotification(`âœ“ Fingerprint enrolled in ${courseIds.length} course(s)!`, 'success');
            
            // SOUND EFFECT: Play enrollment success sound synchronized with notification
            playEnrollmentSuccessSound();
            
            console.log('[SUBMIT] â³ Closing modal and reloading page immediately...');
            
            // CRITICAL FIX: Set flag BEFORE closing modal to prevent cancel from being sent to ESP32
            window.enrollmentConfirmedSuccessfully = true;
            console.log('[SUBMIT] âœ“âœ“âœ“ Set enrollmentConfirmedSuccessfully flag to TRUE - ESP32 cancel will be skipped');
            
            // Resolve promise immediately so button handler knows success
            resolve(data);
            
            // Close modal and reload page IMMEDIATELY - don't wait
            setInstructorEnrollmentInProgress(false);
            closeBiometricRegistrationModal();
            
            // Reload page right away to show updated status
            window.location.reload();
        } else {
            // Enrollment failed - show error details
            console.error('[SUBMIT] Enrollment failed:', data.message);
            
            // SOUND EFFECT: Play enrollment error sound
            playEnrollmentErrorSound();
            
            scanIcon.innerHTML = '<i class="fas fa-exclamation-circle text-6xl text-red-500 mb-4"></i>';
            scanTitle.textContent = 'Enrollment Failed';
            scanSubtitle.textContent = data.message || 'Could not register fingerprint';
            statusEl.innerHTML = `<i class="fas fa-exclamation mr-2 text-red-600"></i> <span class="text-red-700">${data.message || 'Failed to register fingerprint'}</span>`;
            
            showNotification(`âœ— ${data.message || 'Failed to register fingerprint'}`, 'danger');
            
            // Reject the promise with the error
            reject(new Error(data.message || 'Failed to register fingerprint'));
            
            // Show retry button
            if (btn) {
                btn.disabled = false;
                btn.innerHTML = '<i class="fas fa-redo mr-1"></i> Retry';
                btn.className = 'w-full px-4 py-2.5 bg-orange-600 hover:bg-orange-700 text-white font-semibold text-sm rounded-lg transition';
                btn.onclick = function() {
                    btn.disabled = true;
                    btn.innerHTML = '<i class="fas fa-spinner fa-spin mr-1"></i> Restarting...';
                    
                    // Reset enrollment state
                    setInstructorEnrollmentInProgress(false);
                    window.fingerDetectedShown = false;
                    window.enrollmentCompleted = false;
                    
                    // Notify ESP32 to cancel
                    fetch(`http://${R307_IP}/enroll/cancel`, {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({})
                    }).catch(e => console.warn('[RETRY] Cancel request failed:', e));
                    
                    // Wait and retry
                    setTimeout(() => {
                        console.log('[RETRY] Starting new enrollment attempt');
                        proceedWithEnrollment(window.enrollmentCourseIds);
                    }, 3000);
                };
            }
            
            setInstructorEnrollmentInProgress(false);
        }
        })
        .catch(error => {
            clearTimeout(timeoutId);
            console.error('[SUBMIT] Network error during enrollment:', error);
            
            // SOUND EFFECT: Play error sound for network failure
            playEnrollmentErrorSound();
            
            // Reject the promise
            reject(error);
            
            const statusEl = document.getElementById('enrollmentStatus');
            const scanTitle = document.getElementById('scanTitle');
            const scanSubtitle = document.getElementById('scanSubtitle');
            const scanIcon = document.getElementById('scanIcon');
            const btn = document.getElementById('startEnrollBtn');
            
            // Handle timeout vs other errors
            let errorMessage = error.message;
            if (error.name === 'AbortError') {
                errorMessage = 'Registration took too long. Server not responding.';
            }
            
            scanIcon.innerHTML = '<i class="fas fa-exclamation-circle text-6xl text-red-500 mb-4"></i>';
            scanTitle.textContent = 'Connection Error';
            scanSubtitle.textContent = 'Failed to reach server';
            statusEl.innerHTML = `<i class="fas fa-exclamation mr-2 text-red-600"></i> <span class="text-red-700">${errorMessage}</span>`;
        
        showNotification(`âœ— Network error: ${error.message}`, 'danger');
        
        // Show retry button
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = '<i class="fas fa-redo mr-1"></i> Retry';
            btn.className = 'w-full px-4 py-2.5 bg-orange-600 hover:bg-orange-700 text-white font-semibold text-sm rounded-lg transition';
            btn.onclick = function() {
                btn.disabled = true;
                btn.innerHTML = '<i class="fas fa-spinner fa-spin mr-1"></i> Restarting...';
                
                setInstructorEnrollmentInProgress(false);
                window.fingerDetectedShown = false;
                window.enrollmentCompleted = false;
                
                fetch(`http://${R307_IP}/enroll/cancel`, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({})
                }).catch(e => console.warn('[RETRY] Cancel request failed:', e));
                
                setTimeout(() => {
                    console.log('[RETRY] Starting new enrollment attempt after network error');
                    proceedWithEnrollment(window.enrollmentCourseIds);
                }, 3000);
            };
        }
        
        setInstructorEnrollmentInProgress(false);
        });
    });
}

function openRegistrationMethods(instructorId, instructorName) {
    // Close modals first
    closeInstructorRegistrationModal();
    closeRegistrationInstructorsModal();
    
    // Set the registration mode to student self-registration
    window.isStudentRegisterMode = true;
    
    // Store instructor ID for backend reference
    window.currentInstructorId = instructorId;
    
    // Set student ID prefill from page data if available
    const studentIdPrefill = document.querySelector('[data-student-id]')?.getAttribute('data-student-id') || '';
    
    // Get all courses from the current registration modal (before we close it)
    // In the QR scanner, we'll use courseId 0 as a special marker for multi-course registration
    console.log('Opening QR Scanner in student registration mode for instructor:', instructorId);
    
    // Open QR Scanner - courseId of 0 indicates student registering with instructor (multi-course)
    if (typeof window.openQRScanner === 'function') {
        window.openQRScanner(0, studentIdPrefill, '');
    } else {
        console.error('QR Scanner function not available');
        alert('QR Scanner is not available. Please refresh the page and try again.');
    }
}

