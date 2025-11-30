#!/bin/bash
# Setup AWS credentials for video library app

echo "============================================================"
echo "AWS Credentials Setup for Video Library"
echo "============================================================"
echo ""

# Check if AWS credentials file exists
if [ -f ~/.aws/credentials ]; then
    echo "✅ Found AWS credentials file: ~/.aws/credentials"
    
    # Extract credentials from file
    AWS_ACCESS_KEY_ID=$(grep -A 2 "\[default\]" ~/.aws/credentials | grep "aws_access_key_id" | cut -d'=' -f2 | tr -d ' ')
    AWS_SECRET_ACCESS_KEY=$(grep -A 2 "\[default\]" ~/.aws/credentials | grep "aws_secret_access_key" | cut -d'=' -f2 | tr -d ' ')
    
    if [ -n "$AWS_ACCESS_KEY_ID" ] && [ -n "$AWS_SECRET_ACCESS_KEY" ]; then
        echo "✅ Extracted AWS credentials from file"
        echo ""
        echo "Setting environment variables..."
        echo ""
        
        # Export credentials
        export AWS_ACCESS_KEY_ID="$AWS_ACCESS_KEY_ID"
        export AWS_SECRET_ACCESS_KEY="$AWS_SECRET_ACCESS_KEY"
        export AWS_DEFAULT_REGION="us-east-2"
        export S3_BUCKET_NAME="gcmd-production"
        
        echo "✅ Environment variables set:"
        echo "   AWS_ACCESS_KEY_ID: ${AWS_ACCESS_KEY_ID:0:20}..."
        echo "   AWS_SECRET_ACCESS_KEY: ${AWS_SECRET_ACCESS_KEY:0:10}..."
        echo "   AWS_DEFAULT_REGION: $AWS_DEFAULT_REGION"
        echo "   S3_BUCKET_NAME: $S3_BUCKET_NAME"
        echo ""
        echo "============================================================"
        echo "✅ Setup complete! You can now:"
        echo "   1. Run: source setup_aws_credentials.sh"
        echo "   2. Then run: python3 video_library_app.py"
        echo ""
        echo "Or add these to your shell profile (~/.zshrc or ~/.bashrc):"
        echo "   export AWS_ACCESS_KEY_ID=\"$AWS_ACCESS_KEY_ID\""
        echo "   export AWS_SECRET_ACCESS_KEY=\"$AWS_SECRET_ACCESS_KEY\""
        echo "   export AWS_DEFAULT_REGION=\"us-east-2\""
        echo "   export S3_BUCKET_NAME=\"gcmd-production\""
        echo "============================================================"
    else
        echo "❌ Could not extract credentials from file"
        exit 1
    fi
else
    echo "❌ AWS credentials file not found at ~/.aws/credentials"
    echo ""
    echo "To set up AWS credentials:"
    echo "1. Install AWS CLI: brew install awscli"
    echo "2. Configure: aws configure"
    echo "3. Or create ~/.aws/credentials with:"
    echo ""
    echo "   [default]"
    echo "   aws_access_key_id = YOUR_ACCESS_KEY"
    echo "   aws_secret_access_key = YOUR_SECRET_KEY"
    exit 1
fi

