#include <Arduino.h>
#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <Adafruit_Fingerprint.h>
#include <HardwareSerial.h>

// ==================== MQTT BROKER SETTINGS ====================
// Using HiveMQ Public Broker (most reliable)
const char* mqtt_server = "broker.hivemq.com";     // HiveMQ MQTT broker
const int mqtt_port = 1883;                         // Standard MQTT port
const char* mqtt_client_id_base = "esp32_biometric";  // Base ID; actual ID will be unique per device
String mqtt_client_id;

// ==================== WIFI SETTINGS (CONFIGURABLE) ====================
// IMPORTANT: WiFi credentials can be changed via MQTT command
// Topics: biometric/esp32/command with {"command":"set_wifi","ssid":"...","password":"..."}
// 
// For cross-network support:
// 1. Primary: Use below credentials for your main network
// 2. Alternative: Send MQTT command to change WiFi (see handleCommand in code)
// 3. Alternative: Manually edit these lines and re-upload
//
// Supports dynamic reconfiguration via MQTT without recompiling!

String current_ssid = "DE PAZ";          // Change this to your network
String current_password = "Blake_2018";  // Change this to your password

// ==================== STATIC IP (OPTIONAL - DISABLED FOR DHCP) ====================
// Using DHCP (dynamic IP) instead of static for maximum network compatibility
// Static IP prevents connection on networks with different IP ranges
// To enable static IP, uncomment below and set appropriate values for your network:
// IPAddress staticIP(192, 168, 1, 9);
// IPAddress gateway(192, 168, 1, 1);
// IPAddress subnet(255, 255, 255, 0);

// ==================== MQTT TOPICS ====================
// These topics allow communication from any device/network
const char* topic_enroll_request = "biometric/esp32/enroll/request";     // Receive enrollment requests
const char* topic_enroll_response = "biometric/esp32/enroll/response";   // Send enrollment status
const char* topic_scan_ack = "biometric/esp32/scan/acknowledged";        // Receive scan acknowledgment from frontend
const char* topic_detect_request = "biometric/esp32/detect/request";     // Enable/disable detection mode
const char* topic_detect_response = "biometric/esp32/detect/response";   // Send detection results
const char* topic_status = "biometric/esp32/status";                     // Device status
const char* topic_command = "biometric/esp32/command";                   // General commands
const char* topic_fingerprint_result = "biometric/esp32/fingerprint";    // Fingerprint data

// ==================== FINGERPRINT SETUP ====================
HardwareSerial fingerSerial(2);
Adafruit_Fingerprint finger(&fingerSerial);

// ==================== CLIENTS ====================
WiFiClient espClient;
PubSubClient client(espClient);

// ==================== ENROLLMENT VARIABLES ====================
int enrollID = 0;
String enrollmentTemplateID = "";
bool enrollmentInProgress = false;
bool enrollmentCancelled = false;
bool enrollmentConfirmed = false;  // Flag for when user clicks "Confirm & Save"
int detectionMode = 0;  // 0=disabled, 1=registration, 2=attendance
unsigned long lastStatusPublish = 0;
const unsigned long STATUS_PUBLISH_INTERVAL = 30000;  // Publish status every 30 seconds

// ==================== FUNCTION PROTOTYPES ====================
void setup_wifi();
void setup_fingerprint();
void reconnect();
void callback(char* topic, byte* payload, unsigned int length);
void publishStatus();
void handleEnrollmentRequest(JsonDocument& doc);
void handleEnrollmentResponse(JsonDocument& doc);  // Handle completion from Django
void handleEnrollmentCompletion(JsonDocument& doc);  // Handle enrollment_saved from Django
void handleDetectionRequest(JsonDocument& doc);
void handleCommand(JsonDocument& doc);
void enrollFingerprint();
void attendanceScanning();
void publishFingerprintDetection(int fingerprintID, int confidence);

// ==================== SETUP ====================
void setup() {
  Serial.begin(115200);
  delay(500);
  
  Serial.println("\n========== ESP32 Biometric System ==========");
  
  setup_wifi();
  setup_fingerprint();

  // Generate a unique MQTT client id per device to avoid broker kicking us off due to ID conflicts.
  // Client-id conflicts are a common cause of "connected" but missing messages.
  uint64_t mac = ESP.getEfuseMac();
  mqtt_client_id = String(mqtt_client_id_base) + "_" + String((uint32_t)(mac >> 32), HEX) + String((uint32_t)mac, HEX);
  mqtt_client_id.toLowerCase();
  Serial.println(String("[MQTT] Client ID: ") + mqtt_client_id);
  
  // Configure MQTT
  client.setServer(mqtt_server, mqtt_port);
  client.setCallback(callback);
  client.setKeepAlive(60);
  client.setSocketTimeout(15);
  
  Serial.println("✓ Setup complete!\n");
}

// ==================== MAIN LOOP ====================
void loop() {
  // Maintain WiFi connection
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi disconnected, reconnecting...");
    setup_wifi();
  }
  
  // Maintain MQTT connection (CRITICAL: Check and reconnect if needed)
  if (!client.connected()) {
    reconnect();
  }
  
  // CRITICAL: Keep MQTT connection alive by calling loop frequently
  // This also processes incoming messages from subscribed topics
  client.loop();
  
  // Publish status periodically (skip during enrollment)
  if (!enrollmentInProgress && millis() - lastStatusPublish > STATUS_PUBLISH_INTERVAL) {
    publishStatus();
    lastStatusPublish = millis();
  }
  
  // Handle ongoing enrollment
  if (enrollmentInProgress && !enrollmentCancelled) {
    enrollFingerprint();
  }
  
  // Handle attendance scanning
  if (detectionMode == 2) {
    attendanceScanning();
  }
  
  delay(50);  // Reduced from 100ms to keep connection more responsive
}

// ==================== WiFi SETUP (DHCP MODE FOR CROSS-NETWORK) ====================
void setup_wifi() {
  Serial.print("Connecting to WiFi: ");
  Serial.println(current_ssid);
  
  WiFi.mode(WIFI_STA);
  WiFi.setSleep(false);
  WiFi.setAutoReconnect(true);
  WiFi.begin(current_ssid.c_str(), current_password.c_str());
  
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 20) {
    delay(500);
    Serial.print(".");
    attempts++;
  }
  
  Serial.println();
  if (WiFi.status() == WL_CONNECTED) {
    Serial.print("✓ WiFi OK - IP: ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("✗ WiFi Failed - check SSID/password");
  }
}

// ==================== FINGERPRINT SETUP ====================
void setup_fingerprint() {
  Serial.println("[DEBUG] Initializing R307 sensor...");
  
  fingerSerial.begin(57600, SERIAL_8N1, 16, 17);
  delay(500);
  
  Serial.println("[DEBUG] UART initialized at 57600 baud");
  Serial.println("[DEBUG] Testing sensor communication...");
  
  finger.begin(57600);
  delay(500);
  
  // Try to get sensor parameters (simpler than verifyPassword)
  int response = finger.getParameters();
  Serial.print("[DEBUG] getParameters() returned: ");
  Serial.println(response);
  
  bool sensor_detected = false;
  for (int attempt = 0; attempt < 3; attempt++) {
    Serial.print("[DEBUG] Attempt ");
    Serial.print(attempt + 1);
    Serial.print("/3: verifyPassword()...");
    
    if (finger.verifyPassword()) {
      Serial.println(" SUCCESS!");
      Serial.println("✓ R307 Sensor OK");
      sensor_detected = true;
      break;
    } else {
      Serial.println(" FAILED");
      delay(500);
    }
  }
  
  if (!sensor_detected) {
    Serial.println("⚠️  R307 Sensor NOT detected");
    Serial.println("CHECK: 1. Power (5V + 470µF capacitor)  2. Wiring (RX=GPIO16, TX=GPIO17)");
  }
}

// ==================== MQTT RECONNECT ====================
void reconnect() {
  int reconnect_attempts = 0;
  while (!client.connected() && reconnect_attempts < 5) {  // Try 5 times silently
    Serial.print("[MQTT] Connecting...");
    if (client.connect(mqtt_client_id.c_str(), NULL, NULL, NULL, 1, false, NULL, true)) {
      Serial.println(" ✓ Connected!");

      bool s1 = client.subscribe(topic_enroll_request, 1);
      bool s2 = client.subscribe(topic_detect_request, 1);
      bool s3 = client.subscribe(topic_command, 1);
      bool s4 = client.subscribe("biometric/esp32/enroll/completion", 1);

      Serial.println(String("[MQTT] Subscribed enroll/request: ") + (s1 ? "OK" : "FAIL"));
      Serial.println(String("[MQTT] Subscribed detect/request: ") + (s2 ? "OK" : "FAIL"));
      Serial.println(String("[MQTT] Subscribed command: ") + (s3 ? "OK" : "FAIL"));
      Serial.println(String("[MQTT] Subscribed enroll/completion: ") + (s4 ? "OK" : "FAIL"));

      // NOTE: Do not subscribe to topic_enroll_response; ESP32 publishes to it and would receive its own messages.
      return;
    }

    Serial.print(" ✗ Failed, rc=");
    Serial.println(client.state());
    delay(2000);
    reconnect_attempts++;
  }
}

