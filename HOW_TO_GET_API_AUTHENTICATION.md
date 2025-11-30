# How to Get API Authentication for StayCurrentMD

## Current Status

✅ **Guest Token Generation**: Works, but has limited permissions  
❌ **Content Queries**: Guest users cannot query video content  
✅ **API Endpoint**: `https://api.staycurrentmd.com/graphql`

---

## Option 1: Generate Guest Token (Limited Access)

**Status**: ✅ Works, but cannot query videos

The guest token can be generated but has restrictions:
- ❌ Cannot query `getContent` (videos)
- ❌ Cannot query `getContentInfoById`
- ✅ Can generate token
- ⚠️ Limited to certain queries only

**How to generate:**
```bash
./get_api_token.sh
```

**Token saved to**: `api_token.txt`

---

## Option 2: Use User Authentication Token

### Method A: Extract from Mobile App

If you have the app installed and logged in:

1. **On iOS/Android Device:**
   - Open StayCurrentMD app
   - Log in with your account
   - Token is stored in AsyncStorage

2. **Extract Token:**
   - Use React Native Debugger
   - Or check AsyncStorage: `USER_TOKEN` key
   - Or use device file system access

### Method B: Login via API

You can authenticate via the API:

```bash
# Step 1: Request OTP
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

# Step 2: Verify OTP and get token
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
```

**Note**: You'll need a valid email and OTP code.

---

## Option 3: Direct Database Access (Recommended)

If you have database credentials, this is the most efficient method:

### PostgreSQL Connection

```bash
# Connect to database
psql $DATABASE_URL

# Query all video metadata
SELECT 
  c.id,
  c.content_title,
  c.description,
  c.space_id,
  cf.file,                    -- Maps to S3: "videos/{hash}.mp4"
  cf.thumbnail,
  s.name as space_name,
  c.created_at,
  c.updated_at
FROM content c
JOIN associated_content_files cf ON cf.content_id = c.id
LEFT JOIN spaces s ON s.id = c.space_id
WHERE c.content_type_id = 3   -- 3 = VIDEOS
ORDER BY c.created_at DESC;
```

### Export to CSV

```sql
COPY (
  SELECT 
    c.id,
    c.content_title,
    c.description,
    c.space_id,
    cf.file,
    cf.thumbnail,
    s.name as space_name,
    c.created_at
  FROM content c
  JOIN associated_content_files cf ON cf.content_id = c.id
  LEFT JOIN spaces s ON s.id = c.space_id
  WHERE c.content_type_id = 3
) TO '/tmp/videos_metadata.csv' WITH CSV HEADER;
```

---

## Option 4: Backend Admin Panel

If your backend has an admin panel:

1. Log in to admin panel
2. Navigate to Content/Videos section
3. Export all videos to CSV/Excel
4. Filter for `content_type_id = 3`

---

## Option 5: Check Environment Variables

Check if you have database credentials in your local environment:

```bash
# Check .env files
cat ~/lab/designer/.env.local
cat ~/lab/designer/.env.production

# Look for:
# DATABASE_URL=postgresql://...
```

---

## Quick Test: Check What Guest Token Can Do

```bash
TOKEN=$(cat api_token.txt)

# Test 1: Get user details (might work)
curl -X POST https://api.staycurrentmd.com/graphql \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"query": "query { getUserDetails { success } }"}'

# Test 2: Get hubs (might work)
curl -X POST https://api.staycurrentmd.com/graphql \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"query": "query { getHubs { success hubs { id name } } }"}'
```

---

## Recommended Approach

**Best Option**: Direct database access
- ✅ Most efficient
- ✅ Can query all data at once
- ✅ No API rate limits
- ✅ Can export directly to CSV

**Alternative**: User authentication token
- ✅ Full API access
- ⚠️ Requires login credentials
- ⚠️ May have rate limits

**Last Resort**: Admin panel export
- ✅ Easy if available
- ⚠️ May require manual work

---

## Next Steps

1. **Check for database credentials** in `.env` files
2. **Try to extract user token** from app if logged in
3. **Use database access** if available (most efficient)
4. **Contact backend team** for API access or database credentials

Once you have access, I can create a script to:
- ✅ Fetch all video metadata
- ✅ Map to S3 files
- ✅ Create complete Excel inventory
- ✅ Generate comprehensive report

---

## Files Created

- `get_api_token.sh` - Script to generate guest token
- `api_token.txt` - Generated guest token (limited permissions)
- `HOW_TO_GET_API_AUTHENTICATION.md` - This guide

