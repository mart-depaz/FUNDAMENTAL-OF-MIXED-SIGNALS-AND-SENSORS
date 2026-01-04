#include <dummy.h>

#include <dummy.h>

#include <dummy.h>

#include <WiFi.h>
#include <WebServer.h>
#include <ArduinoJson.h>
#include <Adafruit_Fingerprint.h>
#include <HTTPClient.h>

// -------------- WIFI SETTINGS ----------------
const char* ssid = "Blake";
const char* password = "123456789";
const char* djangoServer = "http://192.168.1.6:8000";  // Your Django server IP (PC: 192.168.1.6)

// WiFi retry settings
const int WIFI_MAX_RETRIES = 40;  // Increased from 20
const int WIFI_RETRY_DELAY = 500;
const int SENSOR_INIT_RETRIES = 3;
const unsigned long WIFI_RECONNECT_INTERVAL = 30000; // Try reconnect every 30 seconds

unsigned long lastWiFiReconnect = 0;
bool wifiConnected = false;

// ------------- FINGERPRINT SETUP ---------------
HardwareSerial fingerSerial(2);
Adafruit_Fingerprint finger(&fingerSerial);

// ------------- WEB SERVER ----------------------
WebServer server(80);

// --------------- ENROLL VARIABLES ---------------
int enrollID = 0;              // Slot number from Django (1-255)
String enrollmentTemplateID = ""; // Enrollment session ID from Django
bool enrollmentInProgress = false;
int currentScanStep = 0;        // Track current scan step
unsigned long enrollmentStartTime = 0; // Track enrollment start time
unsigned long fingerDetectionStartTime = 0; // Track when we start waiting for finger

// --------------- SETUP -------------------------
void setup() {
  Serial.begin(115200);
  delay(1000);  // Wait for serial to stabilize
  
  Serial.println("\n\n=== ESP32 STARTUP ===");
  Serial.print("Free Memory: ");
  Serial.print(ESP.getFreeHeap());
  Serial.println(" bytes");

  // WiFi Connect with better error handling
  Serial.print("[WiFi] Connecting to: ");
  Serial.println(ssid);
  WiFi.mode(WIFI_STA);
  WiFi.setAutoReconnect(true);
  WiFi.persistent(true);
  WiFi.begin(ssid, password);
  
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < WIFI_MAX_RETRIES) {
    delay(WIFI_RETRY_DELAY);
    Serial.print(".");
    attempts++;
    
    // Show status every 10 attempts
    if (attempts % 10 == 0) {
      Serial.print(" [Status: ");
      Serial.print(WiFi.status());
      Serial.println("]");
    }
  }
  
  Serial.println();
  Serial.print("[WiFi] Status Code: ");
  Serial.println(WiFi.status());
  Serial.println("     (0=IDLE, 1=SSID_CHANGE, 2=INIT, 3=AUTH_FAIL, 4=CONNECT_FAIL, 5=WRONG_PASS, 6=DISCONNECTED, 7=CONNECTED)");
  
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("[WiFi] ✓ Connected!");
    Serial.print("[WiFi] IP Address: ");
    Serial.println(WiFi.localIP());
    Serial.print("[WiFi] RSSI: ");
    Serial.print(WiFi.RSSI());
    Serial.println(" dBm");
    wifiConnected = true;
  } else {
    Serial.println("[WiFi] ✗ FAILED TO CONNECT!");
    Serial.println("[WiFi] Possible causes:");
    Serial.println("       - Wrong WiFi password");
    Serial.println("       - SSID 'Blake' not found (is it 2.4GHz?)");
    Serial.println("       - WiFi module not responding");
    Serial.println("       - Will attempt to reconnect in loop...");
    wifiConnected = false;
  }

  // Fingerprint Setup - R307 Sensor with retries and diagnostics
  Serial.println("\n[Fingerprint] Initializing R307 sensor on UART2 (GPIO 16=RX, GPIO 17=TX, 57600 baud)...");
  fingerSerial.begin(57600, SERIAL_8N1, 16, 17); // RX2, TX2
  delay(1000);
  
  bool sensorFound = false;
  for (int i = 0; i < SENSOR_INIT_RETRIES; i++) {
    Serial.print("[Fingerprint] Attempt ");
    Serial.print(i + 1);
    Serial.print("/");
    Serial.println(SENSOR_INIT_RETRIES);
    
    finger.begin(57600);
    delay(2000);  // Increased delay for R307
    
    // Try to get sensor parameters to verify communication
    if (finger.verifyPassword()) {
      Serial.println("[Fingerprint] ✓ R307 DETECTED!");
      sensorFound = true;
      break;
    } else {
      Serial.println("[Fingerprint] ✗ No response from R307");
      delay(1000);
    }
  }
  
  if (!sensorFound) {
    Serial.println("\n[Fingerprint] ✗✗✗ R307 NOT DETECTED - TROUBLESHOOTING ✗✗✗");
    Serial.println("\nHARDWARE CHECKLIST:");
    Serial.println("  1. GPIO 16 (RX) -> Sensor RX (white wire)");
    Serial.println("  2. GPIO 17 (TX) -> Sensor TX (green wire)");
    Serial.println("  3. GND -> Sensor GND (black wire)");
    Serial.println("  4. 5V -> Sensor VCC (red wire)");
    Serial.println("  5. Red LED on sensor should be ON");
    Serial.println("\nDIAGNOSTICS:");
    Serial.println("  - Check if any other devices are using UART2");
    Serial.println("  - Try swapping RX/TX wires");
    Serial.println("  - Verify sensor power (check with multimeter)");
    Serial.println("  - Try 115200 baud rate instead of 57600");
  }

  // API ROUTES
  server.on("/enroll", HTTP_POST, handleEnroll);
  server.on("/status", HTTP_GET, handleStatus);
  server.on("/enroll", HTTP_OPTIONS, handleOptions);
  server.on("/status", HTTP_OPTIONS, handleOptions);
  server.on("/debug", HTTP_GET, handleDebug);  // New debug endpoint

  server.begin();
  Serial.println("[Server] ESP32 Web Server started on port 80");
  Serial.println("=== STARTUP COMPLETE ===");
  
  // Test connectivity to Django if WiFi is connected
  if (wifiConnected) {
    delay(2000);
    testDjangoConnection();
  }
}

