from enum import Enum
from fastapi import FastAPI, HTTPException
from app.config import settings  # ensures .env is loaded at startup
from app.tasks import process_email_task, health_check_task
from celery.result import AsyncResult
import logging

from app.types.email import EmailPayload
from pydantic import BaseModel

from app.types.unsubscribe import TaskStatusResponse, TaskStatusEnum

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Unsubscribe Agent API",
    description="""
    ## Automated Email Unsubscription Service
    
    This API automatically processes forwarded emails and unsubscribes from marketing emails using browser automation.
    
    ### How it works:
    1. **Forward emails** to this service via the `/webhook` endpoint
    2. **Queue processing** - emails are queued for background processing
    3. **Browser automation** - workers use AI-powered browsers to navigate unsubscribe links
    4. **Track progress** - monitor task status and results
    
    ### Quick Start:
    - **Test the service**: Use `/test` endpoint for a quick demo
    - **Process emails**: Send email data to `/webhook` endpoint
    - **Monitor tasks**: Check `/task/{task_id}` for status updates
    - **View dashboard**: Access Flower monitoring at `/flower`
    
    ### Example Usage:
    ```bash
    # Test with mock data
    curl -X POST http://localhost:8000/test
    
    # Process a real email
    curl -X POST http://localhost:8000/webhook \\
      -H "Content-Type: application/json" \\
      -d '{"subject": "Newsletter", "from_email": "news@example.com", ...}'
    
    # Check task status
    curl http://localhost:8000/task/{task_id}
    ```
    """,
    version="0.1.0"
)

@app.get("/")
async def root():
    return {
        "status": "running", 
        "version": "0.1.0",
        "docs": "/docs",
        "flower_dashboard": "/flower",
        "test_endpoint": "/test"
    }


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


