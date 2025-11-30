# Elasticsearch Setup Guide

This guide will help you set up Elasticsearch for intelligent fuzzy search in the video library.

## Quick Start (Docker - Recommended)

The easiest way to run Elasticsearch is using Docker:

```bash
# Pull and run Elasticsearch
docker run -d \
  --name elasticsearch \
  -p 9200:9200 \
  -p 9300:9300 \
  -e "discovery.type=single-node" \
  -e "xpack.security.enabled=false" \
  -e "ES_JAVA_OPTS=-Xms512m -Xmx512m" \
  docker.elastic.co/elasticsearch/elasticsearch:8.11.0
```

Wait a few seconds for Elasticsearch to start, then verify it's running:

```bash
curl http://localhost:9200
```

You should see a JSON response with cluster information.

## Alternative: Install Elasticsearch Locally

### macOS (using Homebrew)

```bash
brew tap elastic/tap
brew install elastic/tap/elasticsearch-full
brew services start elastic/tap/elasticsearch-full
```

### Linux

```bash
# Download and install
wget https://artifacts.elastic.co/downloads/elasticsearch/elasticsearch-8.11.0-linux-x86_64.tar.gz
tar -xzf elasticsearch-8.11.0-linux-x86_64.tar.gz
cd elasticsearch-8.11.0
./bin/elasticsearch
```

## Install Python Dependencies

```bash
cd ~/lab/designer/content_transcriptions
source venv/bin/activate
pip install -r requirements.txt
```

## Start the Video Library Server

```bash
python3 video_library_app.py
```

The server will automatically:
1. Connect to Elasticsearch (if running)
2. Create the index with fuzzy search mapping
3. Index all videos for intelligent search

## Verify Elasticsearch is Working

Check the server logs when starting. You should see:
- ✅ Elasticsearch connection successful
- ✅ Created Elasticsearch index 'video_library'
- ✅ Successfully indexed X videos in Elasticsearch

## Test Fuzzy Search

Try searching with typos:
- Search "surgry" (typo for "surgery") - should still find results
- Search "pediatric" (typo for "pediatric") - should find matches
- Search "AI tols" (typo for "AI tools") - should find relevant videos

## Disable Elasticsearch (Fallback Mode)

If you don't want to use Elasticsearch, the app will automatically fall back to basic search:

```bash
export ELASTICSEARCH_ENABLED=false
python3 video_library_app.py
```

Or set it in the code by changing:
```python
ELASTICSEARCH_ENABLED = False
```

## Configuration

You can configure Elasticsearch connection via environment variables:

```bash
export ELASTICSEARCH_HOST=localhost
export ELASTICSEARCH_PORT=9200
export ELASTICSEARCH_ENABLED=true
```

## Troubleshooting

**Elasticsearch won't start?**
- Check if port 9200 is already in use: `lsof -i :9200`
- Make sure you have enough memory (Elasticsearch needs at least 512MB)

**Connection errors?**
- Verify Elasticsearch is running: `curl http://localhost:9200`
- Check firewall settings
- Ensure Elasticsearch is accessible from your application

**Indexing fails?**
- Check Elasticsearch logs
- Verify you have enough disk space
- Try deleting and recreating the index

**Search not working?**
- Check server logs for errors
- Verify videos were indexed (check Elasticsearch: `curl http://localhost:9200/video_library/_count`)
- The app will automatically fall back to basic search if Elasticsearch fails

## Features

With Elasticsearch enabled, you get:
- ✅ **Fuzzy matching** - Finds results even with typos
- ✅ **Relevance scoring** - Most relevant results first
- ✅ **Fast search** - Optimized for large datasets
- ✅ **Phrase matching** - Finds exact phrases
- ✅ **Automatic fallback** - Uses basic search if Elasticsearch unavailable

