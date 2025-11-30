# CloudFront CDN URLs Found

## ✅ CloudFront Distributions Discovered

I found **2 CloudFront distributions** in your configuration:

### 1. Main CloudFront Distribution
- **URL**: `https://d1u4wu4o55kmvh.cloudfront.net`
- **Source**: `production_config.json` → `S3_CLOUDFRONT_BASE_URL`
- **Status**: Private (requires signed URLs)
- **Use**: For serving video files

### 2. HLS Streaming Distribution
- **URL**: `https://d1dnj0gz56dmdu.cloudfront.net`
- **Source**: HLS URLs in video metadata
- **Status**: Private (requires signed URLs)
- **Use**: For HLS streaming (`.m3u8` files)
- **Videos with HLS**: 498 videos have HLS URLs

## Current Status

Both CloudFront distributions return **403 Forbidden**, which means:
- ✅ They exist and are configured
- ⚠️ They require **signed URLs** (CloudFront signed cookies or signed URLs)
- ⚠️ Direct access is not allowed

## Solution: Use Presigned URLs

Since the CloudFront distributions are private, you need to generate **CloudFront signed URLs**. The production config has:
- `S3_CLOUDFRONT_KEY_PAIR_ID`: `K37ZNU0F8NA5XA`
- `S3_CLOUDFRONT_PRIVATE_KEY`: (RSA private key for signing)

### Option 1: Configure CloudFront Signed URLs

Update the video library app to generate CloudFront signed URLs:

```python
import boto3
from botocore.signers import CloudFrontSigner
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
import rsa

def generate_cloudfront_signed_url(url, key_pair_id, private_key_pem, expires_in=3600):
    """Generate CloudFront signed URL"""
    # Parse private key
    private_key = serialization.load_pem_private_key(
        private_key_pem.encode('utf-8'),
        password=None,
        backend=default_backend()
    )
    
    # Create signer
    def rsa_signer(message):
        return private_key.sign(
            message,
            padding.PKCS1v15(),
            hashes.SHA1()
        )
    
    cloudfront_signer = CloudFrontSigner(key_pair_id, rsa_signer)
    
    # Create signed URL
    signed_url = cloudfront_signer.generate_presigned_url(
        url,
        date_less_than=datetime.utcnow() + timedelta(seconds=expires_in)
    )
    
    return signed_url
```

### Option 2: Use Environment Variable (Simpler)

For now, you can set the CloudFront URL and the app will try to use it with presigned URLs:

```bash
export CLOUDFRONT_BASE_URL=https://d1u4wu4o55kmvh.cloudfront.net
export AWS_DEFAULT_REGION=us-east-1
```

### Option 3: Make CloudFront Public (If Appropriate)

If videos should be publicly accessible, you can:
1. Update CloudFront distribution behavior to allow public access
2. Or configure CloudFront to serve from public S3 bucket

## Next Steps

1. **Test with presigned URLs** - Configure CloudFront signing
2. **Or use S3 presigned URLs** - If S3 is the source
3. **Or make CloudFront public** - If videos should be publicly accessible

The video library app has been updated to try the CloudFront URL automatically.

