# Database Access Status

## ✅ psycopg2 Installed Successfully

- ✅ Virtual environment created: `venv/`
- ✅ psycopg2-binary installed
- ✅ pandas and openpyxl installed
- ✅ Database connection works

## ⚠️ Issue: Wrong Database

The database URL in `~/lab/designer/.env.production` points to the **designer app's database**, not the **StayCurrentMD backend database**.

**Designer App Database:**
- Tables: `ContentPiece`, `Card`, `Collection`, `User`, etc.
- This is a different application

**StayCurrentMD Backend Database:**
- Tables: `content`, `associated_content_files`, `spaces`, etc.
- This is what we need for video metadata

---

## Solutions

### Option 1: Find StayCurrentMD Backend Database Credentials

The StayCurrentMD backend API (`https://api.staycurrentmd.com/graphql`) uses a different database. You need:

1. **Check backend repository** for `.env` files
2. **Check backend deployment** (AWS, Heroku, etc.) for environment variables
3. **Ask backend team** for database credentials
4. **Check backend codebase** for database connection configuration

### Option 2: Use API with User Authentication Token (Recommended)

Since we can't access the backend database directly, use the API:

1. **Login via API** to get a user token
2. **Use the token** to query video content
3. **Fetch all metadata** through GraphQL API

**Steps:**
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

# 2. Verify OTP and get token
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

# 3. Save token
echo "YOUR_TOKEN_HERE" > user_token.txt
```

### Option 3: Check for Backend Repository

Look for the StayCurrentMD backend repository:
- Check `~/lab/staycurrentmd/` or similar
- Check for backend codebase with database configuration
- Look for `.env` files in backend repository

---

## Current Status

- ✅ **psycopg2**: Installed and working
- ✅ **Database connection**: Works
- ❌ **Correct database**: Need StayCurrentMD backend database credentials
- ⚠️ **Alternative**: Use API with user authentication token

---

## Next Steps

1. **Find backend database credentials** OR
2. **Login via API** to get user token
3. **Use token** to fetch video metadata

Once you have either:
- Backend database credentials → Update `fetch_videos_from_database.py` with correct connection
- User authentication token → Use `fetch_all_video_metadata.py` (needs token)

---

## Files Ready

- ✅ `fetch_videos_from_database.py` - Ready (needs correct database URL)
- ✅ `fetch_all_video_metadata.py` - Ready (needs user token)
- ✅ `venv/` - Virtual environment with all dependencies

