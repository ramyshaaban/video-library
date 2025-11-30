# Extract Token from Mobile App

## Method 1: Using React Native Debugger (Recommended)

### Step 1: Install React Native Debugger
```bash
# Install React Native Debugger
brew install --cask react-native-debugger

# Or download from: https://github.com/jhen0409/react-native-debugger/releases
```

### Step 2: Enable Debugging
1. Open the StayCurrentMD app on your device/simulator
2. Shake device (or Cmd+D on iOS simulator, Cmd+M on Android)
3. Select "Debug" or "Open Debugger"
4. React Native Debugger should open

### Step 3: Run Extraction Script
In the React Native Debugger console, paste and run:

```javascript
import AsyncStorage from '@react-native-async-storage/async-storage';

async function extractToken() {
  try {
    // Get USER_TOKEN
    const token = await AsyncStorage.getItem('USER_TOKEN');
    console.log('USER_TOKEN:', token);
    
    // Get all keys to see what's available
    const allKeys = await AsyncStorage.getAllKeys();
    console.log('All keys:', allKeys);
    
    // Get all token-related items
    const tokenKeys = allKeys.filter(k => k.includes('TOKEN'));
    const tokenItems = await AsyncStorage.multiGet(tokenKeys);
    console.log('Token items:', tokenItems);
    
    return token;
  } catch (error) {
    console.error('Error:', error);
  }
}

extractToken();
```

### Step 4: Save Token
Copy the token and save it:
```bash
echo "YOUR_TOKEN_HERE" > ~/lab/designer/content_transcriptions/user_token.txt
```

---

## Method 2: Add Temporary Code to App

### Step 1: Add to App Component
Temporarily add this to your app (e.g., in `App.tsx` or a screen):

```typescript
import { useEffect } from 'react';
import { getAsyncData } from './src/utils/storage';
import { keys } from './src/utils/keys';

useEffect(() => {
  const extractToken = async () => {
    try {
      const token = await getAsyncData(keys.userToken);
      console.log('🔑 USER TOKEN:', token);
      console.log('📋 Copy this token and save it to: user_token.txt');
      
      // Also log to alert for easy copying
      if (token) {
        alert(`Token: ${token.substring(0, 50)}...`);
      }
    } catch (error) {
      console.error('Error:', error);
    }
  };
  
  extractToken();
}, []);
```

### Step 2: Run App and Check Console
1. Run the app: `npm start` or `expo start`
2. Check the console/logs for the token
3. Copy the token

### Step 3: Save Token
```bash
echo "YOUR_TOKEN_HERE" > ~/lab/designer/content_transcriptions/user_token.txt
```

---

## Method 3: Using Expo Dev Tools

### Step 1: Open Expo Dev Tools
1. Run: `expo start`
2. Press `m` to open menu
3. Select "Debug Remote JS"

### Step 2: Open Browser Console
1. Open Chrome DevTools (or your browser's console)
2. The app's console logs will appear here

### Step 3: Run Extraction
In the browser console:
```javascript
// Access AsyncStorage through the app's context
// Or use the temporary code method above
```

---

## Method 4: Direct File Access (iOS Simulator)

### For iOS Simulator:
```bash
# Find the app's data directory
xcrun simctl get_app_container booted com.globalcast.staycurrentmd data

# Or check:
~/Library/Developer/CoreSimulator/Devices/[DEVICE_ID]/data/Containers/Data/Application/[APP_ID]/Library/Application Support/

# Look for AsyncStorage files (usually SQLite database)
```

### For Android Emulator:
```bash
# Use adb to access app data
adb shell
run-as com.globalcast.staycurrentmd
cd /data/data/com.globalcast.staycurrentmd/databases/
# Look for AsyncStorage database files
```

---

## Method 5: Using Flipper (If Installed)

1. Install Flipper: https://fbflipper.com/
2. Open Flipper
3. Connect to your app
4. Use AsyncStorage plugin to view all stored data
5. Find `USER_TOKEN` key
6. Copy the value

---

## Quick Test Script

Create a temporary screen or add to existing screen:

```typescript
// In any screen component
import { getAsyncData } from '../utils/storage';
import { keys } from '../utils/keys';

const TestTokenExtraction = () => {
  useEffect(() => {
    const getToken = async () => {
      const token = await getAsyncData(keys.userToken);
      console.log('=== TOKEN EXTRACTION ===');
      console.log('Token:', token);
      console.log('Token length:', token?.length);
      console.log('Token preview:', token?.substring(0, 50) + '...');
      console.log('======================');
    };
    getToken();
  }, []);
  
  return null; // Or return a button to trigger
};
```

---

## After Extracting Token

Once you have the token:

1. **Save it:**
   ```bash
   cd ~/lab/designer/content_transcriptions
   echo "YOUR_TOKEN_HERE" > user_token.txt
   ```

2. **Test it:**
   ```bash
   TOKEN=$(cat user_token.txt)
   curl -X POST https://api.staycurrentmd.com/graphql \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer $TOKEN" \
     -d '{
       "query": "query { getContent(input: {keyword: \"\", content_type_ids: [3], page: 1, page_size: 5}) { content { id content_title } } }"
     }'
   ```

3. **Use it to fetch videos:**
   ```bash
   source venv/bin/activate
   python3 fetch_all_video_metadata.py
   ```

---

## Troubleshooting

- **No token found**: Make sure you're logged in to the app
- **Token expired**: You may need to log in again
- **Can't access AsyncStorage**: Use React Native Debugger or add temporary code

