#!/usr/bin/env python3
"""
Create a standalone HTML video library with embedded data
No server needed - just open the HTML file!
Writes incrementally to avoid memory issues.
"""
import json
import re
from collections import defaultdict

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

def strip_html(html):
    """Strip HTML tags"""
    if not html:
        return ''
    return re.sub(r'<[^>]+>', '', html)

# Load and process data
print("Loading video data...")
videos = load_video_data()
spaces_dict = categorize_by_space(videos)
total_videos = len(videos)
total_spaces = len(spaces_dict)
print(f"✅ Loaded {total_videos} videos across {total_spaces} spaces")

# Open output file for writing
output_file = 'video_library_final.html'
print(f"Writing HTML file (this may take a moment for {total_videos} videos)...")

with open(output_file, 'w', encoding='utf-8') as f:
    # Write HTML header
    f.write('''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>StayCurrentMD Video Library</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container { max-width: 1400px; margin: 0 auto; }
        header {
            background: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        h1 { color: #333; margin-bottom: 10px; }
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
        .stat-label { font-size: 14px; color: #666; margin-bottom: 5px; }
        .stat-value { font-size: 24px; font-weight: bold; color: #333; }
        .back-button {
            background: #667eea;
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 8px;
            font-size: 16px;
            cursor: pointer;
            margin-bottom: 20px;
        }
        .back-button:hover { background: #5568d3; }
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
        .space-title { font-size: 28px; color: #333; margin-bottom: 5px; }
        .space-count { color: #666; font-size: 16px; }
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
        .hidden { display: none; }
        #spaces-view { display: block; }
        #videos-view { display: none; }
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
                    <div class="stat-value" id="total-videos">''' + str(total_videos) + '''</div>
                </div>
                <div class="stat">
                    <div class="stat-label">Total Spaces</div>
                    <div class="stat-value" id="total-spaces">''' + str(total_spaces) + '''</div>
                </div>
                <div class="stat">
                    <div class="stat-label">Last Updated</div>
                    <div class="stat-value" style="font-size: 16px;" id="last-updated">-</div>
                </div>
            </div>
            <input type="text" class="search-box" id="search-box" placeholder="Search spaces or videos...">
        </header>
        
        <div id="spaces-view">
            <div class="spaces-grid" id="spaces-grid"></div>
        </div>
        
        <div id="videos-view" class="hidden">
            <button class="back-button" onclick="showSpaces()">← Back to Spaces</button>
            <div class="videos-container">
                <div class="space-header">
                    <div class="space-title" id="current-space-title">Space Name</div>
                    <div class="space-count" id="current-space-count">0 videos</div>
                </div>
                <div class="videos-grid" id="videos-grid"></div>
                <div class="pagination" id="pagination"></div>
            </div>
        </div>
    </div>
    
    <script>
        // Embedded video data
        const videoData = {
''')
    
    # Write video data incrementally
    space_count = 0
    for space_name, space_videos in sorted(spaces_dict.items(), key=lambda x: len(x[1]), reverse=True):
        space_count += 1
        if space_count % 10 == 0:
            print(f"  Processing space {space_count}/{total_spaces}...")
        
        space_name_js = json.dumps(space_name)
        f.write(f'            {space_name_js}: [\n')
        
        for video in sorted(space_videos, key=lambda x: x.get('created_at', ''), reverse=True):
            title = json.dumps(video.get('title', 'Untitled'))
            desc = video.get('description') or ''
            desc_clean = strip_html(desc)[:200] if desc else 'No description available'
            desc_js = json.dumps(desc_clean)
            video_id = video.get('content_id', 0)
            created = video.get('created_at', '')[:10] if video.get('created_at') else 'Unknown date'
            created_js = json.dumps(created)
            
            f.write(f'''                {{
                    id: {video_id},
                    title: {title},
                    description: {desc_js},
                    created_at: {created_js}
                }},
''')
        
        f.write('            ],\n')
    
    # Write JavaScript code
    f.write('''        };
        
        // State
        let currentSpace = null;
        let currentPage = 1;
        let currentSearch = '';
        const VIDEOS_PER_PAGE = 24;
        
        // Initialize
        function init() {
            document.getElementById('last-updated').textContent = new Date().toLocaleDateString();
            renderSpaces();
        }
        
        // Render spaces
        function renderSpaces() {
            const grid = document.getElementById('spaces-grid');
            grid.innerHTML = '';
            
            const spaces = Object.keys(videoData).sort((a, b) => 
                videoData[b].length - videoData[a].length
            );
            
            spaces.forEach(spaceName => {
                const card = document.createElement('div');
                card.className = 'space-card';
                card.innerHTML = `
                    <div class="space-card-title">${escapeHtml(spaceName)}</div>
                    <div class="space-card-count">${videoData[spaceName].length} videos</div>
                `;
                card.onclick = () => showVideos(spaceName);
                grid.appendChild(card);
            });
        }
        
        // Show spaces view
        function showSpaces() {
            document.getElementById('spaces-view').classList.remove('hidden');
            document.getElementById('videos-view').classList.add('hidden');
            document.getElementById('search-box').value = '';
            currentSearch = '';
            filterSpaces();
        }
        
        // Show videos for a space
        function showVideos(spaceName) {
            currentSpace = spaceName;
            currentPage = 1;
            currentSearch = '';
            
            document.getElementById('spaces-view').classList.add('hidden');
            document.getElementById('videos-view').classList.remove('hidden');
            document.getElementById('current-space-title').textContent = spaceName;
            document.getElementById('search-box').value = '';
            
            renderVideos();
        }
        
        // Render videos for current page
        function renderVideos() {
            if (!currentSpace || !videoData[currentSpace]) return;
            
            let videos = videoData[currentSpace];
            
            // Filter by search
            if (currentSearch) {
                const searchLower = currentSearch.toLowerCase();
                videos = videos.filter(video => 
                    (video.title || '').toLowerCase().includes(searchLower) ||
                    (video.description || '').toLowerCase().includes(searchLower)
                );
            }
            
            const total = videos.length;
            const totalPages = Math.ceil(total / VIDEOS_PER_PAGE);
            const start = (currentPage - 1) * VIDEOS_PER_PAGE;
            const end = start + VIDEOS_PER_PAGE;
            const pageVideos = videos.slice(start, end);
            
            document.getElementById('current-space-count').textContent = 
                `${total} videos${currentSearch ? ' (filtered)' : ''}`;
            
            const grid = document.getElementById('videos-grid');
            grid.innerHTML = '';
            
            if (pageVideos.length === 0) {
                grid.innerHTML = '<div style="text-align: center; padding: 40px; color: #666;">No videos found.</div>';
            } else {
                pageVideos.forEach(video => {
                    const card = document.createElement('div');
                    card.className = 'video-card';
                    card.innerHTML = `
                        <div class="video-title">${escapeHtml(video.title)}</div>
                        <div class="video-description">${escapeHtml(video.description)}</div>
                        <div class="video-meta">
                            <span class="video-id">ID: ${video.id}</span> • ${video.created_at}
                        </div>
                    `;
                    grid.appendChild(card);
                });
            }
            
            renderPagination(total, totalPages);
            window.scrollTo({ top: 0, behavior: 'smooth' });
        }
        
        // Render pagination
        function renderPagination(total, totalPages) {
            const paginationEl = document.getElementById('pagination');
            paginationEl.innerHTML = '';
            
            if (totalPages <= 1) return;
            
            // Previous button
            const prevBtn = document.createElement('button');
            prevBtn.textContent = '← Previous';
            prevBtn.disabled = currentPage === 1;
            prevBtn.onclick = () => {
                if (currentPage > 1) {
                    currentPage--;
                    renderVideos();
                }
            };
            paginationEl.appendChild(prevBtn);
            
            // Page numbers
            const maxVisible = 7;
            let startPage = Math.max(1, currentPage - Math.floor(maxVisible / 2));
            let endPage = Math.min(totalPages, startPage + maxVisible - 1);
            
            if (endPage - startPage < maxVisible - 1) {
                startPage = Math.max(1, endPage - maxVisible + 1);
            }
            
            if (startPage > 1) {
                const firstBtn = document.createElement('button');
                firstBtn.textContent = '1';
                firstBtn.onclick = () => { currentPage = 1; renderVideos(); };
                paginationEl.appendChild(firstBtn);
                if (startPage > 2) {
                    const ellipsis = document.createElement('span');
                    ellipsis.textContent = '...';
                    ellipsis.className = 'pagination-info';
                    paginationEl.appendChild(ellipsis);
                }
            }
            
            for (let i = startPage; i <= endPage; i++) {
                const pageBtn = document.createElement('button');
                pageBtn.textContent = i;
                pageBtn.className = i === currentPage ? 'active' : '';
                pageBtn.onclick = () => { currentPage = i; renderVideos(); };
                paginationEl.appendChild(pageBtn);
            }
            
            if (endPage < totalPages) {
                if (endPage < totalPages - 1) {
                    const ellipsis = document.createElement('span');
                    ellipsis.textContent = '...';
                    ellipsis.className = 'pagination-info';
                    paginationEl.appendChild(ellipsis);
                }
                const lastBtn = document.createElement('button');
                lastBtn.textContent = totalPages;
                lastBtn.onclick = () => { currentPage = totalPages; renderVideos(); };
                paginationEl.appendChild(lastBtn);
            }
            
            // Next button
            const nextBtn = document.createElement('button');
            nextBtn.textContent = 'Next →';
            nextBtn.disabled = currentPage === totalPages;
            nextBtn.onclick = () => {
                if (currentPage < totalPages) {
                    currentPage++;
                    renderVideos();
                }
            };
            paginationEl.appendChild(nextBtn);
            
            // Page info
            const info = document.createElement('span');
            info.className = 'pagination-info';
            info.textContent = `Page ${currentPage} of ${totalPages} (${total} videos)`;
            paginationEl.appendChild(info);
        }
        
        // Filter spaces
        function filterSpaces() {
            const searchTerm = document.getElementById('search-box').value.toLowerCase();
            const cards = document.querySelectorAll('.space-card');
            
            cards.forEach(card => {
                const spaceName = card.querySelector('.space-card-title').textContent.toLowerCase();
                if (spaceName.includes(searchTerm)) {
                    card.classList.remove('hidden');
                } else {
                    card.classList.add('hidden');
                }
            });
        }
        
        // Search videos
        function searchVideos() {
            currentSearch = document.getElementById('search-box').value;
            currentPage = 1;
            renderVideos();
        }
        
        // Utility functions
        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }
        
        // Event listeners
        document.getElementById('search-box').addEventListener('input', function(e) {
            if (document.getElementById('spaces-view').classList.contains('hidden')) {
                clearTimeout(this.searchTimeout);
                this.searchTimeout = setTimeout(searchVideos, 300);
            } else {
                filterSpaces();
            }
        });
        
        // Initialize on load
        init();
    </script>
</body>
</html>''')

print(f"✅ Created standalone library: {output_file}")
print(f"   Total videos: {total_videos}")
print(f"   Total spaces: {total_spaces}")
print(f"\n📂 Just open {output_file} in your browser - no server needed!")
