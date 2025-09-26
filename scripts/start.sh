#!/bin/bash

# Start script for the unsubscribe agent with queuing system

echo "🚀 Starting Unsubscribe Agent with Queue System..."

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

# Build and start services
echo "📦 Building and starting services..."
docker-compose up --build -d

# Wait for services to be ready
echo "⏳ Waiting for services to be ready..."
sleep 10

# Check service health
echo "🔍 Checking service health..."

# Check Redis
if docker-compose exec redis redis-cli ping > /dev/null 2>&1; then
    echo "✅ Redis is running"
else
    echo "❌ Redis is not responding"
fi

# Check API
if curl -f http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ API is running"
else
    echo "❌ API is not responding"
fi

# Check Flower
if curl -f http://localhost:5555 > /dev/null 2>&1; then
    echo "✅ Flower monitoring is running"
else
    echo "❌ Flower is not responding"
fi

echo ""
echo "🎉 Services are starting up!"
echo ""
echo "📊 Available endpoints:"
echo "  • API: http://localhost:8000"
echo "  • Health: http://localhost:8000/health"
echo "  • Flower (monitoring): http://localhost:5555"
echo "  • Test endpoint: http://localhost:8000/test"
echo ""
echo "📝 Useful commands:"
echo "  • View logs: docker-compose logs -f"
echo "  • Scale workers: docker-compose up --scale worker=3"
echo "  • Stop services: docker-compose down"
echo "  • Restart: docker-compose restart"
echo ""
echo "🧪 Test the system:"
echo "  curl -X POST http://localhost:8000/test"
