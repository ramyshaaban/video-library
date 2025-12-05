#!/usr/bin/env python3
"""
StayCurrentMD Video Library - Flask Web Application
A robust video library application with proper structure
Enhanced with Elasticsearch for intelligent fuzzy search
"""
from flask import Flask, render_template, jsonify, request, send_file, Response
import json
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Optional
import os
import re
from difflib import SequenceMatcher
import requests
from urllib.parse import urlparse
import urllib.parse

# Try to import boto3 for presigned URLs (optional)
try:
    import boto3
    from botocore.exceptions import ClientError, NoCredentialsError
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False
    print("ℹ️  boto3 not installed. Install with: pip install boto3 (for presigned URLs)")

# Get the directory where this script is located
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.path.join(BASE_DIR, 'templates')
STATIC_DIR = os.path.join(BASE_DIR, 'static')

app = Flask(__name__, template_folder=TEMPLATE_DIR, static_folder=STATIC_DIR, static_url_path='/static')

# Support for subpath deployment (e.g., /videolibrary)
# Get base path from X-Forwarded-Prefix header (set by nginx)
@app.before_request
def set_base_path():
    base_path = request.headers.get('X-Forwarded-Prefix', '')
    if base_path:
        # Store in g for use in templates
        from flask import g
        g.base_path = base_path.rstrip('/')
    else:
        from flask import g
        g.base_path = ''

# Elasticsearch configuration
ELASTICSEARCH_ENABLED = os.getenv('ELASTICSEARCH_ENABLED', 'true').lower() == 'true'
ELASTICSEARCH_HOST = os.getenv('ELASTICSEARCH_HOST', 'localhost')
ELASTICSEARCH_PORT = int(os.getenv('ELASTICSEARCH_PORT', '9200'))
ELASTICSEARCH_INDEX = 'video_library'

# Initialize Elasticsearch client
es_client = None
if ELASTICSEARCH_ENABLED:
    try:
        from elasticsearch import Elasticsearch
        es_client = Elasticsearch(
            [f'http://{ELASTICSEARCH_HOST}:{ELASTICSEARCH_PORT}'],
            request_timeout=30
        )
        # Test connection
        if es_client.ping():
            print("✅ Elasticsearch connection successful")
        else:
            print("⚠️  Elasticsearch connection failed, falling back to basic search")
            es_client = None
    except ImportError:
        print("⚠️  Elasticsearch library not installed. Install with: pip install elasticsearch")
        print("   Falling back to basic search functionality")
        es_client = None
    except Exception as e:
        print(f"⚠️  Elasticsearch connection error: {e}")
        print("   Falling back to basic search functionality")
        es_client = None
else:
    print("ℹ️  Elasticsearch disabled, using basic search")

# YouTube API Configuration
# Get API key from environment variable for security
YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY')
YOUTUBE_CHANNEL_ID = os.getenv('YOUTUBE_CHANNEL_ID')  # Optional: Set to fetch from specific channel

def get_youtube_channel_id(api_key, channel_username=None):
    """Get channel ID from username or use default channel"""
    if not channel_username:
        # Try to get channel ID from API key's associated channel
        # For now, we'll need the user to provide channel ID or username
        return None
    
    try:
        url = 'https://www.googleapis.com/youtube/v3/channels'
        params = {
            'part': 'id',
            'forUsername': channel_username,
            'key': api_key
        }
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get('items'):
                return data['items'][0]['id']
    except Exception as e:
        print(f"Error getting channel ID: {e}")
    return None

def fetch_youtube_videos(api_key, channel_id=None, max_results=50):
    """Fetch videos from YouTube channel using API"""
    videos = []
    
    try:
        # Use search API - if channel_id provided, filter by it
        url = 'https://www.googleapis.com/youtube/v3/search'
        params = {
            'part': 'snippet',
            'type': 'video',
            'maxResults': min(max_results, 50),  # YouTube API limit is 50 per request
            'order': 'date',
            'key': api_key
        }
        
        # If channel_id provided, filter by it
        if channel_id:
            params['channelId'] = channel_id
        else:
            # If no channel_id, we'll search for popular videos or need to get channel ID from username
            # For now, search without channel filter (will get general results)
            # User should set YOUTUBE_CHANNEL_ID environment variable
            print("⚠️  No channel_id provided. Set YOUTUBE_CHANNEL_ID environment variable or videos will be from general search.")
        
        # Fetch videos
        next_page_token = None
        total_fetched = 0
        
        while total_fetched < max_results:
            if next_page_token:
                params['pageToken'] = next_page_token
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code != 200:
                print(f"❌ YouTube API error: {response.status_code} - {response.text}")
                break
            
            data = response.json()
            
            # Get video details (duration, etc.) for each video
            video_ids = [item['id']['videoId'] for item in data.get('items', [])]
            
            if video_ids:
                # Fetch detailed video information
                details_url = 'https://www.googleapis.com/youtube/v3/videos'
                details_params = {
                    'part': 'snippet,contentDetails,statistics',
                    'id': ','.join(video_ids),
                    'key': api_key
                }
                
                details_response = requests.get(details_url, params=details_params, timeout=10)
                if details_response.status_code == 200:
                    details_data = details_response.json()
                    
                    # Map YouTube videos to our video structure
                    for idx, item in enumerate(data.get('items', [])):
                        video_id = item['id']['videoId']
                        snippet = item.get('snippet', {})
                        
                        # Find corresponding details
                        video_details = None
                        for detail in details_data.get('items', []):
                            if detail['id'] == video_id:
                                video_details = detail
                                break
                        
                        if video_details:
                            content_details = video_details.get('contentDetails', {})
                            duration_iso = content_details.get('duration', 'PT0S')
                            
                            # Convert ISO 8601 duration to seconds
                            import re
                            duration_match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', duration_iso)
                            duration_seconds = 0
                            if duration_match:
                                hours = int(duration_match.group(1) or 0)
                                minutes = int(duration_match.group(2) or 0)
                                seconds = int(duration_match.group(3) or 0)
                                duration_seconds = hours * 3600 + minutes * 60 + seconds
                            
                            # Create video object matching our structure
                            # Generate a numeric content_id from YouTube video ID hash
                            content_id = abs(hash(video_id)) % 1000000  # Use hash to get numeric ID
                            video = {
                                'content_id': content_id,
                                'youtube_id': video_id,
                                'title': snippet.get('title', 'Untitled'),
                                'description': snippet.get('description', ''),
                                'file_path': f'youtube:{video_id}',  # Special marker for YouTube videos
                                'hls_url': None,  # YouTube doesn't use HLS directly
                                'youtube_url': f'https://www.youtube.com/watch?v={video_id}',
                                'youtube_embed_url': f'https://www.youtube.com/embed/{video_id}',
                                'thumbnail': snippet.get('thumbnails', {}).get('high', {}).get('url', ''),
                                'space_name': snippet.get('channelTitle', 'YouTube Channel'),
                                'duration': duration_seconds,
                                'published_at': snippet.get('publishedAt', ''),
                                'view_count': int(video_details.get('statistics', {}).get('viewCount', 0)),
                                'like_count': int(video_details.get('statistics', {}).get('likeCount', 0)),
                                'hash_filename': None,
                                'supports_adaptive': False,
                                'type': 'youtube'
                            }
                            videos.append(video)
                            total_fetched += 1
            
            # Check for next page
            next_page_token = data.get('nextPageToken')
            if not next_page_token or total_fetched >= max_results:
                break
        
        print(f"✅ Fetched {len(videos)} videos from YouTube")
        return videos
        
    except Exception as e:
        print(f"❌ Error fetching YouTube videos: {e}")
        import traceback
        traceback.print_exc()
        return []

