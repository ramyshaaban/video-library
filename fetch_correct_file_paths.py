#!/usr/bin/env python3
"""
Fetch correct file paths from GraphQL API for videos without HLS URLs
"""
import json
import subprocess
import sys
import time

API_URL = "https://api.staycurrentmd.com/graphql"

def get_token():
    """Get token from file"""
    try:
        with open("api_token.txt", "r") as f:
            token = f.read().strip()
            if token:
                return token
    except:
        pass
    return None

def query_video_details(token, content_id):
    """Query single video details from API"""
    query = """
    query GetContentInfoById($input: GetContentInfoByIdInput!) {
      getContentInfoById(input: $input) {
        contentInfo {
          id
          content_title
          associated_content_files {
            id
            file
            thumbnail
            hls_url
          }
        }
      }
    }
    """
    
    variables = {
        "input": {
            "content_id": content_id
        }
    }
    
    curl_cmd = [
        "curl", "-s", "-X", "POST", API_URL,
        "-H", "Content-Type: application/json",
        "-H", f"Authorization: Bearer {token}",
        "-d", json.dumps({"query": query, "variables": variables})
    ]
    
    try:
        result = subprocess.run(curl_cmd, capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            return json.loads(result.stdout)
        else:
            print(f"Error: {result.stderr}")
            return None
    except Exception as e:
        print(f"Error querying API: {e}")
        return None

def update_video_metadata():
    """Update metadata with correct file paths from API"""
    # Load existing metadata
    try:
        with open('all_video_metadata_from_database.json', 'r') as f:
            videos = json.load(f)
    except Exception as e:
        print(f"Error loading metadata: {e}")
        return
    
    # Get token
    token = get_token()
    if not token:
        print("❌ No API token found. Please run get_api_token.py first")
        return
    
    print(f"✅ Using token: {token[:50]}...")
    
    # Find videos without HLS URLs
    videos_without_hls = [v for v in videos if not v.get('hls_url')]
    print(f"\nFound {len(videos_without_hls)} videos without HLS URLs")
    print("Fetching correct file paths from API...")
    print("=" * 60)
    
    updated_count = 0
    errors = []
    
    # Process in batches to avoid rate limiting
    batch_size = 10
    for i in range(0, len(videos_without_hls), batch_size):
        batch = videos_without_hls[i:i+batch_size]
        print(f"\nProcessing batch {i//batch_size + 1} ({len(batch)} videos)...")
        
        for video in batch:
            content_id = video.get('content_id')
            if not content_id:
                continue
            
            print(f"  Fetching content_id {content_id}...", end=" ", flush=True)
            
            response = query_video_details(token, content_id)
            
            if not response or "errors" in response:
                error_msg = response.get("errors", [{}])[0].get("message", "Unknown error") if response else "No response"
                print(f"❌ Error: {error_msg}")
                errors.append((content_id, error_msg))
                time.sleep(0.5)  # Rate limiting
                continue
            
            data = response.get("data", {}).get("getContentInfoById", {}).get("contentInfo", {})
            
            if data and data.get("associated_content_files"):
                files = data["associated_content_files"]
                if len(files) > 0:
                    correct_file = files[0].get("file", "")
                    correct_hls = files[0].get("hls_url", "")
                    
                    # Update video metadata
                    if correct_file and correct_file != video.get('file_path'):
                        video['file_path'] = correct_file
                        # Extract hash filename
                        if '/' in correct_file:
                            video['hash_filename'] = correct_file.split('/')[-1]
                        updated_count += 1
                        print(f"✅ Updated: {correct_file[:60]}...")
                    elif correct_hls:
                        video['hls_url'] = correct_hls
                        updated_count += 1
                        print(f"✅ Got HLS URL")
                    else:
                        print("⚠️  No file or HLS URL")
                else:
                    print("⚠️  No associated_content_files")
            else:
                print("⚠️  No data")
            
            time.sleep(0.3)  # Rate limiting
        
        # Save progress after each batch
        if updated_count > 0:
            with open('all_video_metadata_from_database.json', 'w') as f:
                json.dump(videos, f, indent=2)
            print(f"\n💾 Progress saved: {updated_count} videos updated so far")
    
    # Final save
    with open('all_video_metadata_from_database.json', 'w') as f:
        json.dump(videos, f, indent=2)
    
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"✅ Updated {updated_count} videos")
    print(f"❌ Errors: {len(errors)}")
    
    if errors:
        print("\nErrors:")
        for content_id, error in errors[:10]:
            print(f"  Content ID {content_id}: {error}")
    
    # Count videos with correct paths now
    videos_with_videos_prefix = [v for v in videos if v.get('file_path', '').startswith('videos/')]
    videos_with_hls = [v for v in videos if v.get('hls_url')]
    
    print(f"\n✅ Videos with 'videos/' prefix: {len(videos_with_videos_prefix)}")
    print(f"✅ Videos with HLS URLs: {len(videos_with_hls)}")
    print(f"✅ Total working videos: {len(videos_with_videos_prefix) + len(videos_with_hls)}")

if __name__ == "__main__":
    print("=" * 60)
    print("Fetch Correct File Paths from API")
    print("=" * 60)
    print()
    
    update_video_metadata()

