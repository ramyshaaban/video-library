#!/usr/bin/env python3
"""
Fetch all video metadata from StayCurrentMD GraphQL API
"""
import json
import subprocess
import sys
import time

API_URL = "https://api.staycurrentmd.com/graphql"

def get_token():
    """Get token from file or generate new one"""
    try:
        with open("api_token.txt", "r") as f:
            token = f.read().strip()
            if token:
                return token
    except:
        pass
    
    # Generate new token
    print("Generating new guest token...")
    result = subprocess.run(
        ["bash", "get_api_token.sh"],
        capture_output=True,
        text=True
    )
    
    try:
        with open("api_token.txt", "r") as f:
            return f.read().strip()
    except:
        print("Failed to get token")
        return None

def query_videos(token, page=1, page_size=100):
    """Query videos from API"""
    query = """
    query GetContent($input: GetContentInput!) {
      getContent(input: $input) {
        content {
          id
          content_title
          description
          space_id
          associated_content_files {
            id
            file
            thumbnail
            hls_url
          }
          space_info {
            id
            name
          }
          associated_content_sections {
            id
            section_title
            start_time
          }
          createdAt
          updatedAt
        }
        pagination {
          total_records
          page
          page_size
        }
      }
    }
    """
    
    variables = {
        "input": {
            "keyword": "",  # Empty string for all videos
            "content_type_ids": [3],  # 3 = VIDEOS (array format)
            "page": page,
            "page_size": page_size
        }
    }
    
    # Use curl to make the request
    curl_cmd = [
        "curl", "-s", "-X", "POST", API_URL,
        "-H", "Content-Type: application/json",
        "-H", f"Authorization: Bearer {token}",
        "-d", json.dumps({"query": query, "variables": variables})
    ]
    
    try:
        result = subprocess.run(curl_cmd, capture_output=True, text=True)
        if result.returncode == 0:
            return json.loads(result.stdout)
        else:
            print(f"Error: {result.stderr}")
            return None
    except Exception as e:
        print(f"Error querying API: {e}")
        return None

def fetch_all_videos(token):
    """Fetch all videos in batches"""
    all_videos = []
    page = 1
    page_size = 100
    total_records = None
    
    print("Fetching video metadata from API...")
    print("=" * 60)
    
    while True:
        print(f"Fetching page {page}...", end=" ", flush=True)
        response = query_videos(token, page, page_size)
        
        if not response or "errors" in response:
            print(f"❌ Error: {response.get('errors', 'Unknown error')}")
            break
        
        data = response.get("data", {}).get("getContent", {})
        videos = data.get("content", [])
        pagination = data.get("pagination", {})
        
        if total_records is None:
            total_records = pagination.get("total_records", 0)
            print(f"Total videos: {total_records}")
        else:
            print(f"Got {len(videos)} videos")
        
        if not videos:
            break
        
        all_videos.extend(videos)
        
        # Check if we've got all videos
        if len(all_videos) >= total_records:
            break
        
        page += 1
        time.sleep(0.5)  # Rate limiting
    
    print(f"\n✅ Fetched {len(all_videos)} videos")
    return all_videos

def process_videos(videos):
    """Process videos and extract metadata"""
    processed = []
    
    for video in videos:
        # Get file path from associated_content_files
        file_path = None
        thumbnail = None
        hls_url = None
        
        if video.get("associated_content_files"):
            files = video["associated_content_files"]
            if len(files) > 0:
                file_path = files[0].get("file", "")
                thumbnail = files[0].get("thumbnail", "")
                hls_url = files[0].get("hls_url", "")
        
        # Extract hash from file path
        # Format: "videos/000a300e8f1e74ab4fec71506bea7096.mp4"
        hash_filename = None
        if file_path:
            # Extract just the filename
            hash_filename = file_path.split("/")[-1] if "/" in file_path else file_path
        
        processed.append({
            "content_id": video.get("id"),
            "title": video.get("content_title", ""),
            "description": video.get("description", ""),
            "space_id": video.get("space_id"),
            "space_name": video.get("space_info", {}).get("name", ""),
            "file_path": file_path,
            "hash_filename": hash_filename,
            "thumbnail": thumbnail,
            "hls_url": hls_url,
            "s3_path": f"s3://gcmd-production/{file_path}" if file_path else None,
            "chapters": len(video.get("associated_content_sections", [])),
            "created_at": video.get("createdAt", ""),
            "updated_at": video.get("updatedAt", "")
        })
    
    return processed

if __name__ == "__main__":
    print("=" * 60)
    print("StayCurrentMD Video Metadata Fetcher")
    print("=" * 60)
    print()
    
    # Get token
    token = get_token()
    if not token:
        print("❌ Failed to get API token")
        sys.exit(1)
    
    print(f"✅ Using token: {token[:50]}...")
    print()
    
    # Fetch all videos
    videos = fetch_all_videos(token)
    
    if not videos:
        print("❌ No videos fetched")
        sys.exit(1)
    
    # Process videos
    print("\nProcessing video metadata...")
    processed = process_videos(videos)
    
    # Save to JSON
    output_file = "all_video_metadata_from_api.json"
    with open(output_file, "w") as f:
        json.dump(processed, f, indent=2)
    
    print(f"✅ Saved {len(processed)} videos to: {output_file}")
    
    # Show summary
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"Total videos: {len(processed)}")
    print(f"Videos with titles: {len([v for v in processed if v['title']])}")
    print(f"Videos with descriptions: {len([v for v in processed if v['description']])}")
    print(f"Videos with S3 paths: {len([v for v in processed if v['s3_path']])}")
    print(f"Unique spaces: {len(set(v['space_name'] for v in processed if v['space_name']))}")
    
    print("\nSample videos:")
    for video in processed[:5]:
        print(f"  - {video['title']} (ID: {video['content_id']})")
        print(f"    S3: {video['s3_path']}")