# Load video data
def load_video_data():
    """Load video metadata from YouTube API"""
    # Fetch videos from YouTube
    channel_id = os.getenv('YOUTUBE_CHANNEL_ID')
    max_results = int(os.getenv('YOUTUBE_MAX_RESULTS', '100'))
    
    videos = fetch_youtube_videos(YOUTUBE_API_KEY, channel_id, max_results)
    
    if not videos:
        print("⚠️  No videos fetched from YouTube, trying fallback...")
        # Fallback to JSON file if YouTube fails
        try:
            with open('all_video_metadata_from_database.json', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            print("⚠️  Fallback JSON file not found")
            return []
    
    return videos

def categorize_by_space(videos):
    """Group videos by space name"""
    spaces = defaultdict(list)
    for video in videos:
        space_name = video.get('space_name', 'Unknown Space')
        if not space_name or space_name == '':
            space_name = 'Unknown Space'
        spaces[space_name].append(video)
    return dict(spaces)

def fuzzy_match_ratio(str1, str2):
    """Calculate similarity ratio between two strings (0-1)"""
    return SequenceMatcher(None, str1.lower(), str2.lower()).ratio()

def create_url_slug(text):
    """Create URL-friendly slug from text"""
    if not text:
        return ''
    # Convert to lowercase
    slug = text.lower()
    # Replace spaces and special characters with hyphens
    slug = re.sub(r'[^\w\s-]', '', slug)  # Remove special chars except hyphens
    slug = re.sub(r'[-\s]+', '-', slug)  # Replace spaces and multiple hyphens with single hyphen
    slug = slug.strip('-')  # Remove leading/trailing hyphens
    return slug

def find_video_by_slug(space_name_slug, video_name_slug):
    """Find video by space name and video name slugs"""
    space_name_slug = urllib.parse.unquote(space_name_slug).lower().strip()
    video_name_slug = urllib.parse.unquote(video_name_slug).lower().strip()
    
    print(f"🔍 find_video_by_slug: space='{space_name_slug}', video='{video_name_slug}'")
    
    # Try exact match first
    for video in all_videos:
        video_space_slug = create_url_slug(video.get('space_name', '')).lower().strip()
        video_title_slug = create_url_slug(video.get('title', '')).lower().strip()
        
        if video_space_slug == space_name_slug and video_title_slug == video_name_slug:
            print(f"✅ Exact match found: id={video.get('content_id')}")
            return video
    
    # Try partial match (space name must match, video title can be partial)
    for video in all_videos:
        video_space_slug = create_url_slug(video.get('space_name', '')).lower().strip()
        video_title_slug = create_url_slug(video.get('title', '')).lower().strip()
        
        # Space name must match exactly or be very similar
        if video_space_slug == space_name_slug or space_name_slug in video_space_slug or video_space_slug in space_name_slug:
            # Video title should contain the slug or vice versa
            if video_name_slug in video_title_slug or video_title_slug in video_name_slug:
                print(f"✅ Partial match found: id={video.get('content_id')}, space='{video_space_slug}', title='{video_title_slug[:50]}...'")
                return video
    
    # Try fuzzy match if exact match fails
    best_match = None
    best_score = 0.0
    
    for video in all_videos:
        video_space_slug = create_url_slug(video.get('space_name', '')).lower().strip()
        video_title_slug = create_url_slug(video.get('title', '')).lower().strip()
        
        space_score = fuzzy_match_ratio(video_space_slug, space_name_slug)
        title_score = fuzzy_match_ratio(video_title_slug, video_name_slug)
        
        # Combined score (both must match reasonably well)
        combined_score = (space_score * 0.4) + (title_score * 0.6)
        
        if combined_score > best_score and combined_score > 0.5:  # Lower threshold to 50%
            best_score = combined_score
            best_match = video
    
    if best_match:
        print(f"✅ Fuzzy match found (score={best_score:.2f}): id={best_match.get('content_id')}")
    
    return best_match

def extract_text_from_html(html):
    """Extract plain text from HTML"""
    if not html:
        return ''
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', ' ', html)
    # Decode HTML entities
    text = text.replace('&nbsp;', ' ').replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
    # Clean up whitespace
    text = ' '.join(text.split())
    return text

def fuzzy_match_word(search_word, target_word, min_length=3):
    """Check if search word matches target word with typo tolerance"""
    if len(search_word) < min_length or len(target_word) < min_length:
        return search_word in target_word, 1.0 if search_word in target_word else 0.0
    
    # Exact match
    if search_word == target_word:
        return True, 1.0
    
    # Substring match
    if search_word in target_word or target_word in search_word:
        return True, 0.9
    
    # Fuzzy match
    ratio = fuzzy_match_ratio(search_word, target_word)
    # More lenient threshold for shorter words
    threshold = 0.6 if len(search_word) >= 5 else 0.5
    if ratio >= threshold:
        return True, ratio
    
    return False, 0.0

def fuzzy_search_videos(videos, search_term, threshold=0.5):
    """
    Perform fuzzy search on videos with typo tolerance.
    Returns list of (video, score, match_type) tuples sorted by relevance.
    """
    search_lower = search_term.lower().strip()
    search_words = [w for w in search_lower.split() if len(w) >= 2]
    results = []
    
    # Adjust threshold based on search term length
    if len(search_lower) < 4:
        threshold = 0.4  # More lenient for short searches
    elif len(search_lower) >= 10:
        threshold = 0.6  # Stricter for long searches
    
    for video in videos:
        title = video.get('title', '')
        description = video.get('description', '') or ''
        description_text = extract_text_from_html(description)
        
        title_lower = title.lower()
        desc_lower = description_text.lower()
        
        score = 0.0
        match_type = None
        
        # 1. Exact match in title (highest priority)
        if search_lower in title_lower:
            score = 1.0
            match_type = 'exact_title'
        
        # 2. All search words found in title (phrase match)
        elif search_words and all(any(fuzzy_match_word(sw, tw)[0] for tw in title_lower.split()) for sw in search_words):
            # Calculate average match quality
            word_scores = []
            for sw in search_words:
                best_score = 0.0
                for tw in title_lower.split():
                    _, word_score = fuzzy_match_word(sw, tw)
                    best_score = max(best_score, word_score)
                word_scores.append(best_score)
            avg_score = sum(word_scores) / len(word_scores) if word_scores else 0.0
            score = max(score, min(avg_score * 0.95, 1.0))
            match_type = 'phrase_title'
        
        # 3. Fuzzy match entire search term against title
        elif len(search_lower) >= 3:
            title_ratio = fuzzy_match_ratio(search_lower, title_lower)
            if title_ratio >= threshold:
                score = max(score, title_ratio * 0.85)
                match_type = 'fuzzy_title'
            
            # 4. Check if search term is similar to any significant word in title
            for word in title_lower.split():
                if len(word) >= 3:
                    matched, word_score = fuzzy_match_word(search_lower, word)
                    if matched:
                        score = max(score, word_score * 0.75)
                        match_type = 'fuzzy_word_title'
                        break
        
        # 5. Check description if title score is low
        if score < 0.6:
            if search_lower in desc_lower:
                score = max(score, 0.65)
                match_type = 'exact_description'
            elif search_words and all(any(fuzzy_match_word(sw, tw)[0] for tw in desc_lower.split()[:50]) for sw in search_words):
                score = max(score, 0.55)
                match_type = 'phrase_description'
            elif len(search_lower) >= 3:
                # Check first 300 chars of description for performance
                desc_sample = desc_lower[:300]
                desc_ratio = fuzzy_match_ratio(search_lower, desc_sample)
                if desc_ratio >= threshold:
                    score = max(score, desc_ratio * 0.45)
                    match_type = 'fuzzy_description'
        
        # 6. Partial word matches (lower priority)
        if score < 0.4 and search_words:
            title_matches = sum(1 for sw in search_words for tw in title_lower.split() if fuzzy_match_word(sw, tw)[0])
            desc_matches = sum(1 for sw in search_words for tw in desc_lower.split()[:30] if fuzzy_match_word(sw, tw)[0])
            total_matches = title_matches + desc_matches
            if total_matches > 0:
                score = max(score, (total_matches / len(search_words)) * 0.35)
                match_type = 'partial'
        
        if score > 0:
            results.append((video, score, match_type))
    
    # Sort by score (descending), then by date
    results.sort(key=lambda x: (x[1], x[0].get('created_at', '')), reverse=True)
    return results

def create_elasticsearch_index():
    """Create Elasticsearch index with proper mapping for fuzzy search"""
    if not es_client:
        return False
    
    try:
        # Check if index exists
        if es_client.indices.exists(index=ELASTICSEARCH_INDEX):
            print(f"✅ Elasticsearch index '{ELASTICSEARCH_INDEX}' already exists")
            return True
        
        # Create index with mapping for fuzzy search
        settings = {
            "analysis": {
                "analyzer": {
                    "fuzzy_analyzer": {
                        "type": "custom",
                        "tokenizer": "standard",
                        "filter": [
                            "lowercase",
                            "asciifolding",
                            "fuzzy_filter"
                        ]
                    }
                },
                "filter": {
                    "fuzzy_filter": {
                        "type": "edge_ngram",
                        "min_gram": 2,
                        "max_gram": 15
                    }
                }
            }
        }
        
        mappings = {
            "properties": {
                "content_id": {"type": "integer"},
                "title": {
                    "type": "text",
                    "analyzer": "fuzzy_analyzer",
                    "fields": {
                        "keyword": {"type": "keyword"}
                    }
                },
                "description": {
                    "type": "text",
                    "analyzer": "fuzzy_analyzer"
                },
                "space_name": {
                    "type": "text",
                    "fields": {
                        "keyword": {"type": "keyword"}
                    }
                },
                "created_at": {"type": "date", "format": "strict_date_optional_time||epoch_millis"},
                "updated_at": {"type": "date", "format": "strict_date_optional_time||epoch_millis"},
                "file_path": {"type": "keyword"},
                "thumbnail": {"type": "keyword"},
                "hls_url": {"type": "keyword"}
            }
        }
        
        # Create index - compatible with Elasticsearch 8.x API
        es_client.indices.create(
            index=ELASTICSEARCH_INDEX,
            settings=settings,
            mappings=mappings
        )
        print(f"✅ Created Elasticsearch index '{ELASTICSEARCH_INDEX}' with fuzzy search mapping")
        return True
    except Exception as e:
        print(f"❌ Error creating Elasticsearch index: {e}")
        return False

def index_videos_in_elasticsearch(videos):
    """Index all videos in Elasticsearch"""
    if not es_client:
        return False
    
    try:
        if not create_elasticsearch_index():
            return False
        
        # Delete existing documents (for re-indexing)
        try:
            es_client.delete_by_query(
                index=ELASTICSEARCH_INDEX,
                query={"match_all": {}}
            )
        except Exception:
            pass  # Index might be empty
        
        # Index videos in batches
        batch_size = 100
        indexed_count = 0
        
        for i in range(0, len(videos), batch_size):
            batch = videos[i:i + batch_size]
            body = []
            
            for video in batch:
                # Prepare document for indexing
                doc = {
                    "content_id": video.get('content_id'),
                    "title": video.get('title', ''),
                    "description": video.get('description', '') or '',
                    "space_name": video.get('space_name', 'Unknown Space'),
                    "file_path": video.get('file_path', ''),
                    "thumbnail": video.get('thumbnail', ''),
                    "hls_url": video.get('hls_url', ''),
                    "created_at": video.get('created_at', ''),
                    "updated_at": video.get('updated_at', '')
                }
                
                body.append({
                    "index": {
                        "_index": ELASTICSEARCH_INDEX,
                        "_id": str(video.get('content_id'))
                    }
                })
                body.append(doc)
            
            if body:
                es_client.bulk(body=body)
                indexed_count += len(batch)
                print(f"   Indexed {indexed_count}/{len(videos)} videos...", end='\r')
        
        print(f"\n✅ Successfully indexed {indexed_count} videos in Elasticsearch")
        
        # Refresh index to make documents searchable
        es_client.indices.refresh(index=ELASTICSEARCH_INDEX)
        return True
    except Exception as e:
        print(f"❌ Error indexing videos in Elasticsearch: {e}")
        return False

# Load data on startup
try:
    print("Loading video data...")
    all_videos = load_video_data()
    spaces_dict = categorize_by_space(all_videos)
    print(f"✅ Loaded {len(all_videos)} videos across {len(spaces_dict)} spaces")
    
    # Index videos in Elasticsearch if enabled
    if es_client:
        print("\nIndexing videos in Elasticsearch for intelligent search...")
        index_videos_in_elasticsearch(all_videos)
except Exception as e:
    print(f"❌ Error loading video data: {e}")
    all_videos = []
    spaces_dict = {}

# Add friendly URL route BEFORE the index route to ensure it's matched first
# This route must come before other routes that might catch it
@app.route('/videolibrary/<space_name>/<video_name>')
@app.route('/<space_name>/<video_name>')  # Also support without /videolibrary prefix
def video_with_timestops_friendly(space_name, video_name):
    """Video page with friendly URL: /videolibrary/<space_name>/<video_name>"""
    base_path = request.headers.get('X-Forwarded-Prefix', '')
    
    # Debug: Log the request
    print(f"🎬 Friendly URL route hit: path='{request.path}', space='{space_name}', video='{video_name}'")
    
    # Find video by space name and video name slugs
    video = find_video_by_slug(space_name, video_name)
    
    if not video:
        # Debug: Try to find what videos exist with similar names
        print(f"❌ Video not found. Searching for similar matches...")
        matches_found = []
        for v in all_videos:
            space_slug = create_url_slug(v.get('space_name', '')).lower()
            title_slug = create_url_slug(v.get('title', '')).lower()
            if 'cchmc' in space_slug or 'quad' in title_slug or 'adec' in title_slug:
                matches_found.append({
                    'id': v.get('content_id'),
                    'space': space_slug,
                    'title': title_slug[:80]
                })
                if len(matches_found) >= 5:
                    break
        
        if matches_found:
            print(f"  Found {len(matches_found)} similar videos:")
            for m in matches_found:
                print(f"    ID {m['id']}: space='{m['space']}', title='{m['title']}'")
        
        return jsonify({
            'error': 'Video not found',
            'searched_space': space_name,
            'searched_video': video_name,
            'similar_matches': matches_found[:3] if matches_found else []
        }), 404
    
    # Use the same logic as video_with_timestops but with the found video
    video_id = video.get('content_id')
    
    # Get video URL - use proxy endpoint for reliable streaming
    video_url = video.get('hls_url')
    if not video_url:
        # Use proxy endpoint which handles CloudFront signed URLs
        if base_path:
            video_url = f"{base_path}/api/video/proxy/{video_id}"
        else:
            video_url = f"/api/video/proxy/{video_id}"
    elif video_url.startswith('/'):
        video_url = f"{base_path}{video_url}" if base_path else video_url
    elif not video_url.startswith('http'):
        if base_path:
            video_url = f"{base_path}/api/video/proxy/{video_id}"
        else:
            video_url = f"/api/video/proxy/{video_id}"
    
    # Get timestops from database
    timestops = []
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
        cur.execute("""
            SELECT timestamp, time_formatted, label, summary, type
            FROM video_timestops
            WHERE content_id = %s
            ORDER BY timestamp
        """, (video_id,))
        
        for row in cur.fetchall():
            timestops.append({
                'timestamp': row[0],
                'time_formatted': row[1],
                'label': row[2],
                'summary': row[3],
                'type': row[4]
            })
        
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error fetching timestops: {e}")
        # Try file fallback
        timestops_file = os.path.join(BASE_DIR, 'video_timestops', f'{video_id}_timestops.json')
        if os.path.exists(timestops_file):
            with open(timestops_file, 'r') as f:
                data = json.load(f)
                timestops = data.get('timestops', [])
    
    # Get transcription
    transcription = None
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
        cur.execute("""
            SELECT transcription_text, transcription_json, duration, language, word_count
            FROM video_transcriptions
            WHERE content_id = %s
            LIMIT 1
        """, (video_id,))
        
        row = cur.fetchone()
        if row:
            transcription = {
                'text': row[0],
                'json': row[1] if row[1] else None,
                'duration': row[2],
                'language': row[3],
                'word_count': row[4]
            }
        
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error fetching transcription: {e}")
        # Try file fallback
        transcription_file = os.path.join(BASE_DIR, 'video_transcriptions', f'{video_id}_transcription.json')
        if os.path.exists(transcription_file):
            with open(transcription_file, 'r') as f:
                data = json.load(f)
                transcription_data = data.get('transcription', {})
                transcription = {
                    'text': transcription_data.get('text', ''),
                    'json': transcription_data if transcription_data else None,
                    'duration': transcription_data.get('duration'),
                    'language': transcription_data.get('language'),
                    'word_count': transcription_data.get('word_count')
                }
    
    # Get related videos (from same space, excluding current video)
    related_videos = []
    current_space = video.get('space_name', '')
    for v in all_videos:
        if (v.get('content_id') != video_id and 
            v.get('space_name', '') == current_space and 
            v.get('content_id') is not None):
            related_videos.append(v)
            if len(related_videos) >= 6:  # Limit to 6 related videos
                break
    
    # If not enough videos from same space, add videos from other spaces
    if len(related_videos) < 6:
        for v in all_videos:
            if (v.get('content_id') != video_id and 
                v.get('content_id') is not None and
                v not in related_videos):
                related_videos.append(v)
                if len(related_videos) >= 6:
                    break
    
    # Determine if request is HTTPS (check X-Forwarded-Proto header from Nginx)
    is_https = request.headers.get('X-Forwarded-Proto', 'http') == 'https' or request.is_secure

    return render_template('video_with_timestops.html',
                          video=video,
                          timestops=timestops,
                          transcription=transcription,
                          related_videos=related_videos,
                          base_path=base_path,
                          is_https=is_https)

@app.route('/')
def index():
    """Main library page"""
    base_path = request.headers.get('X-Forwarded-Prefix', '')
    return render_template('library.html', base_path=base_path.rstrip('/') if base_path else '')

@app.route('/hub/cchmc')
@app.route('/videolibrary/hub/cchmc')
def cchmc_hub():
    """CCHMC Hub page listing all divisions"""
    base_path = request.headers.get('X-Forwarded-Prefix', '')
    # If accessed via /videolibrary path locally, set base_path
    if request.path.startswith('/videolibrary') and not base_path:
        base_path = '/videolibrary'
    
    # Define CCHMC divisions and their space names (matching actual space names in database)
    divisions = [
        {
            'name': 'CCHMC Pediatric Surgery',
            'space_name': 'CCHMC Pediatric Surgery',
            'slug': 'cchmc-pediatric-surgery',
            'has_microsite': True,
            'icon': '⚕️'
        },
        {
            'name': 'StayCurrentMD',
            'space_name': 'StayCurrentMD',
            'slug': None,
            'has_microsite': False,
            'icon': '🎓'
        },
        {
            'name': 'StayCurrentMD Español',
            'space_name': 'StayCurrent Espanol',
            'slug': None,
            'has_microsite': False,
            'icon': '🌎'
        },
        {
            'name': 'CCHMC PAG',
            'space_name': 'CCHMC PAG',
            'slug': None,
            'has_microsite': False,
            'icon': '👥'
        },
        {
            'name': 'CCHMC Neurosurgery',
            'space_name': 'CCHMC Neurosurgery',
            'slug': None,
            'has_microsite': False,
            'icon': '🧠'
        },
        {
            'name': 'CCHMC Division of Orthopaedic Surgery',
            'space_name': 'CCHMC Division of Orthopaedic Surgery',
            'slug': None,
            'has_microsite': False,
            'icon': '🦴'
        },
        {
            'name': 'SIM Center',
            'space_name': 'SIM Center',
            'slug': None,
            'has_microsite': False,
            'icon': '🎯'
        },
        {
            'name': 'StayCurrent Forums',
            'space_name': 'StayCurrent Forums',
            'slug': None,
            'has_microsite': False,
            'icon': '💬'
        },
        {
            'name': 'CCHMC Heart Institute',
            'space_name': 'CCHMC Heart Institute',
            'slug': None,
            'has_microsite': False,
            'icon': '❤️'
        }
    ]
    
    # Count videos for each division
    for division in divisions:
        space_name = division['space_name']
        division['video_count'] = len(spaces_dict.get(space_name, []))
    
    return render_template(
        'cchmc_hub.html',
        base_path=base_path.rstrip('/') if base_path else '',
        divisions=divisions
    )

@app.route('/microsite/<slug>')
def microsite(slug):
    """Microsite page for individual doctors/surgeons"""
    base_path = request.headers.get('X-Forwarded-Prefix', '')
    
    # Load microsite configuration
    config_file = os.path.join(BASE_DIR, 'microsites_config.json')
    if not os.path.exists(config_file):
        return jsonify({'error': 'Microsite configuration not found'}), 404
    
    with open(config_file, 'r') as f:
        config = json.load(f)
    
    if slug not in config.get('microsites', {}):
        return jsonify({'error': 'Microsite not found'}), 404
    
    microsite_config = config['microsites'][slug]
    
    # Filter videos for this microsite
    search_terms = microsite_config.get('search_terms', [])
    space_filter = microsite_config.get('space_filter', '')
    microsite_videos = []
    
    for video in all_videos:
        # Check space filter first (if specified)
        if space_filter:
            if video.get('space_name', '') == space_filter:
                microsite_videos.append(video)
                continue
        
        # Check search terms (in title, description, or space name)
        if search_terms:
            title = video.get('title', '').lower()
            description = video.get('description', '').lower() if video.get('description') else ''
            space_name = video.get('space_name', '').lower()
            text = f"{title} {description} {space_name}"
            
            if any(term.lower() in text for term in search_terms):
                microsite_videos.append(video)
    
    # Categorize videos
    categories = categorize_microsite_videos(microsite_videos, microsite_config.get('categories', {}))
    
    # Calculate total likes and shares
    total_likes = sum(video.get('likes', 0) for video in microsite_videos)
    total_shares = sum(video.get('shares', 0) for video in microsite_videos)
    
    # If likes/shares not in data, calculate from views or use defaults
    if total_likes == 0 and total_shares == 0:
        # Estimate based on video count (rough engagement metrics)
        # You can replace this with actual data when available
        total_likes = len(microsite_videos) * 12  # Average 12 likes per video
        total_shares = len(microsite_videos) * 3   # Average 3 shares per video
    
    return render_template(
        'microsite.html',
        base_path=base_path.rstrip('/') if base_path else '',
        microsite=microsite_config,
        categories=categories,
        total_videos=len(microsite_videos),
        total_likes=total_likes,
        total_shares=total_shares
    )

def categorize_microsite_videos(videos, category_config):
    """Categorize videos based on microsite configuration"""
    categories = defaultdict(list)
    
    for video in videos:
        title = video.get('title', '').lower()
        description = video.get('description', '').lower() if video.get('description') else ''
        space = video.get('space_name', '')
        text = f"{title} {description}"
        
        categorized = False
        
        for cat_name, cat_config in category_config.items():
            keywords = cat_config.get('keywords', [])
            space_filter = cat_config.get('space_filter', '')
            
            # Check space filter first
            if space_filter and space == space_filter:
                categories[cat_name].append(video)
                categorized = True
                break
            
            # Check keywords
            if any(keyword.lower() in text for keyword in keywords):
                categories[cat_name].append(video)
                categorized = True
                break
        
        # Don't create "All Videos" category - it's handled separately in template
        # Videos that don't match any category will just not appear in category filters
    
    # Format for template
    result = {}
    for cat_name, cat_videos in categories.items():
        cat_config = category_config.get(cat_name, {})
        result[cat_name] = {
            'videos': cat_videos[:24],  # Limit for initial display
            'total': len(cat_videos),
            'icon': cat_config.get('icon', '📹')
        }
    
    return result

@app.route('/api/microsite/<slug>/videos')
def get_microsite_videos(slug):
    """API endpoint to get videos for a microsite"""
    # Load microsite configuration
    config_file = os.path.join(BASE_DIR, 'microsites_config.json')
    if not os.path.exists(config_file):
        return jsonify({'error': 'Microsite configuration not found'}), 404
    
    with open(config_file, 'r') as f:
        config = json.load(f)
    
    if slug not in config.get('microsites', {}):
        return jsonify({'error': 'Microsite not found'}), 404
    
    microsite_config = config['microsites'][slug]
    search_terms = microsite_config.get('search_terms', [])
    space_filter = microsite_config.get('space_filter', '')
    
    # Filter videos
    microsite_videos = []
    for video in all_videos:
        # Check space filter first (if specified)
        if space_filter:
            if video.get('space_name', '') == space_filter:
                microsite_videos.append(video)
                continue
        
        # Check search terms (in title, description, or space name)
        if search_terms:
            title = video.get('title', '').lower()
            description = video.get('description', '').lower() if video.get('description') else ''
            space_name = video.get('space_name', '').lower()
            text = f"{title} {description} {space_name}"
            
            if any(term.lower() in text for term in search_terms):
                microsite_videos.append(video)
    
    # Get category filter
    category = request.args.get('category', '')
    if category:
        categories = categorize_microsite_videos(microsite_videos, microsite_config.get('categories', {}))
        if category in categories:
            microsite_videos = categories[category]['videos']
    
    # Pagination
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 24, type=int)
    search = request.args.get('search', '', type=str)
    
    # Filter by search
    if search:
        search_lower = search.lower()
        microsite_videos = [
            v for v in microsite_videos
            if search_lower in v.get('title', '').lower() or
               search_lower in (v.get('description') or '').lower()
        ]
    
    # Sort by date
    microsite_videos = sorted(
        microsite_videos,
        key=lambda x: x.get('created_at', ''),
        reverse=True
    )
    
    # Paginate
    total = len(microsite_videos)
    total_pages = (total + per_page - 1) // per_page  # Ceiling division
    start = (page - 1) * per_page
    end = start + per_page
    paginated_videos = microsite_videos[start:end]
    
    # Format for response
    video_list = []
    for video in paginated_videos:
        video_list.append({
            'id': video.get('content_id'),
            'title': video.get('title', 'Untitled'),
            'description': video.get('description', ''),
            'file_path': video.get('file_path', ''),
            'thumbnail': video.get('thumbnail', ''),
            'hls_url': video.get('hls_url', ''),
            'created_at': video.get('created_at', '')[:10] if video.get('created_at') else 'Unknown date'
        })
    
    return jsonify({
        'videos': video_list,
        'total': total,
        'page': page,
        'per_page': per_page,
        'total_pages': total_pages,
        'has_next': page < total_pages,
        'has_prev': page > 1
    })

