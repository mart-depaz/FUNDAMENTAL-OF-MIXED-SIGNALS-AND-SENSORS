// ESP32 Fingerprint Delete Endpoint
// Add this to the handleEnroll() or setup() routing section in main.cpp

void setup() {
  // ... existing WiFi setup code ...
  
  // Add this route for deleting fingerprints during re-registration
  server.on("/api/delete-fingerprint/", HTTP_POST, handleDeleteFingerprint);
}

void handleDeleteFingerprint() {
  """
  API endpoint to delete a fingerprint from the R307 sensor
  Called during re-registration to free up the old fingerprint slot
  
  Request JSON:
  {
      "fingerprint_id": <old_id>,
      "course_id": <course_id>
  }
  
  Response JSON:
  {
      "success": true,
      "message": "Fingerprint ID X deleted successfully",
      "freed_slot": <old_id>
  }
  """
  
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

  int fingerprint_id = doc["fingerprint_id"];
  int course_id = doc["course_id"];

  Serial.println();
  Serial.println("========================================");
  Serial.println("[!] DELETE FINGERPRINT REQUEST RECEIVED");
  Serial.print("Fingerprint ID to delete: ");
  Serial.println(fingerprint_id);
  Serial.print("Course ID: ");
  Serial.println(course_id);
  Serial.println("========================================");

  // Delete the fingerprint from the R307 sensor
  uint8_t p = finger.deleteModel(fingerprint_id);
  
  StaticJsonDocument<300> response;
  
  if (p == FINGERPRINT_OK) {
    Serial.println("[✓] Fingerprint deleted successfully from sensor");
    response["success"] = true;
    response["message"] = "Fingerprint ID " + String(fingerprint_id) + " deleted successfully";
    response["freed_slot"] = fingerprint_id;
    
    String json;
    serializeJson(response, json);
    server.sendHeader("Access-Control-Allow-Origin", "*");
    server.send(200, "application/json", json);
  } else {
    Serial.print("[ERROR] Failed to delete fingerprint. Error code: ");
    Serial.println(p);
    response["success"] = false;
    response["message"] = "Failed to delete fingerprint from sensor";
    response["error_code"] = p;
    
    String json;
    serializeJson(response, json);
    server.sendHeader("Access-Control-Allow-Origin", "*");
    server.send(500, "application/json", json);
  }
  
  Serial.println();
  Serial.println("========================================");
  Serial.println("[✓] SYSTEM READY - WAITING FOR NEXT USER");
  Serial.println("========================================");
  Serial.println();
}