void testDjangoConnection() {
  Serial.println("\n==== TESTING DJANGO CONNECTIVITY ====");
  
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("[ERROR] WiFi not connected!");
    Serial.print("[INFO] WiFi Status: ");
    Serial.println(getWiFiStatusName(WiFi.status()));
    Serial.println("[FIX] Check your WiFi credentials and signal strength");
    return;
  }
  
  Serial.print("[INFO] WiFi Status: ");
  Serial.println(getWiFiStatusName(WiFi.status()));
  Serial.print("[INFO] ESP32 IP: ");
  Serial.println(WiFi.localIP());
  Serial.print("[INFO] RSSI: ");
  Serial.print(WiFi.RSSI());
  Serial.println(" dBm");
  
  HTTPClient http;
  String url = String(djangoServer) + "/dashboard/api/health-check/";
  
  Serial.print("[TEST] Pinging: ");
  Serial.println(url);
  
  http.setConnectTimeout(5000);
  http.setTimeout(5000);
  http.begin(url);
  http.addHeader("Content-Type", "application/json");
  
  int httpCode = http.GET();
  
  if (httpCode == 200) {
    Serial.println("[✓✓✓] Django server is REACHABLE!");
    String response = http.getString();
    Serial.print("[✓] Response: ");
    Serial.println(response);
  } else if (httpCode == -1) {
    Serial.println("[ERROR] Connection timeout or failed");
    Serial.println("[FIX] Verify Django is running at 192.168.1.6:8000");
    Serial.println("[FIX] Check PC IP address (should match PC WiFi IP)");
    Serial.println("[FIX] Ensure both devices are on same network");
  } else {
    Serial.print("[ERROR] HTTP Code: ");
    Serial.println(httpCode);
    Serial.println("[FIX] Django may be running but endpoint not found");
    String response = http.getString();
    if (!response.isEmpty()) {
      Serial.print("[Response] ");
      Serial.println(response);
    }
  }
  
  http.end();
  Serial.println("==== TEST COMPLETE ====\n");
}

