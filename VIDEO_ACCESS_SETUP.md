# Video Access Setup Guide

## Current Status

✅ **Proxy endpoint working** - Videos stream through Flask server with CORS headers
✅ **Thumbnail endpoint fixed** - Returns placeholder instead of 404
⚠️ **S3 access issue** - Getting 400 Bad Request from S3

## The Problem

S3 is returning **400 Bad Request** when trying to access videos. This could be due to:

1. **Incorrect S3 key/path** - The file_path might not match the actual S3 object key
2. **Wrong AWS region** - S3 bucket might be in a different region
3. **Invalid presigned URL** - AWS credentials might not have correct permissions
4. **Bucket/key doesn't exist** - The video file might not be at that S3 path

## Solutions

### Option 1: Verify S3 Path

The file_path in metadata is: `spaces/1/content/11278/file_11278_1_1764082933619.mp4`

But the actual S3 key might be different. Check:
- Is it in a subfolder?
- Does it use a different naming convention?
- Is it in a different bucket?

### Option 2: Configure AWS Credentials Properly

```bash
# Set AWS credentials
export AWS_ACCESS_KEY_ID=your-access-key
export AWS_SECRET_ACCESS_KEY=your-secret-key
export AWS_DEFAULT_REGION=us-east-2  # Check your S3 bucket region
export S3_BUCKET_NAME=gcmd-production

# Restart server
python3 video_library_app.py
```

**Important**: Make sure the AWS credentials have `s3:GetObject` permission for the bucket.

### Option 3: Check S3 Bucket Region

The error shows `x-amz-region: us-east-2`. Make sure you set:
```bash
export AWS_DEFAULT_REGION=us-east-2
```

### Option 4: Verify S3 Object Exists

Test if the object exists:
```bash
aws s3 ls s3://gcmd-production/spaces/1/content/11278/
```

Or check the actual S3 key format in your bucket.

### Option 5: Use Different Video Source

If videos are served from a CDN or different location:
```bash
export VIDEO_CDN_BASE_URL=https://your-actual-cdn-url.com
```

## Debugging

Check server logs when clicking a video:
```bash
# Watch server output
tail -f server.log  # if logging to file
# or check terminal where server is running
```

The logs will show:
- Whether presigned URL was generated
- What error S3 returned
- The actual video URL being used

## Next Steps

1. **Check S3 bucket region** - Set `AWS_DEFAULT_REGION` to match bucket region
2. **Verify AWS credentials** - Ensure they have S3 read permissions
3. **Check file paths** - Verify the S3 key matches the file_path in metadata
4. **Test presigned URL** - Try accessing a presigned URL directly in browser

## Alternative: Use Public URLs

If you can make the bucket public or use a CDN:
1. Configure CORS on S3 bucket
2. Use direct S3 URLs instead of proxy
3. Or set up CloudFront CDN

See `CORS_FIX_GUIDE.md` for CORS configuration.

