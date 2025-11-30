#!/usr/bin/env python3
"""
Generate thumbnails from video first frames
Requires ffmpeg to be installed
"""
import json
import os
import subprocess
import sys
from pathlib import Path

def check_ffmpeg():
    """Check if ffmpeg is installed"""
    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def generate_thumbnail(video_path, output_path, time_offset=1.0):
    """
    Generate thumbnail from video at specified time offset
    
    Args:
        video_path: Path to video file
        output_path: Path to save thumbnail
        time_offset: Time in seconds to extract frame (default: 1.0)
    """
    try:
        cmd = [
            'ffmpeg',
            '-i', video_path,
            '-ss', str(time_offset),
            '-vframes', '1',
            '-q:v', '2',  # High quality
            '-y',  # Overwrite output file
            output_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            return True
        else:
            print(f"Error generating thumbnail: {result.stderr}")
            return False
    except subprocess.TimeoutExpired:
        print(f"Timeout generating thumbnail for {video_path}")
        return False
    except Exception as e:
        print(f"Exception generating thumbnail: {e}")
        return False

def process_videos_from_json(json_file='all_video_metadata_from_database.json', 
                            output_dir='thumbnails',
                            video_base_url=None):
    """
    Process videos from JSON file and generate thumbnails
    
    Args:
        json_file: Path to video metadata JSON file
        output_dir: Directory to save thumbnails
        video_base_url: Base URL for video files (if videos are remote)
    """
    if not check_ffmpeg():
        print("❌ ffmpeg is not installed. Please install it first:")
        print("   macOS: brew install ffmpeg")
        print("   Linux: sudo apt-get install ffmpeg")
        print("   Windows: Download from https://ffmpeg.org/download.html")
        return False
    
    # Load video data
    print(f"Loading video data from {json_file}...")
    with open(json_file, 'r') as f:
        videos = json.load(f)
    
    print(f"Found {len(videos)} videos")
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Process videos
    generated = 0
    skipped = 0
    errors = 0
    
    for i, video in enumerate(videos):
        video_id = video.get('content_id')
        file_path = video.get('file_path', '')
        
        if not file_path:
            skipped += 1
            continue
        
        # Generate thumbnail path
        thumbnail_path = os.path.join(output_dir, f"{video_id}.jpg")
        
        # Skip if already exists
        if os.path.exists(thumbnail_path):
            skipped += 1
            continue
        
        # Determine video source
        if file_path.startswith('http://') or file_path.startswith('https://'):
            # Remote video - download first frame
            video_url = file_path
            print(f"[{i+1}/{len(videos)}] Processing remote video {video_id}...")
            # For remote videos, we'd need to download or use a different approach
            # For now, skip remote videos
            skipped += 1
            continue
        else:
            # Local video file
            if video_base_url:
                video_path = f"{video_base_url}/{file_path}"
            else:
                video_path = file_path
            
            # Check if video file exists
            if not os.path.exists(video_path) and not video_path.startswith('http'):
                skipped += 1
                continue
        
        print(f"[{i+1}/{len(videos)}] Generating thumbnail for video {video_id}...")
        
        # Generate thumbnail
        if generate_thumbnail(video_path, thumbnail_path):
            generated += 1
            print(f"  ✅ Generated: {thumbnail_path}")
        else:
            errors += 1
            print(f"  ❌ Failed to generate thumbnail")
    
    print(f"\n✅ Complete!")
    print(f"   Generated: {generated}")
    print(f"   Skipped: {skipped}")
    print(f"   Errors: {errors}")
    
    return True

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate thumbnails from video first frames')
    parser.add_argument('--json', default='all_video_metadata_from_database.json',
                       help='Path to video metadata JSON file')
    parser.add_argument('--output', default='thumbnails',
                       help='Output directory for thumbnails')
    parser.add_argument('--video-base-url', default=None,
                       help='Base URL for video files (if remote)')
    
    args = parser.parse_args()
    
    process_videos_from_json(args.json, args.output, args.video_base_url)

