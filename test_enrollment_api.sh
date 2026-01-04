#!/bin/bash
# Test script to verify biometric enrollment API flow

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

DJANGO_URL="http://192.168.1.6:8000"
ENROLLMENT_ID=""

echo -e "${YELLOW}=== Biometric Enrollment API Test ===${NC}\n"

# Test 1: Start Enrollment
echo -e "${YELLOW}Test 1: Starting Enrollment${NC}"
RESPONSE=$(curl -s -X POST "$DJANGO_URL/api/start-enrollment/" \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: test" \
  -d '{"course_id": "1"}')

echo "Response: $RESPONSE"
ENROLLMENT_ID=$(echo $RESPONSE | grep -o '"enrollment_id":"[^"]*' | cut -d'"' -f4)
echo -e "Enrollment ID: ${GREEN}$ENROLLMENT_ID${NC}\n"

if [ -z "$ENROLLMENT_ID" ]; then
  echo -e "${RED}Failed to create enrollment${NC}"
  exit 1
fi

# Test 2: Get Initial Status
echo -e "${YELLOW}Test 2: Getting Initial Status${NC}"
curl -s -X GET "$DJANGO_URL/api/enrollment-status/$ENROLLMENT_ID/" | json_pp
echo ""

# Test 3: Simulate Scan Updates
echo -e "${YELLOW}Test 3: Simulating Scan Updates${NC}"

for SCAN in 1 2 3; do
  echo -e "\nSending scan update for scan $SCAN/3..."
  curl -s -X POST "$DJANGO_URL/dashboard/api/broadcast-scan-update/" \
    -H "Content-Type: application/json" \
    -d "{
      \"enrollment_id\": \"$ENROLLMENT_ID\",
      \"slot\": $SCAN,
      \"success\": false,
      \"quality_score\": $((SCAN * 30)),
      \"message\": \"Scan $SCAN/3 - Testing progress update\"
    }"
  
  echo ""
  
  # Get updated status
  echo "Status after scan $SCAN:"
  curl -s -X GET "$DJANGO_URL/api/enrollment-status/$ENROLLMENT_ID/" | json_pp
  echo ""
  
  sleep 1
done

echo -e "${GREEN}=== Test Complete ===${NC}"
