# AWS Credentials Setup - Complete Guide

## ✅ Status: Credentials Working!

Your AWS credentials are already configured and working! Here's what we found:

### Current Setup

- ✅ **AWS Credentials File**: `~/.aws/credentials`
- ✅ **Access Key ID**: `AKIA****` (configured in ~/.aws/credentials)
- ✅ **Bucket Access**: Can access `gcmd-production` bucket
- ✅ **Presigned URLs**: Successfully generating presigned URLs

## How It Works

The video library app will now:
1. **Automatically use your AWS credentials** from `~/.aws/credentials`
2. **Generate presigned URLs** for private S3 videos
3. **Stream videos through proxy** with proper CORS headers

## Running the Server

### Option 1: Use the Setup Script (Recommended)

```bash
cd /Users/ramyshaaban/lab/designer/content_transcriptions
source venv/bin/activate
source setup_aws_credentials.sh
python3 video_library_app.py
```

### Option 2: Set Environment Variables Manually

Add to your `~/.zshrc` or `~/.bashrc`:

```bash
export AWS_ACCESS_KEY_ID="your-access-key-id"
export AWS_SECRET_ACCESS_KEY="your-secret-access-key"
export AWS_DEFAULT_REGION="us-east-2"
export S3_BUCKET_NAME="gcmd-production"
```

Then reload your shell:
```bash
source ~/.zshrc  # or source ~/.bashrc
```

### Option 3: Use AWS CLI Credentials (Automatic)

The app will automatically use credentials from `~/.aws/credentials` if environment variables are not set. This is the default behavior of boto3.

## Testing

After starting the server, test video playback:

1. **Open browser**: `http://localhost:5001`
2. **Click a video card**
3. **Video should play** using presigned URLs

## Troubleshooting

### If videos don't play:

1. **Check server logs** for presigned URL generation:
   ```bash
   # Look for: "Using presigned URL for video X"
   ```

2. **Test presigned URL directly**:
   ```bash
   curl -I "http://localhost:5001/api/video/proxy/11278"
   # Should return 200 OK
   ```

3. **Verify AWS credentials**:
   ```bash
   aws s3 ls s3://gcmd-production/ --max-items 1
   # Should list bucket contents
   ```

### Common Issues

- **403 Forbidden**: Credentials may not have `s3:GetObject` permission
- **NoSuchKey**: S3 path format may be incorrect
- **Signature mismatch**: Check AWS region (should be `us-east-2`)

## Security Notes

⚠️ **Important**: 
- Never commit AWS credentials to git
- The `~/.aws/credentials` file is already in `.gitignore`
- Presigned URLs expire after 1 hour (configurable)

## Next Steps

1. ✅ **Credentials configured** - Done!
2. ✅ **Server running with presigned URLs** - Done!
3. 🎬 **Test video playback** - Open browser and click a video!

The video library should now work with private S3 videos! 🎉