@app.post("/webhook")
async def webhook(email_data: EmailPayload):
    """
    Webhook endpoint that queues email processing for automated unsubscription.
    
    This endpoint:
    1. Validates the incoming email data
    2. Queues the email for background processing
    3. Returns immediately with a task ID
    4. The actual processing happens in a worker using browser automation
    
    **Example Request:**
    ```json
    {
      "subject": "FWD: September Newsletter: Rethinking the Timesheet",
      "from_email": "newsletter@company.com",
      "to_email": "user@example.com",
      "headers": [
        {"name": "From", "value": "newsletter@company.com"},
        {"name": "To", "value": "user@example.com"},
        {"name": "Subject", "value": "FWD: September Newsletter: Rethinking the Timesheet"}
      ],
      "body": {
        "text": "Begin forwarded message:\\n\\nFrom: newsletter@company.com\\nTo: user@example.com\\nSubject: September Newsletter: Rethinking the Timesheet\\n\\nSeptember Newsletter: Rethinking the Timesheet\\n\\nDear Subscriber,\\n\\nThis month we are exploring innovative approaches to time tracking and productivity management.\\n\\nKey Highlights:\\n- New time tracking methodologies\\n- Productivity insights and analytics\\n- Team collaboration tools\\n\\nWe hope you find this content valuable. If you have any questions or feedback, please don't hesitate to reach out.\\n\\nYou received this email because you subscribed to our newsletter.\\nUnsubscribe | Manage Preferences",
        "html": "<!DOCTYPE html><html><head><meta charset=\\"utf-8\\"><title>September Newsletter: Rethinking the Timesheet</title></head><body><div style=\\"font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;\\"><h1 style=\\"color: #333; text-align: center;\\">September Newsletter</h1><h2 style=\\"color: #666;\\">Rethinking the Timesheet</h2><p>Dear Subscriber,</p><p>This month we are exploring innovative approaches to time tracking and productivity management.</p><div style=\\"background-color: #f5f5f5; padding: 15px; margin: 20px 0; border-radius: 5px;\\"><h3 style=\\"margin-top: 0;\\">Key Highlights:</h3><ul><li>New time tracking methodologies</li><li>Productivity insights and analytics</li><li>Team collaboration tools</li></ul></div><p>We hope you find this content valuable. If you have any questions or feedback, please don't hesitate to reach out.</p><div style=\\"text-align: center; margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd;\\"><p style=\\"font-size: 12px; color: #888;\\">You received this email because you subscribed to our newsletter.</p><p style=\\"font-size: 12px; color: #888;\\"><a href=\\"https://company.com/unsubscribe?token=abc123\\" style=\\"color: #007bff;\\">Unsubscribe</a> | <a href=\\"https://company.com/preferences\\" style=\\"color: #007bff;\\">Manage Preferences</a></p></div></div></body></html>"
      }
    }
    ```
    
    **Example Response:**
    ```json
    {
      "status": "PENDING",
      "task_id": "1a2a2d2c-0b01-4e60-a621-cd60cdf9db5b",
      "message": "Email queued for processing",
      "user_email": "user@example.com"
    }
    ```
    
    **Testing:**
    - Use the `/test` endpoint for a quick test with mock data
    - Check task status with `/task/{task_id}`
    - Monitor progress with Flower dashboard at `/flower`
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

@app.get("/task/{task_id}")
async def get_task_status(task_id: str) -> TaskStatusResponse:
    """
    Get the status and results of a queued email processing task.
    
    This endpoint allows you to check the progress and results of an email processing task
    that was queued via the `/webhook` endpoint.
    
    **Task States:**
    - `PENDING`: Task is waiting to be processed by a worker
    - `PROGRESS`: Task is currently being processed
    - `SUCCESS`: Task completed successfully
    - `FAILURE`: Task failed with an error
    
    **Example Request:**
    ```bash
    curl http://localhost:8000/task/1a2a2d2c-0b01-4e60-a621-cd60cdf9db5b
    ```
    
    **Example Response (PENDING):**
    ```json
    {
      "task_id": "1a2a2d2c-0b01-4e60-a621-cd60cdf9db5b",
      "status": "PENDING",
      "message": "Task is waiting to be processed"
    }
    ```
    
    **Example Response (SUCCESS):**
    ```json
    {
      "task_id": "1a2a2d2c-0b01-4e60-a621-cd60cdf9db5b",
      "status": "SUCCESS",
      "result": {
        "success": true,
        "message": "Processed 2 links: 1 successful, 1 failed",
        "total_links_found": 2,
        "links_processed": 2,
        "successful_unsubscribes": 1,
        "failed_unsubscribes": 1,
        "task_id": "1a2a2d2c-0b01-4e60-a621-cd60cdf9db5b",
        "results": [
          {
            "success": true,
            "method": "https",
            "link": "https://company.com/unsubscribe?token=abc123",
            "message": "Successfully unsubscribed from marketing emails"
          },
          {
            "success": false,
            "method": "https",
            "link": "https://company.com/preferences",
            "message": "Unsubscribe failed: 404 Not Found"
          }
        ]
      }
    }
    ```
    
    **Example Response (FAILURE):**
    ```json
    {
      "task_id": "1a2a2d2c-0b01-4e60-a621-cd60cdf9db5b",
      "status": "FAILURE",
      "error": "Task failed: Browser automation error"
    }
    ```
    
    **Usage Tips:**
    - Poll this endpoint every few seconds to check task progress
    - Tasks typically complete within 30-60 seconds
    - Use the `/examples` endpoint to see more usage examples
    - Monitor all tasks with the Flower dashboard at `/flower`
    """
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


@app.post("/test")
async def test_webhook():
    """Test endpoint using the mock payload"""
    try:
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


@app.get("/examples")
async def get_examples():
    """
    Get ready-to-use examples for testing the API.
    
    Returns curl commands and example payloads for easy testing.
    """
    return {
        "webhook_example": {
            "description": "Process a forwarded email for unsubscription",
            "curl_command": """curl -X POST http://localhost:8000/webhook \\
  -H "Content-Type: application/json" \\
  -d '{
    "subject": "FWD: September Newsletter: Rethinking the Timesheet",
    "from_email": "newsletter@company.com",
    "to_email": "user@example.com",
    "headers": [
      {"name": "From", "value": "newsletter@company.com"},
      {"name": "To", "value": "user@example.com"},
      {"name": "Subject", "value": "FWD: September Newsletter: Rethinking the Timesheet"}
    ],
    "body": {
      "text": "Begin forwarded message:\\n\\nFrom: newsletter@company.com\\nTo: user@example.com\\nSubject: September Newsletter: Rethinking the Timesheet\\n\\nSeptember Newsletter: Rethinking the Timesheet\\n\\nDear Subscriber,\\n\\nThis month we are exploring innovative approaches to time tracking and productivity management.\\n\\nKey Highlights:\\n- New time tracking methodologies\\n- Productivity insights and analytics\\n- Team collaboration tools\\n\\nWe hope you find this content valuable. If you have any questions or feedback, please don't hesitate to reach out.\\n\\nYou received this email because you subscribed to our newsletter.\\nUnsubscribe | Manage Preferences",
      "html": "<!DOCTYPE html><html><head><meta charset=\\"utf-8\\"><title>September Newsletter: Rethinking the Timesheet</title></head><body><div style=\\"font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;\\"><h1 style=\\"color: #333; text-align: center;\\">September Newsletter</h1><h2 style=\\"color: #666;\\">Rethinking the Timesheet</h2><p>Dear Subscriber,</p><p>This month we are exploring innovative approaches to time tracking and productivity management.</p><div style=\\"background-color: #f5f5f5; padding: 15px; margin: 20px 0; border-radius: 5px;\\"><h3 style=\\"margin-top: 0;\\">Key Highlights:</h3><ul><li>New time tracking methodologies</li><li>Productivity insights and analytics</li><li>Team collaboration tools</li></ul></div><p>We hope you find this content valuable. If you have any questions or feedback, please don't hesitate to reach out.</p><div style=\\"text-align: center; margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd;\\"><p style=\\"font-size: 12px; color: #888;\\">You received this email because you subscribed to our newsletter.</p><p style=\\"font-size: 12px; color: #888;\\"><a href=\\"https://company.com/unsubscribe?token=abc123\\" style=\\"color: #007bff;\\">Unsubscribe</a> | <a href=\\"https://company.com/preferences\\" style=\\"color: #007bff;\\">Manage Preferences</a></p></div></div></body></html>"
    }
  }'""",
            "expected_response": {
                "status": "PENDING",
                "task_id": "1a2a2d2c-0b01-4e60-a621-cd60cdf9db5b",
                "message": "Email queued for processing",
                "user_email": "user@example.com"
            }
        },
        "test_example": {
            "description": "Quick test with mock data",
            "curl_command": "curl -X POST http://localhost:8000/test",
            "expected_response": {
                "status": "PENDING",
                "task_id": "abc123-def456-ghi789",
                "message": "Test email queued for processing",
                "test_data": "..."
            }
        },
        "status_check_example": {
            "description": "Check task status",
            "curl_command": "curl http://localhost:8000/task/{task_id}",
            "expected_response": {
                "task_id": "1a2a2d2c-0b01-4e60-a621-cd60cdf9db5b",
                "status": "SUCCESS",
                "result": {
                    "success": True,
                    "message": "Processed 1 links: 1 successful, 0 failed",
                    "total_links_found": 1,
                    "successful_unsubscribes": 1,
                    "failed_unsubscribes": 0
                }
            }
        },
        "health_check_example": {
            "description": "Check service health",
            "curl_command": "curl http://localhost:8000/health",
            "expected_response": {
                "status": "healthy",
                "workers": "active",
                "worker_info": {
                    "status": "healthy",
                    "worker": "celery@worker-hostname",
                    "task_id": "health-check-task-id"
                }
            }
        }
    }
