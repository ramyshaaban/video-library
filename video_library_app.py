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
import os
import re
from difflib import SequenceMatcher
import requests
from urllib.parse import urlparse

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

app = Flask(__name__, template_folder=TEMPLATE_DIR)

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

# Load video data
def load_video_data():
    """Load video metadata from database"""
    with open('all_video_metadata_from_database.json', 'r') as f:
        return json.load(f)

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

@app.route('/')
def index():
    """Main library page"""
    return render_template('library.html')

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
    import urllib.parse
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
            'updated_at': video.get('updated_at', '')[:10] if video.get('updated_at') else 'Unknown date'
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

@app.route('/api/search')
def search_all_videos():
    """API endpoint to search videos across all spaces with Elasticsearch fuzzy matching"""
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
            for hit in hits:
                source = hit['_source']
                video_list.append({
                    'id': source.get('content_id'),
                    'title': source.get('title', 'Untitled'),
                    'description': source.get('description', ''),
                    'file_path': source.get('file_path', ''),
                    'thumbnail': source.get('thumbnail', ''),
                    'hls_url': source.get('hls_url', ''),
                    'created_at': source.get('created_at', '')[:10] if source.get('created_at') else 'Unknown date',
                    'updated_at': source.get('updated_at', '')[:10] if source.get('updated_at') else 'Unknown date',
                    'space_name': source.get('space_name', 'Unknown Space'),
                    'score': hit.get('_score', 0)  # Include relevance score for debugging
                })
            
            return jsonify({
                'videos': video_list,
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': total,
                    'total_pages': (total + per_page - 1) // per_page
                },
                'search_term': search,
                'search_engine': 'elasticsearch'
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
    for item in paginated_results:
        video = item['video']
        video_list.append({
            'id': video.get('content_id'),
            'title': video.get('title', 'Untitled'),
            'description': video.get('description', ''),
            'file_path': video.get('file_path', ''),
            'thumbnail': video.get('thumbnail', ''),
            'hls_url': video.get('hls_url', ''),
            'created_at': video.get('created_at', '')[:10] if video.get('created_at') else 'Unknown date',
            'updated_at': video.get('updated_at', '')[:10] if video.get('updated_at') else 'Unknown date',
            'space_name': item['space_name'],
            'score': round(item['score'], 3)  # Include relevance score
        })
    
    return jsonify({
        'videos': video_list,
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': total,
            'total_pages': (total + per_page - 1) // per_page
        },
        'search_term': search,
        'search_engine': 'fuzzy'  # Changed from 'basic' to 'fuzzy'
    })

@app.route('/api/video/<int:video_id>')
def get_video(video_id):
    """API endpoint to get a specific video"""
    for video in all_videos:
        if video.get('content_id') == video_id:
            return jsonify(video)
    return jsonify({'error': 'Video not found'}), 404

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
    """Stream video through proxy to avoid CORS issues"""
    # Find video
    video = None
    for v in all_videos:
        if v.get('content_id') == video_id:
            video = v
            break
    
    if not video:
        return jsonify({'error': 'Video not found'}), 404
    
    # Get video URL
    file_path = video.get('file_path', '')
    hls_url = video.get('hls_url', '')
    
    # Prefer HLS if available (usually has CORS configured)
    if hls_url:
        return jsonify({
            'video_url': hls_url,
            'type': 'hls'
        })
    
    # For S3 videos, use proxy endpoint to avoid CORS
    if file_path:
        # If file_path is already a full URL (CloudFront or S3), use proxy to handle CORS
        if file_path.startswith('http://') or file_path.startswith('https://'):
            return jsonify({
                'video_url': f'/api/video/proxy/{video_id}',
                'type': 'proxy',
                'note': 'Using proxy to handle CORS for CloudFront/S3 URLs'
            })
        
        # Use proxy endpoint for S3 videos
        return jsonify({
            'video_url': f'/api/video/proxy/{video_id}',
            'type': 'proxy',
            'file_path': file_path
        })
    
    return jsonify({'error': 'Video URL not available'}), 404

@app.route('/api/video/proxy/<int:video_id>', methods=['GET', 'HEAD', 'OPTIONS'])
def proxy_video(video_id):
    """Proxy video from S3/CDN to avoid CORS issues"""
    # Find video
    video = None
    for v in all_videos:
        if v.get('content_id') == video_id:
            video = v
            break
    
    if not video:
        return jsonify({'error': 'Video not found'}), 404
    
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
        response.headers['Access-Control-Allow-Headers'] = 'Range'
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
        response_headers = {
            'Content-Type': response.headers.get('Content-Type', 'video/mp4'),
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, HEAD, OPTIONS',
            'Access-Control-Allow-Headers': 'Range',
            'Accept-Ranges': 'bytes',
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
    print("Open your browser to: http://localhost:5001")
    print("=" * 60 + "\n")
    app.run(debug=True, port=5001, host='127.0.0.1')

