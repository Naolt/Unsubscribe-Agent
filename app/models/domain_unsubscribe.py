"""
Domain unsubscription models for the unsubscribe agent.
"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field

from app.types.unsubscribe import TaskStatusEnum
from app.models.domain_crawler import DomainDiscoveryResult, UnsubscribeCandidate


class DomainUnsubscribeRequest(BaseModel):
    """Request to unsubscribe from a domain using discovered unsubscribe pages."""
    domain: str = Field(..., description="Domain to unsubscribe from (e.g., example.com)")
    user_email: str = Field(..., description="User's email address for unsubscription")
    force_refresh: bool = Field(default=False, description="Force refresh domain cache and re-crawl")
    crawl_options: Optional[dict] = Field(default=None, description="Custom crawl options (max_pages, max_depth, etc.)")


class DomainUnsubscribeResponse(BaseModel):
    """Response from domain unsubscription request."""
    status: TaskStatusEnum = Field(..., description="Status of the unsubscription task")
    task_id: str = Field(..., description="Unique task ID for tracking progress")
    message: str = Field(..., description="Human-readable status message")
    domain: str = Field(..., description="Domain that was processed")
    user_email: str = Field(..., description="User email that was processed")
    discovery_result: Optional[DomainDiscoveryResult] = Field(None, description="Domain discovery results")
    unsubscribe_urls: List[str] = Field(default_factory=list, description="All discovered unsubscribe URLs")
    confident_url: Optional[str] = Field(None, description="Most confident unsubscribe URL")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="When the request was processed")


class DomainUnsubscribeTaskResult(BaseModel):
    """Result of a domain unsubscription task."""
    success: bool = Field(..., description="Whether the unsubscription was successful")
    message: str = Field(..., description="Result message")
    domain: str = Field(..., description="Domain that was processed")
    user_email: str = Field(..., description="User email that was processed")
    unsubscribe_urls_found: int = Field(0, description="Number of unsubscribe URLs discovered")
    urls_attempted: int = Field(0, description="Number of URLs attempted for unsubscription")
    successful_unsubscribes: int = Field(0, description="Number of successful unsubscriptions")
    failed_unsubscribes: int = Field(0, description="Number of failed unsubscription attempts")
    results: List[dict] = Field(default_factory=list, description="Detailed results for each URL attempted")
    task_id: str = Field(..., description="Task ID")
    completed_at: datetime = Field(default_factory=datetime.utcnow, description="When the task completed")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
