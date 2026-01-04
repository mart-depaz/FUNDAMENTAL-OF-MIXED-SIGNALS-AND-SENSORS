#!/bin/bash
# Quick Setup Script for MQTT Biometric System
# Run this to install dependencies and configure the system

echo "=================================="
echo "MQTT Biometric System Setup"
echo "=================================="
echo ""

# Check Python version
echo "✓ Checking Python version..."
python --version

# Install Python dependencies
echo ""
echo "✓ Installing Python dependencies..."
pip install paho-mqtt requests

# Create MQTT management command directory
echo ""
echo "✓ Setting up Django management commands..."

# Check if management directory exists
if [ ! -d "accounts/management/commands" ]; then
    mkdir -p accounts/management/commands
    touch accounts/management/__init__.py
    touch accounts/management/commands/__init__.py
fi

# Copy mqtt_bridge to management commands
echo "Moving mqtt_bridge to management commands..."
if [ -f "mqtt_bridge.py" ]; then
    cp mqtt_bridge.py accounts/management/commands/mqtt_bridge.py
    echo "✓ mqtt_bridge.py copied to accounts/management/commands/"
else
    echo "⚠ mqtt_bridge.py not found in root directory"
fi

# Create static files directory if needed
echo ""
echo "✓ Creating directories..."
mkdir -p templates
mkdir -p static/js
mkdir -p static/css

echo ""
echo "=================================="
echo "Setup Complete!"
echo "=================================="
echo ""
echo "Next steps:"
echo "1. Update your Django settings.py to include API URLs"
echo "2. Run: python manage.py migrate"
echo "3. Start MQTT bridge: python manage.py mqtt_bridge"
echo "4. In another terminal: python manage.py runserver"
echo "5. Students can now enroll from any network!"
echo ""
echo "Test the API:"
echo "curl -X POST http://localhost:8000/api/student/enroll/start/ \\"
echo "  -H 'Content-Type: application/json' \\"
echo "  -d '{\"student_id\": \"TEST001\"}'"
echo ""
