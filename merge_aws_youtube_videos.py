#!/usr/bin/env python3
"""
Script to merge unmatched AWS videos with YouTube videos.
Loads AWS videos from database and adds those that weren't matched to YouTube.
"""

import json
import os
import sys
from difflib import SequenceMatcher

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def similarity_score(str1, str2):
    """Calculate similarity score between two strings"""
    if not str1 or not str2:
        return 0.0
    return SequenceMatcher(None, str1.lower().strip(), str2.lower().strip()).ratio()

def normalize_title(title):
    """Normalize title for comparison"""
    if not title:
        return ""
    title = title.lower().strip()
    title = title.replace(" - staycurrentmd", "").replace(" | staycurrentmd", "")
    return title

def load_aws_videos_from_database():
    """Load all AWS videos from database"""
    try:
        import psycopg2
        with open('production_rds_credentials.json', 'r') as f:
            creds = json.load(f)
        
        conn = psycopg2.connect(
            host=creds['host'],
            port=creds['port'],
            user=creds['username'],
            password=creds['password'],
            database=creds.get('dbInstanceIdentifier', 'staycurrentmd'),
            sslmode='prefer'
        )
        cur = conn.cursor()
        
        # Query all videos from database with full details
        cur.execute("""
            SELECT 
                v.content_id,
                v.title,
                v.description,
                v.space_name,
                v.file_path,
                v.hash_filename,
                v.thumbnail,
                v.hls_url,
                v.s3_path,
                v.bucket,
                v.folder,
                v.created_at,
                v.updated_at
            FROM videos v
            WHERE v.space_name IS NOT NULL AND v.space_name != ''
            ORDER BY v.content_id
        """)
        
        aws_videos = []
        for row in cur.fetchall():
            aws_videos.append({
                'content_id': row[0],
                'title': row[1] or '',
                'description': row[2] or '',
                'space_name': row[3] or '',
                'file_path': row[4] or '',
                'hash_filename': row[5],
                'thumbnail': row[6] or '',
                'hls_url': row[7] or '',
                's3_path': row[8],
                'bucket': row[9],
                'folder': row[10],
                'created_at': str(row[11]) if row[11] else '',
                'updated_at': str(row[12]) if row[12] else '',
                'type': 'aws'  # Mark as AWS video
            })
        
        cur.close()
        conn.close()
        print(f"✅ Loaded {len(aws_videos)} AWS videos from database")
        return aws_videos
    except Exception as e:
        print(f"❌ Error loading AWS videos from database: {e}")
        import traceback
        traceback.print_exc()
        return []

def find_unmatched_aws_videos(aws_videos, youtube_videos):
    """Find AWS videos that don't have a YouTube match"""
    unmatched = []
    
    print(f"\n🔍 Finding unmatched AWS videos...")
    print(f"   AWS videos: {len(aws_videos)}")
    print(f"   YouTube videos: {len(youtube_videos)}")
    
    for aws_video in aws_videos:
        aws_title = normalize_title(aws_video.get('title', ''))
        
        # Check if there's a matching YouTube video
        found_match = False
        for yt_video in youtube_videos:
            yt_title = normalize_title(yt_video.get('title', ''))
            title_score = similarity_score(aws_title, yt_title)
            
            # If titles are very similar (>0.85), consider it matched
            if title_score > 0.85:
                found_match = True
                break
        
        if not found_match:
            unmatched.append(aws_video)
    
    print(f"   ✅ Found {len(unmatched)} unmatched AWS videos")
    return unmatched

def merge_videos(youtube_videos, aws_unmatched_videos):
    """Merge YouTube and unmatched AWS videos"""
    all_videos = []
    
    # Add YouTube videos
    all_videos.extend(youtube_videos)
    
    # Add unmatched AWS videos
    all_videos.extend(aws_unmatched_videos)
    
    print(f"\n✅ Merged videos:")
    print(f"   YouTube: {len(youtube_videos)}")
    print(f"   AWS (unmatched): {len(aws_unmatched_videos)}")
    print(f"   Total: {len(all_videos)}")
    
    return all_videos

def main():
    """Main function"""
    print("=" * 60)
    print("Merging AWS and YouTube Videos")
    print("=" * 60)
    
    # Load YouTube videos
    print("\n📥 Loading YouTube videos...")
    try:
        from video_library_app import fetch_youtube_videos, YOUTUBE_API_KEY, YOUTUBE_CHANNEL_ID
        
        if not YOUTUBE_API_KEY:
            print("❌ YOUTUBE_API_KEY not set")
            return
        
        youtube_videos = fetch_youtube_videos(YOUTUBE_API_KEY, YOUTUBE_CHANNEL_ID, None)
        print(f"   Loaded {len(youtube_videos)} YouTube videos")
    except Exception as e:
        print(f"❌ Error loading YouTube videos: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Load AWS videos from database
    print("\n📥 Loading AWS videos from database...")
    aws_videos = load_aws_videos_from_database()
    
    if not aws_videos:
        print("❌ No AWS videos found")
        return
    
    # Find unmatched AWS videos
    unmatched_aws = find_unmatched_aws_videos(aws_videos, youtube_videos)
    
    # Merge videos
    all_videos = merge_videos(youtube_videos, unmatched_aws)
    
    # Get space distribution
    from collections import defaultdict
    space_counts = defaultdict(int)
    for video in all_videos:
        space = video.get('space_name', 'Unknown')
        space_counts[space] += 1
    
    print(f"\n📊 Final video distribution by space:")
    for space, count in sorted(space_counts.items(), key=lambda x: -x[1]):
        print(f"   {space}: {count} videos")
    
    # Save merged videos
    output_file = 'merged_videos.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_videos, f, indent=2, ensure_ascii=False)
    print(f"\n💾 Saved merged videos to {output_file}")
    
    # Save unmatched AWS videos separately for reference
    unmatched_file = 'unmatched_aws_videos.json'
    with open(unmatched_file, 'w', encoding='utf-8') as f:
        json.dump(unmatched_aws, f, indent=2, ensure_ascii=False)
    print(f"💾 Saved unmatched AWS videos to {unmatched_file}")
    
    print("\n✅ Done!")

if __name__ == '__main__':
    main()