@app.route('/api/spaces')
def get_spaces():
    """API endpoint to get all spaces"""
    spaces_list = []
    for space_name, videos in sorted(spaces_dict.items(), key=lambda x: len(x[1]), reverse=True):
        spaces_list.append({
            'name': space_name,
            'video_count': len(videos),
            'videos_with_descriptions': len([v for v in videos if v.get('description')])
        })
    return jsonify({
        'spaces': spaces_list,
        'total_videos': len(all_videos),
        'total_spaces': len(spaces_dict)
    })

@app.route('/api/spaces/<space_name>/videos')
def get_space_videos(space_name):
    """API endpoint to get videos for a specific space"""
    # Decode space name from URL
    space_name = urllib.parse.unquote(space_name)
    
    if space_name not in spaces_dict:
        return jsonify({'error': 'Space not found'}), 404
    
    videos = spaces_dict[space_name]
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 24, type=int)
    search = request.args.get('search', '', type=str)
    
    # Filter by search if provided
    filtered_videos = videos
    if search:
        search_lower = search.lower()
        filtered_videos = [
            v for v in videos
            if search_lower in v.get('title', '').lower() or
               search_lower in (v.get('description') or '').lower()
        ]
    
    # Sort by date (newest first)
    filtered_videos = sorted(
        filtered_videos,
        key=lambda x: x.get('created_at', ''),
        reverse=True
    )
    
    # Paginate
    total = len(filtered_videos)
    start = (page - 1) * per_page
    end = start + per_page
    paginated_videos = filtered_videos[start:end]
    
    # Format videos for response
    video_list = []
    for video in paginated_videos:
        video_list.append({
            'id': video.get('content_id'),
            'title': video.get('title', 'Untitled'),
            'description': video.get('description', ''),
            'file_path': video.get('file_path', ''),
            'thumbnail': video.get('thumbnail', ''),
            'hls_url': video.get('hls_url', ''),
            'created_at': video.get('created_at', '')[:10] if video.get('created_at') else 'Unknown date',
            'updated_at': video.get('updated_at', '')[:10] if video.get('updated_at') else 'Unknown date',
            'space_name': video.get('space_name', 'Unknown Space')
        })
    
    return jsonify({
        'videos': video_list,
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': total,
            'total_pages': (total + per_page - 1) // per_page
        },
        'space_name': space_name
    })

