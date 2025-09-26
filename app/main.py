from enum import Enum
from fastapi import FastAPI, HTTPException
from app.config import settings  # ensures .env is loaded at startup
from app.tasks import process_email_task, health_check_task
from celery.result import AsyncResult
import logging

from app.types.email import EmailPayload
from pydantic import BaseModel

logger = logging.getLogger(__name__)

app = FastAPI(title="Unsubscribe Agent API")

@app.get("/")
async def root():
    return {"status": "running", "version": "0.1.0"}


@app.get("/health")
async def health():
    """Health check endpoint that also checks worker status"""
    try:
        # Queue a health check task to verify workers are running
        health_task = health_check_task.delay()
        
        # Wait for result with timeout
        try:
            health_result = health_task.get(timeout=10)
            return {
                "status": "healthy",
                "workers": "active",
                "worker_info": health_result
            }
        except Exception as e:
            logger.warning(f"Health check task failed: {e}")
            return {
                "status": "degraded",
                "workers": "unavailable",
                "error": str(e)
            }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unavailable")


class TaskStatusEnum(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCESS = "success"
    FAILURE = "failure"

class TaskStatusResponse(BaseModel):
    task_id: str
    status: TaskStatusEnum
    message: str | None = None
    result: dict | None = None
    error: str | None = None

@app.get("/task/{task_id}")
async def get_task_status(task_id: str) -> TaskStatusResponse:
    """Get status of a queued task"""
    try:
        task_result = AsyncResult(task_id, app=process_email_task.app)
        
        if task_result.state == 'PENDING':
            response = TaskStatusResponse(
                task_id=task_id,
                status=TaskStatusEnum.PENDING,
                message="Task is waiting to be processed"
                )
        elif task_result.state == 'PROGRESS':
            response = TaskStatusResponse(
                task_id=task_id,
                status=TaskStatusEnum.PROCESSING,
                message="Task is currently being processed"
            )
        elif task_result.state == 'SUCCESS':
            response = TaskStatusResponse(
                task_id=task_id,
                status=TaskStatusEnum.SUCCESS,
                result=task_result.result
            )
        elif task_result.state == 'FAILURE':
            response = TaskStatusResponse(
                task_id=task_id,
                status=TaskStatusEnum.FAILURE,
                error=str(task_result.info)
            )
        else:
            response = TaskStatusResponse(
                task_id=task_id,
                status=task_result.state,
                result=task_result.result if task_result.ready() else None
            )
        
        return response
        
    except Exception as e:
        logger.error(f"Error getting task status for {task_id}: {e}")
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")


mock_payload = {
  "email_id": "12345",
  "from_email": "newsletter@shoppingworld.com",
  "to_email": "naol@example.com",
  "subject": "Your Weekly Deals Are Here!",
  "headers": [
    {"name": "Message-ID", "value": "<abc123@shoppingworld.com>"},
    {"name": "Date", "value": "Mon, 16 Sep 2025 14:22:01 +0000"},
    {"name": "List-Unsubscribe", "value": "<mailto:unsubscribe@shoppingworld.com?subject=unsubscribe>, <https://shoppingworld.com/unsubscribe?uid=12345>"}
  ],
  "body": {
    "text": "Check out our latest offers and discounts...",
    "html": "<html><body>Check out our latest offers and discounts...</body></html>"
  }
}


@app.post("/webhook")
async def webhook(email_data: EmailPayload):
    """
    Webhook endpoint that queues email processing instead of processing immediately.
    
    This endpoint now:
    1. Validates the incoming email data
    2. Queues the email for background processing
    3. Returns immediately with a task ID
    4. The actual processing happens in a worker
    """
    try:
        logger.info(f"Received webhook request with email data: {email_data.subject or 'No subject'}")
        
        # Validate required fields
        if not email_data.subject and not email_data.from_email:
            raise HTTPException(status_code=400, detail="Missing required email fields")
        
        # Queue the task for background processing
        task = process_email_task.delay(email_data.dict(), user_email=email_data.from_email)
        
        logger.info(f"Queued email processing task: {task.id}")
        
        return TaskStatusResponse(
            status=TaskStatusEnum.PENDING,
            task_id=task.id,
            message="Email queued for processing",
            user_email=email_data.from_email
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.post("/test")
async def test_webhook():
    """Test endpoint using the mock payload"""
    try:
        # Use the mock payload for testing
        task = process_email_task.delay(mock_payload, "test@example.com")
        
        return {
            "status": TaskStatusEnum.PENDING,
            "task_id": task.id,
            "message": "Test email queued for processing",
            "test_data": mock_payload
        }
        
    except Exception as e:
        logger.error(f"Error in test endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"Test failed: {str(e)}")
