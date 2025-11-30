# Video Player Configuration Guide

## Current Issues & Solutions

### Issue 1: Videos Not Playing

**Problem**: Videos have file paths like `spaces/1/content/11264/file_11264_1_1763501491907.mp4` but these need to be converted to full S3/CDN URLs.

**Solution**: Configure the S3/CDN base URL:

```bash
# Set environment variable
export VIDEO_CDN_BASE_URL=https://gcmd-production.s3.amazonaws.com
# or if using CloudFront CDN:
export VIDEO_CDN_BASE_URL=https://d1234567890.cloudfront.net

# Then restart the server
python3 video_library_app.py
```

**Alternative**: If videos are on a different CDN, update the base URL in `video_library_app.py`:
```python
base_url = os.getenv('VIDEO_CDN_BASE_URL', 'https://your-actual-cdn-url.com')
```

### Issue 2: CORS Errors

If you see CORS errors in the browser console, you need to configure CORS on your S3 bucket or CDN:

**For S3:**
1. Go to S3 bucket → Permissions → CORS
2. Add this configuration:
```json
[
    {
        "AllowedHeaders": ["*"],
        "AllowedMethods": ["GET", "HEAD"],
        "AllowedOrigins": ["*"],
        "ExposeHeaders": []
    }
]
```

**For CloudFront:**
- CORS is handled automatically if configured on S3

### Issue 3: Thumbnails Not Showing

**Problem**: Thumbnails are showing default placeholders instead of video frames.

**Solution**: Generate thumbnails from videos:

```bash
# Install ffmpeg first
brew install ffmpeg  # macOS
# or
sudo apt-get install ffmpeg  # Linux

# Generate thumbnails (this will take time for 2000+ videos)
python3 generate_thumbnails.py

# This creates thumbnails in the thumbnails/ directory
# The server will automatically serve them
```

**Note**: Thumbnail generation requires:
- ffmpeg installed
- Access to video files (local or via URL)
- Time (several hours for 2000+ videos)

## Quick Test

Test if videos are accessible:

```bash
# Test video URL construction
curl -I "https://gcmd-production.s3.amazonaws.com/spaces/1/content/11264/file_11264_1_1763501491907.mp4"

# Test thumbnail endpoint
curl -I "http://localhost:5001/api/video/11264/thumbnail"
```

## Configuration Options

### Environment Variables

```bash
# Video CDN/S3 base URL
export VIDEO_CDN_BASE_URL=https://gcmd-production.s3.amazonaws.com

# Thumbnail/CDN base URL (if different)
export CDN_BASE_URL=https://gcmd-production.s3.amazonaws.com

# S3 base URL (alternative)
export S3_BASE_URL=https://gcmd-production.s3.amazonaws.com
```

### Video URL Priority

The system tries to load videos in this order:
1. `hls_url` (if available) - Best for streaming
2. `/api/video/stream/<id>` - Constructs S3/CDN URL
3. Direct `file_path` if it's already a full URL

## Troubleshooting

### Videos Still Don't Play

1. **Check browser console** for errors:
   - CORS errors → Configure S3 CORS
   - 404 errors → Check S3 URL is correct
   - Network errors → Check video file exists

2. **Verify S3 URL format**:
   ```bash
   # Test a video URL directly
   curl -I "https://gcmd-production.s3.amazonaws.com/spaces/1/content/11264/file_11264_1_1763501491907.mp4"
   ```

3. **Check video file permissions**:
   - S3 bucket should allow public read access
   - Or use presigned URLs (requires AWS credentials)

### Thumbnails Still Not Showing

1. **Check if thumbnails were generated**:
   ```bash
   ls -la thumbnails/ | head -10
   ```

2. **Check thumbnail endpoint**:
   ```bash
   curl -I "http://localhost:5001/api/video/11264/thumbnail"
   ```

3. **Generate thumbnails manually**:
   ```bash
   python3 generate_thumbnails.py --json all_video_metadata_from_database.json --output thumbnails
   ```

## Next Steps

1. **Configure S3/CDN URL** - Set `VIDEO_CDN_BASE_URL` environment variable
2. **Set up CORS** - Configure CORS on S3 bucket
3. **Generate thumbnails** - Run thumbnail generation script
4. **Test playback** - Click a video and verify it plays

## Alternative: Use Presigned URLs

If videos are private, you'll need to generate presigned URLs using AWS credentials:

```python
import boto3
from datetime import timedelta

s3_client = boto3.client('s3')
url = s3_client.generate_presigned_url(
    'get_object',
    Params={'Bucket': 'gcmd-production', 'Key': file_path},
    ExpiresIn=3600
)
```

This requires AWS credentials and boto3 library.

