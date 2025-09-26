# Queue System Implementation

This document describes the queuing system implementation for the Unsubscribe Agent.

## Overview

The queue system uses **Redis + Celery** to process email unsubscriptions asynchronously, providing:

- ✅ **Non-blocking webhooks** - Instant response, background processing
- ✅ **Concurrent processing** - Multiple emails processed simultaneously  
- ✅ **Automatic retries** - Failed browser automation retries automatically
- ✅ **Easy scaling** - Add workers with one command
- ✅ **Queue persistence** - Tasks survive restarts
- ✅ **Monitoring** - Real-time queue status and worker health

## Architecture

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Webhook   │───▶│    Redis    │───▶│   Workers   │
│  (FastAPI)  │    │   (Queue)   │    │  (Celery)   │
└─────────────┘    └─────────────┘    └─────────────┘
       │                   │                   │
       ▼                   ▼                   ▼
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│ Task Status │    │  Persisted  │    │ Browser     │
│   API       │    │    Data     │    │ Automation  │
└─────────────┘    └─────────────┘    └─────────────┘
```

## Quick Start

### 1. Start the System
```bash
# Using the start script
./scripts/start.sh

# Or manually
docker-compose up --build -d
```

### 2. Test the System
```bash
# Test with mock data
curl -X POST http://localhost:8000/test

# Check task status (replace TASK_ID with actual ID)
curl http://localhost:8000/task/TASK_ID
```

### 3. Monitor
- **API Health**: http://localhost:8000/health
- **Flower Dashboard**: http://localhost:5555
- **Logs**: `docker-compose logs -f`

## Services

### Redis (Port 6379)
- **Purpose**: Task queue and result backend
- **Persistence**: Enabled with AOF (Append Only File)
- **Health Check**: `redis-cli ping`

### FastAPI App (Port 8000)
- **Purpose**: Webhook endpoint and task status API
- **Endpoints**:
  - `POST /webhook` - Queue email processing
  - `GET /health` - Health check with worker status
  - `GET /task/{task_id}` - Get task status
  - `POST /test` - Test endpoint with mock data

### Celery Workers
- **Purpose**: Background email processing
- **Concurrency**: 2 workers per container (configurable)
- **Memory**: 2GB limit per worker
- **Retry**: 3 attempts with exponential backoff

### Flower (Port 5555)
- **Purpose**: Real-time monitoring dashboard
- **Features**: Task status, worker health, queue metrics

## Scaling

### Scale Workers
```bash
# Scale to 3 worker containers
docker-compose up --scale worker=3

# Scale to 5 worker containers  
docker-compose up --scale worker=5
```

### Resource Limits
Each worker container has:
- **Memory**: 2GB limit, 1GB reservation
- **CPU**: Shared with other containers
- **Concurrency**: 2 tasks per worker (browser automation is resource-intensive)

## Task Types

### 1. `process_email_task`
- **Purpose**: Main email processing task
- **Input**: Email data dict, user email
- **Retries**: 3 attempts (60s, 120s, 240s)
- **Output**: Processing results with success/failure counts

### 2. `health_check_task`
- **Purpose**: Worker health monitoring
- **Input**: None
- **Retries**: None
- **Output**: Worker status information

### 3. `retry_failed_unsubscribe_task`
- **Purpose**: Retry individual failed unsubscribes
- **Input**: Unsubscribe data (link, method, user_email)
- **Retries**: 2 attempts (30s, 60s)
- **Output**: Retry results

## Configuration

### Environment Variables
```bash
REDIS_URL=redis://redis:6379
LOG_LEVEL=INFO
```

### Celery Settings
```python
# app/celery_app.py
'worker_prefetch_multiplier': 1,  # Process one task at a time
'task_acks_late': True,           # Acknowledge after completion
'worker_disable_rate_limits': True,  # No rate limits
```

## Monitoring

### Health Checks
```bash
# Check all services
curl http://localhost:8000/health

# Check specific task
curl http://localhost:8000/task/TASK_ID

# Check Redis
docker-compose exec redis redis-cli ping
```

### Flower Dashboard
- **URL**: http://localhost:5555
- **Features**:
  - Active tasks
  - Worker status
  - Task history
  - Queue statistics
  - Failed tasks

### Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f worker
docker-compose logs -f app
docker-compose logs -f redis
```

## Troubleshooting

### Common Issues

1. **Workers not processing tasks**
   ```bash
   # Check worker logs
   docker-compose logs worker
   
   # Restart workers
   docker-compose restart worker
   ```

2. **Redis connection issues**
   ```bash
   # Check Redis health
   docker-compose exec redis redis-cli ping
   
   # Restart Redis
   docker-compose restart redis
   ```

3. **Tasks stuck in PENDING**
   ```bash
   # Check worker status
   curl http://localhost:8000/health
   
   # Scale up workers
   docker-compose up --scale worker=3
   ```

### Performance Tuning

1. **Increase worker concurrency** (if you have more CPU/memory):
   ```yaml
   # docker-compose.yml
   command: celery -A app.celery_app worker --loglevel=info --concurrency=4
   ```

2. **Add more worker containers**:
   ```bash
   docker-compose up --scale worker=5
   ```

3. **Monitor resource usage**:
   ```bash
   docker stats
   ```

## Development

### Local Development
```bash
# Install dependencies
uv sync

# Start Redis locally
docker run -d -p 6379:6379 redis:alpine

# Start worker locally
celery -A app.celery_app worker --loglevel=info

# Start API locally
uvicorn app.main:app --reload
```

### Testing
```bash
# Test webhook
curl -X POST http://localhost:8000/webhook \
  -H "Content-Type: application/json" \
  -d '{"subject": "Test", "from_email": "test@example.com", ...}'

# Test with mock data
curl -X POST http://localhost:8000/test
```

## Production Considerations

1. **Redis Persistence**: Already configured with AOF
2. **Health Checks**: All services have health checks
3. **Restart Policies**: `unless-stopped` for all services
4. **Resource Limits**: Memory limits set for workers
5. **Monitoring**: Flower dashboard for real-time monitoring
6. **Logging**: Structured logging with configurable levels

## Next Steps

1. **Add more task types** for different processing needs
2. **Implement task prioritization** for urgent emails
3. **Add metrics collection** (Prometheus/Grafana)
4. **Implement dead letter queue** for permanently failed tasks
5. **Add task scheduling** for delayed processing