def get_timestops_for_videos(video_ids: List[int]) -> Dict[int, List[Dict]]:
    """Get timestops for multiple videos from database"""
    if not video_ids:
        return {}
    
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
        
        # Search timestops that match the search term
        placeholders = ','.join(['%s'] * len(video_ids))
        cur.execute(f"""
            SELECT content_id, timestamp, time_formatted, label, summary, type
            FROM video_timestops
            WHERE content_id IN ({placeholders})
            ORDER BY content_id, timestamp
        """, tuple(video_ids))
        
        timestops_dict = {}
        for row in cur.fetchall():
            video_id = row[0]
            if video_id not in timestops_dict:
                timestops_dict[video_id] = []
            timestops_dict[video_id].append({
                'timestamp': row[1],
                'time_formatted': row[2],
                'label': row[3],
                'summary': row[4],
                'type': row[5]
            })
        
        cur.close()
        conn.close()
        return timestops_dict
    except Exception as e:
        print(f"⚠️  Error fetching timestops: {e}")
        return {}

def search_timestops_in_database(search_term: str) -> List[int]:
    """Search timestops in database and return matching video IDs"""
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
        
        # Full-text search in timestops
        cur.execute("""
            SELECT DISTINCT content_id
            FROM video_timestops
            WHERE 
                to_tsvector('english', label || ' ' || COALESCE(summary, '')) @@ plainto_tsquery('english', %s)
            ORDER BY content_id
        """, (search_term,))
        
        video_ids = [row[0] for row in cur.fetchall()]
        
        cur.close()
        conn.close()
        return video_ids
    except Exception as e:
        print(f"⚠️  Error searching timestops: {e}")
        return []

def search_transcriptions_in_database(search_term: str) -> List[int]:
    """Search transcriptions in database and return matching video IDs"""
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
        
        # Full-text search in transcriptions
        cur.execute("""
            SELECT DISTINCT content_id
            FROM video_transcriptions
            WHERE 
                to_tsvector('english', transcription_text) @@ plainto_tsquery('english', %s)
            ORDER BY content_id
        """, (search_term,))
        
        video_ids = [row[0] for row in cur.fetchall()]
        
        cur.close()
        conn.close()
        return video_ids
    except Exception as e:
        print(f"⚠️  Error searching transcriptions: {e}")
        return []

