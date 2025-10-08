from enum import Enum
from fastapi import FastAPI, HTTPException, Request
from app.config import settings  # ensures .env is loaded at startup
from app.tasks import process_email_task, health_check_task
from celery.result import AsyncResult
import logging
from datetime import datetime

from app.types.email import EmailPayload
from pydantic import BaseModel

from app.types.unsubscribe import TaskStatusResponse, TaskStatusEnum
from app.models.domain_crawler import (
    DomainDiscoveryRequest,
    DomainQueryRequest,
    DomainDiscoveryResult,
    DomainQueryResult
)
from app.services.crawler import (
    DomainCrawlerService,
    DomainDiscoveryService,
    DomainStorageService
)


class EmailData(BaseModel):
    """Gumloop Gmail Reader data format"""
    email_bodies: str
    sender_addresses: str
    recipient_addresses: str
    subjects: str

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


@app.post("/gumloop-test")
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


# Domain Discovery Endpoints

@app.post("/discover/domain", response_model=DomainDiscoveryResult)
async def discover_domain(request: DomainDiscoveryRequest):
    """
    Discover unsubscribe pages for a domain using web crawling.
    
    This endpoint crawls a domain to find publicly available unsubscribe or email preference pages.
    It uses breadth-first crawling to explore the website and identify pages where users can
    submit their email to unsubscribe without requiring login or tokens.
    
    **Example Request:**
    ```json
    {
      "domain": "spglobal.com",
      "max_pages": 10,
      "max_depth": 3,
      "include_subdomains": false
    }
    ```
    
    **Example Response:**
    ```json
    {
      "domain": "spglobal.com",
      "status": "completed",
      "confident_result": {
        "url": "https://pages.marketintelligence.spglobal.com/Unsubscribe-Preferences.html",
        "confidence": 0.9,
        "reason": "Page content analysis: unsubscribe",
        "found_on_page": "https://spglobal.com/privacy-policy",
        "has_email_form": true,
        "has_unsubscribe_text": true
      },
      "possible_candidates": [...],
      "crawl_summary": {
        "pages_visited": 5,
        "successful_crawls": 5,
        "total_links_found": 23,
        "total_processing_time_seconds": 12.5
      },
      "errors": [],
      "discovered_at": "2024-01-15T10:30:00Z"
    }
    ```
    """
    try:
        logger.info(f"Starting domain discovery for {request.domain}")
        
        # Create crawler and discovery service
        async with DomainCrawlerService(timeout=10, delay=1.0) as crawler:
            discovery_service = DomainDiscoveryService(crawler)
            result = await discovery_service.discover_domain(request)
            
            # Store the result if we found a confident unsubscribe page
            if result.confident_result:
                storage_service = DomainStorageService()
                storage_service.add_domain_entry(request.domain, result.confident_result)
                logger.info(f"Stored domain entry for {request.domain}")
            
            return result
            
    except Exception as e:
        logger.error(f"Domain discovery failed for {request.domain}: {e}")
        raise HTTPException(status_code=500, detail=f"Domain discovery failed: {str(e)}")


@app.get("/discover/domain/{domain}", response_model=DomainQueryResult)
async def query_domain(domain: str, include_inactive: bool = False):
    """
    Query the domain index for unsubscribe pages.
    
    This endpoint looks up a domain in the stored index to find previously discovered
    unsubscribe pages. It returns the unsubscribe URL and confidence score if found.
    
    **Example Request:**
    ```bash
    curl "http://localhost:8000/discover/domain/spglobal.com?include_inactive=false"
    ```
    
    **Example Response:**
    ```json
    {
      "domain": "spglobal.com",
      "found": true,
      "unsubscribe_url": "https://pages.marketintelligence.spglobal.com/Unsubscribe-Preferences.html",
      "confidence": 0.9,
      "discovered_at": "2024-01-15T10:30:00Z",
      "last_verified": null,
      "query_time": "2024-01-15T11:00:00Z"
    }
    ```
    """
    try:
        storage_service = DomainStorageService()
        request = DomainQueryRequest(domain=domain, include_inactive=include_inactive)
        result = storage_service.query_domain(request)
        
        return result
        
    except Exception as e:
        logger.error(f"Domain query failed for {domain}: {e}")
        raise HTTPException(status_code=500, detail=f"Domain query failed: {str(e)}")


@app.get("/discover/stats")
async def get_domain_stats():
    """
    Get statistics about the domain index.
    
    Returns information about the stored domain index including total domains,
    verification status, and confidence distribution.
    
    **Example Response:**
    ```json
    {
      "total_domains": 150,
      "verified_entries": 45,
      "average_confidence": 0.82,
      "high_confidence_entries": 120,
      "medium_confidence_entries": 25,
      "low_confidence_entries": 5,
      "storage_path": "data/domain_index.json"
    }
    ```
    """
    try:
        storage_service = DomainStorageService()
        stats = storage_service.get_stats()
        return stats
        
    except Exception as e:
        logger.error(f"Failed to get domain stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get domain stats: {str(e)}")


@app.get("/discover/domains")
async def list_domains():
    """
    List all domains in the index.
    
    Returns a list of all domains that have been discovered and stored in the index.
    
    **Example Response:**
    ```json
    {
      "domains": ["spglobal.com", "cnn.com", "amazon.com"],
      "count": 3
    }
    ```
    """
    try:
        storage_service = DomainStorageService()
        domains = storage_service.list_domains()
        return {"domains": domains, "count": len(domains)}
        
    except Exception as e:
        logger.error(f"Failed to list domains: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list domains: {str(e)}")


@app.delete("/discover/domain/{domain}")
async def remove_domain(domain: str):
    """
    Remove a domain from the index.
    
    This endpoint removes a domain and its unsubscribe page information from the stored index.
    
    **Example Request:**
    ```bash
    curl -X DELETE "http://localhost:8000/discover/domain/example.com"
    ```
    
    **Example Response:**
    ```json
    {
      "success": true,
      "message": "Domain example.com removed from index"
    }
    ```
    """
    try:
        storage_service = DomainStorageService()
        success = storage_service.remove_domain(domain)
        
        if success:
            return {"success": True, "message": f"Domain {domain} removed from index"}
        else:
            return {"success": False, "message": f"Domain {domain} not found in index"}
            
    except Exception as e:
        logger.error(f"Failed to remove domain {domain}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to remove domain: {str(e)}")
