"""
Email processing router for webhook and task management.
"""

import logging
from datetime import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.types.email import EmailPayload
from app.types.unsubscribe import TaskStatusResponse, TaskStatusEnum
from app.tasks import process_email_task
from celery.result import AsyncResult

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/email", tags=["email"])

class EmailData(BaseModel):
    """Gumloop Gmail Reader data format"""
    email_bodies: str
    sender_addresses: str
    recipient_addresses: str
    subjects: str

@router.post("/webhook")
async def webhook(gumloop_data: EmailData):
    """
    Webhook endpoint that processes Gumloop Gmail Reader data for automated unsubscription.
    
    This endpoint:
    1. Receives data in Gumloop Gmail Reader format
    2. Converts it to internal EmailPayload format
    3. Queues the email for background processing
    4. Returns immediately with a task ID
    5. The actual processing happens in a worker using browser automation
    
    **Gumloop Gmail Reader Format:**
    ```json
    {
      "subjects": "Newsletter Title",
      "sender_addresses": "newsletter@company.com",
      "recipient_addresses": "user@example.com",
      "email_bodies": "<html>Email content...</html>"
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
    - Use the `/gumloop-test` endpoint for testing data format
    - Check task status with `/task/{task_id}`
    - Monitor progress with Flower dashboard at `/flower`
    """
    try:
        logger.info(f"Received Gumloop webhook: {gumloop_data.subjects or 'No subject'}")
        
        # Convert Gumloop format to internal EmailPayload format
        email_payload = EmailPayload(
            subject=gumloop_data.subjects,
            from_email=gumloop_data.sender_addresses,
            to_email=gumloop_data.recipient_addresses,
            headers=[
                {"name": "From", "value": gumloop_data.sender_addresses},
                {"name": "To", "value": gumloop_data.recipient_addresses},
                {"name": "Subject", "value": gumloop_data.subjects}
            ],
            body={
                "text": gumloop_data.email_bodies,  # Assuming HTML, but could be text
                "html": gumloop_data.email_bodies   # Same content for both
            }
        )
        
        logger.info(f"Converted to EmailPayload: {email_payload.subject}")
        
        # Validate required fields
        if not email_payload.subject and not email_payload.from_email:
            raise HTTPException(status_code=400, detail="Missing required email fields")
        
        # Queue the task for background processing
        task = process_email_task.delay(email_payload.dict(), user_email=email_payload.from_email)
        
        logger.info(f"Queued email processing task: {task.id}")
        
        return TaskStatusResponse(
            status=TaskStatusEnum.PENDING,
            task_id=task.id,
            message="Email queued for processing",
            user_email=email_payload.from_email
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.post("/gumloop-test")
async def gumloop_test(email_data: EmailData):
    """
    Test endpoint for Gumloop Gmail Reader integration.
    
    This endpoint receives data in Gumloop's Gmail Reader format and logs it.
    It also shows how to convert it to our internal EmailPayload format.
    """
    try:
        logger.info("=== GUMLOOP GMAIL READER DATA ===")
        logger.info(f"Subject: {email_data.subjects}")
        logger.info(f"Sender: {email_data.sender_addresses}")
        logger.info(f"Recipient: {email_data.recipient_addresses}")
        logger.info(f"Body length: {len(email_data.email_bodies)} characters")
        logger.info(f"Body preview: {email_data.email_bodies[:200]}...")
        logger.info("=== END GUMLOOP DATA ===")
        
        # Convert Gumloop format to our internal EmailPayload format
        converted_payload = EmailPayload(
            subject=email_data.subjects,
            from_email=email_data.sender_addresses,
            to_email=email_data.recipient_addresses,
            headers=[
                {"name": "From", "value": email_data.sender_addresses},
                {"name": "To", "value": email_data.recipient_addresses},
                {"name": "Subject", "value": email_data.subjects}
            ],
            body={
                "text": email_data.email_bodies,  # Assuming HTML, but could be text
                "html": email_data.email_bodies   # Same content for both
            }
        )
        
        logger.info("=== CONVERTED TO INTERNAL FORMAT ===")
        logger.info(f"Converted payload: {converted_payload.dict()}")
        logger.info("=== END CONVERSION ===")
        
        # Return success response with conversion info
        return {
            "status": "received",
            "message": "Gumloop Gmail Reader data processed successfully",
            "timestamp": datetime.utcnow().isoformat(),
            "original_data": {
                "subject": email_data.subjects,
                "sender": email_data.sender_addresses,
                "recipient": email_data.recipient_addresses,
                "body_length": len(email_data.email_bodies)
            },
            "conversion_successful": True
        }
        
    except Exception as e:
        logger.error(f"Error in gumloop test endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/task/{task_id}")
async def get_task_status(task_id: str):
    """
    Get the status of an unsubscribe task.
    
    Args:
        task_id: The task ID returned from the webhook
        
    Returns:
        Task status and result if completed
    """
    try:
        # Get task result from Celery
        task_result = AsyncResult(task_id)
        
        if task_result.state == "PENDING":
            return TaskStatusResponse(
                status=TaskStatusEnum.PENDING,
                task_id=task_id,
                message="Task is still processing"
            )
        elif task_result.state == "SUCCESS":
            return TaskStatusResponse(
                status=TaskStatusEnum.SUCCESS,
                task_id=task_id,
                message="Task completed successfully",
                result=task_result.result
            )
        elif task_result.state == "FAILURE":
            return TaskStatusResponse(
                status=TaskStatusEnum.FAILURE,
                task_id=task_id,
                message="Task failed",
                error=str(task_result.info)
            )
        else:
            return TaskStatusResponse(
                status=TaskStatusEnum.PENDING,
                task_id=task_id,
                message=f"Task is in state: {task_result.state}"
            )
            
    except Exception as e:
        logger.error(f"Error getting task status: {e}")
        raise HTTPException(status_code=500, detail=str(e))
