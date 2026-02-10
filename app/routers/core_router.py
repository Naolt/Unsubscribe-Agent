"""
Core router for basic application endpoints.
"""

from fastapi import APIRouter

router = APIRouter(tags=["core"])

@router.get("/")
async def root():
    return {
        "status": "running", 
        "version": "0.1.0",
        "docs": "/docs",
        "flower_dashboard": "/flower",
        "test_endpoint": "/test"
    }

@router.get("/health")
async def health():
    """
    Health check endpoint that verifies the application and worker status.
    
    Returns:
        - 200: Application is healthy
        - 503: Application is degraded (workers unavailable)
    """
    try:
        # Check if Celery workers are available
        from app.tasks import health_check_task
        result = health_check_task.delay()
        
        # Wait for result with timeout
        try:
            result.get(timeout=5)
            return {"status": "healthy", "workers": "available"}
        except Exception:
            return {"status": "degraded", "workers": "unavailable", "error": "The operation timed out."}
            
    except Exception as e:
        return {"status": "degraded", "workers": "unavailable", "error": str(e)}

@router.get("/examples")
async def examples():
    """
    Provide example usage of the API endpoints.
    """
    return {
        "webhook_example": {
            "endpoint": "POST /webhook",
            "description": "Forward an email to automatically unsubscribe",
            "example_payload": {
                "subject": "Newsletter: Weekly Updates",
                "from_email": "newsletter@company.com",
                "to_email": "user@example.com",
                "headers": [
                    {"name": "From", "value": "newsletter@company.com"},
                    {"name": "To", "value": "user@example.com"},
                    {"name": "Subject", "value": "Newsletter: Weekly Updates"}
                ],
                "body": {
                    "text": "This is a newsletter email...",
                    "html": "<html><body>This is a newsletter email...</body></html>"
                }
            }
        },
        "task_status_example": {
            "endpoint": "GET /task/{task_id}",
            "description": "Check the status of an unsubscribe task",
            "example_response": {
                "status": "SUCCESS",
                "task_id": "123e4567-e89b-12d3-a456-426614174000",
                "result": {
                    "unsubscribed": True,
                    "method": "link_click",
                    "unsubscribe_url": "https://company.com/unsubscribe"
                }
            }
        },
        "domain_discovery_example": {
            "endpoint": "POST /discover/domain",
            "description": "Discover unsubscribe pages for a domain",
            "example_payload": {
                "domain": "example.com",
                "max_pages": 10,
                "max_depth": 3,
                "include_subdomains": False
            }
        }
    }
