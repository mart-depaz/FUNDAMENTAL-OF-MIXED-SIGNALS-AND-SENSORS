#!/usr/bin/env python3
"""
Test script to simulate ESP32 sending enrollment scan updates via MQTT
"""

import paho.mqtt.client as mqtt
import json
import time
import uuid

# MQTT Settings (must match ESP32 and Django settings)
MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT = 1883
TOPIC_ENROLL_RESPONSE = "biometric/esp32/enroll/response"

# Test parameters
SLOT = 5
SESSION_ID = str(uuid.uuid4())  # Use a UUID to simulate what Django would send

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("[TEST] Connected to MQTT broker")
    else:
        print(f"[TEST] Failed to connect, return code {rc}")

def on_disconnect(client, userdata, rc):
    print(f"[TEST] Disconnected from MQTT broker")

def send_enrollment_scan(slot, session_id, step, message):
    """Send a single scan progress update"""
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        
        payload = {
            "status": "progress",
            "step": step,
            "slot": slot,
            "template_id": session_id,
            "message": message,
            "success": True
        }
        
        print(f"\n[TEST] Sending SCAN {step}/3:")
        print(f"[TEST] Payload: {json.dumps(payload, indent=2)}")
        
        client.publish(TOPIC_ENROLL_RESPONSE, json.dumps(payload))
        client.loop()
        time.sleep(0.5)  # Brief pause
        
    finally:
        client.disconnect()

def main():
    print("="*80)
    print("[TEST] ===== SIMULATING ESP32 ENROLLMENT SCANS =====")
    print("="*80)
    print(f"[TEST] MQTT Broker: {MQTT_BROKER}:{MQTT_PORT}")
    print(f"[TEST] Topic: {TOPIC_ENROLL_RESPONSE}")
    print(f"[TEST] Session ID: {SESSION_ID}")
    print(f"[TEST] Slot: {SLOT}")
    print("="*80)
    
    # Send 3 scans
    print("\n[TEST] Sending SCAN 1 of 3...")
    send_enrollment_scan(SLOT, SESSION_ID, 1, "Scan 1/3 captured - place finger again")
    
    print("\n[TEST] Waiting 3 seconds before SCAN 2...")
    time.sleep(3)
    
    print("\n[TEST] Sending SCAN 2 of 3...")
    send_enrollment_scan(SLOT, SESSION_ID, 2, "Scan 2/3 captured - place finger again")
    
    print("\n[TEST] Waiting 3 seconds before SCAN 3...")
    time.sleep(3)
    
    print("\n[TEST] Sending SCAN 3 of 3...")
    send_enrollment_scan(SLOT, SESSION_ID, 3, "Scan 3/3 captured - creating fingerprint model")
    
    print("\n" + "="*80)
    print("[TEST] ===== ENROLLMENT SCANS SENT =====")
    print("[TEST] Check Django console to see if messages were received")
    print("[TEST] Check browser F12 console to see if WebSocket received updates")
    print("="*80 + "\n")

if __name__ == "__main__":
    main()