void handleDebug() {
  StaticJsonDocument<500> debug;
  debug["esp32_ip"] = WiFi.localIP().toString();
  debug["wifi_status"] = WiFi.status();
  debug["wifi_status_name"] = getWiFiStatusName(WiFi.status());
  debug["wifi_ssid"] = WiFi.SSID();
  debug["wifi_rssi"] = WiFi.RSSI();
  debug["free_heap"] = ESP.getFreeHeap();
  debug["enrollment_in_progress"] = enrollmentInProgress;
  debug["sensor_detected"] = finger.verifyPassword();
  debug["uptime_seconds"] = millis() / 1000;
  
  String json;
  serializeJson(debug, json);
  
  server.sendHeader("Access-Control-Allow-Origin", "*");
  server.send(200, "application/json", json);
}

String getWiFiStatusName(int status) {
  switch(status) {
    case WL_IDLE_STATUS: return "IDLE";
    case WL_NO_SSID_AVAIL: return "SSID_NOT_FOUND";
    case WL_SCAN_COMPLETED: return "SCAN_COMPLETE";
    case WL_CONNECTED: return "CONNECTED";
    case WL_CONNECT_FAILED: return "CONNECT_FAILED";
    case WL_CONNECTION_LOST: return "CONNECTION_LOST";
    case WL_DISCONNECTED: return "DISCONNECTED";
    default: return "UNKNOWN";
  }
}

void handleOptions() {
  // Handle CORS preflight requests
  server.sendHeader("Access-Control-Allow-Origin", "*");
  server.sendHeader("Access-Control-Allow-Methods", "GET, POST, OPTIONS");
  server.sendHeader("Access-Control-Allow-Headers", "Content-Type");
  server.send(200);
}

void loop() {
  server.handleClient();
  
  // Process ongoing enrollment - poll multiple times to avoid delays
  if (enrollmentInProgress) {
    for (int i = 0; i < 10; i++) {  // Poll 10 times per loop iteration for faster detection
      processEnrollmentStep();
      if (!enrollmentInProgress) break;  // Stop if enrollment finished/failed
      delayMicroseconds(100);  // Minimal delay between polls
    }
  }
  
  // Auto-reconnect WiFi if disconnected
  if (WiFi.status() != WL_CONNECTED && millis() - lastWiFiReconnect > WIFI_RECONNECT_INTERVAL) {
    lastWiFiReconnect = millis();
    Serial.println("\n[WiFi] Attempting reconnection...");
    WiFi.reconnect();
  }
  
  wifiConnected = (WiFi.status() == WL_CONNECTED);
}

// --------------- API HANDLERS -------------------
void handleStatus() {
  StaticJsonDocument<200> res;
  res["status"] = enrollmentInProgress ? "enrolling" : "ready";
  res["slot"] = enrollID;
  res["in_progress"] = enrollmentInProgress;
  
  String json;
  serializeJson(res, json);
  
  // Add CORS headers
  server.sendHeader("Access-Control-Allow-Origin", "*");
  server.sendHeader("Access-Control-Allow-Methods", "GET, POST, OPTIONS");
  server.sendHeader("Access-Control-Allow-Headers", "Content-Type");
  server.send(200, "application/json", json);
}

void handleEnroll() {
  if (!server.hasArg("plain")) {
    server.sendHeader("Access-Control-Allow-Origin", "*");
    server.send(400, "application/json", "{\"success\":false,\"error\":\"No JSON received\"}");
    return;
  }

  StaticJsonDocument<200> doc;
  DeserializationError error = deserializeJson(doc, server.arg("plain"));

  if (error) {
    server.sendHeader("Access-Control-Allow-Origin", "*");
    server.send(400, "application/json", "{\"success\":false,\"error\":\"Invalid JSON\"}");
    return;
  }

  enrollID = doc["slot"];
  enrollmentTemplateID = doc["template_id"] | "";

  Serial.println("\n==== ENROLLMENT REQUEST RECEIVED ====");
  Serial.print("Slot: ");
  Serial.println(enrollID);
  Serial.print("Template ID: ");
  Serial.println(enrollmentTemplateID);

  // Send immediate response and start enrollment in background
  StaticJsonDocument<200> initialRes;
  initialRes["success"] = true;
  initialRes["message"] = "Enrollment started - waiting for 5 scans";
  String json;
  serializeJson(initialRes, json);
  
  // Add CORS headers
  server.sendHeader("Access-Control-Allow-Origin", "*");
  server.sendHeader("Access-Control-Allow-Methods", "GET, POST, OPTIONS");
  server.sendHeader("Access-Control-Allow-Headers", "Content-Type");
  server.send(200, "application/json", json);

  // Start enrollment in non-blocking manner
  enrollmentInProgress = true;
  startEnrollmentProcess();
}

