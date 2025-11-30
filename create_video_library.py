#!/usr/bin/env python3
"""
Create a public video library categorized by space name
"""
import json
import pandas as pd
from collections import defaultdict
from datetime import datetime

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

def create_excel_library(spaces_dict):
    """Create Excel file with sheets for each space"""
    excel_file = "video_library_by_space.xlsx"
    
    with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:
        # Create summary sheet
        summary_data = {
            'Space Name': [],
            'Video Count': [],
            'Videos with Descriptions': [],
            'Oldest Video': [],
            'Newest Video': []
        }
        
        for space_name, videos in sorted(spaces_dict.items()):
            summary_data['Space Name'].append(space_name)
            summary_data['Video Count'].append(len(videos))
            summary_data['Videos with Descriptions'].append(
                len([v for v in videos if v.get('description')])
            )
            
            # Get date range
            dates = [v.get('created_at', '') for v in videos if v.get('created_at')]
            if dates:
                summary_data['Oldest Video'].append(min(dates))
                summary_data['Newest Video'].append(max(dates))
            else:
                summary_data['Oldest Video'].append('N/A')
                summary_data['Newest Video'].append('N/A')
        
        summary_df = pd.DataFrame(summary_data)
        summary_df.to_excel(writer, sheet_name='Summary', index=False)
        
        # Create sheet for each space
        for space_name, videos in sorted(spaces_dict.items()):
            # Clean space name for sheet name (Excel has 31 char limit)
            sheet_name = space_name[:31] if len(space_name) > 31 else space_name
            sheet_name = sheet_name.replace('/', '_').replace('\\', '_').replace('?', '_')
            
            # Prepare data
            space_data = []
            for video in sorted(videos, key=lambda x: x.get('created_at', ''), reverse=True):
                description = video.get('description') or ''
                if description:
                    description = description[:500]  # Truncate long descriptions
                
                space_data.append({
                    'ID': video.get('content_id'),
                    'Title': video.get('title', ''),
                    'Description': description,
                    'File Path': video.get('file_path', ''),
                    'Thumbnail': video.get('thumbnail', ''),
                    'HLS URL': video.get('hls_url', ''),
                    'Created At': video.get('created_at', ''),
                    'Updated At': video.get('updated_at', ''),
                    'Chapters': video.get('chapters', 0)
                })
            
            df = pd.DataFrame(space_data)
            
            # Clean data for Excel
            import re
            for col in df.columns:
                if df[col].dtype == 'object':
                    df[col] = df[col].astype(str).apply(
                        lambda x: re.sub(r'[\x00-\x08\x0B-\x0C\x0E-\x1F]', '', x) if pd.notna(x) else x
                    )
            
            df.to_excel(writer, sheet_name=sheet_name, index=False)
    
    print(f"✅ Created Excel library: {excel_file}")
    return excel_file

