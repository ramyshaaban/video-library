# Video URL Solution

## Problem Identified

After analyzing the database and mobile app:

1. **Database stores**: `spaces/1/content/11278/file_11278_1_1764082933619.mp4`
2. **Mobile app expects**: Complete URLs (CloudFront/CDN) or S3 paths
3. **S3 bucket structure**: Uses hash-based paths like `videos/000a300e8f1e74ab4fec71506bea7096.mp4`

## Current Status

- ✅ Database has 3871 videos with `spaces/` prefix format
- ❌ Database has 0 videos with `videos/` hash-based format
- ✅ Video library app updated to try multiple path formats

## Solution Options

### Option 1: Use CDN/CloudFront (Recommended)

If you have a CloudFront distribution that serves the `spaces/` paths:

```bash
export VIDEO_CDN_BASE_URL=https://your-cloudfront-url.cloudfront.net
```

The app will construct URLs as: `${CDN_BASE_URL}/spaces/1/content/11278/file_11278_1_1764082933619.mp4`

### Option 2: Configure S3 Public Access

Make the S3 bucket publicly readable and use direct S3 URLs:

```bash
export VIDEO_CDN_BASE_URL=https://gcmd-production.s3.amazonaws.com
```

### Option 3: Use Presigned URLs

Configure AWS credentials for presigned URLs:

```bash
export AWS_ACCESS_KEY_ID=your-key
export AWS_SECRET_ACCESS_KEY=your-secret
export AWS_DEFAULT_REGION=us-east-2
export S3_BUCKET_NAME=gcmd-production
```

The app will automatically generate presigned URLs for private S3 buckets.

### Option 4: Find Hash Mapping

If videos are actually stored with hash-based names in S3, you need to:
1. Query the S3 bucket to find the actual file names
2. Create a mapping from `content_id` → S3 hash
3. Update the metadata with correct paths

## Next Steps

1. **Check if you have CloudFront CDN URL** - This is likely what the mobile app uses
2. **Test with S3 public URL** - See if `https://gcmd-production.s3.amazonaws.com/spaces/1/content/11278/file_11278_1_1764082933619.mp4` works
3. **Configure AWS credentials** - For presigned URLs if bucket is private

## Testing

After configuring, test a video:

```bash
# Test video URL
curl -I "http://localhost:5001/api/video/proxy/11278"

# Should return 200 OK with video stream
```

