# Running App to Extract Token

## ✅ What I've Done

1. **Added TokenExtractor component** to the home screen
2. **Started the app** in the background (running `npm run web`)

## 📋 Next Steps

### Step 1: Check if App is Running

The app should be starting. Check for:
- Terminal output showing the web URL (usually `http://localhost:8081` or `http://localhost:19006`)
- Browser may auto-open, or manually navigate to the URL

### Step 2: Open the App in Browser

1. Look for the URL in the terminal output
2. Open it in your browser
3. Wait for the app to load

### Step 3: Log In

1. Log in to the StayCurrentMD app with your credentials
2. The TokenExtractor component will appear on the home screen

### Step 4: Extract Token

**Method A: Using TokenExtractor Component (Easiest)**
- The component will show on the home screen
- Check the browser console (F12 or Cmd+Option+I)
- Look for the token in console logs
- Copy the token

**Method B: Using Browser Console Script**
1. Open browser DevTools (F12 or Cmd+Option+I)
2. Go to Console tab
3. Paste and run the script from `extract_from_browser_console.js`
4. Copy the token from console output

**Method C: From Network Tab**
1. Open DevTools > Network tab
2. Navigate or make any API request in the app
3. Find a request to `api.staycurrentmd.com/graphql`
4. Check Request Headers > Authorization
5. Copy the Bearer token value

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

### Step 7: Fetch All Videos

Once token is verified:

```bash
source venv/bin/activate
python3 fetch_all_video_metadata.py
```

## 🔧 Troubleshooting

**App not starting?**
- Check if Node.js and npm are installed
- Run: `cd "/Users/ramyshaaban/lab/StayCurrentMD Mobile/staycurrent-mobile" && npm install`
- Then: `npm run web`

**No token found?**
- Make sure you're logged in
- Check browser console for errors
- Try the Network tab method

**Token expired?**
- Log out and log back in
- Extract token again

## 🧹 Cleanup

After extracting the token, remove the TokenExtractor component:

1. Edit: `StayCurrentMD Mobile/staycurrent-mobile/src/screens/mobile/home/GlassHome.tsx`
2. Remove: `import { TokenExtractor } from '../../components/TokenExtractor'`
3. Remove: `<TokenExtractor />` from the JSX

