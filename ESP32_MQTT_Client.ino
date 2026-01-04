#include <Arduino.h>
#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <Adafruit_Fingerprint.h>
#include <HardwareSerial.h>

// ==================== MQTT BROKER SETTINGS ====================
// Using HiveMQ Free Broker (public, no authentication needed for POC)
const char* mqtt_server = "broker.hivemq.com";      // Free MQTT broker
const int mqtt_port = 1883;                         // Standard MQTT port
const char* mqtt_client_id = "esp32_biometric_01";  // Unique device ID

// ==================== WIFI SETTINGS ====================
const char* ssid = "DE PAZ";
const char* password = "Blake_2018";

// ==================== STATIC IP (OPTIONAL) ====================
IPAddress staticIP(192, 168, 1, 9);
IPAddress gateway(192, 168, 1, 1);
IPAddress subnet(255, 255, 255, 0);
IPAddress dns(8, 8, 8, 8);

// ==================== MQTT TOPICS ====================
// These topics allow communication from any device/network
const char* topic_enroll_request = "biometric/esp32/enroll/request";     // Receive enrollment requests
const char* topic_enroll_response = "biometric/esp32/enroll/response";   // Send enrollment status
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
void handleDetectionRequest(JsonDocument& doc);
void enrollFingerprint();
void publishFingerprintDetection(int fingerprintID, int confidence);

// ==================== SETUP ====================
void setup() {
  Serial.begin(115200);
  delay(1000);
  
  Serial.println("\n\n");
  Serial.println("========================================");
  Serial.println("ESP32 Biometric MQTT System - Starting");
  Serial.println("========================================");
  
  setup_wifi();
  setup_fingerprint();
  
  // Configure MQTT
  client.setServer(mqtt_server, mqtt_port);
  client.setCallback(callback);
  
  Serial.println("Setup complete!");
}

// ==================== MAIN LOOP ====================
void loop() {
  // Maintain WiFi connection
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi disconnected, reconnecting...");
    setup_wifi();
  }
  
  // Maintain MQTT connection
  if (!client.connected()) {
    reconnect();
  }
  client.loop();
  
  // Publish status periodically
  if (millis() - lastStatusPublish > STATUS_PUBLISH_INTERVAL) {
    publishStatus();
    lastStatusPublish = millis();
  }
  
  // Handle ongoing enrollment
  if (enrollmentInProgress && !enrollmentCancelled) {
    enrollFingerprint();
  }
  
  delay(100);
}

// ==================== WiFi SETUP ====================
void setup_wifi() {
  Serial.print("\nConnecting to WiFi: ");
  Serial.println(ssid);
  
  // Optional: Use static IP for faster connection
  WiFi.config(staticIP, gateway, subnet, dns);
  WiFi.begin(ssid, password);
  
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 20) {
    delay(500);
    Serial.print(".");
    attempts++;
  }
  
  Serial.println();
  if (WiFi.status() == WL_CONNECTED) {
    Serial.print("✓ WiFi Connected! IP: ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("✗ WiFi Connection Failed!");
  }
}

// ==================== FINGERPRINT SETUP ====================
void setup_fingerprint() {
  Serial.println("\n[DEBUG] Initializing fingerprint sensor R307...");
  fingerSerial.begin(57600, SERIAL_8N1, 16, 17);  // RX=GPIO16, TX=GPIO17
  delay(500);
  
  finger.begin(57600);
  delay(1500);
  
  if (finger.verifyPassword()) {
    Serial.println("✓ R307 Fingerprint Sensor Detected!");
    Serial.print("Sensor capacity: ");
    Serial.println(finger.capacity);
    Serial.print("Stored fingerprints: ");
    Serial.println(finger.templateCount);
  } else {
    Serial.println("✗ R307 NOT DETECTED! Check connections.");
  }
}

