# Mobile App Video URL Analysis

## Key Finding

After analyzing the StayCurrentMD mobile app codebase, I found how videos are accessed:

### Video Player Component (`videoPlayer.tsx`)

**Line 442**: The video player uses:
```typescript
const source = isWeb ? (data?.url || data?.file) : (data?.file || data?.url);
```

**Key Points:**
1. The app expects `data.file` or `data.url` to be a **complete URL** (not just a path)
2. It prefers `hls_url` if available (HLS streaming)
3. For CloudFront/AWS URLs, it has special handling (lines 286-307)

### Expected Data Format

The mobile app expects the `associated_content_files` to have:
- `file`: Complete URL like `https://cloudfront.net/videos/000a300e8f1e74ab4fec71506bea7096.mp4`
- OR: S3 path like `videos/000a300e8f1e74ab4fec71506bea7096.mp4` (hash-based)
- `hls_url`: HLS streaming URL (preferred for web)
- `thumbnail`: Thumbnail URL

### Current Metadata Issue

Your metadata has:
- `file_path`: `"spaces/1/content/11278/file_11278_1_1764082933619.mp4"` ❌
- This doesn't match the expected format: `"videos/[hash].mp4"` ✅

### Solution

You need to either:

1. **Query the API** to get the correct `associated_content_files.file` format
   - Use `fetch_all_video_metadata.py` with a valid user token
   - This will get the correct `videos/[hash].mp4` format

2. **Use a CDN Base URL** to construct full URLs
   - If you have CloudFront: `export VIDEO_CDN_BASE_URL=https://your-cloudfront-url.cloudfront.net`
   - The app constructs: `${CDN_BASE_URL}/${file_path}`

3. **Map content_id to S3 hash**
   - The database has a mapping from `content_id` → S3 hash
   - Query `associated_content_files` table to get the correct `file` field

### Next Steps

1. Check if `fetch_all_video_metadata.py` can get the correct format
2. If not, query the database directly for `associated_content_files.file`
3. Update the video library app to use the correct S3 path format

