from datetime import datetime
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field


class DiscoveryStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class DomainIndexEntry(BaseModel):
    """Represents a discovered unsubscribe page for a domain"""
    domain: str = Field(..., description="The domain name (e.g., spglobal.com)")
    unsubscribe_url: str = Field(..., description="The discovered unsubscribe/preferences page URL")
    last_verified: Optional[datetime] = Field(None, description="When this entry was last verified to work")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class DomainDiscoveryRequest(BaseModel):
    """Request to discover unsubscribe pages for a domain"""
    domain: str = Field(..., description="Domain to discover (e.g., spglobal.com)")
    max_pages: int = Field(default=10, ge=1, le=50, description="Maximum pages to crawl")
    include_subdomains: bool = Field(default=True, description="Whether to include subdomains in search")
    force_rediscovery: bool = Field(default=False, description="Force rediscovery even if domain exists")


class DomainDiscoveryResult(BaseModel):
    """Result of domain discovery process"""
    domain: str
    status: DiscoveryStatus
    entries_found: List[DomainIndexEntry] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
    discovered_at: datetime = Field(default_factory=datetime.utcnow)
    processing_time_seconds: float = 0.0
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class DomainQueryRequest(BaseModel):
    """Request to query the domain index"""
    domain: str = Field(..., description="Domain to look up")
    include_inactive: bool = Field(default=False, description="Include entries that haven't been verified recently")


class DomainQueryResult(BaseModel):
    """Result of domain index query"""
    domain: str
    found: bool
    entries: List[DomainIndexEntry] = Field(default_factory=list)
    query_time: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