def create_json_library(spaces_dict):
    """Create JSON file for web/public use"""
    library = {
        'metadata': {
            'generated_at': datetime.now().isoformat(),
            'total_videos': sum(len(videos) for videos in spaces_dict.values()),
            'total_spaces': len(spaces_dict),
            'version': '1.0'
        },
        'spaces': {}
    }
    
    for space_name, videos in sorted(spaces_dict.items()):
        library['spaces'][space_name] = {
            'video_count': len(videos),
            'videos': []
        }
        
        for video in sorted(videos, key=lambda x: x.get('created_at', ''), reverse=True):
            library['spaces'][space_name]['videos'].append({
                'id': video.get('content_id'),
                'title': video.get('title', ''),
                'description': video.get('description', ''),
                'file_path': video.get('file_path', ''),
                'thumbnail': video.get('thumbnail', ''),
                'hls_url': video.get('hls_url', ''),
                'created_at': video.get('created_at', ''),
                'updated_at': video.get('updated_at', ''),
                'chapters': video.get('chapters', 0)
            })
    
    json_file = "video_library_by_space.json"
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(library, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Created JSON library: {json_file}")
    return json_file

def create_html_library(spaces_dict):
    """Create HTML file for public viewing with space navigation and pagination"""
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>StayCurrentMD Video Library</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
        }
        header {
            background: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        h1 {
            color: #333;
            margin-bottom: 10px;
        }
        .stats {
            display: flex;
            gap: 20px;
            margin-top: 20px;
            flex-wrap: wrap;
        }
        .stat {
            background: #f8f9fa;
            padding: 15px 20px;
            border-radius: 8px;
            flex: 1;
            min-width: 200px;
        }
        .stat-label {
            font-size: 14px;
            color: #666;
            margin-bottom: 5px;
        }
        .stat-value {
            font-size: 24px;
            font-weight: bold;
            color: #333;
        }
        .back-button {
            background: #667eea;
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 8px;
            font-size: 16px;
            cursor: pointer;
            margin-bottom: 20px;
            transition: background 0.2s;
        }
        .back-button:hover {
            background: #5568d3;
        }
        .spaces-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
            gap: 20px;
        }
        .space-card {
            background: white;
            border-radius: 10px;
            padding: 25px;
            cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            border: 2px solid transparent;
        }
        .space-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 8px 16px rgba(0,0,0,0.1);
            border-color: #667eea;
        }
        .space-card-title {
            font-size: 22px;
            font-weight: 600;
            color: #333;
            margin-bottom: 10px;
        }
        .space-card-count {
            color: #667eea;
            font-size: 16px;
            font-weight: 500;
        }
        .videos-container {
            background: white;
            border-radius: 10px;
            padding: 30px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        .space-header {
            border-bottom: 3px solid #667eea;
            padding-bottom: 15px;
            margin-bottom: 25px;
        }
        .space-title {
            font-size: 28px;
            color: #333;
            margin-bottom: 5px;
        }
        .space-count {
            color: #666;
            font-size: 16px;
        }
        .videos-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .video-card {
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            padding: 20px;
            transition: transform 0.2s, box-shadow 0.2s;
            background: #fafafa;
            height: 100%;
            display: flex;
            flex-direction: column;
        }
        .video-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 8px 16px rgba(0,0,0,0.1);
        }
        .video-title {
            font-size: 18px;
            font-weight: 600;
            color: #333;
            margin-bottom: 10px;
            line-height: 1.4;
        }
        .video-description {
            font-size: 14px;
            color: #666;
            line-height: 1.6;
            margin-bottom: 15px;
            display: -webkit-box;
            -webkit-line-clamp: 3;
            -webkit-box-orient: vertical;
            overflow: hidden;
            flex-grow: 1;
        }
        .video-meta {
            font-size: 12px;
            color: #999;
            margin-top: auto;
            padding-top: 10px;
            border-top: 1px solid #e0e0e0;
        }
        .video-id {
            font-family: monospace;
            background: #f0f0f0;
            padding: 2px 6px;
            border-radius: 4px;
        }
        .search-box {
            width: 100%;
            padding: 15px;
            font-size: 16px;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            margin-bottom: 20px;
        }
        .search-box:focus {
            outline: none;
            border-color: #667eea;
        }
        .pagination {
            display: flex;
            justify-content: center;
            align-items: center;
            gap: 10px;
            margin-top: 30px;
            flex-wrap: wrap;
        }
        .pagination button {
            background: white;
            border: 2px solid #e0e0e0;
            padding: 10px 16px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 14px;
            transition: all 0.2s;
        }
        .pagination button:hover:not(:disabled) {
            background: #667eea;
            color: white;
            border-color: #667eea;
        }
        .pagination button:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }
        .pagination button.active {
            background: #667eea;
            color: white;
            border-color: #667eea;
        }
        .pagination-info {
            color: #666;
            font-size: 14px;
            margin: 0 10px;
        }
        .hidden {
            display: none;
        }
        #spaces-view {
            display: block;
        }
        #videos-view {
            display: none;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>📚 StayCurrentMD Video Library</h1>
            <p>Browse videos organized by medical specialty and space</p>
            <div class="stats">
                <div class="stat">
                    <div class="stat-label">Total Videos</div>
                    <div class="stat-value" id="total-videos">0</div>
                </div>
                <div class="stat">
                    <div class="stat-label">Total Spaces</div>
                    <div class="stat-value" id="total-spaces">0</div>
                </div>
                <div class="stat">
                    <div class="stat-label">Last Updated</div>
                    <div class="stat-value" style="font-size: 16px;" id="last-updated">-</div>
                </div>
            </div>
            <input type="text" class="search-box" id="search-box" placeholder="Search spaces or videos...">
        </header>
        
        <div id="spaces-view">
            <div class="spaces-grid" id="spaces-grid">
"""
    
    # Add space cards
    total_videos = 0
    for space_name, videos in sorted(spaces_dict.items(), key=lambda x: len(x[1]), reverse=True):
        total_videos += len(videos)
        # Use JSON encoding for data attribute to match JavaScript
        import json as json_lib
        space_name_json = json_lib.dumps(space_name)[1:-1]  # Remove quotes, keep escaping
        # Use onclick that reads from data attribute to avoid quote issues
        html_content += f"""
                <div class="space-card" data-space-name="{space_name_json}" data-video-count="{len(videos)}" onclick="handleSpaceClick(this.getAttribute('data-space-name'))">
                    <div class="space-card-title">{space_name}</div>
                    <div class="space-card-count">{len(videos)} videos</div>
                </div>
