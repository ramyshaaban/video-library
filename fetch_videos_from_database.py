#!/usr/bin/env python3
"""
Fetch video metadata directly from PostgreSQL database
"""
import os
import sys
import subprocess
import json
import pandas as pd
from urllib.parse import urlparse

def get_database_url():
    """Get database URL from AWS credentials file or environment"""
    # First, try reading from AWS credentials file
    try:
        with open('production_rds_credentials.json', 'r') as f:
            creds = json.load(f)
            # URL encode the password to handle special characters
            from urllib.parse import quote_plus
            username = quote_plus(creds['username'])
            password = quote_plus(creds['password'])
            host = creds['host']
            port = creds['port']
            database = creds.get('dbInstanceIdentifier', 'staycurrentmd')
            # Build connection string
            db_url = f"postgresql://{username}:{password}@{host}:{port}/{database}"
            print(f"✅ Found database credentials from AWS Secrets Manager")
            return db_url
    except Exception as e:
        print(f"Error reading credentials: {e}")
        pass
    
    # Try environment variable
    db_url = os.environ.get('DATABASE_URL') or os.environ.get('POSTGRES_URL')
    if db_url:
        return db_url
    
    # Try reading from various .env files
    env_files = [
        '../.env.production',  # designer folder
        '../../StayCurrentMD Mobile/staycurrent-mobile/.env',  # StayCurrentMD Mobile
        '../../staycurrentmd/ui-enhancement-ramy/.env',  # staycurrentmd folder
    ]
    
    for env_file in env_files:
        try:
            with open(env_file, 'r') as f:
                for line in f:
                    if line.startswith('DATABASE_URL=') or line.startswith('POSTGRES_URL='):
                        db_url = line.split('=', 1)[1].strip().strip('"').strip("'")
                        if db_url:
                            print(f"Found database URL in: {env_file}")
                            return db_url
        except:
            continue
    
    return db_url

def query_database_with_psql(db_url, query):
    """Query database using psql"""
    try:
        # Parse connection string
        parsed = urlparse(db_url)
        
        # Extract connection details
        user = parsed.username
        password = parsed.password
        host = parsed.hostname
        port = parsed.port or 5432
        database = parsed.path.lstrip('/').split('?')[0]
        
        # Set PGPASSWORD environment variable
        env = os.environ.copy()
        env['PGPASSWORD'] = password
        
        # Build psql command
        cmd = [
            'psql',
            '-h', host,
            '-p', str(port),
            '-U', user,
            '-d', database,
            '-t',  # Tuples only
            '-A',  # Unaligned output
            '-F', ',',  # Field separator
            '-c', query
        ]
        
        result = subprocess.run(
            cmd,
            env=env,
            capture_output=True,
            text=True,
            timeout=300
        )
        
        if result.returncode == 0:
            return result.stdout
        else:
            print(f"Error: {result.stderr}")
            return None
    except Exception as e:
        print(f"Error querying database: {e}")
        return None

