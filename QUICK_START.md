# Quick Start Guide - Video Library with AWS

## ✅ Setup Complete!

Your AWS credentials are configured and the server is ready.

## Start the Server

```bash
cd /Users/ramyshaaban/lab/designer/content_transcriptions
source venv/bin/activate
source setup_aws_credentials.sh
python3 video_library_app.py
```

## Access the App

Open your browser: **http://localhost:5001**

## Video Playback Status

### ✅ Working (498 videos)
Videos with **HLS URLs** will play automatically. These use CloudFront streaming.

### ⚠️ Not Working Yet (remaining videos)
Videos without HLS URLs need the S3 hash mapping. The database stores `spaces/...` paths but S3 uses hash-based `videos/[hash].mp4` format.

## Test a Working Video

Video ID **8863** has an HLS URL and should work:
- Open: http://localhost:5001
- Search for video ID 8863 or "Western Pediatric Trauma"
- Click to play - it should work!

## AWS Credentials

✅ **Already configured** in `~/.aws/credentials`
- The app automatically uses these credentials
- Presigned URLs are generated for S3 access
- No additional setup needed!

## Troubleshooting

If videos don't play:
1. Check browser console (F12) for errors
2. Check server logs for presigned URL generation
3. Verify AWS credentials: `aws s3 ls s3://gcmd-production/ --max-items 1`

## Next Steps

To fix remaining videos:
1. Find mapping from `content_id` → S3 hash
2. Or query GraphQL API for correct file paths
3. Or use HLS URLs where available (already working!)

🎉 **You're all set!** Try opening the app and playing a video with an HLS URL.

