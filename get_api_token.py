#!/usr/bin/env python3
"""
Get API authentication token for StayCurrentMD
"""
import requests
import json

# API endpoint
API_URL = "https://api.staycurrentmd.com/graphql"

def generate_guest_token():
    """
    Generate a guest token using the GraphQL mutation
    This doesn't require authentication
    """
    mutation = """
    mutation GenerateGuestToken {
      generateGuestToken {
        success
        message
        guest_token
      }
    }
    """
    
    try:
        response = requests.post(
            API_URL,
            json={"query": mutation},
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get("data", {}).get("generateGuestToken", {}).get("success"):
                token = data["data"]["generateGuestToken"]["guest_token"]
                print(f"✅ Guest token generated successfully!")
                print(f"Token: {token[:50]}...")
                return token
            else:
                print(f"❌ Token generation failed: {data}")
                return None
        else:
            print(f"❌ HTTP Error: {response.status_code}")
            print(f"Response: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Error generating guest token: {e}")
        return None

def test_token(token):
    """
    Test if the token works by making a simple query
    """
    query = """
    query {
      getHubs {
        success
        message
      }
    }
    """
    
    try:
        response = requests.post(
            API_URL,
            json={"query": query},
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}"
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get("data", {}).get("getHubs", {}).get("success"):
                print("✅ Token is valid and working!")
                return True
            else:
                print(f"⚠️ Token may not be valid: {data}")
                return False
        else:
            print(f"❌ HTTP Error: {response.status_code}")
            print(f"Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error testing token: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("StayCurrentMD API Token Generator")
    print("=" * 60)
    print()
    
    print("Step 1: Generating guest token...")
    token = generate_guest_token()
    
    if token:
        print()
        print("Step 2: Testing token...")
        if test_token(token):
            print()
            print("=" * 60)
            print("✅ SUCCESS! Token is ready to use")
            print("=" * 60)
            print()
            print("Save this token to use in API queries:")
            print(f"Token: {token}")
            print()
            print("Usage example:")
            print(f'  Authorization: Bearer {token}')
            print()
            
            # Save token to file
            with open("api_token.txt", "w") as f:
                f.write(token)
            print("✅ Token saved to: api_token.txt")
        else:
            print()
            print("⚠️ Token generated but test failed. Token may still work for some queries.")
    else:
        print()
        print("❌ Failed to generate token. Check API endpoint and network connection.")

