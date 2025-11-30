# StayCurrentMD Video Library - Flask Application

## 🚀 Quick Start

### 1. Start the Server

```bash
cd ~/lab/designer/content_transcriptions
source venv/bin/activate
python3 video_library_app.py
```

The server will start on: **http://localhost:5000**

### 2. Open in Browser

Open your browser and navigate to:
```
http://localhost:5000
```

## ✨ Features

- ✅ **Robust Flask Backend** - Proper API endpoints
- ✅ **RESTful API** - Clean separation of data and presentation
- ✅ **Clickable Space Cards** - Works reliably with proper event handling
- ✅ **Pagination** - 24 videos per page for easy navigation
- ✅ **Search Functionality** - Search spaces or videos
- ✅ **Real-time Stats** - Total videos and spaces displayed correctly
- ✅ **Error Handling** - Proper error messages and loading states

## 📁 Files

- `video_library_app.py` - Flask application server
- `templates/library.html` - Frontend interface
- `all_video_metadata_from_database.json` - Video data source

## 🔧 API Endpoints

- `GET /` - Main library page
- `GET /api/spaces` - Get all spaces with video counts
- `GET /api/spaces/<space_name>/videos` - Get videos for a space
  - Query params: `?page=1&per_page=24&search=term`
- `GET /api/video/<video_id>` - Get specific video details

## 🎯 How It Works

1. **Spaces View**: Shows all spaces in a grid
2. **Click Space**: Loads videos for that space via API
3. **Videos View**: Shows videos in paginated grid
4. **Pagination**: Navigate through pages of videos
5. **Search**: Filter spaces or videos in real-time

## 🛠️ Troubleshooting

**Server won't start?**
- Make sure Flask is installed: `pip install flask`
- Check if port 5000 is available
- Check console for error messages

**Spaces not loading?**
- Check browser console (F12) for errors
- Verify `all_video_metadata_from_database.json` exists
- Check server logs for errors

**Videos not showing?**
- Check network tab in browser DevTools
- Verify API endpoint is responding: `curl http://localhost:5000/api/spaces`

## 📊 Advantages Over Static HTML

1. **Separation of Concerns** - Backend handles data, frontend handles UI
2. **API-Based** - Can be integrated with other applications
3. **Scalable** - Easy to add features like authentication, caching, etc.
4. **Reliable** - Proper error handling and loading states
5. **Maintainable** - Clean code structure

