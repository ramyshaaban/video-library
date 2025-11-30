# S3 Path Mismatch Issue

## Problem Identified

The database stores file paths like:
- `spaces/1/content/11278/file_11278_1_1764082933619.mp4`

But these files **do NOT exist** in S3 at that path.

## Root Cause

The database stores the **original upload path**, but S3 uses a **hash-based storage system**:
- Database: `spaces/1/content/11278/file_11278_1_1764082933619.mp4`
- S3 Actual: `videos/000a300e8f1e74ab4fec71506bea7096.mp4` (hash-based)

## Solution Options

### Option 1: Find the Mapping (Recommended)

We need to find how `content_id` maps to the actual S3 hash. This mapping might be in:
1. **Database**: Check if there's a hash field in `content_file` table
2. **API**: The GraphQL API might return the correct path
3. **S3 Metadata**: Check if S3 objects have metadata linking to content_id

### Option 2: Use HLS URLs

498 videos have HLS URLs that work:
- Format: `https://d1dnj0gz56dmdu.cloudfront.net/[uuid]/AppleHLS1/[hash].m3u8`
- These are working CloudFront URLs

### Option 3: Query API for Correct Paths

The GraphQL API might return the correct `associated_content_files.file` path that matches S3.

## Next Steps

1. Check database for hash mapping
2. Query API to get correct file paths
3. Use HLS URLs where available
4. Create mapping from content_id → S3 hash