@app.route('/api/search')
def search_all_videos():
    """API endpoint to search videos across all spaces with timestop support"""
    search = request.args.get('search', '', type=str)
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 24, type=int)
    
    if not search:
        return jsonify({
            'videos': [],
            'pagination': {
                'page': 1,
                'per_page': per_page,
                'total': 0,
                'total_pages': 0
            }
        })
    
    # Search timestops and transcriptions in database
    timestop_video_ids = search_timestops_in_database(search)
    transcription_video_ids = search_transcriptions_in_database(search)
    
    # Combine all video IDs from timestops and transcriptions
    all_matching_video_ids = set(timestop_video_ids + transcription_video_ids)
    
    timestop_videos = {}
    if all_matching_video_ids:
        # Get video details for timestop/transcription matches
        for video in all_videos:
            if video.get('content_id') in all_matching_video_ids:
                timestop_videos[video.get('content_id')] = video
    
    # Use Elasticsearch if available, otherwise fall back to basic search
    if es_client:
        try:
            # Elasticsearch query with fuzzy matching
            query = {
                "bool": {
                    "should": [
                        {
                            "match": {
                                "title": {
                                    "query": search,
                                    "fuzziness": "AUTO",  # Automatic fuzziness based on term length
                                    "boost": 3.0  # Title matches are more important
                                }
                            }
                        },
                        {
                            "match": {
                                "description": {
                                    "query": search,
                                    "fuzziness": "AUTO",
                                    "boost": 1.0
                                }
                            }
                        },
                        {
                            "match_phrase": {
                                "title": {
                                    "query": search,
                                    "boost": 5.0  # Exact phrase matches in title are highest priority
                                }
                            }
                        },
                        {
                            "match_phrase": {
                                "description": {
                                    "query": search,
                                    "boost": 2.0
                                }
                            }
                        }
                    ],
                    "minimum_should_match": 1
                }
            }
            
            # Execute search
            from_index = (page - 1) * per_page
            response = es_client.search(
                index=ELASTICSEARCH_INDEX,
                query=query,
                sort=[
                    {"created_at": {"order": "desc"}},
                    "_score"
                ],
                from_=from_index,
                size=per_page
            )
            
            # Extract results
            total = response['hits']['total']['value'] if isinstance(response['hits']['total'], dict) else response['hits']['total']
            hits = response['hits']['hits']
            
            # Format videos for response
            video_list = []
            video_ids_from_search = []
            for hit in hits:
                source = hit['_source']
                video_id = source.get('content_id')
                video_ids_from_search.append(video_id)
                video_list.append({
                    'id': video_id,
                    'title': source.get('title', 'Untitled'),
                    'description': source.get('description', ''),
                    'file_path': source.get('file_path', ''),
                    'thumbnail': source.get('thumbnail', ''),
                    'hls_url': source.get('hls_url', ''),
                    'created_at': source.get('created_at', '')[:10] if source.get('created_at') else 'Unknown date',
                    'updated_at': source.get('updated_at', '')[:10] if source.get('updated_at') else 'Unknown date',
                    'space_name': source.get('space_name', 'Unknown Space'),
                    'score': hit.get('_score', 0),
                    'match_type': 'metadata'
                })
            
            # Add timestop matches (if not already in results)
            for video_id in timestop_video_ids:
                if video_id not in video_ids_from_search and video_id in timestop_videos:
                    video = timestop_videos[video_id]
                    video_list.append({
                        'id': video_id,
                        'title': video.get('title', 'Untitled'),
                        'description': video.get('description', ''),
                        'file_path': video.get('file_path', ''),
                        'thumbnail': video.get('thumbnail', ''),
                        'hls_url': video.get('hls_url', ''),
                        'created_at': video.get('created_at', '')[:10] if video.get('created_at') else 'Unknown date',
                        'updated_at': video.get('updated_at', '')[:10] if video.get('updated_at') else 'Unknown date',
                        'space_name': video.get('space_name', 'Unknown Space'),
                        'score': 0.5,  # Lower score for timestop-only matches
                        'match_type': 'timestop'
                    })
            
            # Get timestops for all videos in results
            all_video_ids = [v['id'] for v in video_list]
            timestops_dict = get_timestops_for_videos(all_video_ids)
            
            # Filter and attach relevant timestops (matching search term)
            search_lower = search.lower()
            for video in video_list:
                video_id = video['id']
                if video_id in timestops_dict:
                    # Filter timestops that match search term
                    relevant_timestops = [
                        ts for ts in timestops_dict[video_id]
                        if search_lower in ts['label'].lower() or 
                           (ts.get('summary') and search_lower in ts['summary'].lower())
                    ]
                    video['relevant_timestops'] = relevant_timestops[:5]  # Limit to 5 most relevant
            
            # Re-sort by score (timestop matches + metadata matches)
            video_list.sort(key=lambda x: x['score'], reverse=True)
            
            # Paginate
            total = len(video_list)
            start = (page - 1) * per_page
            end = start + per_page
            paginated_videos = video_list[start:end]
            
            return jsonify({
                'videos': paginated_videos,
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': total,
                    'total_pages': (total + per_page - 1) // per_page
                },
                'search_term': search,
                'search_engine': 'elasticsearch',
                'timestop_matches': len(timestop_video_ids)
            })
        except Exception as e:
            print(f"⚠️  Elasticsearch search error: {e}, falling back to basic search")
            # Fall through to basic search
    
    # Fallback to fuzzy search if Elasticsearch is not available
    print(f"Using fuzzy search for: '{search}'")
    fuzzy_results = fuzzy_search_videos(all_videos, search, threshold=0.5)
    
    # Format results
    matched_videos = []
    for video, score, match_type in fuzzy_results:
        matched_videos.append({
            'video': video,
            'space_name': video.get('space_name', 'Unknown Space'),
            'score': score,
            'match_type': match_type
        })
    
    # Paginate
    total = len(matched_videos)
    start = (page - 1) * per_page
    end = start + per_page
    paginated_results = matched_videos[start:end]
    
    # Format videos for response
    video_list = []
    video_ids_from_search = []
    for item in paginated_results:
        video = item['video']
        video_id = video.get('content_id')
        video_ids_from_search.append(video_id)
        video_list.append({
            'id': video_id,
            'title': video.get('title', 'Untitled'),
            'description': video.get('description', ''),
            'file_path': video.get('file_path', ''),
            'thumbnail': video.get('thumbnail', ''),
            'hls_url': video.get('hls_url', ''),
            'created_at': video.get('created_at', '')[:10] if video.get('created_at') else 'Unknown date',
            'updated_at': video.get('updated_at', '')[:10] if video.get('updated_at') else 'Unknown date',
            'space_name': item['space_name'],
            'score': round(item['score'], 3),
            'match_type': 'metadata'
        })
    
    # Add timestop matches (if not already in results)
    for video_id in timestop_video_ids:
        if video_id not in video_ids_from_search and video_id in timestop_videos:
            video = timestop_videos[video_id]
            video_list.append({
                'id': video_id,
                'title': video.get('title', 'Untitled'),
                'description': video.get('description', ''),
                'file_path': video.get('file_path', ''),
                'thumbnail': video.get('thumbnail', ''),
                'hls_url': video.get('hls_url', ''),
                'created_at': video.get('created_at', '')[:10] if video.get('created_at') else 'Unknown date',
                'updated_at': video.get('updated_at', '')[:10] if video.get('updated_at') else 'Unknown date',
                'space_name': video.get('space_name', 'Unknown Space'),
                'score': 0.5,
                'match_type': 'timestop'
            })
    
    # Get timestops for all videos
    all_video_ids = [v['id'] for v in video_list]
    timestops_dict = get_timestops_for_videos(all_video_ids)
    
    # Filter and attach relevant timestops
    search_lower = search.lower()
    for video in video_list:
        video_id = video['id']
        if video_id in timestops_dict:
            relevant_timestops = [
                ts for ts in timestops_dict[video_id]
                if search_lower in ts['label'].lower() or 
                   (ts.get('summary') and search_lower in ts['summary'].lower())
            ]
            video['relevant_timestops'] = relevant_timestops[:5]
    
    # Re-sort by score
    video_list.sort(key=lambda x: x['score'], reverse=True)
    
    # Re-paginate after adding timestop matches
    total = len(video_list)
    start = (page - 1) * per_page
    end = start + per_page
    paginated_videos = video_list[start:end]
    
    return jsonify({
        'videos': paginated_videos,
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': total,
            'total_pages': (total + per_page - 1) // per_page
        },
        'search_term': search,
        'search_engine': 'fuzzy',
        'timestop_matches': len(timestop_video_ids)
    })

@app.route('/api/video/<int:video_id>')
def get_video(video_id):
    """API endpoint to get a specific video"""
    for video in all_videos:
        if video.get('content_id') == video_id:
            return jsonify(video)
    return jsonify({'error': 'Video not found'}), 404

@app.route('/api/video/<int:video_id>/timestops')
def get_video_timestops(video_id):
    """API endpoint to get AI-generated timestops for a video"""
    timestops_file = os.path.join(BASE_DIR, 'video_timestops', f'{video_id}_timestops.json')
    
    if os.path.exists(timestops_file):
        try:
            with open(timestops_file, 'r') as f:
                data = json.load(f)
                return jsonify({
                    'content_id': video_id,
                    'timestops': data.get('timestops', []),
                    'status': data.get('status', 'success'),
                    'processed_at': data.get('processed_at')
                })
        except Exception as e:
            return jsonify({'error': f'Error reading timestops: {str(e)}'}), 500
    else:
        return jsonify({
            'content_id': video_id,
            'timestops': [],
            'status': 'not_processed',
            'message': 'Timestops not yet generated for this video'
        })

@app.route('/api/video/<int:video_id>/transcription')
def get_video_transcription(video_id):
    """API endpoint to get transcription for a video"""
    transcription_file = os.path.join(BASE_DIR, 'video_transcriptions', f'{video_id}_transcription.json')
    
    if os.path.exists(transcription_file):
        try:
            with open(transcription_file, 'r') as f:
                data = json.load(f)
                return jsonify({
                    'content_id': video_id,
                    'transcription': data.get('transcription', {}),
                    'processed_at': data.get('processed_at')
                })
        except Exception as e:
            return jsonify({'error': f'Error reading transcription: {str(e)}'}), 500
    else:
        return jsonify({
            'content_id': video_id,
            'transcription': None,
            'status': 'not_processed',
            'message': 'Transcription not yet generated for this video'
        })

