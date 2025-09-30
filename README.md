# Unsubscribe Agent

Automates unsubscribing from marketing/notification emails using AI-powered browser automation. Simply forward emails to the service and it will automatically find and click unsubscribe links.

## 🚀 Features

- **Email Processing**: Forward emails via webhook endpoint
- **AI-Powered**: Uses LLM to intelligently identify unsubscribe links
- **Browser Automation**: Automated browser navigation and form filling
- **Task Queue**: Background processing with Celery and Redis
- **Docker Ready**: Complete containerized setup
- **Monitoring**: Flower dashboard for task monitoring
- **API Documentation**: Interactive Swagger/OpenAPI docs

## 📋 Requirements

- Python 3.13+
- Docker & Docker Compose (recommended)
- Google API Key for LLM (configure via `.env`)

## 🛠️ Quick Start

### Option 1: Docker Compose (Recommended)

1. **Clone and setup**:
```bash
git clone <repository>
cd unsubscribe-agent
cp .env.example .env
# Edit .env and add your GOOGLE_API_KEY
```

2. **Start services**:
```bash
# Make the script executable and run it
chmod +x scripts/start.sh
./scripts/start.sh
```

The script will:
- ✅ Check Docker is running
- 📦 Build and start all services
- ⏳ Wait for services to be ready
- 🔍 Verify all services are healthy
- 📊 Show you all available endpoints
- 🧪 Provide test commands

3. **Access dashboards**:
- **API Documentation**: http://localhost:8000/docs
- **Task Monitoring**: http://localhost:5555 (Flower)
- **Examples**: http://localhost:8000/examples

### Option 2: Local Development

1. **Install dependencies**:
```bash
uv sync  # or: pip install -e .
```

2. **Start Redis** (required for task queue):
```bash
# Using Docker
docker run -d -p 6379:6379 redis:alpine

# Or install locally
brew install redis  # macOS
sudo apt install redis-server  # Ubuntu
```

3. **Start services**:
```bash
# Terminal 1: Start FastAPI
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2: Start Celery worker
uv run celery -A app.celery_app worker --loglevel=info --concurrency=2

# Terminal 3: Start Flower (optional)
uv run celery -A app.celery_app flower --port=5555
```

## 📧 How to Use

### 1. Forward an Email
Send a POST request to `/webhook` with email data:

```bash
curl -X POST http://localhost:8000/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "subject": "FWD: Newsletter from Company",
    "from_email": "newsletter@company.com",
    "to_email": "user@example.com",
    "headers": [
      {"name": "From", "value": "newsletter@company.com"},
      {"name": "To", "value": "user@example.com"},
      {"name": "Subject", "value": "FWD: Newsletter from Company"}
    ],
    "body": {
      "text": "Email content with unsubscribe links...",
      "html": "<html>Email HTML with unsubscribe links...</html>"
    }
  }'
```

### 2. Check Task Status
```bash
curl http://localhost:8000/task/{task_id}
```

### 3. View Results
The response will show:
- Total links found
- Successful unsubscribes
- Failed attempts with error messages
- Detailed results for each link

## 🔧 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Service status and links |
| `/health` | GET | Health check with worker status |
| `/webhook` | POST | Process forwarded email |
| `/task/{task_id}` | GET | Check task status and results |
| `/test` | POST | Quick test with mock data |
| `/examples` | GET | Ready-to-use curl commands |
| `/docs` | GET | Interactive API documentation |

## 🐳 Docker Services

The Docker Compose setup includes:

- **app**: FastAPI web server (port 8000)
- **worker**: Celery worker for background processing
- **redis**: Message broker and result backend (port 6379)
- **flower**: Task monitoring dashboard (port 5555)

### 🛠️ Management Commands

```bash
# View logs
docker-compose logs -f

# Scale workers (for more concurrent processing)
docker-compose up --scale worker=3

# Stop services
docker-compose down

# Restart services
docker-compose restart

# Rebuild and restart
docker-compose up --build -d
```

## 📊 Monitoring

### Flower Dashboard
Access at http://localhost:5555 to monitor:
- Active tasks
- Task history
- Worker status
- Task results

### Health Checks
```bash
# Check overall health
curl http://localhost:8000/health

# Check specific task
curl http://localhost:8000/task/{task_id}
```

## ⚙️ Configuration

Create `.env` file:
```bash
# Required
GOOGLE_API_KEY=your_google_api_key_here

# Optional
LOG_LEVEL=INFO
REDIS_URL=redis://localhost:6379
USE_LLM_ONLY=false
HEADLESS=true
```

## 🧪 Testing

### Quick Test
```bash
curl -X POST http://localhost:8000/test
```

### Full Test
```bash
# Get examples
curl http://localhost:8000/examples

# Use the provided curl commands to test with real data
```

## 🔍 How It Works

1. **Email Processing**: Extracts unsubscribe links from forwarded emails
2. **Link Analysis**: Uses LLM to identify the best unsubscribe links
3. **Browser Automation**: Launches browser and navigates to unsubscribe pages
4. **Form Filling**: Automatically fills forms and clicks unsubscribe buttons
5. **Result Tracking**: Returns detailed results for each attempt

## 🚨 Important Notes

- **Forwarded Emails Only**: The service only processes forwarded emails
- **User-Specific Links**: Each unsubscribe link is unique and cannot be cached
- **Browser Automation**: Requires proper browser setup (handled automatically in Docker)
- **Rate Limiting**: Built-in rate limiting to avoid overwhelming unsubscribe pages

## 🛠️ Development

### Project Structure
```
app/
├── main.py              # FastAPI application
├── celery_app.py        # Celery configuration
├── tasks.py             # Background tasks
├── handlers/            # Email processing
├── services/            # Business logic
├── types/               # Data models
└── tools/               # Utilities
```

### Adding New Features
1. Add new endpoints in `app/main.py`
2. Create background tasks in `app/tasks.py`
3. Update documentation in README.md
4. Test with Docker Compose

## 📝 License

MIT

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test with Docker Compose
5. Submit a pull request

---

**Ready to test?** Start with `docker-compose up -d` and visit http://localhost:8000/docs for the interactive API documentation!