"""
Celery configuration for the unsubscribe agent.
Handles task queuing and worker management.
"""

from celery import Celery
from app.config import settings

# Create Celery app instance
celery_app = Celery('unsubscribe_agent')

# Configure Celery
redis_url = getattr(settings, 'REDIS_URL', 'redis://localhost:6379')
celery_app.config_from_object({
    'broker_url': f'{redis_url}/0',
    'result_backend': f'{redis_url}/0',
    'task_serializer': 'json',
    'accept_content': ['json'],
    'result_serializer': 'json',
    'timezone': 'UTC',
    'enable_utc': True,
    'task_track_started': True,
    'task_reject_on_worker_lost': True,
    'worker_prefetch_multiplier': 1,  # Process one task at a time for browser automation
    'task_acks_late': True,  # Acknowledge tasks after completion
    'worker_disable_rate_limits': True,  # Disable rate limits for our use case
    'task_default_retry_delay': 0,  # Disable retries
    'task_max_retries': 0,  # No retries
})

# Auto-discover tasks from app.tasks module
celery_app.autodiscover_tasks(['app'])

if __name__ == '__main__':
    celery_app.start()
