# ✅ App is Running! - Final Instructions

## �� Status

✅ **App is running** (process ID: 90778)  
✅ **TokenExtractor component** added to home screen  
✅ **Ready to extract token**

## 📋 Step-by-Step Instructions

### Step 1: Find the Web URL

The app should be running on one of these URLs:
- `http://localhost:8081`
- `http://localhost:19006`
- `http://localhost:3000`

**Check the terminal where you ran `npm run web`** - it will show the exact URL.

### Step 2: Open in Browser

1. Open your browser
2. Navigate to the URL shown in terminal
3. Wait for the app to load

### Step 3: Log In

1. Log in to StayCurrentMD with your credentials
2. The TokenExtractor component will appear on the home screen

### Step 4: Extract Token

**Method 1: Browser Console (Easiest)**
1. Open DevTools (F12 or Cmd+Option+I)
2. Go to Console tab
3. Look for logs starting with "🔍 Extracting token..."
4. Find the token in the console output
5. Copy the full token

**Method 2: Network Tab**
1. Open DevTools > Network tab
2. Navigate or make any action in the app
3. Find a request to `api.staycurrentmd.com/graphql`
4. Click on it
5. Go to Headers tab
6. Find "Authorization: Bearer ..."
7. Copy the token (everything after "Bearer ")

**Method 3: Browser Console Script**
1. Open DevTools > Console
2. Paste and run the script from `extract_from_browser_console.js`
3. Copy the token from output

### Step 5: Save Token

```bash
cd ~/lab/designer/content_transcriptions
echo "YOUR_TOKEN_HERE" > user_token.txt
```

### Step 6: Test Token

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

If you see video data, the token works! ✅

### Step 7: Fetch All Videos

```bash
source venv/bin/activate
python3 fetch_all_video_metadata.py
```

## 🧹 Cleanup (After Extracting Token)

Remove the TokenExtractor component:

1. Edit: `StayCurrentMD Mobile/staycurrent-mobile/src/screens/mobile/home/GlassHome.tsx`
2. Remove this line: `import { TokenExtractor } from '../../components/TokenExtractor'`
3. Remove this line: `<TokenExtractor />`

## �� Troubleshooting

**Can't find the URL?**
- Check the terminal output
- Look for "Metro waiting on..." or "Web is waiting on..."
- Try: `http://localhost:8081` or `http://localhost:19006`

**App not loading?**
- Wait a bit longer (first load can take time)
- Check terminal for errors
- Try refreshing the browser

**No token in console?**
- Make sure you're logged in
- Check Network tab method instead
- Token might be in localStorage (check DevTools > Application > Local Storage)

**Token doesn't work?**
- Token might have expired - log out and log back in
- Make sure you copied the full token (it's long!)
