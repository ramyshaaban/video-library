#!/bin/bash
# Get API authentication token for StayCurrentMD

API_URL="https://api.staycurrentmd.com/graphql"

echo "============================================================"
echo "StayCurrentMD API Token Generator"
echo "============================================================"
echo ""

echo "Step 1: Generating guest token..."
echo ""

# Generate guest token
RESPONSE=$(curl -s -X POST "$API_URL" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "mutation GenerateGuestToken { generateGuestToken { success message guest_token } }"
  }')

echo "Response:"
echo "$RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE"
echo ""

# Extract token using Python
TOKEN=$(echo "$RESPONSE" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    if data.get('data', {}).get('generateGuestToken', {}).get('success'):
        token = data['data']['generateGuestToken']['guest_token']
        print(token)
    else:
        print('ERROR')
        sys.exit(1)
except:
    print('ERROR')
    sys.exit(1)
")

if [ "$TOKEN" != "ERROR" ] && [ -n "$TOKEN" ]; then
    echo "✅ Guest token generated successfully!"
    echo ""
    echo "Token (first 50 chars): ${TOKEN:0:50}..."
    echo ""
    
    echo "Step 2: Testing token..."
    TEST_RESPONSE=$(curl -s -X POST "$API_URL" \
      -H "Content-Type: application/json" \
      -H "Authorization: Bearer $TOKEN" \
      -d '{
        "query": "query { getHubs { success message } }"
      }')
    
    TEST_SUCCESS=$(echo "$TEST_RESPONSE" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    if data.get('data', {}).get('getHubs', {}).get('success'):
        print('SUCCESS')
    else:
        print('FAILED')
except:
    print('FAILED')
")
    
    if [ "$TEST_SUCCESS" = "SUCCESS" ]; then
        echo "✅ Token is valid and working!"
        echo ""
        echo "============================================================"
        echo "✅ SUCCESS! Token is ready to use"
        echo "============================================================"
        echo ""
        echo "Token saved to: api_token.txt"
        echo "$TOKEN" > api_token.txt
        echo ""
        echo "You can now use this token to query the API."
        echo "Example:"
        echo "  Authorization: Bearer $TOKEN"
    else
        echo "⚠️ Token generated but test query failed."
        echo "Token may still work for some queries."
        echo "$TOKEN" > api_token.txt
        echo "Token saved to: api_token.txt"
    fi
else
    echo "❌ Failed to generate token."
    echo "Please check:"
    echo "  1. Network connection"
    echo "  2. API endpoint is accessible"
    echo "  3. API allows guest token generation"
fi