// ==================== MQTT CALLBACK ====================
void callback(char* topic, byte* payload, unsigned int length) {
  Serial.print("Message received on topic: ");
  Serial.println(topic);
  
  // If Django clears a retained message it will publish a zero-length payload.
  // Ignore these to avoid parsing errors and spurious "invalid JSON" logs.
  if (length == 0) {
    Serial.println("[MQTT] Ignoring empty payload (retained clear)");
    return;
  }
  
  // Convert payload to string
  String message;
  for (unsigned int i = 0; i < length; i++) {
    message += (char)payload[i];
  }
  Serial.println("Payload: " + message);
  
  // Parse JSON
  StaticJsonDocument<256> doc;
  DeserializationError error = deserializeJson(doc, message);
  
  if (error) {
    Serial.print("JSON parse error: ");
    Serial.println(error.c_str());
    return;
  }
  
  // Route to appropriate handler
  if (strcmp(topic, topic_enroll_request) == 0) {
    handleEnrollmentRequest(doc);
  } else if (strcmp(topic, topic_enroll_response) == 0) {
    handleEnrollmentResponse(doc);  // Handle completion messages from Django
  } else if (strcmp(topic, "biometric/esp32/enroll/completion") == 0) {
    handleEnrollmentCompletion(doc);  // Handle enrollment_saved from Django
  } else if (strcmp(topic, topic_detect_request) == 0) {
    handleDetectionRequest(doc);
  } else if (strcmp(topic, topic_command) == 0) {
    handleCommand(doc);
  } else {
    Serial.print("[CALLBACK] Unknown topic: ");
    Serial.println(topic);
  }
}

// ==================== HANDLE ENROLLMENT REQUEST ====================
void handleEnrollmentRequest(JsonDocument& doc) {
  int slot = doc["slot"] | 0;
  String template_id = doc["template_id"] | "";
  String action = doc["action"] | "start";
  
  Serial.println("Enrollment Request:");
  Serial.print("  Slot: ");
  Serial.println(slot);
  Serial.print("  Template ID: ");
  Serial.println(template_id);
  Serial.print("  Action: ");
  Serial.println(action);
  
  if (action == "start") {
    // Clear any retained start message immediately so it won't replay after reboot/reconnect.
    // This ensures enrollment only starts when the user explicitly clicks Start again.
    // (We still keep retain=True on the backend so ESP32 doesn't miss the start on flaky WiFi.)
    bool cleared = client.publish(topic_enroll_request, "", true);
    Serial.println(String("[MQTT] Cleared retained enroll/request: ") + (cleared ? "OK" : "FAIL"));

    // Check if another enrollment is already in progress
    if (enrollmentInProgress) {
      Serial.println("[ENROLLMENT] ✗ BLOCKED: Another enrollment already in progress!");
      StaticJsonDocument<128> response;
      response["status"] = "blocked";
      response["message"] = "Another student is currently enrolling. Please wait...";
      response["waiting_for"] = "enrollment_completion";
      response["slot"] = enrollID;
      response["template_id"] = enrollmentTemplateID;
      String jsonStr;
      serializeJson(response, jsonStr);
      client.publish(topic_enroll_response, jsonStr.c_str());
      client.loop();
      return;
    }
    
    int capacity = (finger.capacity > 0) ? finger.capacity : 300;
    if (slot < 1 || slot > capacity) {
      Serial.println("Invalid slot number!");
      // Publish error
      StaticJsonDocument<128> response;
      response["status"] = "error";
      response["message"] = "Invalid slot number (1-" + String(capacity) + ")";
      response["error_code"] = slot;
      response["slot"] = slot;
      response["template_id"] = template_id;
      String jsonStr;
      serializeJson(response, jsonStr);
      client.publish(topic_enroll_response, jsonStr.c_str());
      return;
    }
    
    enrollID = slot;
    enrollmentTemplateID = template_id;
    enrollmentInProgress = true;
    enrollmentCancelled = false;
    enrollmentConfirmed = false;
    
    Serial.println("[ENROLLMENT] ✓ Flag set: enrollmentInProgress = true");
    Serial.println("[ENROLLMENT] ✓ Flag set: enrollmentCancelled = false");
    Serial.println("[ENROLLMENT] ✓ Flag set: enrollmentConfirmed = false");
    
    // Publish started
    StaticJsonDocument<128> response;
    response["status"] = "started";
    response["slot"] = enrollID;
    response["template_id"] = enrollmentTemplateID;
    String jsonStr;
    serializeJson(response, jsonStr);
    client.publish(topic_enroll_response, jsonStr.c_str());
    client.loop();
    
    Serial.println("Enrollment started for slot " + String(enrollID));
  } 
  else if (action == "confirm") {
    // User clicked "Confirm & Save" button - create and save the model
    Serial.println("[ENROLLMENT] ✓ Enrollment confirmation received from user!");
    Serial.println("[ENROLLMENT] → Proceeding to create and store fingerprint model...");
    enrollmentConfirmed = true;
  }
  else if (action == "cancel" || action == "cancel_enrollment") {
    enrollmentCancelled = true;
    enrollmentInProgress = false;
    enrollmentConfirmed = false;
    
    // Publish cancelled
    StaticJsonDocument<128> response;
    response["status"] = "cancelled";
    response["slot"] = enrollID;
    response["template_id"] = enrollmentTemplateID;
    String jsonStr;
    serializeJson(response, jsonStr);
    client.publish(topic_enroll_response, jsonStr.c_str());
    
    Serial.println("Enrollment cancelled!");
  }
}

// ==================== HANDLE ENROLLMENT RESPONSE FROM DJANGO ====================
// Called when Django sends completion message after user confirms enrollment
void handleEnrollmentResponse(JsonDocument& doc) {
  String status = doc["status"] | "";
  String message = doc["message"] | "";
  String template_id = doc["template_id"] | "";
  
  Serial.println("\n================================================================================");
  Serial.println("[ENROLLMENT RESPONSE] Message from Django:");
  Serial.print("  Status: ");
  Serial.println(status);
  Serial.print("  Template ID: ");
  Serial.println(template_id);
  Serial.print("  Message: ");
  Serial.println(message);
  Serial.println("================================================================================\n");
  
  // If Django confirms the enrollment was saved, reset enrollment flags
  if (status == "enrollment_saved") {
    Serial.println("[ENROLLMENT] ✓✓✓ Django confirmed: Fingerprint saved to database!");
    Serial.println("[ENROLLMENT] ✓✓✓ Resetting enrollment flags for next enrollment...");
    
    // Reset all enrollment flags to allow next enrollment
    enrollmentInProgress = false;
    enrollmentCancelled = false;
    enrollmentConfirmed = false;
    enrollID = 0;
    enrollmentTemplateID = "";
    
    Serial.println("[ENROLLMENT] ✓✓✓ READY FOR NEXT ENROLLMENT!");
    Serial.println();
  }
}

// ==================== HANDLE ENROLLMENT COMPLETION FROM DJANGO ====================
// Called when Django publishes enrollment_saved message via MQTT
void handleEnrollmentCompletion(JsonDocument& doc) {
  String status = doc["status"] | "";
  String message = doc["message"] | "";
  String template_id = doc["template_id"] | "";
  
  Serial.println("\n================================================================================");
  Serial.println("[ENROLLMENT COMPLETION] Message from Django:");
  Serial.print("  Status: ");
  Serial.println(status);
  Serial.print("  Template ID: ");
  Serial.println(template_id);
  Serial.print("  Message: ");
  Serial.println(message);
  Serial.println("================================================================================\n");
  
  // If Django confirms the enrollment was saved, reset enrollment flags
  if (status == "enrollment_saved") {
    Serial.println("[ENROLLMENT] ✓✓✓ Django confirmed: Fingerprint saved to database!");
    Serial.println("[ENROLLMENT] ✓✓✓ Resetting enrollment flags for next enrollment...");
    
    // Reset all enrollment flags to allow next enrollment
    enrollmentInProgress = false;
    enrollmentCancelled = false;
    enrollmentConfirmed = false;
    enrollID = 0;
    enrollmentTemplateID = "";
    
    Serial.println("[ENROLLMENT] ✓✓✓ READY FOR NEXT ENROLLMENT!");
    Serial.println();
  }
}

