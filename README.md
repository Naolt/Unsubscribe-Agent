# Unsubscribe Agent

Automates unsubscribing from marketing/notification emails using AI-powered browser automation. Simply forward emails to the service and it will automatically find and click unsubscribe links.

## 🚀 Features

- **Email Processing**: Forward emails via webhook endpoint
- **AI-Powered**: Uses configurable LLM providers (Google Gemini, OpenAI, Anthropic) for email analysis
- **Browser Automation**: Automated browser navigation with configurable AI models (Ollama, Gemini)
- **Flexible Configuration**: Mix and match providers for email processing vs browser automation
- **Task Queue**: Background processing with Celery and Redis
- **Docker Ready**: Complete containerized setup
- **Monitoring**: Flower dashboard for task monitoring
- **API Documentation**: Interactive Swagger/OpenAPI docs

## 📋 Requirements

- Python 3.13+
- Docker & Docker Compose (recommended)
- API Key for your chosen LLM provider (configure via `.env`)
  - Google API Key (for Gemini)
  - OpenAI API Key (for GPT models)
  - Anthropic API Key (for Claude models)
  - Ollama (for local models - no API key needed)

## 🛠️ Quick Start

### Option 1: Docker Compose (Recommended)

1. **Clone and setup**:
```bash
git clone <repository>
cd unsubscribe-agent
cp env.example .env
# Edit .env and configure your LLM providers
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

Create `.env` file with your preferred LLM providers:

### Quick Setup (Hybrid - Recommended)
```bash
# Email processing with Gemini
LLM_MODEL_PROVIDER=google_genai
LLM_MODEL_NAME=gemini-2.5-flash
GOOGLE_API_KEY=your_google_api_key_here

# Browser automation with Ollama (local)
BROWSER_LLM_PROVIDER=ollama
BROWSER_MODEL_NAME=llama3.2:3b

# Optional settings
LOG_LEVEL=INFO
REDIS_URL=redis://localhost:6379
USE_LLM_ONLY=false
HEADLESS=true
```

### All-Gemini Setup
```bash
# Use Gemini for both email processing and browser automation
LLM_MODEL_PROVIDER=google_genai
LLM_MODEL_NAME=gemini-2.5-flash
GOOGLE_API_KEY=your_google_api_key_here
BROWSER_LLM_PROVIDER=gemini
BROWSER_MODEL_NAME=gemini-2.5-flash
```

### All-Local Setup
```bash
# Ollama for browser automation (external provider still needed for email)
LLM_MODEL_PROVIDER=google_genai
LLM_MODEL_NAME=gemini-2.5-flash
GOOGLE_API_KEY=your_google_api_key_here
BROWSER_LLM_PROVIDER=ollama
BROWSER_MODEL_NAME=tinyllama:1.1b
```

For complete configuration options, see [LLM Configuration Guide](docs/LLM_CONFIG.md).

## 🧪 Testing

### Quick Test
```bash
curl -X POST http://localhost:8000/test
```

### Browser Automation Test
```bash
# Test browser automation with your configured model
uv run test_browser_use.py
```

### Full Test
```bash
# Get examples
curl http://localhost:8000/examples

# Use the provided curl commands to test with real data
```

## 🔍 How It Works

1. **Email Processing**: Extracts unsubscribe links from forwarded emails using configurable LLM providers
2. **Link Analysis**: Uses AI to intelligently identify the best unsubscribe links
3. **Browser Automation**: Launches browser and navigates to unsubscribe pages using configurable AI models
4. **Form Filling**: Automatically fills forms and clicks unsubscribe buttons
5. **Result Tracking**: Returns detailed results for each attempt

### AI Model Usage
- **Email Analysis**: Uses external LLM providers (Gemini, GPT, Claude) to analyze email content and identify unsubscribe links
- **Browser Automation**: Uses configurable models (Ollama for local, Gemini for external) to control browser interactions
- **Flexible Setup**: Mix and match providers based on your needs (privacy, cost, performance)

## 🚨 Important Notes

- **Forwarded Emails Only**: The service only processes forwarded emails
- **User-Specific Links**: Each unsubscribe link is unique and cannot be cached
- **Browser Automation**: Requires proper browser setup (handled automatically in Docker)
- **Rate Limiting**: Built-in rate limiting to avoid overwhelming unsubscribe pages
- **Model Configuration**: Choose your AI models based on privacy, cost, and performance needs
- **Local vs External**: Use Ollama for local privacy or external providers for better performance

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