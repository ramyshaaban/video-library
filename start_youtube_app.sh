#!/bin/bash
# Start Flask app with YouTube integration on port 5002 for /video-library path

cd /home/ponsky/video-library

# Kill existing YouTube Flask app (but keep AWS one on 5001)
pkill -9 -f "video_library_app.py.*5002" || pkill -9 -f "FLASK_PORT=5002" || true
sleep 2

# Activate virtual environment
source venv/bin/activate

# Set YouTube environment variables
export YOUTUBE_API_KEY="AIzaSyA5-KATvhgQvETeGau2KZ2K1lvkMZQWg9A"
export YOUTUBE_CHANNEL_ID="UC7tyknq3hgjWGVLgLXqV1pA"
# Don't set YOUTUBE_MAX_RESULTS to fetch ALL videos
# export YOUTUBE_MAX_RESULTS="100"
export FLASK_PORT="5002"
export FLASK_HOST="0.0.0.0"

# Start Flask app on port 5002 for YouTube integration
nohup python video_library_app.py > /tmp/flask_youtube.log 2>&1 &

echo "✅ Flask app started with YouTube integration on port 5002"
echo "Check logs: tail -f /tmp/flask_youtube.log"