// ==================== HANDLE DETECTION REQUEST ====================
void handleDetectionRequest(JsonDocument& doc) {
  String action = doc["action"] | "disable";
  
  Serial.println("Detection Request:");
  Serial.print("  Action: ");
  Serial.println(action);
  Serial.print("  Mode: ");
  
  // Check if action is start/enable
  if (action == "enable" || action == "start" || action == "start_detection") {
    // Mode can come as integer or string
    if (doc.containsKey("mode")) {
      int modeInt = -1;
      
      // Try to read as integer first
      if (doc["mode"].is<int>()) {
        modeInt = doc["mode"].as<int>();
      } else {
        // Try to read as string
        String modeStr = doc["mode"] | "";
        Serial.println(modeStr);
        
        if (modeStr == "registration" || modeStr == "1") {
          modeInt = 1;
        } else if (modeStr == "attendance" || modeStr == "2") {
          modeInt = 2;
        }
      }
      
      // Convert integer mode to string for logging
      String modeDisplay = (modeInt == 1) ? "registration" : (modeInt == 2) ? "attendance" : "unknown";
      
      if (modeInt == 1 || modeInt == 2) {
        detectionMode = modeInt;
        Serial.println("Detection enabled in mode " + String(modeInt) + " (" + modeDisplay + ")");
      } else {
        Serial.println(modeDisplay);
        // Invalid mode, disable detection
        detectionMode = 0;
        Serial.println("Invalid mode, detection disabled");
      }
    } else {
      Serial.println("No mode specified");
      detectionMode = 0;
    }
  } else if (action == "disable" || action == "stop" || action == "stop_detection") {
    Serial.println("Detection disabled");
    detectionMode = 0;
  } else {
    Serial.print("Unknown action: ");
    Serial.println(action);
    detectionMode = 0;
  }
  
  // Publish status
  publishStatus();
}

// ==================== HANDLE GENERAL COMMANDS ====================
void handleCommand(JsonDocument& doc) {
  String cmd = doc["command"] | "";
  
  if (cmd == "restart") {
    Serial.println("Restart command received!");
    delay(1000);
    ESP.restart();
  }
  else if (cmd == "set_wifi") {
    // Command to change WiFi network dynamically via MQTT
    // Message format: {"command":"set_wifi","ssid":"NewNetwork","password":"NewPassword"}
    String newSSID = doc["ssid"] | "";
    String newPassword = doc["password"] | "";
    
    if (newSSID.length() > 0) {
      Serial.println("\n========================================");
      Serial.println("[WIFI] Changing WiFi network...");
      Serial.println("[WIFI] New SSID: " + newSSID);
      Serial.println("[WIFI] New Password: " + (newPassword.length() > 0 ? String(newPassword.length()) + " characters" : "none"));
      
      // Update global variables
      current_ssid = newSSID;
      current_password = newPassword;
      
      // Disconnect and reconnect with new credentials
      WiFi.disconnect();
      delay(1000);
      WiFi.begin(current_ssid.c_str(), current_password.c_str());
      
      // Wait for connection
      int attempts = 0;
      while (WiFi.status() != WL_CONNECTED && attempts < 10) {
        delay(500);
        Serial.print(".");
        attempts++;
      }
      
      Serial.println();
      if (WiFi.status() == WL_CONNECTED) {
        Serial.println("[WIFI] ✓ Connected to new network!");
        Serial.print("[WIFI] IP: ");
        Serial.println(WiFi.localIP());
        Serial.println("========================================\n");
        
        // Publish success
        StaticJsonDocument<256> response;
        response["command"] = "set_wifi";
        response["status"] = "success";
        response["ssid"] = current_ssid;
        response["ip"] = WiFi.localIP().toString();
        String jsonStr;
        serializeJson(response, jsonStr);
        client.publish(topic_status, jsonStr.c_str());
      } else {
        Serial.println("[WIFI] ✗ Failed to connect to new network");
        Serial.println("========================================\n");
        
        // Publish failure
        StaticJsonDocument<256> response;
        response["command"] = "set_wifi";
        response["status"] = "failed";
        response["ssid"] = newSSID;
        String jsonStr;
        serializeJson(response, jsonStr);
        client.publish(topic_status, jsonStr.c_str());
      }
    } else {
      Serial.println("[WIFI] ✗ SSID not provided");
    }
  }
  else if (cmd == "sensor_info") {
    StaticJsonDocument<256> response;
    response["command"] = "sensor_info";
    response["capacity"] = finger.capacity;
    response["stored"] = finger.templateCount;
    String jsonStr;
    serializeJson(response, jsonStr);
    client.publish(topic_status, jsonStr.c_str());
  }
  else if (cmd == "test_sensor") {
    Serial.println("\n=== SENSOR TEST MODE ===");
    Serial.println("Testing R307 finger detection...");
    Serial.println("Place your finger on the sensor now!");
    
    StaticJsonDocument<256> response;
    response["command"] = "test_sensor";
    response["status"] = "testing";
    
    // Try to read finger 10 times
    int detections = 0;
    for (int i = 0; i < 10; i++) {
      Serial.print("Attempt ");
      Serial.print(i + 1);
      Serial.print(": ");
      
      int p = finger.getImage();
      if (p == FINGERPRINT_OK) {
        detections++;
        Serial.println("✓ FINGER DETECTED!");
      } else if (p == FINGERPRINT_NOFINGER) {
        Serial.println("No finger");
      } else {
        Serial.print("Error code: ");
        Serial.println(p);
      }
      delay(1000);
    }
    
    response["detections"] = detections;
    response["test_complete"] = true;
    String jsonStr;
    serializeJson(response, jsonStr);
    client.publish(topic_status, jsonStr.c_str());
  }
  else if (cmd == "clear_all") {
    Serial.println("Clear all fingerprints command received!");
    finger.emptyDatabase();
    delay(1000);
    
    StaticJsonDocument<128> response;
    response["command"] = "clear_all";
    response["status"] = "success";
    String jsonStr;
    serializeJson(response, jsonStr);
    client.publish(topic_status, jsonStr.c_str());
  }
}

