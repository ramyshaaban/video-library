# API Authentication Guide - Complete Solutions

## ✅ What I Found

1. **Guest Token**: Can be generated, but has limited permissions
2. **Database Credentials**: Found in `.env.production` (Prisma connection)
3. **API Endpoint**: `https://api.staycurrentmd.com/graphql`

---

## Solution 1: Use Prisma (Recommended - You Have Prisma Setup!)

You already have Prisma configured in your `designer` folder! This is the easiest way.

### Steps:

1. **Navigate to designer folder:**
   ```bash
   cd ~/lab/designer
   ```

2. **Use Prisma Studio or Prisma Client:**
   ```bash
   # Option A: Use Prisma Studio (GUI)
   npx prisma studio
   # Then navigate to Content table and filter content_type_id = 3
   
   # Option B: Create a script using Prisma Client
   ```

3. **Create a Prisma query script:**
   ```typescript
   // fetch-videos.ts
   import { PrismaClient } from '@prisma/client'
   
   const prisma = new PrismaClient()
   
   async function fetchVideos() {
     const videos = await prisma.content.findMany({
       where: { content_type_id: 3 },
       include: {
         associated_content_files: true,
         space: true
       }
     })
     
     console.log(JSON.stringify(videos, null, 2))
   }
   
   fetchVideos()
   ```

---

## Solution 2: Install psycopg2 and Query Directly

### Install psycopg2:

```bash
# Option 1: Using pip with --user flag
pip3 install --user psycopg2-binary

# Option 2: Using virtual environment
python3 -m venv venv
source venv/bin/activate
pip install psycopg2-binary

# Option 3: Using homebrew (if on macOS)
brew install postgresql
pip3 install psycopg2-binary
```

### Then run:
```bash
cd ~/lab/designer/content_transcriptions
python3 fetch_videos_from_database.py
```

---

## Solution 3: Use User Authentication Token

### Method A: Login via API

1. **Request OTP:**
   ```bash
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
   ```

2. **Verify OTP and get token:**
   ```bash
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

3. **Save token and use it:**
   ```bash
   echo "YOUR_TOKEN_HERE" > user_token.txt
   ```

### Method B: Extract from App

If you have the app installed and logged in:
- Token is stored in AsyncStorage as `USER_TOKEN`
- Use React Native Debugger to extract it
- Or check device file system

---

## Solution 4: Use Prisma Migrate/Query

Since you have Prisma setup, you can use it directly:

```bash
cd ~/lab/designer

# Check Prisma schema
cat prisma/schema.prisma

# Use Prisma Client in Node.js
node -e "
const { PrismaClient } = require('@prisma/client')
const prisma = new PrismaClient()
prisma.content.findMany({
  where: { content_type_id: 3 },
  include: { associated_content_files: true }
}).then(videos => {
  console.log(JSON.stringify(videos, null, 2))
  prisma.\$disconnect()
})
"
```

---

## Quick Start: Use Prisma (Easiest!)

Since you already have Prisma configured:

```bash
cd ~/lab/designer

# Install dependencies if needed
npm install  # or yarn install

# Use Prisma Studio (visual interface)
npx prisma studio

# Or create a simple script
```

I can create a Node.js/TypeScript script that uses your existing Prisma setup to fetch all video metadata. Would you like me to do that?

---

## Files Available

- ✅ `get_api_token.sh` - Generates guest token (limited access)
- ✅ `api_token.txt` - Generated guest token
- ✅ `fetch_videos_from_database.py` - Database query script (needs psycopg2)
- ✅ `HOW_TO_GET_API_AUTHENTICATION.md` - Detailed guide
- ✅ `API_AUTHENTICATION_GUIDE.md` - This file

---

## Recommended Next Step

**Use Prisma** since you already have it set up! It's the easiest and most reliable method.

Would you like me to:
1. Create a Prisma script to fetch all videos?
2. Help install psycopg2?
3. Set up user authentication?