@app.route('/video/<int:video_id>')
@app.route('/videolibrary/video/<int:video_id>')
def video_with_timestops(video_id):
    """Video page with timestops, transcription, and search"""
    base_path = request.headers.get('X-Forwarded-Prefix', '')
    
    # Find video
    video = None
    for v in all_videos:
        if v.get('content_id') == video_id:
            video = v
            break
    
    if not video:
        return jsonify({'error': 'Video not found'}), 404
    
    # Get video URL - use proxy endpoint for reliable streaming
    video_url = video.get('hls_url')
    if not video_url:
        # Use proxy endpoint which handles CloudFront signed URLs
        if base_path:
            video_url = f"{base_path}/api/video/proxy/{video_id}"
        else:
            video_url = f"/api/video/proxy/{video_id}"
    elif video_url.startswith('/'):
        video_url = f"{base_path}{video_url}" if base_path else video_url
    elif not video_url.startswith('http'):
        if base_path:
            video_url = f"{base_path}/api/video/proxy/{video_id}"
        else:
            video_url = f"/api/video/proxy/{video_id}"
    
    # Get timestops from database
    timestops = []
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
        cur.execute("""
            SELECT timestamp, time_formatted, label, summary, type
            FROM video_timestops
            WHERE content_id = %s
            ORDER BY timestamp
        """, (video_id,))
        
        for row in cur.fetchall():
            timestops.append({
                'timestamp': row[0],
                'time_formatted': row[1],
                'label': row[2],
                'summary': row[3],
                'type': row[4]
            })
        
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error fetching timestops: {e}")
        # Try file fallback
        timestops_file = os.path.join(BASE_DIR, 'video_timestops', f'{video_id}_timestops.json')
        if os.path.exists(timestops_file):
            with open(timestops_file, 'r') as f:
                data = json.load(f)
                timestops = data.get('timestops', [])
    
    # Get transcription
    transcription = None
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
        cur.execute("""
            SELECT transcription_text, transcription_json
            FROM video_transcriptions
            WHERE content_id = %s
        """, (video_id,))
        
        row = cur.fetchone()
        if row:
            transcription = {
                'text': row[0],
                'json': row[1] if row[1] else None
            }
        
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error fetching transcription: {e}")
        # Try file fallback
        transcription_file = os.path.join(BASE_DIR, 'video_transcriptions', f'{video_id}_transcription.json')
        if os.path.exists(transcription_file):
            with open(transcription_file, 'r') as f:
                data = json.load(f)
                transcription_data = data.get('transcription', {})
                transcription = {
                    'text': transcription_data.get('text', ''),
                    'json': transcription_data if transcription_data else None
                }
    
    # Get related videos (from same space, excluding current video)
    related_videos = []
    current_space = video.get('space_name', '')
    for v in all_videos:
        if (v.get('content_id') != video_id and 
            v.get('space_name', '') == current_space and 
            v.get('content_id') is not None):
            related_videos.append(v)
            if len(related_videos) >= 6:  # Limit to 6 related videos
                break
    
    # If not enough videos from same space, add videos from other spaces
    if len(related_videos) < 6:
        for v in all_videos:
            if (v.get('content_id') != video_id and 
                v.get('content_id') is not None and
                v not in related_videos):
                related_videos.append(v)
                if len(related_videos) >= 6:
                    break
    
    # Determine if request is HTTPS (check X-Forwarded-Proto header from Nginx)
    is_https = request.headers.get('X-Forwarded-Proto', 'http') == 'https' or request.is_secure
    
    return render_template(
        'video_with_timestops.html',
        base_path=base_path.rstrip('/') if base_path else '',
        video=video,
        video_url=video_url,
        timestops=timestops,
        transcription=transcription,
        related_videos=related_videos,
        is_https=is_https
    )

def generate_presigned_url(bucket_name, object_key, expiration=3600):
    """Generate a presigned URL for S3 object using signature version 4"""
    if not BOTO3_AVAILABLE:
        return None
    
    try:
        # Get region from environment or try to detect (error showed us-east-2)
        region = os.getenv('AWS_DEFAULT_REGION') or os.getenv('AWS_REGION') or 'us-east-2'
        
        # Create S3 client with region and signature version 4
        from botocore.client import Config
        s3_client = boto3.client(
            's3',
            region_name=region,
            config=Config(signature_version='s3v4')  # Force signature version 4
        )
        
        # Generate presigned URL
        url = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': bucket_name, 'Key': object_key},
            ExpiresIn=expiration
        )
        return url
    except NoCredentialsError:
        print("⚠️  AWS credentials not configured. Set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY")
        return None
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        error_msg = e.response.get('Error', {}).get('Message', str(e))
        print(f"⚠️  Error generating presigned URL ({error_code}): {error_msg}")
        return None
    except Exception as e:
        print(f"⚠️  Unexpected error generating presigned URL: {e}")
        return None

def generate_cloudfront_signed_url(url_path, expiration=3600):
    """Generate a CloudFront signed URL using the private key from config"""
    try:
        # Load production config
        config_path = 'production_config.json'
        if not os.path.exists(config_path):
            return None
        
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        cloudfront_base = config.get('S3_CLOUDFRONT_BASE_URL')
        key_pair_id = config.get('S3_CLOUDFRONT_KEY_PAIR_ID')
        private_key_pem = config.get('S3_CLOUDFRONT_PRIVATE_KEY')
        
        if not all([cloudfront_base, key_pair_id, private_key_pem]):
            return None
        
        # Decode base64 private key
        import base64
        private_key_data = base64.b64decode(private_key_pem)
        private_key_pem_decoded = private_key_data.decode('utf-8')
        
        # Generate CloudFront signed URL
        from botocore.signers import CloudFrontSigner
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import padding
        from cryptography.hazmat.backends import default_backend
        from datetime import datetime, timedelta
        
        # Load private key
        private_key = serialization.load_pem_private_key(
            private_key_pem_decoded.encode('utf-8'),
            password=None,
            backend=default_backend()
        )
        
        # Create signer function
        def rsa_signer(message):
            return private_key.sign(
                message,
                padding.PKCS1v15(),
                hashes.SHA1()
            )
        
        cloudfront_signer = CloudFrontSigner(key_pair_id, rsa_signer)
        
        # Create full URL
        full_url = f"{cloudfront_base}/{url_path}"
        
        # Generate signed URL
        expire_date = datetime.utcnow() + timedelta(seconds=expiration)
        signed_url = cloudfront_signer.generate_presigned_url(
            full_url,
            date_less_than=expire_date
        )
        
        return signed_url
    except ImportError:
        print("⚠️  cryptography library not installed. Install with: pip install cryptography")
        return None
    except Exception as e:
        print(f"⚠️  Error generating CloudFront signed URL: {e}")
        return None

@app.route('/api/video/stream/<int:video_id>')
def stream_video(video_id):
    """Get video stream URL - supports both YouTube and AWS videos"""
    # Find video (cached in memory, very fast)
    video = None
    for v in all_videos:
        if v.get('content_id') == video_id:
            video = v
            break
    
    if not video:
        return jsonify({'error': 'Video not found'}), 404
    
    # Check if this is a YouTube video
    if video.get('type') == 'youtube' or video.get('file_path', '').startswith('youtube:'):
        youtube_id = video.get('youtube_id') or video.get('file_path', '').replace('youtube:', '')
        youtube_embed_url = video.get('youtube_embed_url') or f'https://www.youtube.com/embed/{youtube_id}'
        
        return jsonify({
            'video_url': youtube_embed_url,
            'type': 'youtube',
            'supports_adaptive': True,  # YouTube handles adaptive streaming
            'youtube_id': youtube_id,
            'youtube_url': video.get('youtube_url', f'https://www.youtube.com/watch?v={youtube_id}')
        })
    
    # Get video URL - prefer HLS for adaptive streaming
    file_path = video.get('file_path', '')
    hls_url = video.get('hls_url', '')
    
    # Prefer HLS if available (adaptive bitrate streaming)
    if hls_url:
        # Ensure HTTPS if needed
        is_https = request.headers.get('X-Forwarded-Proto', 'http') == 'https' or request.is_secure
        if is_https and hls_url.startswith('http://'):
            hls_url = hls_url.replace('http://', 'https://')
        
        return jsonify({
            'video_url': hls_url,
            'type': 'hls',
            'supports_adaptive': True
        })
    
    # For non-HLS videos, use proxy endpoint to avoid CORS
    # Return proxy URL immediately (don't generate presigned URL here - let proxy handle it)
    base_path = request.headers.get('X-Forwarded-Prefix', '')
    proxy_url = f"{base_path}/api/video/proxy/{video_id}" if base_path else f"/api/video/proxy/{video_id}"
    
    return jsonify({
        'video_url': proxy_url,
        'type': 'mp4',
        'supports_adaptive': False,
        'file_path': file_path
    })