// ==================== ATTENDANCE SCANNING ====================
void attendanceScanning() {
  // This function continuously scans for fingerprints during attendance mode
  // Uses HARDWARE-BASED MATCHING for accuracy (fingerprints stored in sensor memory)
  // When a match is found, publishes the fingerprint slot number to Django
  // Django looks up which student has that fingerprint_id
  
  static unsigned long lastScanTime = 0;
  const unsigned long SCAN_INTERVAL = 300;  // Scan every 300ms (reduce sensor packet errors)
  static unsigned long lastDebugTime = 0;

  // Anti-fraud / accuracy hardening
  // Only publish a match when it is STABLE to prevent wrong IDs (e.g., 101/102/103 flip).
  const int MIN_CONFIDENCE = 40;                 // Faster UX: accept moderate confidence matches
  const int HIGH_CONFIDENCE_BYPASS = 65;          // Strong match: allow fast confirm
  const int REQUIRED_STABLE_READS = 1;            // Faster UX: publish on first acceptable match
  const unsigned long MIN_PUBLISH_INTERVAL = 1500; // Prevent rapid repeats (faster instructor UX)
  static int lastCandidateId = -1;
  static int stableReads = 0;
  static bool requireFingerRemoval = false;
  static unsigned long lastPublishMs = 0;
  static unsigned long lastHintMs = 0;
  
  // Limit scan frequency to avoid overwhelming the sensor
  if (millis() - lastScanTime < SCAN_INTERVAL) {
    return;
  }
  lastScanTime = millis();
  
  // Try to get fingerprint image
  int p = finger.getImage();

  // Require finger removal between publishes to avoid repeated/unstable scans
  if (p == FINGERPRINT_NOFINGER) {
    if (requireFingerRemoval) {
      requireFingerRemoval = false;
      lastCandidateId = -1;
      stableReads = 0;
      Serial.println("[ATTENDANCE] ✓ Finger removed - ready for next student");
    }
    return;
  }

  if (requireFingerRemoval) {
    // Finger still present after a publish; ignore until removed.
    return;
  }
  
  if (p == FINGERPRINT_OK) {
    // Image captured successfully
    Serial.println("✓ Fingerprint detected during attendance!");
    
    // Convert image to template
    int p2 = finger.image2Tz(1);
    
    if (p2 == FINGERPRINT_OK) {
      Serial.println("✓ Fingerprint template created!");
      
      // ==================== HARDWARE-BASED MATCHING ====================
      // Search the sensor's database for this fingerprint
      // This is ACCURATE because we're comparing against enrolled templates in sensor memory
      int p3 = finger.fingerFastSearch();

      // Retry once on transient sensor errors (often caused by fast loops / packet errors)
      if (p3 != FINGERPRINT_OK && p3 != FINGERPRINT_NOTFOUND) {
        delay(60);
        p3 = finger.fingerFastSearch();
      }
      
      if (p3 == FINGERPRINT_OK) {
        // Match found!
        int fingerprintID = finger.fingerID;
        int confidence = finger.confidence;

        Serial.print("✓ MATCH FOUND! ID: ");
        Serial.print(fingerprintID);
        Serial.print(", Confidence: ");
        Serial.println(confidence);

        if (fingerprintID > 0 && fingerprintID < 100) {
          if (!requireFingerRemoval && (millis() - lastHintMs) > 1500) {
            StaticJsonDocument<256> doc;
            doc["fingerprint_id"] = -2;
            doc["confidence"] = confidence;
            doc["timestamp"] = millis();
            doc["mode"] = "attendance";
            doc["match_type"] = "hint";
            doc["reason"] = "legacy_slot";

            String jsonStr;
            serializeJson(doc, jsonStr);
            client.publish(topic_fingerprint_result, jsonStr.c_str());
            Serial.println("Hint published to Django: " + jsonStr);
            lastHintMs = millis();
          }

          lastCandidateId = -1;
          stableReads = 0;
          return;
        }

        // Enforce minimum confidence
        if (confidence < MIN_CONFIDENCE) {
          Serial.println("[ATTENDANCE] ✗ Low confidence - ignoring match");

          if (!requireFingerRemoval && (millis() - lastHintMs) > 700) {
            StaticJsonDocument<256> doc;
            doc["fingerprint_id"] = -2;
            doc["confidence"] = confidence;
            doc["timestamp"] = millis();
            doc["mode"] = "attendance";
            doc["match_type"] = "hint";
            doc["reason"] = "low_confidence";

            String jsonStr;
            serializeJson(doc, jsonStr);
            client.publish(topic_fingerprint_result, jsonStr.c_str());
            Serial.println("Hint published to Django: " + jsonStr);
            lastHintMs = millis();
          }

          lastCandidateId = -1;
          stableReads = 0;
          return;
        }

        // High-confidence fast path: publish immediately.
        // This prevents the system from never publishing (and thus no name shown in frontend)
        // when the sensor occasionally flips IDs before stabilizing.
        if (confidence >= HIGH_CONFIDENCE_BYPASS) {
          Serial.println("[ATTENDANCE] ✓ High confidence - bypassing stable read requirement");
          stableReads = REQUIRED_STABLE_READS;
        } else {
          // Enforce stable reads (same ID twice in a row)
          if (lastCandidateId == fingerprintID) {
            stableReads++;
          } else {
            lastCandidateId = fingerprintID;
            stableReads = 1;
          }

          Serial.print("[ATTENDANCE] Stable reads for ID ");
          Serial.print(fingerprintID);
          Serial.print(": ");
          Serial.println(stableReads);

          // If we only got 1 stable read, do an immediate confirm search.
          // This keeps accuracy (must match the SAME ID twice) while improving publish reliability
          // when the sensor intermittently throws packet errors.
          if (stableReads < REQUIRED_STABLE_READS) {
            // Re-capture and re-search for confirmation. This is more reliable than re-calling
            // fingerFastSearch() immediately (which often fails with packet error 23).
            int confirmP = -1;
            int confirmId = -1;
            int confirmConf = 0;

            for (int attempt = 0; attempt < 2 && stableReads < REQUIRED_STABLE_READS; attempt++) {
              delay(120);
              int c1 = finger.getImage();
              if (c1 != FINGERPRINT_OK) {
                continue;
              }
              int c2 = finger.image2Tz(1);
              if (c2 != FINGERPRINT_OK) {
                continue;
              }
              confirmP = finger.fingerFastSearch();
              if (confirmP == FINGERPRINT_OK) {
                confirmId = finger.fingerID;
                confirmConf = finger.confidence;
                if (confirmId == fingerprintID && confirmConf >= MIN_CONFIDENCE) {
                  stableReads = REQUIRED_STABLE_READS;
                }
              }
            }

            if (stableReads >= REQUIRED_STABLE_READS) {
              Serial.println("[ATTENDANCE] ✓ Confirm re-scan succeeded");
            } else {
              Serial.print("[ATTENDANCE] ✗ Confirm re-scan failed (p=");
              Serial.print(confirmP);
              Serial.print(", id=");
              Serial.print(confirmId);
              Serial.print(", conf=");
              Serial.print(confirmConf);
              Serial.println(")");

              if (!requireFingerRemoval && (millis() - lastHintMs) > 1500) {
                StaticJsonDocument<256> doc;
                doc["fingerprint_id"] = -2;
                doc["confidence"] = confidence;
                doc["timestamp"] = millis();
                doc["mode"] = "attendance";
                doc["match_type"] = "hint";
                doc["reason"] = "confirm_failed";

                String jsonStr;
                serializeJson(doc, jsonStr);
                client.publish(topic_fingerprint_result, jsonStr.c_str());
                Serial.println("Hint published to Django: " + jsonStr);
                lastHintMs = millis();
              }
            }
          }

          if (stableReads < REQUIRED_STABLE_READS) {
            return;
          }
        }

        // Rate limit publishes
        if (millis() - lastPublishMs < MIN_PUBLISH_INTERVAL) {
          Serial.println("[ATTENDANCE] Rate-limited publish - ignoring");
          return;
        }

        // Publish the matched fingerprint slot to Django
        // Django will look up which student has this fingerprint_id
        StaticJsonDocument<256> doc;
        doc["fingerprint_id"] = fingerprintID;
        doc["confidence"] = confidence;
        doc["timestamp"] = millis();
        doc["mode"] = "attendance";
        doc["match_type"] = "hardware";  // Indicate this is hardware-matched (accurate)

        String jsonStr;
        serializeJson(doc, jsonStr);

        client.publish(topic_fingerprint_result, jsonStr.c_str());
        Serial.println("Match published to Django (stable): " + jsonStr);

        lastPublishMs = millis();
        requireFingerRemoval = true;
        lastCandidateId = -1;
        stableReads = 0;

        // Small delay to reduce sensor spam
        delay(250);

      } else if (p3 == FINGERPRINT_NOTFOUND) {
        // No match found in sensor database
        Serial.println("✗ No match in sensor database - fingerprint not enrolled");

        // Publish an explicit "unregistered" event so the frontend can show a warning.
        // Use fingerprint_id=-1 as the sentinel value.
        if (millis() - lastPublishMs >= MIN_PUBLISH_INTERVAL) {
          StaticJsonDocument<256> doc;
          doc["fingerprint_id"] = -1;
          doc["confidence"] = 0;
          doc["timestamp"] = millis();
          doc["mode"] = "attendance";
          doc["match_type"] = "hardware";

          String jsonStr;
          serializeJson(doc, jsonStr);
          client.publish(topic_fingerprint_result, jsonStr.c_str());
          Serial.println("Unregistered published to Django: " + jsonStr);

          lastPublishMs = millis();
          requireFingerRemoval = true;
          lastCandidateId = -1;
          stableReads = 0;
        }
        
      } else {
        Serial.print("✗ Sensor search error: ");
        Serial.println(p3);

        if (!requireFingerRemoval && (millis() - lastHintMs) > 1500) {
          StaticJsonDocument<256> doc;
          doc["fingerprint_id"] = -2;
          doc["confidence"] = 0;
          doc["timestamp"] = millis();
          doc["mode"] = "attendance";
          doc["match_type"] = "hint";
          doc["reason"] = String("sensor_search_error_") + String(p3);

          String jsonStr;
          serializeJson(doc, jsonStr);
          client.publish(topic_fingerprint_result, jsonStr.c_str());
          Serial.println("Hint published to Django: " + jsonStr);
          lastHintMs = millis();
        }

        // Reset candidate tracking after sensor errors
        lastCandidateId = -1;
        stableReads = 0;
      }
    } else {
      Serial.print("✗ Fingerprint template error: ");
      Serial.println(p2);

      if (!requireFingerRemoval && (millis() - lastHintMs) > 1500) {
        StaticJsonDocument<256> doc;
        doc["fingerprint_id"] = -2;
        doc["confidence"] = 0;
        doc["timestamp"] = millis();
        doc["mode"] = "attendance";
        doc["match_type"] = "hint";
        doc["reason"] = String("template_error_") + String(p2);

        String jsonStr;
        serializeJson(doc, jsonStr);
        client.publish(topic_fingerprint_result, jsonStr.c_str());
        Serial.println("Hint published to Django: " + jsonStr);
        lastHintMs = millis();
      }
    }
  } else if (p != FINGERPRINT_NOFINGER) {
    // Some other error (not "no finger" which is normal)
    if (millis() - lastDebugTime > 5000) {  // Only log errors every 5 seconds to avoid spam
      Serial.print("✗ Sensor error during getImage(): ");
      Serial.println(p);
      lastDebugTime = millis();
    }

    if (!requireFingerRemoval && (millis() - lastHintMs) > 1500) {
      StaticJsonDocument<256> doc;
      doc["fingerprint_id"] = -2;
      doc["confidence"] = 0;
      doc["timestamp"] = millis();
      doc["mode"] = "attendance";
      doc["match_type"] = "hint";
      doc["reason"] = String("get_image_error_") + String(p);

      String jsonStr;
      serializeJson(doc, jsonStr);
      client.publish(topic_fingerprint_result, jsonStr.c_str());
      Serial.println("Hint published to Django: " + jsonStr);
      lastHintMs = millis();
    }
  }
  // If p == FINGERPRINT_NOFINGER, just continue scanning (normal state)
}