def query_database_with_python(db_url):
    """Query database using Python (requires psycopg2)"""
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        
        # Try to use credentials file directly first
        try:
            with open('production_rds_credentials.json', 'r') as f:
                creds = json.load(f)
                # Try different database names
                db_names = ['staycurrentmd', 'postgres', creds.get('dbInstanceIdentifier', 'staycurrentmd')]
                
                for db_name in db_names:
                    try:
                        print(f"Trying to connect to database: {db_name}")
                        conn = psycopg2.connect(
                            host=creds['host'],
                            port=creds['port'],
                            user=creds['username'],
                            password=creds['password'],
                            database=db_name,
                            sslmode='prefer'  # Try prefer first, then require
                        )
                        print(f"✅ Connected to database: {db_name}")
                        break
                    except psycopg2.OperationalError as e:
                        if 'password authentication failed' in str(e):
                            print(f"❌ Password authentication failed for {db_name}")
                            continue
                        raise
                    except Exception as e:
                        print(f"⚠️ Error connecting to {db_name}: {e}")
                        continue
                else:
                    # If all database names failed, try with URL parsing
                    raise Exception("All database names failed")
        except:
            # Fallback to URL parsing
            parsed = urlparse(db_url)
            conn = psycopg2.connect(
                host=parsed.hostname,
                port=parsed.port or 5432,
                user=parsed.username,
                password=parsed.password,
                database=parsed.path.lstrip('/').split('?')[0] or 'postgres',
                sslmode='prefer'
            )
        
        # First, check what tables exist
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Get all tables
            cur.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_type = 'BASE TABLE'
                ORDER BY table_name;
            """)
            tables = [row['table_name'] for row in cur.fetchall()]
            print(f"Available tables: {', '.join(tables)}")
            
            # Check for content-related tables
            content_tables = [t for t in tables if 'content' in t.lower() or 'Content' in t]
            print(f"Content-related tables: {content_tables}")
            
            # Check table columns for ContentPiece
            if 'ContentPiece' in tables:
                cur.execute("""
                    SELECT column_name, data_type 
                    FROM information_schema.columns 
                    WHERE table_name = 'ContentPiece'
                    ORDER BY ordinal_position;
                """)
                columns = cur.fetchall()
                print(f"ContentPiece columns: {[c['column_name'] for c in columns]}")
        
        # Query using correct table names (content_file, not associated_content_files)
        query = """
            SELECT 
              c.id,
              c.content_title,
              c.description,
              c.space_id,
              c.content_type_id,
              cf.file,
              cf.thumbnail,
              cf.hls_url,
              s.name as space_name,
              c.created_at,
              c.updated_at
            FROM content c
            JOIN content_file cf ON cf.content_id = c.id
            LEFT JOIN spaces s ON s.id = c.space_id
            WHERE c.content_type_id = 3
            ORDER BY c.created_at DESC;
        """
        
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query)
            results = cur.fetchall()
            if results:
                print(f"✅ Query successful! Found {len(results)} videos")
                return [dict(row) for row in results]
            else:
                print("⚠️ Query returned no results")
                return []
    except ImportError:
        print("psycopg2 not installed. Install with: pip install psycopg2-binary")
        return None
    except Exception as e:
        print(f"Error querying database: {e}")
        return None

def process_videos(videos):
    """Process videos and map to S3"""
    processed = []
    
    for video in videos:
        file_path = video.get('file', '')
        
        # Extract hash filename
        hash_filename = None
        if file_path:
            hash_filename = file_path.split('/')[-1] if '/' in file_path else file_path
        
        # Determine S3 path
        s3_path = None
        bucket = None
        folder = None
        
        if file_path:
            if file_path.startswith('videos/'):
                bucket = 'gcmd-production'
                folder = 'videos'
                s3_path = f"s3://{bucket}/{file_path}"
            elif file_path.startswith('vimeo_videos/'):
                bucket = 'gcmd-production'
                folder = 'vimeo_videos'
                s3_path = f"s3://{bucket}/{file_path}"
        
        processed.append({
            'content_id': video.get('id'),
            'title': video.get('content_title', ''),
            'description': video.get('description', ''),
            'space_id': video.get('space_id'),
            'space_name': video.get('space_name', ''),
            'file_path': file_path,
            'hash_filename': hash_filename,
            'thumbnail': video.get('thumbnail', ''),
            'hls_url': video.get('hls_url', ''),
            's3_path': s3_path,
            'bucket': bucket,
            'folder': folder,
            'created_at': str(video.get('created_at', '')),
            'updated_at': str(video.get('updated_at', ''))
        })
    
    return processed

if __name__ == "__main__":
    print("=" * 60)
    print("Fetch Video Metadata from Database")
    print("=" * 60)
    print()
    
    # Get database URL
    db_url = get_database_url()
    if not db_url:
        print("❌ Database URL not found")
        print("Please set DATABASE_URL environment variable or check .env.production")
        sys.exit(1)
    
    print(f"✅ Found database URL")
    print(f"   Host: {urlparse(db_url).hostname}")
    print()
    
    # Try Python method first (more reliable)
    print("Attempting to query database using Python...")
    videos = query_database_with_python(db_url)
    
    if not videos:
        print("Python method failed, trying psql...")
        # Fallback to psql
        query = """
        SELECT 
          c.id,
          c.content_title,
          c.description,
          c.space_id,
          cf.file,
          cf.thumbnail,
          s.name as space_name
        FROM content c
        JOIN associated_content_files cf ON cf.content_id = c.id
        LEFT JOIN spaces s ON s.id = c.space_id
        WHERE c.content_type_id = 3
        LIMIT 10;
        """
        result = query_database_with_psql(db_url, query)
        if result:
            print("✅ psql query successful")
            print("Note: Full implementation needed for CSV parsing")
            sys.exit(0)
    
    if not videos:
        print("❌ Failed to query database")
        print("\nTroubleshooting:")
        print("1. Check database credentials")
        print("2. Install psycopg2: pip install psycopg2-binary")
        print("3. Verify database connection")
        sys.exit(1)
    
    print(f"✅ Fetched {len(videos)} videos from database")
    print()
    
    # Process videos
    print("Processing video metadata...")
    processed = process_videos(videos)
    
    # Save to JSON
    json_file = "all_video_metadata_from_database.json"
    with open(json_file, 'w') as f:
        json.dump(processed, f, indent=2)
    print(f"✅ Saved to: {json_file}")
    
    # Save to Excel
    df = pd.DataFrame(processed)
    
    # Clean data for Excel (remove illegal characters)
    import re
    for col in df.columns:
        if df[col].dtype == 'object':
            df[col] = df[col].astype(str).apply(lambda x: re.sub(r'[\x00-\x08\x0B-\x0C\x0E-\x1F]', '', x) if pd.notna(x) else x)
    
    excel_file = "all_video_metadata_from_database.xlsx"
    with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='All Videos', index=False)
        
        # Summary
        summary = {
            'Metric': [
                'Total Videos',
                'Videos with Titles',
                'Videos with Descriptions',
                'Unique Spaces',
                'Videos in gcmd-production/videos',
                'Videos in gcmd-production/vimeo_videos'
            ],
            'Value': [
                len(df),
                len(df[df['title'] != '']),
                len(df[df['description'] != '']),
                df['space_name'].nunique(),
                len(df[df['folder'] == 'videos']),
                len(df[df['folder'] == 'vimeo_videos'])
            ]
        }
        summary_df = pd.DataFrame(summary)
        summary_df.to_excel(writer, sheet_name='Summary', index=False)
    
    print(f"✅ Saved to: {excel_file}")
    
    # Show summary
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"Total videos: {len(processed)}")
    print(f"Videos with titles: {len([v for v in processed if v['title']])}")
    print(f"Videos with descriptions: {len([v for v in processed if v['description']])}")
    print(f"Videos with S3 paths: {len([v for v in processed if v['s3_path']])}")
    print(f"Unique spaces: {df['space_name'].nunique()}")
    
    print("\nSample videos:")
    for video in processed[:5]:
        print(f"  - {video['title']} (ID: {video['content_id']})")
        print(f"    S3: {video['s3_path']}")

