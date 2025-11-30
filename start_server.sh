#!/bin/bash
# Start the video library server

cd "/Users/ramyshaaban/lab/video library"
source venv/bin/activate
source setup_aws_credentials.sh
python3 video_library_app.py