// ==================== MQTT RECONNECT ====================
void reconnect() {
  int reconnect_attempts = 0;
  while (!client.connected() && reconnect_attempts < 5) {
    Serial.print("Attempting MQTT connection...");
    
    if (client.connect(mqtt_client_id)) {
      Serial.println("✓ Connected to MQTT Broker!");
      
      // Subscribe to topics
      client.subscribe(topic_enroll_request);
      client.subscribe(topic_detect_request);
      client.subscribe(topic_command);
      
      Serial.println("Subscribed to topics:");
      Serial.println("  - " + String(topic_enroll_request));
      Serial.println("  - " + String(topic_detect_request));
      Serial.println("  - " + String(topic_command));
      
      // Publish online status
      client.publish(topic_status, "{\"status\":\"online\",\"timestamp\":0}");
    } else {
      Serial.print("✗ Failed, rc=");
      Serial.print(client.state());
      Serial.println(" retrying in 5 seconds...");
      delay(5000);
    }
    reconnect_attempts++;
  }
}

// ==================== MQTT CALLBACK ====================
void callback(char* topic, byte* payload, unsigned int length) {
  Serial.print("Message received on topic: ");
  Serial.println(topic);
  
  // Convert payload to string
  String message = "";
  for (int i = 0; i < length; i++) {
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
  } else if (strcmp(topic, topic_detect_request) == 0) {
    handleDetectionRequest(doc);
  } else if (strcmp(topic, topic_command) == 0) {
    handleCommand(doc);
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
    if (slot < 1 || slot > 127) {
      Serial.println("Invalid slot number!");
      // Publish error
      StaticJsonDocument<128> response;
      response["status"] = "error";
      response["message"] = "Invalid slot number (1-127)";
      String jsonStr;
      serializeJson(response, jsonStr);
      client.publish(topic_enroll_response, jsonStr.c_str());
      return;
    }
    
    enrollID = slot;
    enrollmentTemplateID = template_id;
    enrollmentInProgress = true;
    enrollmentCancelled = false;
    
    // Publish started
    StaticJsonDocument<128> response;
    response["status"] = "started";
    response["slot"] = enrollID;
    response["template_id"] = enrollmentTemplateID;
    String jsonStr;
    serializeJson(response, jsonStr);
    client.publish(topic_enroll_response, jsonStr.c_str());
    
    Serial.println("Enrollment started for slot " + String(enrollID));
  } 
  else if (action == "cancel") {
    enrollmentCancelled = true;
    enrollmentInProgress = false;
    
    // Publish cancelled
    StaticJsonDocument<128> response;
    response["status"] = "cancelled";
    response["slot"] = enrollID;
    String jsonStr;
    serializeJson(response, jsonStr);
    client.publish(topic_enroll_response, jsonStr.c_str());
    
    Serial.println("Enrollment cancelled!");
  }
}

