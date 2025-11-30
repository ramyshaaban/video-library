#!/bin/bash
# Deployment script for staycurrentapp.com

set -e

echo "============================================================"
echo "Deploying Video Library to staycurrentapp.com"
echo "============================================================"
echo ""

# Configuration
SERVER="72.167.132.33"
DEPLOY_USER="ponsky"
DEPLOY_PATH="/home/ponsky/video-library"
SSH_KEY="${HOME}/.ssh/id_ed25519"

# Check if sshpass is available for password authentication
if command -v sshpass &> /dev/null; then
    SSH_CMD="sshpass -p 'PhE@C1%5MAuv' ssh"
    SCP_CMD="sshpass -p 'PhE@C1%5MAuv' scp"
else
    echo "⚠️  sshpass not installed. You'll need to enter password manually."
    echo "   Install with: brew install hudochenkov/sshpass/sshpass"
    echo ""
    SSH_CMD="ssh"
    SCP_CMD="scp"
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
    --exclude='.gitignore' \
    -czf /tmp/video-library-deploy.tar.gz .

echo "✅ Archive created: /tmp/video-library-deploy.tar.gz"
echo ""

# Upload to server
echo "📤 Uploading to server..."
if command -v sshpass &> /dev/null; then
    sshpass -p 'PhE@C1%5MAuv' scp /tmp/video-library-deploy.tar.gz ${DEPLOY_USER}@${SERVER}:/tmp/
else
    scp /tmp/video-library-deploy.tar.gz ${DEPLOY_USER}@${SERVER}:/tmp/
fi

echo "✅ Upload complete"
echo ""

# Deploy on server
echo "🚀 Deploying on server..."
if command -v sshpass &> /dev/null; then
    sshpass -p 'PhE@C1%5MAuv' ssh ${DEPLOY_USER}@${SERVER} << 'ENDSSH'
        set -e
        DEPLOY_PATH="/home/ponsky/video-library"
        
        # Create directory if it doesn't exist
        mkdir -p $DEPLOY_PATH
        cd $DEPLOY_PATH
        
        # Backup existing deployment
        if [ -d "$DEPLOY_PATH" ] && [ "$(ls -A $DEPLOY_PATH 2>/dev/null)" ]; then
            echo "📦 Backing up existing deployment..."
            tar -czf /tmp/video-library-backup-$(date +%Y%m%d-%H%M%S).tar.gz -C $DEPLOY_PATH . 2>/dev/null || true
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
User=ponsky
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
        sudo systemctl status video-library.service --no-pager -l || true
ENDSSH
else
    echo "Please run the following commands manually on the server:"
    echo ""
    echo "ssh ${DEPLOY_USER}@${SERVER}"
    echo ""
    echo "Then run:"
    cat << 'MANUAL_DEPLOY'
        DEPLOY_PATH="/home/ponsky/video-library"
        mkdir -p $DEPLOY_PATH
        cd $DEPLOY_PATH
        tar -xzf /tmp/video-library-deploy.tar.gz
        python3 -m venv venv
        source venv/bin/activate
        pip install --upgrade pip
        pip install -r requirements.txt
        source setup_aws_credentials.sh
        # Then set up systemd service as shown above
MANUAL_DEPLOY
fi

echo ""
echo "============================================================"
echo "✅ Deployment Complete!"
echo "============================================================"
echo ""
echo "🌐 Application should be available at:"
echo "   http://72.167.132.33:5001"
echo "   or"
echo "   http://staycurrentapp.com:5001"
echo ""
echo "📋 To check service status:"
echo "   ssh ${DEPLOY_USER}@${SERVER} 'sudo systemctl status video-library'"
echo ""
echo "📋 To view logs:"
echo "   ssh ${DEPLOY_USER}@${SERVER} 'sudo journalctl -u video-library -f'"
echo ""
