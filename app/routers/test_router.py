"""
Test router for development and testing endpoints.
"""

from fastapi import APIRouter

router = APIRouter(prefix="/test", tags=["test"])

@router.post("/")
async def test_endpoint():
    """
    Simple test endpoint for development.
    """
    return {
        "message": "Test endpoint is working!",
        "status": "success",
        "timestamp": "2025-01-01T00:00:00Z"
    }