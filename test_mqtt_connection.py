#!/usr/bin/env python
"""Test MQTT connection to HiveMQ broker"""

import paho.mqtt.client as mqtt
import time
import socket

def on_connect(client, userdata, flags, rc):
    print(f"✓ Connected with code: {rc}")

def on_disconnect(client, userdata, rc):
    print(f"✗ Disconnected with code: {rc}")

# Test DNS resolution first
print("Testing DNS resolution for broker.hivemq.com...")
try:
    ip = socket.gethostbyname('broker.hivemq.com')
    print(f"✓ Resolved to IP: {ip}")
except Exception as e:
    print(f"✗ DNS resolution failed: {e}")
    exit(1)

# Test MQTT connection
print("\nAttempting MQTT connection to broker.hivemq.com:1883...")
try:
    client = mqtt.Client("test_django_mqtt", clean_session=False)
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    
    # Connect with 5 second timeout
    client.connect('broker.hivemq.com', 1883, keepalive=30)
    client.loop_start()
    
    # Wait for connection
    print("Waiting for connection (max 5 seconds)...")
    for i in range(50):
        time.sleep(0.1)
        if client._state == mqtt.mqtt_cs_connected:
            print("✓ Successfully connected!")
            client.loop_stop()
            exit(0)
    
    print("✗ Connection timeout after 5 seconds")
    client.loop_stop()
    exit(1)
    
except Exception as e:
    print(f"✗ Connection error: {e}")
    import traceback
    traceback.print_exc()
    exit(1)