@app.route('/api/video/proxy/<int:video_id>', methods=['GET', 'HEAD', 'OPTIONS'])
def proxy_video(video_id):
    """Proxy video from S3/CDN to avoid CORS issues - YouTube videos redirect to embed"""
    # Find video
    video = None
    for v in all_videos:
        if v.get('content_id') == video_id:
            video = v
            break
    
    if not video:
        return jsonify({'error': 'Video not found'}), 404
    
    # Check if this is a YouTube video - redirect to YouTube embed
    if video.get('type') == 'youtube' or video.get('file_path', '').startswith('youtube:'):
        youtube_id = video.get('youtube_id') or video.get('file_path', '').replace('youtube:', '')
        youtube_embed_url = f'https://www.youtube.com/embed/{youtube_id}'
        from flask import redirect
        return redirect(youtube_embed_url, code=302)
    
    file_path = video.get('file_path', '')
    hls_url = video.get('hls_url', '')
    hash_filename = video.get('hash_filename', '')
    
    # Initialize video_url
    video_url = None
    
    # Prefer HLS
    if hls_url:
        video_url = hls_url
    elif file_path:
        # Check if file_path is already in videos/ or vimeo_videos/ format (correct S3 path)
        if file_path.startswith('videos/') or file_path.startswith('vimeo_videos/'):
            # This is the correct S3 path format, generate presigned URL
            if BOTO3_AVAILABLE:
                bucket_name = os.getenv('S3_BUCKET_NAME', 'gcmd-production')
            try:
                presigned_url = generate_presigned_url(bucket_name, file_path)
                if presigned_url:
                    # Use presigned URL without testing (testing can cause false errors)
                    video_url = presigned_url
                    print(f"✅ Using presigned URL for S3 path: {file_path}")
                else:
                    print(f"⚠️  Failed to generate presigned URL for: {file_path}")
            except Exception as e:
                print(f"⚠️  Error generating presigned URL for {file_path}: {e}")
            else:
                # No boto3, try public S3 URL
                video_url = f"https://gcmd-production.s3.amazonaws.com/{file_path}"
                print(f"⚠️  Using public S3 URL (may not work): {video_url}")
        elif file_path.startswith('http://') or file_path.startswith('https://'):
            # If file_path is already a full URL (CloudFront signed URL), handle it
            # Extract S3 path from CloudFront URL (remove domain and query params)
            from urllib.parse import urlparse
            parsed = urlparse(file_path)
            s3_path = parsed.path.lstrip('/')
            
            # Try to generate fresh CloudFront signed URL (don't test expired URLs - just generate new ones)
            # Testing expired URLs causes error messages to appear
            print(f"Generating fresh CloudFront signed URL for expired URL...")
            # Try to generate new CloudFront signed URL
            cloudfront_signed_url = generate_cloudfront_signed_url(s3_path)
            if cloudfront_signed_url:
                # Use the signed URL directly without testing (testing causes error messages)
                video_url = cloudfront_signed_url
                print(f"✅ Generated fresh CloudFront signed URL for: {s3_path}")
            else:
                # CloudFront signing failed, try S3 presigned URL
                print(f"⚠️  CloudFront signing failed, trying S3 presigned URL...")
                if BOTO3_AVAILABLE and s3_path:
                    try:
                        bucket_name = os.getenv('S3_BUCKET_NAME', 'gcmd-production')
                        presigned_url = generate_presigned_url(bucket_name, s3_path)
                        if presigned_url:
                            video_url = presigned_url
                            print(f"✅ Generated S3 presigned URL for: {s3_path}")
                        else:
                            # Last resort: use CloudFront without signature
                            cloudfront_base = 'https://d1u4wu4o55kmvh.cloudfront.net'
                            video_url = f"{cloudfront_base}/{s3_path}"
                            print(f"⚠️  Using CloudFront URL without signature: {video_url[:100]}...")
                    except Exception as e:
                        print(f"⚠️  Error generating presigned URL: {e}")
                        cloudfront_base = 'https://d1u4wu4o55kmvh.cloudfront.net'
                        video_url = f"{cloudfront_base}/{s3_path}"
                else:
                    cloudfront_base = 'https://d1u4wu4o55kmvh.cloudfront.net'
                    video_url = f"{cloudfront_base}/{s3_path}"
                    print(f"⚠️  Using CloudFront URL without signature: {video_url[:100]}...")
        else:
            # For spaces/ paths, prioritize CloudFront signed URLs since they're served via CDN
            # These paths typically don't exist in S3 directly but are accessible via CloudFront
            if file_path.startswith('spaces/'):
                # Try CloudFront signed URL first for spaces/ paths
                cloudfront_signed = generate_cloudfront_signed_url(file_path)
                if cloudfront_signed:
                    video_url = cloudfront_signed
                    print(f"✅ Using CloudFront signed URL for spaces/ path: {file_path}")
                else:
                    # Fallback to S3 presigned URL if CloudFront fails
                    if BOTO3_AVAILABLE:
                        bucket_name = os.getenv('S3_BUCKET_NAME', 'gcmd-production')
                        try:
                            presigned_url = generate_presigned_url(bucket_name, file_path)
                            if presigned_url:
                                video_url = presigned_url
                                print(f"✅ Using S3 presigned URL for: {file_path}")
                        except:
                            pass
            else:
                # For other path formats, try S3 presigned URLs first, then CloudFront
                bucket_name = os.getenv('S3_BUCKET_NAME', 'gcmd-production')
                base_urls = [
                    os.getenv('VIDEO_CDN_BASE_URL'),
                    os.getenv('S3_BASE_URL'),
                    os.getenv('CLOUDFRONT_BASE_URL'),
                    'https://d1u4wu4o55kmvh.cloudfront.net',  # From production config
                    'https://gcmd-production.s3.amazonaws.com',
                ]
                base_urls = [url for url in base_urls if url]
                
                # Try multiple S3 path formats
                s3_paths_to_try = []
                
                # 1. Original file_path as-is
                s3_paths_to_try.append(file_path)
                
                # 2. Try videos/ folder with hash_filename (if hash-based format exists)
                if hash_filename:
                    s3_paths_to_try.append(f"videos/{hash_filename}")
                    # Extract just filename if hash_filename has path
                    filename_only = hash_filename.split('/')[-1]
                    if filename_only != hash_filename:
                        s3_paths_to_try.append(f"videos/{filename_only}")
                
                # 3. Try vimeo_videos/ folder
                if hash_filename:
                    s3_paths_to_try.append(f"vimeo_videos/{hash_filename}")
                    filename_only = hash_filename.split('/')[-1]
                    if filename_only != hash_filename:
                        s3_paths_to_try.append(f"vimeo_videos/{filename_only}")
                
                # Try presigned URLs first (if AWS credentials available)
                if BOTO3_AVAILABLE:
                    for s3_key in s3_paths_to_try:
                        try:
                            presigned_url = generate_presigned_url(bucket_name, s3_key)
                            if presigned_url:
                                video_url = presigned_url
                                print(f"✅ Using presigned URL for S3 key: {s3_key}")
                                break
                        except Exception as e:
                            continue
                    
                    # If no presigned URL, try CloudFront signed URL for the first path
                    if not video_url and s3_paths_to_try:
                        first_path = s3_paths_to_try[0]
                        cloudfront_signed = generate_cloudfront_signed_url(first_path)
                        if cloudfront_signed:
                            video_url = cloudfront_signed
                            print(f"✅ Using CloudFront signed URL for: {first_path}")
                
                # If still no URL, use first path format as fallback
                if not video_url and base_urls:
                    video_url = f"{base_urls[0]}/{s3_paths_to_try[0]}"
    else:
        return jsonify({'error': 'Video URL not available'}), 404
    
    if not video_url:
        return jsonify({'error': 'Could not construct video URL'}), 404
    
    # Handle OPTIONS request for CORS preflight
    if request.method == 'OPTIONS':
        response = Response()
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, HEAD, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Range, Content-Type'
        response.headers['Access-Control-Expose-Headers'] = 'Content-Length, Content-Range, Accept-Ranges'
        response.headers['Access-Control-Max-Age'] = '86400'
        return response
    
    # Stream video with proper headers
    # Get range header for video seeking support
    range_header = request.headers.get('Range', None)
    headers = {}
    if range_header:
        headers['Range'] = range_header
    
    # Stream from source
    # For CloudFront signed URLs, we need to preserve the full URL including query parameters
    # Try the video URL - if it fails, try fallback URLs before returning error
    response = None
    last_error = None
    
    try:
            # Don't follow redirects for CloudFront URLs to preserve signed URL parameters
            follow_redirects = not ('cloudfront.net' in video_url or 'Policy=' in video_url)
            response = requests.get(video_url, headers=headers, stream=True, timeout=30, allow_redirects=follow_redirects)
    except requests.exceptions.RequestException as e:
        last_error = e
        # Try fallback: generate CloudFront signed URL if we haven't already
        if 'cloudfront.net' not in video_url or 'Policy=' not in video_url:
            try:
                from urllib.parse import urlparse
                parsed = urlparse(video_url)
                s3_path = parsed.path.lstrip('/')
                if s3_path:
                    cloudfront_signed = generate_cloudfront_signed_url(s3_path)
                    if cloudfront_signed:
                        try:
                            response = requests.get(cloudfront_signed, headers=headers, stream=True, timeout=30, allow_redirects=False)
                            video_url = cloudfront_signed
                            print(f"✅ Fallback CloudFront signed URL worked")
                        except:
                            pass
            except:
                pass
        
    # Check if request was successful - try fallbacks if needed
    if not response or response.status_code not in [200, 206]:  # 206 is Partial Content (for range requests)
        # Try one more fallback before giving up
        if response and 'cloudfront.net' in video_url and 'Policy=' in video_url:
            # Already tried CloudFront signed URL, try S3 presigned as last resort
            try:
                from urllib.parse import urlparse
                parsed = urlparse(video_url)
                s3_path = parsed.path.lstrip('/')
                if s3_path and BOTO3_AVAILABLE:
                    bucket_name = os.getenv('S3_BUCKET_NAME', 'gcmd-production')
                    presigned_url = generate_presigned_url(bucket_name, s3_path)
                    if presigned_url:
                        try:
                            fallback_response = requests.get(presigned_url, headers=headers, stream=True, timeout=30)
                            if fallback_response.status_code in [200, 206]:
                                response = fallback_response
                                video_url = presigned_url
                                print(f"✅ Fallback S3 presigned URL worked")
                        except:
                            pass
            except:
                pass
            
        # Only return error if we've exhausted all options
        if not response or response.status_code not in [200, 206]:
            # Return a simple error - don't show detailed error messages that confuse users
            # The video player will handle the error gracefully
            return Response('', status=response.status_code if response else 500)
    
    # Prepare response headers (only reached if response is successful)
    if response and response.status_code in [200, 206]:
        # Get content type from response or determine from URL
        content_type = response.headers.get('Content-Type', 'video/mp4')
        # Ensure proper content type for video files
        if not content_type.startswith('video/') and not content_type.startswith('application/'):
            # Try to determine from file extension
            if video_url.endswith('.mp4'):
                content_type = 'video/mp4'
            elif video_url.endswith('.webm'):
                content_type = 'video/webm'
            elif video_url.endswith('.m3u8'):
                content_type = 'application/vnd.apple.mpegurl'
            else:
                content_type = 'video/mp4'
        
        response_headers = {
            'Content-Type': content_type,
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, HEAD, OPTIONS',
            'Access-Control-Allow-Headers': 'Range, Content-Type',
            'Access-Control-Expose-Headers': 'Content-Length, Content-Range, Accept-Ranges',
            'Accept-Ranges': 'bytes',
            'Cache-Control': 'public, max-age=3600',
        }
        
        # Handle range requests (for video seeking)
        if range_header and response.status_code == 206:
            response_headers['Content-Range'] = response.headers.get('Content-Range')
            response_headers['Content-Length'] = response.headers.get('Content-Length')
        
        # Handle HEAD request - return headers only
        if request.method == 'HEAD':
            return Response('', status=response.status_code, headers=response_headers)
        
        # Stream the video for GET requests
        def generate():
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    yield chunk
        
        return Response(
            generate(),
            status=response.status_code,
            headers=response_headers
        )
    
