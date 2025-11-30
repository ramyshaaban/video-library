#!/bin/bash
# Setup script for Elasticsearch with Docker

echo "🚀 Setting up Elasticsearch for Video Library..."
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first:"
    echo "   https://docs.docker.com/get-docker/"
    exit 1
fi

# Check if Elasticsearch container already exists
if docker ps -a --format '{{.Names}}' | grep -q "^elasticsearch$"; then
    echo "⚠️  Elasticsearch container already exists"
    read -p "Do you want to remove and recreate it? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Stopping and removing existing container..."
        docker stop elasticsearch 2>/dev/null
        docker rm elasticsearch 2>/dev/null
    else
        echo "Starting existing container..."
        docker start elasticsearch
        echo "✅ Elasticsearch should be running on http://localhost:9200"
        exit 0
    fi
fi

# Pull and run Elasticsearch
echo "Pulling Elasticsearch image..."
docker pull docker.elastic.co/elasticsearch/elasticsearch:8.11.0

echo "Starting Elasticsearch container..."
docker run -d \
  --name elasticsearch \
  -p 9200:9200 \
  -p 9300:9300 \
  -e "discovery.type=single-node" \
  -e "xpack.security.enabled=false" \
  -e "ES_JAVA_OPTS=-Xms512m -Xmx512m" \
  docker.elastic.co/elasticsearch/elasticsearch:8.11.0

# Wait for Elasticsearch to be ready
echo "Waiting for Elasticsearch to start..."
sleep 10

# Check if Elasticsearch is responding
max_attempts=30
attempt=0
while [ $attempt -lt $max_attempts ]; do
    if curl -s http://localhost:9200 > /dev/null 2>&1; then
        echo "✅ Elasticsearch is running!"
        echo ""
        echo "You can verify it's working by running:"
        echo "  curl http://localhost:9200"
        echo ""
        echo "Next steps:"
        echo "1. Install Python dependencies: pip install -r requirements.txt"
        echo "2. Start the video library server: python3 video_library_app.py"
        echo ""
        echo "The server will automatically index all videos on startup."
        exit 0
    fi
    attempt=$((attempt + 1))
    echo "   Attempt $attempt/$max_attempts - waiting for Elasticsearch..."
    sleep 2
done

echo "❌ Elasticsearch failed to start. Please check the logs:"
echo "   docker logs elasticsearch"
exit 1