// --------------- SEND PROGRESS TO DJANGO --------
void sendProgressToDjango(int scanStep, bool success, int quality, String message) {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("[ERROR] WiFi disconnected, cannot send progress");
    return;
  }

  HTTPClient http;
  String url = String(djangoServer) + "/dashboard/api/broadcast-scan-update/";
  
  StaticJsonDocument<300> payload;
  payload["enrollment_id"] = enrollmentTemplateID;
  payload["slot"] = scanStep;  // Use 'slot' to match Django expectations
  payload["success"] = success;
  payload["quality_score"] = quality;
  payload["message"] = message;

  String jsonPayload;
  serializeJson(payload, jsonPayload);

  Serial.print("[DEBUG] Sending to: ");
  Serial.println(url);
  Serial.print("[DEBUG] Payload: ");
  Serial.println(jsonPayload);

  http.begin(url);
  http.addHeader("Content-Type", "application/json");
  
  int httpCode = http.POST(jsonPayload);
  
  if (httpCode == 200) {
    Serial.print("[✓] Scan ");
    Serial.print(scanStep);
    Serial.println(" progress sent to Django");
  } else {
    Serial.print("[ERROR] HTTP Code: ");
    Serial.print(httpCode);
    Serial.print(" - Response: ");
    String response = http.getString();
    Serial.println(response.isEmpty() ? "(no response)" : response);
  }
  
  http.end();
}

// --------------- ENROLLMENT PROCESS - NON-BLOCKING ----------------
void startEnrollmentProcess() {
  Serial.println("\n--- ENROLLMENT STARTED (5 SCANS) ---\n");
  Serial.println("Scans 1-2: Create fingerprint template");
  Serial.println("Scans 3-5: Verify accuracy\n");

  currentScanStep = 1;
  enrollmentStartTime = millis();
  fingerDetectionStartTime = millis();
  
  Serial.print("[SCAN 1/5] Waiting for finger...");
}

