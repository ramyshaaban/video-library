#!/bin/bash
# Deployment script for staycurrentapp.com

set -e

echo "============================================================"
echo "Deploying Video Library to staycurrentapp.com"
echo "============================================================"
echo ""

# Configuration
SERVER="staycurrentapp.com"
DEPLOY_USER="deploy"  # Adjust if different
DEPLOY_PATH="/var/www/video-library"  # Adjust if different
SSH_KEY="${HOME}/.ssh/id_ed25519"

# Check if SSH key exists
if [ ! -f "$SSH_KEY" ]; then
    echo "❌ SSH key not found at $SSH_KEY"
    echo "Please provide the correct SSH key path"
    exit 1
fi

echo "📦 Preparing deployment..."
echo ""

# Create deployment package (exclude venv, thumbnails, etc.)
echo "Creating deployment archive..."
tar --exclude='venv' \
    --exclude='thumbnails' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.git' \
    --exclude='.DS_Store' \
    --exclude='*.log' \
    --exclude='server.pid' \
    -czf /tmp/video-library-deploy.tar.gz .

echo "✅ Archive created: /tmp/video-library-deploy.tar.gz"
echo ""

# Upload to server
echo "📤 Uploading to server..."
scp -i "$SSH_KEY" /tmp/video-library-deploy.tar.gz ${DEPLOY_USER}@${SERVER}:/tmp/

echo "✅ Upload complete"
echo ""

# Deploy on server
echo "🚀 Deploying on server..."
ssh -i "$SSH_KEY" ${DEPLOY_USER}@${SERVER} << 'ENDSSH'
    set -e
    DEPLOY_PATH="/var/www/video-library"
    
    # Create directory if it doesn't exist
    sudo mkdir -p $DEPLOY_PATH
    sudo chown $USER:$USER $DEPLOY_PATH
    
    # Backup existing deployment
    if [ -d "$DEPLOY_PATH" ] && [ "$(ls -A $DEPLOY_PATH)" ]; then
        echo "📦 Backing up existing deployment..."
        sudo tar -czf /tmp/video-library-backup-$(date +%Y%m%d-%H%M%S).tar.gz -C $DEPLOY_PATH .
    fi
    
    # Extract new deployment
    echo "📂 Extracting new deployment..."
    cd $DEPLOY_PATH
    tar -xzf /tmp/video-library-deploy.tar.gz
    
    # Set up Python virtual environment
    if [ ! -d "venv" ]; then
        echo "🐍 Creating Python virtual environment..."
        python3 -m venv venv
    fi
    
    # Install dependencies
    echo "📥 Installing dependencies..."
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
    
    # Set up AWS credentials (if needed)
    if [ -f "setup_aws_credentials.sh" ]; then
        echo "🔑 Setting up AWS credentials..."
        source setup_aws_credentials.sh
    fi
    
    # Create systemd service (if needed)
    echo "⚙️  Setting up systemd service..."
    sudo tee /etc/systemd/system/video-library.service > /dev/null << EOF
[Unit]
Description=Video Library Flask Application
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$DEPLOY_PATH
Environment="PATH=$DEPLOY_PATH/venv/bin"
ExecStart=$DEPLOY_PATH/venv/bin/python3 $DEPLOY_PATH/video_library_app.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
    
    # Reload systemd and restart service
    sudo systemctl daemon-reload
    sudo systemctl enable video-library.service
    sudo systemctl restart video-library.service
    
    echo "✅ Deployment complete!"
    echo ""
    echo "📊 Service status:"
    sudo systemctl status video-library.service --no-pager -l
ENDSSH

echo ""
echo "============================================================"
echo "✅ Deployment Complete!"
echo "============================================================"
echo ""
echo "🌐 Application should be available at:"
echo "   http://staycurrentapp.com:5001"
echo "   or"
echo "   https://staycurrentapp.com/video-library"
echo ""
echo "📋 To check service status:"
echo "   ssh ${DEPLOY_USER}@${SERVER} 'sudo systemctl status video-library'"
echo ""
echo "📋 To view logs:"
echo "   ssh ${DEPLOY_USER}@${SERVER} 'sudo journalctl -u video-library -f'"
echo ""

