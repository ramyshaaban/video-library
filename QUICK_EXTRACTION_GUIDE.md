# Quick Token Extraction Guide

## ✅ Easiest Method: Add Temporary Component

### Step 1: Add TokenExtractor Component
The component is already created at:
`StayCurrentMD Mobile/staycurrent-mobile/src/components/TokenExtractor.tsx`

### Step 2: Import and Use in Any Screen
Add this to any screen (e.g., `src/screens/mobile/home/GlassHome.tsx`):

```typescript
import { TokenExtractor } from '../../components/TokenExtractor';

// In your component's return:
<TokenExtractor />
```

### Step 3: Run App and Check
1. Run: `npm start` or `expo start`
2. Navigate to the screen where you added the component
3. Check console/logs for the token
4. Copy the token

### Step 4: Save Token
```bash
cd ~/lab/designer/content_transcriptions
echo "YOUR_TOKEN_HERE" > user_token.txt
```

### Step 5: Remove Component
Remove `<TokenExtractor />` from your screen after extracting.

---

## Alternative: React Native Debugger

### Step 1: Install React Native Debugger
```bash
brew install --cask react-native-debugger
```

### Step 2: Enable Debugging
1. Open StayCurrentMD app
2. Shake device (or Cmd+D on iOS, Cmd+M on Android)
3. Select "Debug" or "Open Debugger"

### Step 3: Run in Console
Paste this in the React Native Debugger console:

```javascript
const AsyncStorage = require('@react-native-async-storage/async-storage').default;

(async () => {
  const token = await AsyncStorage.getItem('USER_TOKEN');
  console.log('TOKEN:', token);
  return token;
})();
```

### Step 4: Save Token
```bash
echo "YOUR_TOKEN_HERE" > ~/lab/designer/content_transcriptions/user_token.txt
```

---

## After Extracting Token

Once you have the token saved:

1. **Test it:**
   ```bash
   cd ~/lab/designer/content_transcriptions
   TOKEN=$(cat user_token.txt)
   curl -X POST https://api.staycurrentmd.com/graphql \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer $TOKEN" \
     -d '{
       "query": "query { getContent(input: {keyword: \"\", content_type_ids: [3], page: 1, page_size: 5}) { content { id content_title } } }"
     }'
   ```

2. **Fetch all videos:**
   ```bash
   source venv/bin/activate
   python3 fetch_all_video_metadata.py
   ```

---

## Troubleshooting

- **No token found**: Make sure you're logged into the app
- **Token expired**: Log in again to get a new token
- **Can't access console**: Use the TokenExtractor component method instead
