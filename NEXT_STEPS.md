# Next Steps: Getting Video Metadata

## ✅ What's Done

1. **psycopg2 installed** ✅
   - Virtual environment: `venv/`
   - All dependencies ready

2. **Database connection works** ✅
   - Can connect to databases
   - Script is ready

3. **Issue identified** ⚠️
   - The database URL found is for the **designer app**, not StayCurrentMD backend
   - StayCurrentMD backend is hosted separately (not in local repos)

## 🔍 What We Found

- **StayCurrentMD Mobile**: Frontend mobile app (React Native/Expo)
- **Backend API**: `https://api.staycurrentmd.com/graphql` (hosted separately)
- **Database**: Not in local repositories - hosted on server

## 🎯 Recommended Solution: Use API with User Authentication

Since the backend database is not accessible locally, use the GraphQL API:

### Step 1: Get User Authentication Token

**Option A: Login via API (Recommended)**

```bash
# 1. Request OTP
curl -X POST https://api.staycurrentmd.com/graphql \
  -H "Content-Type: application/json" \
  -d '{
    "query": "mutation RequestOtp($input: RequestOtpInput!) { requestOtp(input: $input) { success message } }",
    "variables": {
      "input": {
        "identifier": "your-email@example.com",
        "is_pass_login": false
      }
    }
  }'

# 2. Check your email for OTP code

# 3. Verify OTP and get token
curl -X POST https://api.staycurrentmd.com/graphql \
  -H "Content-Type: application/json" \
  -d '{
    "query": "mutation VerifyOtp($input: VerifyOtpInput!) { verifyOtp(input: $input) { success message token user_id } }",
    "variables": {
      "input": {
        "identifier": "your-email@example.com",
        "otp": "123456",
        "device_type": "web",
        "app_version": "1.0.0"
      }
    }
  }'

# 4. Save the token
echo "YOUR_TOKEN_HERE" > user_token.txt
```

**Option B: Extract from Mobile App**
- If you have the app installed and logged in
- Token is stored in AsyncStorage as `USER_TOKEN`
- Use React Native Debugger to extract it

### Step 2: Use Token to Fetch Videos

Once you have the token, I can update `fetch_all_video_metadata.py` to use it and fetch all video metadata from the API.

## 📋 Alternative: Get Backend Database Credentials

If you have access to the backend deployment:

1. **Check backend repository** (if you have it)
2. **Check deployment platform** (AWS, Heroku, etc.) for environment variables
3. **Ask backend team** for database credentials
4. **Check backend admin panel** for database connection info

Once you have the correct database URL, update `fetch_videos_from_database.py` and it will work.

## 🚀 What Happens Next

Once you provide either:
- **User authentication token** → I'll update the API script to fetch all videos
- **Backend database credentials** → I'll update the database script to query directly

Then I'll:
1. Fetch all 7,228 videos with metadata
2. Map titles and descriptions to S3 files
3. Create complete Excel inventory
4. Generate comprehensive report

## 📁 Files Ready

- ✅ `venv/` - Virtual environment with psycopg2, pandas, openpyxl
- ✅ `fetch_videos_from_database.py` - Ready (needs correct database URL)
- ✅ `fetch_all_video_metadata.py` - Ready (needs user token)
- ✅ `get_api_token.sh` - Guest token generator (limited permissions)

---

**Which option would you like to proceed with?**
1. Login via API to get user token
2. Provide backend database credentials
3. Extract token from mobile app