// ==================== HANDLE DETECTION REQUEST ====================
void handleDetectionRequest(JsonDocument& doc) {
  String action = doc["action"] | "disable";
  String mode = doc["mode"] | "attendance";  // "attendance" or "registration"
  
  Serial.println("Detection Request:");
  Serial.print("  Action: ");
  Serial.println(action);
  Serial.print("  Mode: ");
  Serial.println(mode);
  
  if (action == "enable") {
    if (mode == "registration") {
      detectionMode = 1;
    } else if (mode == "attendance") {
      detectionMode = 2;
    }
    Serial.println("Detection enabled in mode: " + mode);
  } else if (action == "disable") {
    detectionMode = 0;
    Serial.println("Detection disabled");
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
  else if (cmd == "sensor_info") {
    StaticJsonDocument<256> response;
    response["command"] = "sensor_info";
    response["capacity"] = finger.capacity;
    response["stored"] = finger.templateCount;
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
  
  if (millis() - lastStep < 2000) {
    return;  // Wait 2 seconds between steps
  }
  lastStep = millis();
  
  if (!enrollmentInProgress) {
    enrollmentStep = 0;
    return;
  }
  
  if (enrollmentCancelled) {
    enrollmentStep = 0;
    return;
  }
  
  Serial.print("Enrollment step: ");
  Serial.println(enrollmentStep + 1);
  
  if (enrollmentStep == 0) {
    // Step 1: Get first scan
    int p = finger.imageProcess();
    if (p == FINGERPRINT_OK) {
      p = finger.fingerFastSearch();
      if (p == FINGERPRINT_OK) {
        // Duplicate found
        StaticJsonDocument<128> response;
        response["status"] = "error";
        response["message"] = "Fingerprint already exists!";
        String jsonStr;
        serializeJson(response, jsonStr);
        client.publish(topic_enroll_response, jsonStr.c_str());
        
        enrollmentInProgress = false;
        enrollmentStep = 0;
        return;
      }
      
      // First scan OK
      StaticJsonDocument<128> response;
      response["status"] = "progress";
      response["step"] = 1;
      response["message"] = "First scan successful, place finger again";
      String jsonStr;
      serializeJson(response, jsonStr);
      client.publish(topic_enroll_response, jsonStr.c_str());
      
      enrollmentStep = 1;
    } else {
      // No finger detected
      StaticJsonDocument<128> response;
      response["status"] = "waiting";
      response["message"] = "Waiting for finger...";
      String jsonStr;
      serializeJson(response, jsonStr);
      client.publish(topic_enroll_response, jsonStr.c_str());
    }
  }
  else if (enrollmentStep == 1) {
    // Step 2: Get second scan
    int p = finger.imageProcess();
    if (p == FINGERPRINT_OK) {
      int p2 = finger.fingerFastSearch();
      if (p2 == FINGERPRINT_OK) {
        // Duplicate found
        StaticJsonDocument<128> response;
        response["status"] = "error";
        response["message"] = "Fingerprint already exists!";
        String jsonStr;
        serializeJson(response, jsonStr);
        client.publish(topic_enroll_response, jsonStr.c_str());
        
        enrollmentInProgress = false;
        enrollmentStep = 0;
        return;
      }
      
      // Second scan OK
      StaticJsonDocument<128> response;
      response["status"] = "progress";
      response["step"] = 2;
      response["message"] = "Second scan successful, place finger once more";
      String jsonStr;
      serializeJson(response, jsonStr);
      client.publish(topic_enroll_response, jsonStr.c_str());
      
      enrollmentStep = 2;
    } else {
      // No finger detected
      StaticJsonDocument<128> response;
      response["status"] = "waiting";
      response["message"] = "Waiting for finger (scan 2)...";
      String jsonStr;
      serializeJson(response, jsonStr);
      client.publish(topic_enroll_response, jsonStr.c_str());
    }
  }
  else if (enrollmentStep == 2) {
    // Step 3: Get third scan and create template
    int p = finger.imageProcess();
    if (p == FINGERPRINT_OK) {
      int p2 = finger.fingerFastSearch();
      if (p2 == FINGERPRINT_OK) {
        // Duplicate found
        StaticJsonDocument<128> response;
        response["status"] = "error";
        response["message"] = "Fingerprint already exists!";
        String jsonStr;
        serializeJson(response, jsonStr);
        client.publish(topic_enroll_response, jsonStr.c_str());
        
        enrollmentInProgress = false;
        enrollmentStep = 0;
        return;
      }
      
      // All scans OK, create template
      int p3 = finger.createModel();
      if (p3 == FINGERPRINT_OK) {
        // Store template
        p3 = finger.storeModel(enrollID);
        if (p3 == FINGERPRINT_OK) {
          // Success!
          StaticJsonDocument<256> response;
          response["status"] = "success";
          response["slot"] = enrollID;
          response["template_id"] = enrollmentTemplateID;
          response["message"] = "Fingerprint enrolled successfully!";
          String jsonStr;
          serializeJson(response, jsonStr);
          client.publish(topic_enroll_response, jsonStr.c_str());
          
          Serial.println("✓ Fingerprint enrolled successfully!");
          enrollmentInProgress = false;
          enrollmentStep = 0;
        } else {
          // Storage error
          StaticJsonDocument<128> response;
          response["status"] = "error";
          response["message"] = "Failed to store fingerprint";
          String jsonStr;
          serializeJson(response, jsonStr);
          client.publish(topic_enroll_response, jsonStr.c_str());
          
          enrollmentInProgress = false;
          enrollmentStep = 0;
        }
      }
    } else {
      // No finger detected
      StaticJsonDocument<128> response;
      response["status"] = "waiting";
      response["message"] = "Waiting for finger (scan 3)...";
      String jsonStr;
      serializeJson(response, jsonStr);
      client.publish(topic_enroll_response, jsonStr.c_str());
    }
  }
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