def generate_thumbnail_from_video(video_url, output_path, time_offset=1.0):
    """Generate thumbnail from video URL using ffmpeg"""
    try:
        import subprocess
        cmd = [
            'ffmpeg',
            '-i', video_url,
            '-ss', str(time_offset),
            '-vframes', '1',
            '-q:v', '2',  # High quality
            '-y',  # Overwrite output file
            output_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return result.returncode == 0
    except Exception as e:
        print(f"Error generating thumbnail from video: {e}")
        return False

@app.route('/api/video/<int:video_id>/thumbnail')
def get_video_thumbnail(video_id):
    """Get video thumbnail - serve from local cache, S3, CloudFront, or generate from first frame"""
    # Find video
    video = None
    for v in all_videos:
        if v.get('content_id') == video_id:
            video = v
            break
    
    if not video:
        return jsonify({'error': 'Video not found'}), 404
    
    # Check for locally generated thumbnail first
    thumbnail_dir = 'thumbnails'
    os.makedirs(thumbnail_dir, exist_ok=True)
    local_thumbnail = os.path.join(thumbnail_dir, f"{video_id}.jpg")
    if os.path.exists(local_thumbnail):
        response = send_file(local_thumbnail, mimetype='image/jpeg')
        response.headers['Cache-Control'] = 'public, max-age=86400'
        return response
    
    # Check if thumbnail exists in metadata
    thumbnail = video.get('thumbnail', '')
    file_path = video.get('file_path', '')
    hash_filename = video.get('hash_filename', '')
    
    # List of thumbnail paths to try (in order of preference)
    thumbnail_paths_to_try = []
    
    # 1. First, try the thumbnail from metadata (but skip generic default thumbnails)
    # Generic default thumbnails are the same for all videos, so we'll try to generate from video instead
    if thumbnail and 'public-assets/defaults/default_thumbnail.jpg' not in thumbnail:
        thumbnail_paths_to_try.append(thumbnail)
    
    # 2. Try to construct thumbnail from video hash/path
    if hash_filename and not hash_filename.startswith('http'):
        # Clean hash filename
        clean_hash = hash_filename.split('?')[0].split('/')[-1]
        if clean_hash.endswith('.mp4'):
            # Replace .mp4 with .jpg
            thumbnail_hash = clean_hash.replace('.mp4', '.jpg')
            # Try videos/ path
            thumbnail_paths_to_try.append(f'videos/{thumbnail_hash}')
    elif file_path:
        if file_path.startswith('videos/'):
            # Extract hash from file_path
            video_hash = file_path.split('/')[-1].replace('.mp4', '.jpg')
            thumbnail_paths_to_try.append(f'videos/{video_hash}')
        elif file_path.startswith('http'):
            # Extract path from CloudFront URL and construct thumbnail path
            from urllib.parse import urlparse
            parsed = urlparse(file_path)
            path = parsed.path.lstrip('/')
            # Format: spaces/1/content/11278/file_11278_1_1764082933619.mp4
            # -> spaces/1/content/11278/thumbnail_11278_1_1764082933619.jpg
            if '/content/' in path:
                parts = path.split('/')
                if len(parts) >= 4:
                    content_dir = '/'.join(parts[:-1])  # spaces/1/content/11278
                    filename = parts[-1]  # file_11278_1_1764082933619.mp4
                    if filename.startswith('file_') and filename.endswith('.mp4'):
                        thumb_name = filename.replace('file_', 'thumbnail_').replace('.mp4', '.jpg')
                        thumbnail_paths_to_try.append(f'{content_dir}/{thumb_name}')
    
    # Try each thumbnail path until one works
    for thumbnail_path in thumbnail_paths_to_try:
        if not thumbnail_path:
            continue
        # If thumbnail is a URL, proxy it
        if thumbnail_path.startswith('http://') or thumbnail_path.startswith('https://'):
            try:
                response = requests.get(thumbnail_path, stream=True, timeout=5)
                if response.status_code == 200:
                    return Response(
                        response.content,
                        mimetype='image/jpeg',
                        headers={'Cache-Control': 'public, max-age=3600'}
                    )
            except Exception as e:
                continue
        
        # If thumbnail is a relative path, try multiple approaches
        # 1. Try CloudFront with signed URL (even if direct access fails, signed URL might work)
        cloudfront_base = 'https://d1u4wu4o55kmvh.cloudfront.net'
        
        # Generate CloudFront signed URL for thumbnail
        signed_url = generate_cloudfront_signed_url(thumbnail_path)
        if signed_url:
            try:
                response = requests.get(signed_url, stream=True, timeout=5)
                if response.status_code == 200:
                    return Response(
                        response.content,
                        mimetype='image/jpeg',
                        headers={'Cache-Control': 'public, max-age=3600'}
                    )
            except Exception as e:
                pass
        
        # 2. Try S3 presigned URL
        if BOTO3_AVAILABLE:
            bucket_name = os.getenv('S3_BUCKET_NAME', 'gcmd-production')
            try:
                # Try videos/ path
                s3_paths_to_try = [thumbnail_path]
                # Also try with videos/ prefix if not already there
                if not thumbnail_path.startswith('videos/') and not thumbnail_path.startswith('spaces/'):
                    s3_paths_to_try.append(f"videos/{thumbnail_path.split('/')[-1]}")
                
                for s3_path in s3_paths_to_try:
                    try:
                        presigned_url = generate_presigned_url(bucket_name, s3_path)
                        if presigned_url:
                            response = requests.get(presigned_url, stream=True, timeout=5)
                            if response.status_code == 200:
                                return Response(
                                    response.content,
                                    mimetype='image/jpeg',
                                    headers={'Cache-Control': 'public, max-age=3600'}
                                )
                    except:
                        continue
            except Exception as e:
                print(f"Error generating S3 presigned URL for thumbnail: {e}")
        
        # 3. Try public S3/CDN URLs
        base_urls = [
            os.getenv('CDN_BASE_URL'),
            os.getenv('S3_BASE_URL'),
            cloudfront_base,
            'https://gcmd-production.s3.amazonaws.com',
            'https://cdn.staycurrentmd.com',
        ]
        base_urls = [url for url in base_urls if url]
        
        for base_url in base_urls:
            thumbnail_url = f"{base_url}/{thumbnail_path}"
            try:
                response = requests.get(thumbnail_url, stream=True, timeout=5)
                if response.status_code == 200:
                    return Response(
                        response.content,
                        mimetype='image/jpeg',
                        headers={'Cache-Control': 'public, max-age=3600'}
                    )
            except:
                continue
        
        # 4. If local file exists
        if os.path.exists(thumbnail_path):
            response = send_file(thumbnail_path, mimetype='image/jpeg')
            response.headers['Cache-Control'] = 'public, max-age=3600'
            return response
    
    # If all thumbnail paths failed OR we have a generic default thumbnail, try generating from video
    original_thumbnail = video.get('thumbnail', '')
    is_default_thumbnail = original_thumbnail and 'public-assets/defaults/default_thumbnail.jpg' in original_thumbnail
    
    if is_default_thumbnail or not thumbnail_paths_to_try:
        # Try to generate thumbnail from video
        try:
            # Get video stream URL
            video_stream_response = requests.get(f'http://localhost:5001/api/video/stream/{video_id}', timeout=5)
            if video_stream_response.status_code == 200:
                stream_data = video_stream_response.json()
                proxy_url = stream_data.get('video_url', '')
                
                if proxy_url and proxy_url.startswith('/'):
                    # Make it a full URL
                    proxy_url = f'http://localhost:5001{proxy_url}'
                
                # Generate thumbnail from video
                if generate_thumbnail_from_video(proxy_url, local_thumbnail, time_offset=1.0):
                    if os.path.exists(local_thumbnail):
                        response = send_file(local_thumbnail, mimetype='image/jpeg')
                        response.headers['Cache-Control'] = 'public, max-age=86400'
                        return response
        except Exception as e:
            print(f"Error generating thumbnail from video for {video_id}: {e}")
    
    # Return a placeholder image instead of 404
    # Create a simple 1x1 transparent PNG as placeholder
    placeholder_png = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xdb\x00\x00\x00\x00IEND\xaeB`\x82'
    
    return Response(
        placeholder_png,
        mimetype='image/png',
        headers={
            'Cache-Control': 'public, max-age=300',
            'Access-Control-Allow-Origin': '*'
        }
    )

if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("StayCurrentMD Video Library Server")
    print("=" * 60)
    print(f"Total Videos: {len(all_videos)}")
    print(f"Total Spaces: {len(spaces_dict)}")
    print("\nStarting server...")
    
    # Use environment variable for host, default to 0.0.0.0 for production
    host = os.getenv('FLASK_HOST', '0.0.0.0')
    port = int(os.getenv('FLASK_PORT', '5001'))
    debug = os.getenv('FLASK_ENV', 'production').lower() != 'production'
    
    print(f"Server will be available at: http://{host}:{port}")
    print("=" * 60 + "\n")
    app.run(debug=debug, port=port, host=host)

