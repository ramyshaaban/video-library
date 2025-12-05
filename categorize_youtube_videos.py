#!/usr/bin/env python3
"""
Script to categorize YouTube videos into spaces by matching them with AWS videos.
Compares YouTube and AWS libraries, identifies identical videos, and assigns spaces.
"""

import json
import os
import sys
from difflib import SequenceMatcher
from collections import defaultdict

# Add current directory to path
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
    # Remove common prefixes/suffixes, extra spaces, etc.
    title = title.lower().strip()
    # Remove common YouTube suffixes
    title = title.replace(" - staycurrentmd", "").replace(" | staycurrentmd", "")
    return title

def match_videos(youtube_videos, aws_videos):
    """
    Match YouTube videos with AWS videos based on title similarity.
    Returns a dict mapping YouTube video content_id to AWS video space_name.
    """
    matches = {}
    unmatched_youtube = []
    
    print(f"\n🔍 Matching {len(youtube_videos)} YouTube videos with {len(aws_videos)} AWS videos...")
    
    for yt_video in youtube_videos:
        yt_title = normalize_title(yt_video.get('title', ''))
        yt_desc = (yt_video.get('description', '') or '')[:200]  # First 200 chars
        
        best_match = None
        best_score = 0.0
        best_space = None
        
        for aws_video in aws_videos:
            aws_title = normalize_title(aws_video.get('title', ''))
            aws_space = aws_video.get('space_name', '')
            
            # Calculate title similarity
            title_score = similarity_score(yt_title, aws_title)
            
            # If titles are very similar (>0.85), consider it a match
            if title_score > best_score and title_score > 0.85:
                best_score = title_score
                best_match = aws_video
                best_space = aws_space
        
        if best_match and best_space:
            matches[yt_video.get('content_id')] = {
                'space_name': best_space,
                'match_score': best_score,
                'youtube_title': yt_video.get('title'),
                'aws_title': best_match.get('title')
            }
            print(f"  ✅ Matched: '{yt_video.get('title')[:50]}...' → {best_space} (score: {best_score:.2f})")
        else:
            unmatched_youtube.append(yt_video)
    
    print(f"\n📊 Matching Results:")
    print(f"   Matched: {len(matches)} videos")
    print(f"   Unmatched: {len(unmatched_youtube)} videos")
    
    return matches, unmatched_youtube

def categorize_youtube_videos():
    """Main function to categorize YouTube videos"""
    
    # Load YouTube videos (from current app state)
    print("📥 Loading YouTube videos...")
    try:
        from video_library_app import fetch_youtube_videos, YOUTUBE_API_KEY, YOUTUBE_CHANNEL_ID
        
        if not YOUTUBE_API_KEY:
            print("❌ YOUTUBE_API_KEY not set")
            return
        
        youtube_videos = fetch_youtube_videos(YOUTUBE_API_KEY, YOUTUBE_CHANNEL_ID, None)
        print(f"   Loaded {len(youtube_videos)} YouTube videos")
    except Exception as e:
        print(f"❌ Error loading YouTube videos: {e}")
        return
    
    # Load AWS videos (from JSON file or database)
    print("\n📥 Loading AWS videos...")
    aws_videos = []
    
    # Try loading from JSON file
    json_file = 'all_video_metadata_from_database.json'
    if os.path.exists(json_file):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                aws_videos = json.load(f)
            print(f"   Loaded {len(aws_videos)} AWS videos from JSON file")
        except Exception as e:
            print(f"   ⚠️  Error loading JSON file: {e}")
    
    # If JSON failed, try loading from database
    if not aws_videos:
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
            
            # Query videos from database
            cur.execute("""
                SELECT content_id, title, description, space_name, file_path
                FROM videos
                WHERE space_name IS NOT NULL AND space_name != ''
                ORDER BY content_id
            """)
            
            for row in cur.fetchall():
                aws_videos.append({
                    'content_id': row[0],
                    'title': row[1] or '',
                    'description': row[2] or '',
                    'space_name': row[3] or '',
                    'file_path': row[4] or ''
                })
            
            cur.close()
            conn.close()
            print(f"   Loaded {len(aws_videos)} AWS videos from database")
        except Exception as e:
            print(f"   ❌ Error loading from database: {e}")
            return
    
    if not aws_videos:
        print("❌ No AWS videos found")
        return
    
    # Get unique spaces from AWS videos
    aws_spaces = set(v.get('space_name', '') for v in aws_videos if v.get('space_name'))
    print(f"\n📁 Found {len(aws_spaces)} spaces in AWS library:")
    for space in sorted(aws_spaces):
        count = sum(1 for v in aws_videos if v.get('space_name') == space)
        print(f"   - {space}: {count} videos")
    
    # Match videos
    matches, unmatched = match_videos(youtube_videos, aws_videos)
    
    # Update YouTube videos with space names
    print(f"\n🔄 Updating YouTube videos with space names...")
    updated_count = 0
    space_counts = defaultdict(int)
    
    for yt_video in youtube_videos:
        content_id = yt_video.get('content_id')
        if content_id in matches:
            new_space = matches[content_id]['space_name']
            yt_video['space_name'] = new_space
            space_counts[new_space] += 1
            updated_count += 1
    
    print(f"\n✅ Updated {updated_count} YouTube videos")
    print(f"\n📊 Videos by space:")
    for space, count in sorted(space_counts.items()):
        print(f"   - {space}: {count} videos")
    
    if unmatched:
        print(f"\n⚠️  {len(unmatched)} YouTube videos remain unmatched (staying in 'StayCurrentMD' space)")
    
    # Save updated YouTube videos to a file for review
    output_file = 'youtube_videos_categorized.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(youtube_videos, f, indent=2, ensure_ascii=False)
    print(f"\n💾 Saved categorized videos to {output_file}")
    
    # Also create a mapping file
    mapping_file = 'youtube_to_space_mapping.json'
    mapping = {}
    for yt_video in youtube_videos:
        content_id = yt_video.get('content_id')
        space_name = yt_video.get('space_name', 'StayCurrentMD')
        mapping[content_id] = {
            'space_name': space_name,
            'title': yt_video.get('title'),
            'youtube_id': yt_video.get('youtube_id')
        }
    
    with open(mapping_file, 'w', encoding='utf-8') as f:
        json.dump(mapping, f, indent=2, ensure_ascii=False)
    print(f"💾 Saved space mapping to {mapping_file}")
    
    return youtube_videos, matches

if __name__ == '__main__':
    categorize_youtube_videos()