"""
    
    html_content += """
            </div>
        </div>
        
        <div id="videos-view" class="hidden">
            <button class="back-button" onclick="showSpaces()">← Back to Spaces</button>
            <div class="videos-container">
                <div class="space-header">
                    <div class="space-title" id="current-space-title">Space Name</div>
                    <div class="space-count" id="current-space-count">0 videos</div>
                </div>
                <div class="videos-grid" id="videos-grid">
                    <!-- Videos will be loaded here -->
                </div>
                <div class="pagination" id="pagination">
                    <!-- Pagination will be generated here -->
                </div>
            </div>
        </div>
    </div>
    
    <script>
        // Video data storage
        const videoData = {
"""
    
    # Add video data as JSON
    import json as json_lib
    for space_name, videos in sorted(spaces_dict.items()):
        # Use JSON encoding to match the data attribute
        space_name_js = json_lib.dumps(space_name)[1:-1]  # Remove quotes, keep escaping
        html_content += f'            "{space_name_js}": [\n'
        for video in sorted(videos, key=lambda x: x.get('created_at', ''), reverse=True):
            # Properly escape strings for JavaScript
            import json as json_lib
            
            title = video.get('title', 'Untitled')
            desc = video.get('description') or ''
            if desc:
                # Strip HTML tags and limit length
                import re
                desc_clean = re.sub(r'<[^>]+>', '', desc)  # Remove HTML tags
                description = desc_clean[:200] if len(desc_clean) > 200 else desc_clean
            else:
                description = 'No description available'
            
            video_id = video.get('content_id', '')
            created_at = video.get('created_at', '')[:10] if video.get('created_at') else 'Unknown date'
            
            # Use JSON encoding for all strings to ensure proper escaping
            title_js = json_lib.dumps(title)
            desc_js = json_lib.dumps(description)
            created_js = json_lib.dumps(created_at)
            
            html_content += f"""                {{
                    id: {video_id},
                    title: {title_js},
                    description: {desc_js},
                    created_at: {created_js}
                }},\n"""
        html_content += "            ],\n"
    
    html_content += f"""        }};
        
        // Constants
        const VIDEOS_PER_PAGE = 24;
        let currentSpace = null;
        let currentPage = 1;
        
        // Initialize on page load
        function initializePage() {{
            // Set stats
            const totalVideosEl = document.getElementById('total-videos');
            const totalSpacesEl = document.getElementById('total-spaces');
            const lastUpdatedEl = document.getElementById('last-updated');
            
            if (totalVideosEl) totalVideosEl.textContent = '{total_videos}';
            if (totalSpacesEl) totalSpacesEl.textContent = '{len(spaces_dict)}';
            if (lastUpdatedEl) lastUpdatedEl.textContent = new Date().toLocaleDateString();
            
            console.log('Page initialized. Total videos:', '{total_videos}', 'Total spaces:', '{len(spaces_dict)}');
            console.log('VideoData keys:', Object.keys(videoData).length);
        }}
        
        // Run initialization
        if (document.readyState === 'loading') {{
            document.addEventListener('DOMContentLoaded', initializePage);
        }} else {{
            initializePage();
        }}
        
        // Global function to handle space clicks (called from onclick)
        function handleSpaceClick(spaceName) {{
            console.log('handleSpaceClick called with:', spaceName);
            console.log('Available spaces:', Object.keys(videoData));
            if (spaceName && videoData[spaceName]) {{
                showVideos(spaceName);
            }} else {{
                console.error('Space not found:', spaceName);
                alert('Error: Could not load videos for "' + spaceName + '".\\n\\nAvailable spaces: ' + Object.keys(videoData).slice(0, 5).join(', ') + '...');
            }}
        }}
        
        // Also attach event listeners as backup
        function attachSpaceCardHandlers() {{
            const cards = document.querySelectorAll('.space-card');
            console.log('Found', cards.length, 'space cards');
            cards.forEach(card => {{
                // Only add if onclick is not already set
                if (!card.onclick) {{
                    card.addEventListener('click', function(e) {{
                        e.preventDefault();
                        e.stopPropagation();
                        const spaceName = this.getAttribute('data-space-name');
                        handleSpaceClick(spaceName);
                    }});
                }}
            }});
        }}
        
        // Attach handlers when DOM is ready
        if (document.readyState === 'loading') {{
            document.addEventListener('DOMContentLoaded', function() {{
                attachSpaceCardHandlers();
                // Set stats again in case DOM wasn't ready
                try {{
                    document.getElementById('total-videos').textContent = '{total_videos}';
                    document.getElementById('total-spaces').textContent = '{len(spaces_dict)}';
                    document.getElementById('last-updated').textContent = new Date().toLocaleDateString();
                }} catch(e) {{
                    console.error('Error setting stats on DOMContentLoaded:', e);
                }}
            }});
        }} else {{
            // DOM already loaded
            setTimeout(function() {{
                attachSpaceCardHandlers();
            }}, 100);
        }}
        
        // Show spaces view
        function showSpaces() {{
            document.getElementById('spaces-view').classList.remove('hidden');
            document.getElementById('videos-view').classList.add('hidden');
            document.getElementById('search-box').value = '';
            filterSpaces();
        }}
        
        // Show videos for a space
        function showVideos(spaceName) {{
            currentSpace = spaceName;
            currentPage = 1;
            document.getElementById('spaces-view').classList.add('hidden');
            document.getElementById('videos-view').classList.remove('hidden');
            document.getElementById('current-space-title').textContent = spaceName;
            document.getElementById('current-space-count').textContent = videoData[spaceName].length + ' videos';
            renderVideos();
        }}
        
        // Render videos for current page
        function renderVideos() {{
            if (!currentSpace || !videoData[currentSpace]) return;
            
            const videos = videoData[currentSpace];
            const startIndex = (currentPage - 1) * VIDEOS_PER_PAGE;
            const endIndex = startIndex + VIDEOS_PER_PAGE;
            const pageVideos = videos.slice(startIndex, endIndex);
            
            const grid = document.getElementById('videos-grid');
            grid.innerHTML = '';
            
            pageVideos.forEach(video => {{
                const card = document.createElement('div');
                card.className = 'video-card';
                card.innerHTML = `
                    <div class="video-title">${{video.title}}</div>
                    <div class="video-description">${{video.description}}</div>
                    <div class="video-meta">
                        <span class="video-id">ID: ${{video.id}}</span> • ${{video.created_at}}
                    </div>
                `;
                grid.appendChild(card);
            }});
            
            renderPagination(videos.length);
        }}
        
        // Render pagination
        function renderPagination(totalVideos) {{
            const totalPages = Math.ceil(totalVideos / VIDEOS_PER_PAGE);
            const pagination = document.getElementById('pagination');
            pagination.innerHTML = '';
            
            if (totalPages <= 1) return;
            
            // Previous button
            const prevBtn = document.createElement('button');
            prevBtn.textContent = '← Previous';
            prevBtn.disabled = currentPage === 1;
            prevBtn.onclick = () => {{
                if (currentPage > 1) {{
                    currentPage--;
                    renderVideos();
                    window.scrollTo({{ top: 0, behavior: 'smooth' }});
                }}
            }};
            pagination.appendChild(prevBtn);
            
            // Page numbers
            const maxVisiblePages = 7;
            let startPage = Math.max(1, currentPage - Math.floor(maxVisiblePages / 2));
            let endPage = Math.min(totalPages, startPage + maxVisiblePages - 1);
            
            if (endPage - startPage < maxVisiblePages - 1) {{
                startPage = Math.max(1, endPage - maxVisiblePages + 1);
            }}
            
            if (startPage > 1) {{
                const firstBtn = document.createElement('button');
                firstBtn.textContent = '1';
                firstBtn.onclick = () => {{
                    currentPage = 1;
                    renderVideos();
                    window.scrollTo({{ top: 0, behavior: 'smooth' }});
                }};
                pagination.appendChild(firstBtn);
                if (startPage > 2) {{
                    const ellipsis = document.createElement('span');
                    ellipsis.textContent = '...';
                    ellipsis.className = 'pagination-info';
                    pagination.appendChild(ellipsis);
                }}
            }}
            
            for (let i = startPage; i <= endPage; i++) {{
                const pageBtn = document.createElement('button');
                pageBtn.textContent = i;
                pageBtn.className = i === currentPage ? 'active' : '';
                pageBtn.onclick = () => {{
                    currentPage = i;
                    renderVideos();
                    window.scrollTo({{ top: 0, behavior: 'smooth' }});
                }};
                pagination.appendChild(pageBtn);
            }}
            
            if (endPage < totalPages) {{
                if (endPage < totalPages - 1) {{
                    const ellipsis = document.createElement('span');
                    ellipsis.textContent = '...';
                    ellipsis.className = 'pagination-info';
                    pagination.appendChild(ellipsis);
                }}
                const lastBtn = document.createElement('button');
                lastBtn.textContent = totalPages;
                lastBtn.onclick = () => {{
                    currentPage = totalPages;
                    renderVideos();
                    window.scrollTo({{ top: 0, behavior: 'smooth' }});
                }};
                pagination.appendChild(lastBtn);
            }}
            
            // Next button
            const nextBtn = document.createElement('button');
            nextBtn.textContent = 'Next →';
            nextBtn.disabled = currentPage === totalPages;
            nextBtn.onclick = () => {{
                if (currentPage < totalPages) {{
                    currentPage++;
                    renderVideos();
                    window.scrollTo({{ top: 0, behavior: 'smooth' }});
                }}
            }};
            pagination.appendChild(nextBtn);
            
            // Page info
            const info = document.createElement('span');
            info.className = 'pagination-info';
            info.textContent = `Page ${{currentPage}} of ${{totalPages}} (${{totalVideos}} videos)`;
            pagination.appendChild(info);
        }}
        
        // Search functionality for spaces
        function filterSpaces() {{
            const searchTerm = document.getElementById('search-box').value.toLowerCase();
            const spaceCards = document.querySelectorAll('.space-card');
            
            spaceCards.forEach(card => {{
                const spaceName = card.getAttribute('data-space-name').toLowerCase();
                if (spaceName.includes(searchTerm)) {{
                    card.classList.remove('hidden');
                }} else {{
                    card.classList.add('hidden');
                }}
            }});
        }}
        
        // Search functionality for videos
        function filterVideos() {{
            if (!currentSpace) return;
            
            const searchTerm = document.getElementById('search-box').value.toLowerCase();
            const videos = videoData[currentSpace];
            const filteredVideos = videos.filter(video => 
                video.title.toLowerCase().includes(searchTerm) || 
                video.description.toLowerCase().includes(searchTerm)
            );
            
            // Temporarily replace videoData for this space
            const originalVideos = videoData[currentSpace];
            videoData[currentSpace] = filteredVideos;
            currentPage = 1;
            renderVideos();
            videoData[currentSpace] = originalVideos;
        }}
        
        // Search box event listener
        document.getElementById('search-box').addEventListener('input', function(e) {{
            if (document.getElementById('spaces-view').classList.contains('hidden')) {{
                filterVideos();
            }} else {{
                filterSpaces();
            }}
        }});
        
        // Fallback: Set stats immediately if elements exist
        (function() {{
            try {{
                const vEl = document.getElementById('total-videos');
                const sEl = document.getElementById('total-spaces');
                const dEl = document.getElementById('last-updated');
                if (vEl) vEl.textContent = '{total_videos}';
                if (sEl) sEl.textContent = '{len(spaces_dict)}';
                if (dEl) dEl.textContent = new Date().toLocaleDateString();
            }} catch(e) {{
                console.error('Fallback stats error:', e);
            }}
        }})();
    </script>
