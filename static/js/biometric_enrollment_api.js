/**
 * BIOMETRIC ENROLLMENT - Network-Agnostic via Django API
 * 
 * IMPORTANT: This module handles fingerprint enrollment through:
 * - Django REST API (not direct ESP32 connection)
 * - MQTT Bridge handles ESP32 communication
 * - Works on ANY network: mobile data, different WiFi, cellular
 * 
 * SAFETY: This code only affects biometric enrollment, does not touch:
 * - Course enrollment
 * - Attendance system
 * - Any existing dashboard functionality
 */

class BiometricEnrollmentManager {
  constructor() {
    this.isEnrolling = false;
    this.currentSession = null;
    this.statusCheckInterval = null;
  }

  /**
   * Start fingerprint enrollment
   * Works on ANY network via Django API
   */
  async startEnrollment(studentId, courseId = null) {
    if (this.isEnrolling) {
      return { success: false, message: "Enrollment already in progress" };
    }

    try {
      this.isEnrolling = true;
      console.log("Starting fingerprint enrollment via API...");

      // Call Django API endpoint (network-agnostic)
      const response = await fetch("/api/student/enroll/start/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": this._getCsrfToken(),
        },
        body: JSON.stringify({
          student_id: studentId,
          course_id: courseId,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.message || "Enrollment failed");
      }

      // Success!
      this.currentSession = {
        sessionId: data.session_id,
        slot: data.slot,
        studentId: studentId,
        startTime: new Date(),
      };

      console.log("Enrollment started. Session:", this.currentSession);

      // Start checking status every 2 seconds
      this._startStatusChecking(studentId);

      return {
        success: true,
        message: data.message,
        slot: data.slot,
        nextStep: data.next_step,
      };
    } catch (error) {
      console.error("Enrollment error:", error);
      this.isEnrolling = false;
      return { success: false, message: error.message };
    }
  }

  /**
   * Check enrollment status
   * Safe to call frequently
   */
  async checkStatus(studentId) {
    try {
      const response = await fetch(
        `/api/student/enroll/status/?student_id=${studentId}`
      );
      const data = await response.json();

      if (response.ok) {
        return data.enrollments || [];
      }
    } catch (error) {
      console.error("Status check error:", error);
    }
    return [];
  }

  /**
   * Cancel enrollment
   * Safe operation
   */
  async cancelEnrollment(studentId) {
    try {
      const response = await fetch("/api/student/enroll/cancel/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": this._getCsrfToken(),
        },
        body: JSON.stringify({ student_id: studentId }),
      });

      const data = await response.json();
      this.isEnrolling = false;
      this._stopStatusChecking();

      return { success: response.ok, message: data.message };
    } catch (error) {
      console.error("Cancel error:", error);
      return { success: false, message: error.message };
    }
  }

  /**
   * Mark attendance using fingerprint
   */
  async markAttendance(fingerprintId) {
    try {
      const response = await fetch("/api/student/attendance/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": this._getCsrfToken(),
        },
        body: JSON.stringify({ fingerprint_id: fingerprintId }),
      });

      const data = await response.json();
      return { success: response.ok, ...data };
    } catch (error) {
      console.error("Attendance error:", error);
      return { success: false, message: error.message };
    }
  }

  /**
   * Get device status
   * Safe read-only operation
   */
  async getDeviceStatus() {
    try {
      const response = await fetch("/api/device/status/");
      const data = await response.json();

      if (response.ok) {
        return data.device || {};
      }
    } catch (error) {
      console.error("Device status error:", error);
    }
    return {};
  }

  // ===== PRIVATE METHODS =====

  _startStatusChecking(studentId) {
    if (this.statusCheckInterval) {
      clearInterval(this.statusCheckInterval);
    }

    this.statusCheckInterval = setInterval(async () => {
      const enrollments = await this.checkStatus(studentId);

      // Check if any enrollment is complete
      const completed = enrollments.find((e) => e.is_enrolled);
      if (completed) {
        this._stopStatusChecking();
        this.isEnrolling = false;

        // Trigger callback if exists
        if (window.onBiometricEnrollmentComplete) {
          window.onBiometricEnrollmentComplete(completed);
        }
      }
    }, 2000);
  }

  _stopStatusChecking() {
    if (this.statusCheckInterval) {
      clearInterval(this.statusCheckInterval);
      this.statusCheckInterval = null;
    }
  }

  _getCsrfToken() {
    return (
      document.querySelector('[name="csrfmiddlewaretoken"]')?.value ||
      document.cookie
        .split("; ")
        .find((row) => row.startsWith("csrftoken="))
        ?.split("=")[1] ||
      ""
    );
  }
}

// Create global instance
window.biometricManager = new BiometricEnrollmentManager();

// Export for use
if (typeof module !== "undefined" && module.exports) {
  module.exports = BiometricEnrollmentManager;
}