// ==================== PUBLISH STATUS ====================
void publishStatus() {
  StaticJsonDocument<256> doc;
  doc["device_id"] = mqtt_client_id;
  doc["status"] = "online";
  doc["wifi_signal"] = WiFi.RSSI();
  doc["enrollment_in_progress"] = enrollmentInProgress;
  doc["detection_mode"] = detectionMode;
  doc["fingerprints_stored"] = finger.templateCount;
  doc["fingerprint_capacity"] = finger.capacity;
  doc["uptime_seconds"] = millis() / 1000;
  
  String jsonStr;
  serializeJson(doc, jsonStr);
  client.publish(topic_status, jsonStr.c_str());
  
  Serial.println("Status published: " + jsonStr);
}

// ==================== ENROLL FINGERPRINT ====================
void enrollFingerprint() {
  static int enrollmentStep = 0;
  static unsigned long lastStep = 0;
  static unsigned long stepStartTime = 0;  // Track when we published a scan to wait before advancing
  static int noFingerCount = 0;
  static bool waitingMessageShown[3] = {false, false, false};  // Track if waiting message was already shown for each step
  static bool requireFingerRelease = false;
  static bool removeMessageShown = false;
  static unsigned long lastWaitingReminder = 0;
  static bool modelCreated = false;
  
  // Fast polling - check every 200ms for responsive detection
  if (millis() - lastStep < 200) {
    return;  // Wait 200ms between checks
  }
  lastStep = millis();
  
  if (!enrollmentInProgress) {
    enrollmentStep = 0;
    noFingerCount = 0;
    waitingMessageShown[0] = false;
    waitingMessageShown[1] = false;
    waitingMessageShown[2] = false;
    requireFingerRelease = false;
    removeMessageShown = false;
    lastWaitingReminder = 0;
    modelCreated = false;
    return;
  }
  
  if (enrollmentCancelled) {
    enrollmentStep = 0;
    noFingerCount = 0;
    waitingMessageShown[0] = false;
    waitingMessageShown[1] = false;
    waitingMessageShown[2] = false;
    requireFingerRelease = false;
    removeMessageShown = false;
    lastWaitingReminder = 0;
    return;
  }

  // Require the user to remove their finger between scans.
  // This dramatically improves reliability, especially for scan 3.
  if (requireFingerRelease) {
    int rp = finger.getImage();
    if (rp == FINGERPRINT_NOFINGER) {
      requireFingerRelease = false;
      removeMessageShown = false;
      noFingerCount = 0;
      stepStartTime = millis();
      Serial.println("[ENROLLMENT] ✓ Finger removed - ready for next scan");
      Serial.println();
    } else {
      if (!removeMessageShown) {
        Serial.println("\n========================================");
        Serial.println("[ENROLLMENT] REMOVE YOUR FINGER");
        Serial.println("Then place it again for the next scan...");
        Serial.println("========================================\n");
        removeMessageShown = true;
      }
      return;
    }
  }
  
  if (enrollmentStep == 0) {
    // Step 1: Get first scan
    if (!waitingMessageShown[0]) {
      Serial.println("\n========================================");
      Serial.println("[SCAN 1/3] PLACE FINGER ON SENSOR");
      Serial.println("========================================");
      Serial.println("[ENROLLMENT] ⏳ Waiting for finger placement (Scan 1/3)...");
      waitingMessageShown[0] = true;
    }
    
    int p = finger.getImage();
    
    if (p == FINGERPRINT_OK) {
      Serial.println("\n========================================");
      Serial.println("[✓✓✓] FINGER DETECTED! [✓✓✓]");
      Serial.println("========================================\n");
      noFingerCount = 0;
      
      // Convert image to template to assess quality
      int conv = finger.image2Tz(1);
      
      // Estimate quality based on conversion result
      uint16_t imageQuality = 80;  // Default good quality
      if (conv == FINGERPRINT_IMAGEMESS) {
        imageQuality = 45;
        Serial.println("[QUALITY] Image quality: LOW (messy/unclear)");
      } else if (conv == FINGERPRINT_FEATUREFAIL) {
        imageQuality = 60;
        Serial.println("[QUALITY] Image quality: MEDIUM (insufficient features)");
      } else if (conv == FINGERPRINT_OK) {
        imageQuality = 95;
        Serial.println("[QUALITY] Image quality: HIGH (clear)");
      } else {
        Serial.print("[ERROR] Image conversion failed with code: ");
        Serial.println(conv);
        imageQuality = 0;
      }
      
      Serial.print("[QUALITY SCORE] ");
      Serial.println(imageQuality);
      
      // Check if quality is acceptable (threshold: 50%)
      Serial.println("[VALIDATION] Checking quality threshold...");
      if (imageQuality < 50) {
        Serial.println("[❌] Image quality too low - please try again with a clearer contact");
        Serial.println("[TIPS] Press finger firmly and keep it still");
        
        StaticJsonDocument<256> response;
        response["status"] = "capture_failed";
        response["message"] = "Image quality too low. Press finger firmly on sensor.";
        response["template_id"] = enrollmentTemplateID;
        response["slot"] = enrollID;
        response["quality"] = imageQuality;
        response["step"] = 1;
        String jsonStr;
        serializeJson(response, jsonStr);
        client.publish(topic_enroll_response, jsonStr.c_str());
        client.loop();
        
        // Reset scan - go back to waiting for scan 1
        Serial.println("[DEBUG] Quality rejected - resetting scan 1...");
        enrollmentStep = 0;
        noFingerCount = 0;
        waitingMessageShown[0] = false;
        return;
      }
      
      Serial.println("[✓] Quality PASSED - proceeding with enrollment (allowing re-registration)...");
      // NOTE: We do NOT check for duplicates here because students may re-register their fingerprint
      // The slot number uniquely identifies the student, so we allow overwriting
      
      // SCAN 1/3 is valid, publishing progress...
      
      // First scan OK - good quality
      Serial.println("\n========================================");
      Serial.println("[✓] SCAN 1/3 CAPTURED");
      Serial.println("========================================\n");
      
      StaticJsonDocument<256> response;
      response["status"] = "progress";
      response["step"] = 1;
      response["message"] = "Scan 1/3 captured - place finger again";
      response["template_id"] = enrollmentTemplateID;
      response["slot"] = enrollID;
      response["success"] = true;  // CRITICAL: Mark as successful scan
      String jsonStr;
      serializeJson(response, jsonStr);
      Serial.println("[MQTT PUBLISH] Sending scan 1/3 progress to frontend...");
      Serial.println("[MQTT PAYLOAD] " + jsonStr);
      client.publish(topic_enroll_response, jsonStr.c_str());
      client.loop();  // Process MQTT immediately after publish
      Serial.println("[MQTT] ✓ Scan 1/3 progress published");
      
      // Advance to step 1 - no waiting, just proceed
      stepStartTime = millis();
      enrollmentStep = 1;
      noFingerCount = 0;
      waitingMessageShown[1] = false;  // Reset for next step
      requireFingerRelease = true;
      removeMessageShown = false;
      lastWaitingReminder = 0;
      Serial.println("[STEP 1→2] Proceeding to next scan...\n");
      return;
    } else if (p == FINGERPRINT_NOFINGER) {
      // No finger detected - only print waiting message once
      noFingerCount++;
      if (!waitingMessageShown[0]) {
        Serial.println("\n========================================");
        Serial.println("[SCAN 1/3] Waiting for finger...");
        Serial.println("[SENSOR] Press your finger firmly on the sensor");
        Serial.println("========================================\n");
        waitingMessageShown[0] = true;
        
        StaticJsonDocument<256> response;
        response["status"] = "waiting";
        response["message"] = "Waiting for finger on sensor...";
        response["template_id"] = enrollmentTemplateID;
        response["slot"] = enrollID;
        String jsonStr;
        serializeJson(response, jsonStr);
        client.publish(topic_enroll_response, jsonStr.c_str());
        client.loop();  // Process MQTT immediately
      }
      
      // Timeout after 30 seconds of waiting
      if (noFingerCount > 60) {
        StaticJsonDocument<128> response;
        response["status"] = "error";
        response["message"] = "No finger detected. Enrollment timeout.";
        String jsonStr;
        serializeJson(response, jsonStr);
        client.publish(topic_enroll_response, jsonStr.c_str());
        client.loop();  // Process MQTT immediately
        
        Serial.println("\n========================================");
        Serial.println("[ERROR] Timeout waiting for finger");
        Serial.println("========================================\n");
        
        enrollmentInProgress = false;
        enrollmentStep = 0;
        noFingerCount = 0;
        waitingMessageShown[0] = false;
      }
    } else {
      // Communication or other error - enhanced diagnostics
      noFingerCount++;
      
      // Only print error message occasionally to avoid spam
      if (noFingerCount % 10 == 1) {  // Every 10 attempts = every 2 seconds with 200ms polling
        Serial.println("\n========================================");
        Serial.print("[❌ ERROR] Sensor communication error: ");
        Serial.println(p);
        
        switch(p) {
          case 1:
            Serial.println("[DIAGNOSIS] Error 1: Communication error with R307 sensor");
            Serial.println("[POSSIBLE CAUSES] ");
            Serial.println("  - UART connection loose");
            Serial.println("  - Incorrect baud rate (should be 57600)");
            Serial.println("  - Sensor power issue");
            Serial.println("  - Corrupted sensor firmware");
            Serial.println("[ATTEMPTING RECOVERY] Reinitializing sensor...");
            finger.begin(57600);  // Reinitialize sensor
            delay(100);
            Serial.println("[RECOVERY] Sensor reinitialized - waiting for finger...");
            break;
          case 2:
            Serial.println("[DIAGNOSIS] Error 2: No finger detected");
            Serial.println("[ACTION] Please place finger on sensor");
            break;
          case 0xFE:
            Serial.println("[DIAGNOSIS] Error 0xFE: Image read error");
            Serial.println("[ACTION] Clean sensor and try again");
            break;
          case 0xFF:
            Serial.println("[DIAGNOSIS] Error 0xFF: Unknown error or sensor timeout");
            Serial.println("[ACTION] Waiting for sensor response...");
            break;
          default:
            Serial.print("[DIAGNOSIS] Unknown error code: 0x");
            Serial.println(p, HEX);
        }
        Serial.println("========================================\n");
      }
      
      // Timeout after 30 seconds of waiting
      if (noFingerCount > 150) {  // Increased timeout to 30 seconds (150 × 200ms)
        Serial.println("\n========================================");
        Serial.println("❌ ENROLLMENT FAILED - TIMEOUT");
        Serial.println("No valid fingerprint detected within 30 seconds");
        Serial.println("========================================\n");
        
        StaticJsonDocument<128> response;
        response["status"] = "error";
        response["message"] = "Timeout: No fingerprint detected within 30 seconds";
        String jsonStr;
        serializeJson(response, jsonStr);
        client.publish(topic_enroll_response, jsonStr.c_str());
        client.loop();
        
        enrollmentInProgress = false;
        enrollmentStep = 0;
        noFingerCount = 0;
        waitingMessageShown[0] = false;
      }
    }
  }
  else if (enrollmentStep == 1) {
    // Step 2: Get second scan
    if (!waitingMessageShown[1]) {
      Serial.println("\n========================================");
      Serial.println("[SCAN 2/3] PLACE FINGER ON SENSOR");
      Serial.println("========================================");
      Serial.println("[ENROLLMENT] ⏳ Waiting for finger placement (Scan 2/3)...");
      waitingMessageShown[1] = true;
    }
    
    // Simply wait 2 seconds after first scan before accepting second scan
    // No need to wait for acknowledgment - just proceed automatically
    if (millis() - stepStartTime < 2000) {
      return;  // Still waiting for 2-second delay
    }
    
    int p = finger.getImage();
    if (p == FINGERPRINT_OK) {
      Serial.println("\n========================================");
      Serial.println("[✓✓✓] FINGER DETECTED! [✓✓✓]");
      Serial.println("========================================\n");
      noFingerCount = 0;
      
      // Convert image to template to assess quality
      int conv = finger.image2Tz(1);
      
      // Estimate quality based on conversion result
      uint16_t imageQuality = 80;  // Default good quality
      if (conv == FINGERPRINT_IMAGEMESS) {
        imageQuality = 45;
        Serial.println("[QUALITY] Image quality: LOW (messy/unclear)");
      } else if (conv == FINGERPRINT_FEATUREFAIL) {
        imageQuality = 60;
        Serial.println("[QUALITY] Image quality: MEDIUM (insufficient features)");
      } else if (conv == FINGERPRINT_OK) {
        imageQuality = 95;
        Serial.println("[QUALITY] Image quality: HIGH (clear)");
      } else {
        Serial.print("[ERROR] Image conversion failed with code: ");
        Serial.println(conv);
        imageQuality = 0;
      }
      
      Serial.print("[QUALITY SCORE] ");
      Serial.println(imageQuality);
      
      // Check if quality is acceptable
      Serial.println("[VALIDATION] Checking quality threshold...");
      if (imageQuality < 50) {
        Serial.println("[❌] Image quality too low - please try again with a clearer contact");
        Serial.println("[TIPS] Press finger firmly and keep it still");
        
        StaticJsonDocument<256> response;
        response["status"] = "capture_failed";
        response["message"] = "Image quality too low. Press finger firmly on sensor.";
        response["template_id"] = enrollmentTemplateID;
        response["slot"] = enrollID;
        response["quality"] = imageQuality;
        response["step"] = 2;
        String jsonStr;
        serializeJson(response, jsonStr);
        client.publish(topic_enroll_response, jsonStr.c_str());
        client.loop();
        
        // Reset scan 2 - go back to waiting for scan 2
        Serial.println("[DEBUG] Quality rejected - resetting scan 2...");
        enrollmentStep = 1;
        noFingerCount = 0;
        waitingMessageShown[1] = false;
        return;
      }
      
      Serial.println("[✓] Quality PASSED - proceeding with enrollment...");
      
      // Quality passed - proceed with scan 2
      
      // Second scan OK
      Serial.println("\n========================================");
      Serial.println("[✓] SCAN 2/3 CAPTURED");
      Serial.println("========================================\n");
      StaticJsonDocument<256> response;
      response["status"] = "progress";
      response["step"] = 2;
      response["message"] = "Scan 2/3 captured - place finger once more";
      response["template_id"] = enrollmentTemplateID;
      response["slot"] = enrollID;
      response["success"] = true;  // CRITICAL: Mark as successful scan
      String jsonStr;
      serializeJson(response, jsonStr);
      Serial.println("[MQTT PUBLISH] Sending scan 2/3 progress to frontend...");
      Serial.println("[MQTT PAYLOAD] " + jsonStr);
      client.publish(topic_enroll_response, jsonStr.c_str());
      client.loop();  // Process MQTT immediately after publish
      Serial.println("[MQTT] ✓ Scan 2/3 progress published");
      
      // Advance to step 2 - no waiting, just proceed
      stepStartTime = millis();
      enrollmentStep = 2;
      noFingerCount = 0;
      waitingMessageShown[2] = false;  // Reset for next step
      requireFingerRelease = true;
      removeMessageShown = false;
      lastWaitingReminder = 0;
      Serial.println("[STEP 2→3] Proceeding to next scan...\n");
      return;
    } else if (p == FINGERPRINT_NOFINGER) {
      noFingerCount++;
      if (!waitingMessageShown[1]) {
        Serial.println("\n========================================");
        Serial.println("[SCAN 2/3] Waiting for finger...");
        Serial.println("[SENSOR] Press your finger firmly on the sensor");
        Serial.println("========================================\n");
        waitingMessageShown[1] = true;
        
        StaticJsonDocument<256> response;
        response["status"] = "waiting";
        response["message"] = "Waiting for finger (scan 2)...";
        response["template_id"] = enrollmentTemplateID;
        response["slot"] = enrollID;
        String jsonStr;
        serializeJson(response, jsonStr);
        client.publish(topic_enroll_response, jsonStr.c_str());
        client.loop();  // Process MQTT immediately
      }
      
      // Timeout after 30 seconds
      if (noFingerCount > 150) {
        Serial.println("\n========================================");
        Serial.println("❌ ENROLLMENT FAILED - TIMEOUT (SCAN 2)");
        Serial.println("No valid fingerprint detected within 30 seconds");
        Serial.println("========================================\n");
        
        StaticJsonDocument<128> response;
        response["status"] = "error";
        response["message"] = "Timeout during scan 2";
        String jsonStr;
        serializeJson(response, jsonStr);
        client.publish(topic_enroll_response, jsonStr.c_str());
        client.loop();
        
        enrollmentInProgress = false;
        enrollmentStep = 0;
        noFingerCount = 0;
        waitingMessageShown[1] = false;
      }
    } else {
      // Communication or other error - enhanced diagnostics
      noFingerCount++;
      
      // Only print error message occasionally to avoid spam
      if (noFingerCount % 10 == 1) {  // Every 10 attempts = every 2 seconds with 200ms polling
        Serial.println("\n========================================");
        Serial.print("[❌ ERROR] Sensor communication error (Scan 2): ");
        Serial.println(p);
        Serial.println("[ATTEMPTING RECOVERY] Reinitializing sensor...");
        finger.begin(57600);  // Reinitialize sensor
        delay(100);
        Serial.println("[RECOVERY] Sensor reinitialized - waiting for finger...");
        Serial.println("========================================\n");
      }
      
      // Timeout after 30 seconds of waiting
      if (noFingerCount > 150) {  // Increased timeout to 30 seconds (150 × 200ms)
        Serial.println("\n========================================");
        Serial.println("❌ ENROLLMENT FAILED - TIMEOUT (SCAN 2)");
        Serial.println("No valid fingerprint detected within 30 seconds");
        Serial.println("========================================\n");
        
        StaticJsonDocument<128> response;
        response["status"] = "error";
        response["message"] = "Timeout during scan 2";
        String jsonStr;
        serializeJson(response, jsonStr);
        client.publish(topic_enroll_response, jsonStr.c_str());
        client.loop();
        
        enrollmentInProgress = false;
        enrollmentStep = 0;
        noFingerCount = 0;
        waitingMessageShown[1] = false;
      }
    }
  }
  else if (enrollmentStep == 2) {
    // Step 3: Get third scan and model creation
    if (!waitingMessageShown[2]) {
      Serial.println("\n========================================");
      Serial.println("[SCAN 3/3] PLACE FINGER ON SENSOR");
      Serial.println("========================================");
      Serial.println("[ENROLLMENT] ⏳ Waiting for finger placement (Scan 3/3)...");
      waitingMessageShown[2] = true;
    }
    
    // Simply wait 2 seconds after second scan before accepting third scan
    // No need to wait for acknowledgment - just proceed automatically
    if (millis() - stepStartTime < 2000) {
      return;  // Still waiting for 2-second delay
    }
    
    int p = finger.getImage();
    if (p == FINGERPRINT_OK) {
      Serial.println("\n========================================");
      Serial.println("[✓✓✓] FINGER DETECTED! [✓✓✓]");
      Serial.println("========================================\n");
      noFingerCount = 0;
      
      // Convert image to template to assess quality
      int conv = finger.image2Tz(2);  // Store in buffer 2
      
      // Estimate quality based on conversion result
      uint16_t imageQuality = 80;  // Default good quality
      if (conv == FINGERPRINT_IMAGEMESS) {
        imageQuality = 45;
        Serial.println("[QUALITY] Image quality: LOW (messy/unclear)");
      } else if (conv == FINGERPRINT_FEATUREFAIL) {
        imageQuality = 60;
        Serial.println("[QUALITY] Image quality: MEDIUM (insufficient features)");
      } else if (conv == FINGERPRINT_OK) {
        imageQuality = 95;
        Serial.println("[QUALITY] Image quality: HIGH (clear)");
      } else {
        Serial.print("[ERROR] Image conversion failed with code: ");
        Serial.println(conv);
        imageQuality = 0;
      }
      
      Serial.print("[QUALITY SCORE] ");
      Serial.println(imageQuality);
      
      // Check if quality is acceptable
      Serial.println("[VALIDATION] Checking quality threshold...");
      if (imageQuality < 50) {
        Serial.println("[❌] Image quality too low - please try again with a clearer contact");
        Serial.println("[TIPS] Press finger firmly and keep it still");
        
        StaticJsonDocument<256> response;
        response["status"] = "capture_failed";
        response["message"] = "Image quality too low. Press finger firmly on sensor.";
        response["template_id"] = enrollmentTemplateID;
        response["slot"] = enrollID;
        response["quality"] = imageQuality;
        response["step"] = 3;
        String jsonStr;
        serializeJson(response, jsonStr);
        client.publish(topic_enroll_response, jsonStr.c_str());
        client.loop();
        
        // Reset scan 3 - go back to waiting for scan 3
        Serial.println("[DEBUG] Quality rejected - resetting scan 3...");
        enrollmentStep = 2;
        noFingerCount = 0;
        waitingMessageShown[2] = false;
        return;
      }

      Serial.println("[✓] Quality PASSED - finalizing enrollment...");
      
      Serial.println("\n========================================");
      Serial.println("[✓] SCAN 3/3 CAPTURED");
      Serial.println("========================================\n");
      
      // Send progress update for SCAN 3/3
      StaticJsonDocument<256> scan3_response;
      scan3_response["status"] = "progress";
      scan3_response["step"] = 3;
      scan3_response["message"] = "Scan 3/3 captured - all scans complete!";
      scan3_response["template_id"] = enrollmentTemplateID;
      scan3_response["slot"] = enrollID;
      scan3_response["success"] = true;
      String scan3_json;
      serializeJson(scan3_response, scan3_json);
      Serial.println("[MQTT PUBLISH] Sending scan 3/3 complete to frontend...");
      Serial.println("[MQTT PAYLOAD] " + scan3_json);
      client.publish(topic_enroll_response, scan3_json.c_str());
      client.loop();
      
      // IMPORTANT: Create the fingerprint model NOW (before asking the user to confirm).
      // This ensures mismatches are detected immediately and the user can retry right away.
      Serial.println("\n========================================");
      Serial.println("Creating fingerprint template...");
      Serial.println("========================================");

      int modelP = finger.createModel();
      if (modelP != FINGERPRINT_OK) {
        Serial.print("Model creation error code: ");
        Serial.println(modelP);
        Serial.println("Images don't match - enrollment failed");

        StaticJsonDocument<256> response;
        response["status"] = "error";
        response["message"] = "Fingerprint images don't match - please try again";
        response["error_code"] = modelP;
        response["template_id"] = enrollmentTemplateID;
        response["slot"] = enrollID;
        String jsonStr;
        serializeJson(response, jsonStr);
        client.publish(topic_enroll_response, jsonStr.c_str());
        client.loop();

        // Reset state for retry
        Serial.println("[ENROLLMENT] ✓ RESETTING STATE for retry...");
        enrollmentInProgress = false;
        enrollmentConfirmed = false;
        enrollmentCancelled = false;
        enrollmentStep = 0;
        enrollID = 0;
        enrollmentTemplateID = "";
        noFingerCount = 0;
        waitingMessageShown[0] = false;
        waitingMessageShown[1] = false;
        waitingMessageShown[2] = false;
        requireFingerRelease = false;
        removeMessageShown = false;
        lastWaitingReminder = 0;
        modelCreated = false;
        Serial.println("[ENROLLMENT] ✓ STATE RESET COMPLETE - Ready for retry\n");
        return;
      }

      modelCreated = true;

      // ALL 3 SCANS COMPLETE and model created - wait for user confirmation to STORE it.
      Serial.println("\n[ENROLLMENT] Waiting for user confirmation to save fingerprint model...");
      
      // Send "ready_for_confirmation" message to frontend
      StaticJsonDocument<256> confirmation_response;
      confirmation_response["status"] = "ready_for_confirmation";
      confirmation_response["step"] = 3;
      confirmation_response["message"] = "All scans captured! Click 'Confirm & Save' to finalize enrollment.";
      confirmation_response["template_id"] = enrollmentTemplateID;
      confirmation_response["slot"] = enrollID;
      String confirmation_json;
      serializeJson(confirmation_response, confirmation_json);
      Serial.println("[MQTT PUBLISH] Sending ready_for_confirmation to frontend...");
      Serial.println("[MQTT PAYLOAD] " + confirmation_json);
      client.publish(topic_enroll_response, confirmation_json.c_str());
      client.loop();
      Serial.println("[MQTT] ✓ Ready for confirmation message published and processed\n");
      
      // Move to step 3 - waiting for confirmation
      enrollmentStep = 3;
      noFingerCount = 0;
      return;  // Exit and wait for confirmation message from frontend
    } else if (p == FINGERPRINT_NOFINGER) {
      noFingerCount++;
      // Print a reminder every ~5 seconds so it doesn't look like it froze.
      if (millis() - lastWaitingReminder > 5000) {
        Serial.println("[ENROLLMENT] ⏳ Still waiting for finger (Scan 3/3)...");
        lastWaitingReminder = millis();
      }
      if (!waitingMessageShown[2]) {
        Serial.println("\n========================================");
        Serial.println("[SCAN 3/3] Waiting for finger...");
        Serial.println("[SENSOR] Press your finger firmly on the sensor");
        Serial.println("========================================\n");
        waitingMessageShown[2] = true;
        
        StaticJsonDocument<256> response;
        response["status"] = "waiting";
        response["message"] = "Waiting for finger (scan 3)...";
        response["template_id"] = enrollmentTemplateID;
        response["slot"] = enrollID;
        String jsonStr;
        serializeJson(response, jsonStr);
        client.publish(topic_enroll_response, jsonStr.c_str());
        client.loop();  // Process MQTT immediately
      }
      
      // Timeout after 30 seconds
      if (noFingerCount > 150) {
        Serial.println("\n========================================");
        Serial.println("❌ ENROLLMENT FAILED - TIMEOUT (SCAN 3)");
        Serial.println("No valid fingerprint detected within 30 seconds");
        Serial.println("========================================\n");
        
        StaticJsonDocument<128> response;
        response["status"] = "error";
        response["message"] = "Timeout during scan 3";
        String jsonStr;
        serializeJson(response, jsonStr);
        client.publish(topic_enroll_response, jsonStr.c_str());
        client.loop();
        
        enrollmentInProgress = false;
        enrollmentStep = 0;
        noFingerCount = 0;
        waitingMessageShown[2] = false;
        requireFingerRelease = false;
        removeMessageShown = false;
        lastWaitingReminder = 0;
      }
    } else {
      // Communication or other error - enhanced diagnostics
      noFingerCount++;
      
      // Only print error message occasionally to avoid spam
      if (noFingerCount % 10 == 1) {  // Every 10 attempts = every 2 seconds with 200ms polling
        Serial.println("\n========================================");
        Serial.print("[❌ ERROR] Sensor communication error (Scan 3): ");
        Serial.println(p);
        Serial.println("[ATTEMPTING RECOVERY] Reinitializing sensor...");
        finger.begin(57600);  // Reinitialize sensor
        delay(100);
        Serial.println("[RECOVERY] Sensor reinitialized - waiting for finger...");
        Serial.println("========================================\n");
      }
      
      // Timeout after 30 seconds of waiting
      if (noFingerCount > 150) {  // Increased timeout to 30 seconds (150 × 200ms)
        Serial.println("\n========================================");
        Serial.println("❌ ENROLLMENT FAILED - TIMEOUT (SCAN 3)");
        Serial.println("No valid fingerprint detected within 30 seconds");
        Serial.println("========================================\n");
        
        StaticJsonDocument<128> response;
        response["status"] = "error";
        response["message"] = "Timeout during scan 3";
        String jsonStr;
        serializeJson(response, jsonStr);
        client.publish(topic_enroll_response, jsonStr.c_str());
        client.loop();
        
        enrollmentInProgress = false;
        enrollmentStep = 0;
        noFingerCount = 0;
        waitingMessageShown[2] = false;
      }
    }
  }
  else if (enrollmentStep == 3) {
    // Step 3: Waiting for user confirmation to create and save model
    if (enrollmentConfirmed) {
      // User clicked "Confirm & Save" - store the already-created model
      if (!modelCreated) {
        StaticJsonDocument<256> response;
        response["status"] = "error";
        response["message"] = "Enrollment model not ready - please restart enrollment";
        response["template_id"] = enrollmentTemplateID;
        response["slot"] = enrollID;
        String jsonStr;
        serializeJson(response, jsonStr);
        client.publish(topic_enroll_response, jsonStr.c_str());
        client.loop();
        enrollmentInProgress = false;
        enrollmentConfirmed = false;
        enrollmentCancelled = false;
        enrollmentStep = 0;
        enrollID = 0;
        enrollmentTemplateID = "";
        noFingerCount = 0;
        waitingMessageShown[0] = false;
        waitingMessageShown[1] = false;
        waitingMessageShown[2] = false;
        requireFingerRelease = false;
        removeMessageShown = false;
        lastWaitingReminder = 0;
        modelCreated = false;
        return;
      }

      Serial.println("\n========================================");
      Serial.println("Saving fingerprint template...");
      Serial.println("========================================");

      Serial.print("Storing template to slot ");
      Serial.println(enrollID);

      int p3 = finger.storeModel(enrollID);
      if (p3 == FINGERPRINT_OK) {
          // Success!
          Serial.println("✓ Fingerprint enrolled successfully!");
          Serial.println("========================================\n");
          
          StaticJsonDocument<256> response;
          response["status"] = "success";
          response["slot"] = enrollID;
          response["template_id"] = enrollmentTemplateID;
          response["message"] = "Fingerprint enrolled successfully!";
          response["success"] = true;
          String jsonStr;
          serializeJson(response, jsonStr);
          client.publish(topic_enroll_response, jsonStr.c_str());
          client.loop();  // Process MQTT immediately
          
          // Enrollment complete - reset ALL state flags for next user
          Serial.println("[ENROLLMENT] ✓ RESETTING STATE for next enrollment...");
          enrollmentInProgress = false;
          enrollmentConfirmed = false;
          enrollmentCancelled = false;
          enrollmentStep = 0;
          enrollID = 0;
          enrollmentTemplateID = "";
          noFingerCount = 0;
          waitingMessageShown[0] = false;
          waitingMessageShown[1] = false;
          waitingMessageShown[2] = false;
          requireFingerRelease = false;
          removeMessageShown = false;
          lastWaitingReminder = 0;
          modelCreated = false;
          Serial.println("[ENROLLMENT] ✓ STATE RESET COMPLETE - Ready for next user\n");
      } else {
        // Storage error
        Serial.print("Storage error code: ");
        Serial.println(p3);
        
        StaticJsonDocument<256> response;
        response["status"] = "error";
        response["message"] = "Failed to store fingerprint (code: " + String(p3) + ")";
        response["error_code"] = p3;
        response["slot"] = enrollID;
        response["template_id"] = enrollmentTemplateID;
        String jsonStr;
        serializeJson(response, jsonStr);
        client.publish(topic_enroll_response, jsonStr.c_str());
        client.loop();
        
        // Reset state for retry
        Serial.println("[ENROLLMENT] ✓ RESETTING STATE for retry...");
        enrollmentInProgress = false;
        enrollmentConfirmed = false;
        enrollmentCancelled = false;
        enrollmentStep = 0;
        enrollID = 0;
        enrollmentTemplateID = "";
        noFingerCount = 0;
        waitingMessageShown[0] = false;
        waitingMessageShown[1] = false;
        waitingMessageShown[2] = false;
        requireFingerRelease = false;
        removeMessageShown = false;
        lastWaitingReminder = 0;
        modelCreated = false;
        Serial.println("[ENROLLMENT] ✓ STATE RESET COMPLETE - Ready for retry\n");
      }
    }
  }
  // If not confirmed yet, just stay in waiting state
}

// ==================== PUBLISH FINGERPRINT DETECTION ====================
void publishFingerprintDetection(int fingerprintID, int confidence) {
  StaticJsonDocument<256> doc;
  doc["fingerprint_id"] = fingerprintID;
  doc["confidence"] = confidence;
  doc["timestamp"] = millis();
  doc["mode"] = (detectionMode == 1) ? "registration" : "attendance";
  
  String jsonStr;
  serializeJson(doc, jsonStr);
  client.publish(topic_fingerprint_result, jsonStr.c_str());
  
  Serial.println("Fingerprint published: " + jsonStr);
}