</body>
</html>
"""
    
    html_file = "video_library.html"
    with open(html_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"✅ Created HTML library: {html_file}")
    return html_file

if __name__ == "__main__":
    print("=" * 60)
    print("Creating Public Video Library by Space")
    print("=" * 60)
    print()
    
    # Load data
    print("Loading video data...")
    videos = load_video_data()
    print(f"✅ Loaded {len(videos)} videos")
    print()
    
    # Categorize by space
    print("Categorizing videos by space...")
    spaces_dict = categorize_by_space(videos)
    print(f"✅ Found {len(spaces_dict)} spaces")
    print()
    
    # Show summary
    print("Space Summary:")
    for space_name, space_videos in sorted(spaces_dict.items(), key=lambda x: len(x[1]), reverse=True):
        print(f"  {space_name}: {len(space_videos)} videos")
    print()
    
    # Create outputs
    print("Creating library files...")
    excel_file = create_excel_library(spaces_dict)
    json_file = create_json_library(spaces_dict)
    html_file = create_html_library(spaces_dict)
    
    print()
    print("=" * 60)
    print("✅ Library Creation Complete!")
    print("=" * 60)
    print()
    print("Files created:")
    print(f"  📊 {excel_file} - Excel file with sheets per space")
    print(f"  📄 {json_file} - JSON file for programmatic access")
    print(f"  🌐 {html_file} - HTML file for public viewing")
    print()
    print("You can open the HTML file in a browser to view the library!")

