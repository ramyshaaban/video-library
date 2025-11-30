# Deployment Guide

## Server Information

- **Server**: 72.167.132.33 (staycurrentapp.com)
- **Username**: ponsky
- **Deployment Path**: /home/ponsky/video-library

## Quick Deployment

### Option 1: Automated Deployment (with sshpass)

1. Install sshpass:
   ```bash
   brew install hudochenkov/sshpass/sshpass
   ```

2. Run deployment script:
   ```bash
   ./deploy.sh
   ```

### Option 2: Manual Deployment

1. Create deployment archive:
   ```bash
   tar --exclude='venv' --exclude='thumbnails' --exclude='__pycache__' \
       --exclude='*.pyc' --exclude='.git' --exclude='.DS_Store' \
       --exclude='*.log' --exclude='server.pid' \
       -czf /tmp/video-library-deploy.tar.gz .
   ```

2. Upload to server:
   ```bash
   scp /tmp/video-library-deploy.tar.gz ponsky@72.167.132.33:/tmp/
   ```
   (Password: PhE@C1%5MAuv)

3. SSH into server:
   ```bash
   ssh ponsky@72.167.132.33
   ```
   (Password: PhE@C1%5MAuv)

4. On the server, run:
   ```bash
   DEPLOY_PATH="/home/ponsky/video-library"
   mkdir -p $DEPLOY_PATH
   cd $DEPLOY_PATH
   
   # Extract files
   tar -xzf /tmp/video-library-deploy.tar.gz
   
   # Create virtual environment
   python3 -m venv venv
   source venv/bin/activate
   
   # Install dependencies
   pip install --upgrade pip
   pip install -r requirements.txt
   
   # Set up AWS credentials
   source setup_aws_credentials.sh
   
   # Test run
   python3 video_library_app.py
   ```

## Setting up as a Service

To run the application as a systemd service:

1. Create service file:
   ```bash
   sudo nano /etc/systemd/system/video-library.service
   ```

2. Add this content:
   ```ini
   [Unit]
   Description=Video Library Flask Application
   After=network.target

   [Service]
   Type=simple
   User=ponsky
   WorkingDirectory=/home/ponsky/video-library
   Environment="PATH=/home/ponsky/video-library/venv/bin"
   ExecStart=/home/ponsky/video-library/venv/bin/python3 /home/ponsky/video-library/video_library_app.py
   Restart=always
   RestartSec=10

   [Install]
   WantedBy=multi-user.target
   ```

3. Enable and start service:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable video-library.service
   sudo systemctl start video-library.service
   ```

4. Check status:
   ```bash
   sudo systemctl status video-library.service
   ```

5. View logs:
   ```bash
   sudo journalctl -u video-library -f
   ```

## Accessing the Application

After deployment, the application will be available at:
- **Local**: http://72.167.132.33:5001
- **Domain**: http://staycurrentapp.com:5001

## Updating the Application

To update after making changes:

1. Push changes to GitHub:
   ```bash
   git add .
   git commit -m "Update description"
   git push origin master
   ```

2. Run deployment script again:
   ```bash
   ./deploy.sh
   ```

Or manually:
1. Upload new archive
2. SSH to server
3. Extract and restart service:
   ```bash
   cd /home/ponsky/video-library
   tar -xzf /tmp/video-library-deploy.tar.gz
   source venv/bin/activate
   pip install -r requirements.txt
   sudo systemctl restart video-library.service
   ```

## Troubleshooting

### Service not starting
```bash
sudo journalctl -u video-library -n 50
```

### Port already in use
```bash
sudo lsof -i :5001
sudo kill <PID>
```

### Check if service is running
```bash
sudo systemctl status video-library.service
```

### Restart service
```bash
sudo systemctl restart video-library.service
```