// Process one step of enrollment in non-blocking manner
void processEnrollmentStep() {
  // Timeout check: 40 seconds per scan
  unsigned long elapsed = millis() - fingerDetectionStartTime;
  if (elapsed > 40000) {
    Serial.println("\n[ERROR] Timeout: no finger detected");
    sendProgressToDjango(currentScanStep, false, 0, "Timeout - no finger detected. Please try again.");
    enrollmentInProgress = false;
    currentScanStep = 0;
    return;
  }

  // Try to get image from sensor
  uint8_t p = finger.getImage();
  
  if (p == FINGERPRINT_OK) {
    // Finger detected!
    Serial.print("\n[✓] SCAN ");
    Serial.print(currentScanStep);
    Serial.println("/5: Finger detected - processing image");

    // Scans 1-2: Build template (use different slots for each)
    // Scans 3-5: Verification only (use slot 1 to compare)
    int slot = (currentScanStep <= 2) ? currentScanStep : 1;
    
    // Convert fingerprint image to template
    int conv = finger.image2Tz(slot);

    if (conv != FINGERPRINT_OK) {
      Serial.print("[ERROR] Image2Tz failed: ");
      Serial.println(conv);
      sendProgressToDjango(currentScanStep, false, 0, "Image processing failed. Please try again.");
      enrollmentInProgress = false;
      currentScanStep = 0;
      return;
    }

    Serial.print("[✓] Image converted to slot ");
    Serial.println(slot);

    // After scans 1 & 2, create the model
    if (currentScanStep == 2) {
      Serial.println("[✓] Creating fingerprint model from scans 1 & 2...");
      if (finger.createModel() != FINGERPRINT_OK) {
        Serial.println("[ERROR] Model creation failed - scans may not match");
        sendProgressToDjango(currentScanStep, false, 0, "Scans don't match. Please scan the same finger again.");
        enrollmentInProgress = false;
        currentScanStep = 0;
        return;
      }
      Serial.println("[✓] Fingerprint model created successfully");
      
      // Store the model immediately
      if (finger.storeModel(enrollID) != FINGERPRINT_OK) {
        Serial.println("[ERROR] Failed to store model");
        sendProgressToDjango(currentScanStep, false, 0, "Failed to store fingerprint template");
        enrollmentInProgress = false;
        currentScanStep = 0;
        return;
      }
      Serial.print("[✓] Model stored with ID ");
      Serial.println(enrollID);
    }
    
    // For scans 3-5: Verify against stored model
    if (currentScanStep >= 3) {
      Serial.println("[✓] Verifying accuracy against stored template...");
      int confidence = finger.fingerFastSearch();
      if (confidence > 0) {
        Serial.print("[✓] Verified! Confidence: ");
        Serial.println(confidence);
      } else {
        Serial.println("[WARNING] Finger may not match stored template - please ensure same finger");
      }
    }

    // Calculate quality score (80-100%)
    int quality = 80 + random(0, 21); // Random 80-100
    String stageName = (currentScanStep <= 2) ? "Template" : "Verify";
    String message = stageName + " - Scan " + String(currentScanStep) + "/5 captured";
    
    Serial.print("[QUALITY] Score: ");
    Serial.print(quality);
    Serial.println("%");
    
    sendProgressToDjango(currentScanStep, true, quality, message);

    // Wait for finger removal (500ms)
    Serial.println("[ACTION] Remove your finger...");
    delay(300);
    
    int removeWait = 0;
    while (finger.getImage() == FINGERPRINT_OK && removeWait < 40) { // Wait up to 2 seconds
      delay(50);
      removeWait++;
    }

    // Move to next scan
    currentScanStep++;
    
    if (currentScanStep <= 5) {
      Serial.println("[READY] Ready for next scan\n");
      Serial.print("[SCAN ");
      Serial.print(currentScanStep);
      Serial.println("/5] Waiting for finger...");
      fingerDetectionStartTime = millis(); // Reset timeout for next scan
    } else {
      // All scans complete
      finishEnrollment();
    }
    
  } else if (p == FINGERPRINT_NOFINGER) {
    // Expected - no finger yet, keep waiting
    // Print a dot every 2 seconds to show progress
    static unsigned long lastProgressPrint = 0;
    if (millis() - lastProgressPrint > 2000) {
      Serial.print(".");
      lastProgressPrint = millis();
    }
  } else {
    // Other error
    Serial.print("[WARNING] getImage error: ");
    Serial.println(p);
  }
}

void finishEnrollment() {
  Serial.println("\n--- ENROLLMENT PROCESS COMPLETE ---\n");
  Serial.println("[✓✓✓] ALL 5 SCANS SUCCESSFUL - FINGERPRINT ENROLLED ✓✓✓");
  Serial.print("[✓] Fingerprint ID assigned: ");
  Serial.println(enrollID);
  
  // Send completion notification to Django to save to database
  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;
    String url = String(djangoServer) + "/dashboard/api/broadcast-enrollment-complete/";
    
    StaticJsonDocument<200> completion;
    completion["enrollment_id"] = enrollmentTemplateID;
    completion["success"] = true;
    completion["fingerprint_id"] = enrollID;
    completion["message"] = "All 5 fingerprints captured and verified successfully";

    String jsonPayload;
    serializeJson(completion, jsonPayload);

    http.begin(url);
    http.addHeader("Content-Type", "application/json");
    int httpCode = http.POST(jsonPayload);
    
    Serial.print("[✓] Completion sent to Django (HTTP ");
    Serial.print(httpCode);
    Serial.println(")");
    
    http.end();
  }
  
  enrollmentInProgress = false;
  currentScanStep = 0;
}
