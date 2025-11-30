# Video Library Application

A Flask-based video library application for browsing and playing videos from StayCurrentMD.

## Quick Start

### Start the Server

```bash
cd "/Users/ramyshaaban/lab/video library"
source venv/bin/activate
source setup_aws_credentials.sh
python3 video_library_app.py
```

Or use the convenience script:
```bash
./start_server.sh
```

### Access the Application

Open your browser to: **http://localhost:5001**

## Features

- ✅ Browse videos by space/collection
- ✅ Global search with typo tolerance
- ✅ Video player with thumbnails
- ✅ AWS S3 integration with presigned URLs
- ✅ HLS streaming support
- ✅ CloudFront CDN support

## Configuration

### AWS Credentials

AWS credentials are automatically loaded from `~/.aws/credentials`. The app uses these to generate presigned URLs for private S3 videos.

### Environment Variables (Optional)

```bash
export AWS_DEFAULT_REGION=us-east-2
export S3_BUCKET_NAME=gcmd-production
export VIDEO_CDN_BASE_URL=https://d1u4wu4o55kmvh.cloudfront.net
```

## Project Structure

- `video_library_app.py` - Main Flask application
- `templates/library.html` - Frontend HTML template
- `all_video_metadata_from_database.json` - Video metadata
- `requirements.txt` - Python dependencies
- `venv/` - Python virtual environment

## Status

✅ **Server Running**: http://localhost:5001
✅ **Videos Loaded**: 2187 videos across 23 spaces
✅ **AWS Integration**: Configured and working
✅ **HLS Support**: 498 videos with HLS URLs

## Troubleshooting

### Server Not Starting

1. Check if port 5001 is in use: `lsof -i :5001`
2. Verify virtual environment: `source venv/bin/activate`
3. Check dependencies: `pip install -r requirements.txt`

### Stop the Server

```bash
pkill -f video_library_app.py
```

Or if using PID file:
```bash
kill $(cat server.pid)
```

## Notes

- The server runs in debug mode by default
- Videos are loaded from `all_video_metadata_from_database.json`
- AWS credentials are required for video playback (presigned URLs)

