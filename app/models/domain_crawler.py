from datetime import datetime
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class PageType(str, Enum):
    HOMEPAGE = "homepage"
    PRIVACY_POLICY = "privacy_policy"
    UNSUBSCRIBE = "unsubscribe"
    CONTACT = "contact"
    TERMS = "terms"
    OTHER = "other"


class LinkInfo(BaseModel):
    """Represents a link found on a webpage"""
    href: str = Field(..., description="The URL of the link")
    text: str = Field(..., description="The text content of the link")
    context: str = Field(..., description="Where the link was found (footer, navigation, content, etc.)")
    parent_element: Optional[str] = Field(None, description="HTML parent element (div, nav, footer, etc.)")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class CrawlResult(BaseModel):
    """Result of crawling a single URL"""
    url: str = Field(..., description="The URL that was crawled")
    success: bool = Field(..., description="Whether the crawl was successful")
    links_found: List[LinkInfo] = Field(default_factory=list, description="All links found on the page")
    error_message: Optional[str] = Field(None, description="Error message if crawl failed")
    processing_time_seconds: float = Field(0.0, description="Time taken to crawl the page")
    page_title: Optional[str] = Field(None, description="Title of the page")
    page_type: PageType = Field(PageType.OTHER, description="Type of page based on content analysis")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class UnsubscribeCandidate(BaseModel):
    """A potential unsubscribe page found during crawling"""
    url: str = Field(..., description="URL of the potential unsubscribe page")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score (0-1)")
    reason: str = Field(..., description="Why this is considered an unsubscribe page")
    found_on_page: str = Field(..., description="Which page this link was found on")
    has_email_form: bool = Field(False, description="Whether the page has an email input form")
    has_unsubscribe_text: bool = Field(False, description="Whether the page contains unsubscribe-related text")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class DomainDiscoveryResult(BaseModel):
    """Result of discovering unsubscribe pages for a domain"""
    domain: str = Field(..., description="The domain that was crawled")
    status: str = Field(..., description="Status of the discovery process")
    confident_result: Optional[UnsubscribeCandidate] = Field(None, description="High-confidence unsubscribe page found")
    possible_candidates: List[UnsubscribeCandidate] = Field(default_factory=list, description="Other potential unsubscribe pages")
    crawl_summary: dict = Field(default_factory=dict, description="Summary of the crawling process")
    errors: List[str] = Field(default_factory=list, description="Any errors encountered during crawling")
    discovered_at: datetime = Field(default_factory=datetime.utcnow, description="When the discovery was completed")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class DomainDiscoveryRequest(BaseModel):
    """Request to discover unsubscribe pages for a domain"""
    domain: str = Field(..., description="Domain to discover (e.g., spglobal.com)")
    max_pages: int = Field(default=10, ge=1, le=20, description="Maximum pages to crawl")
    max_depth: int = Field(default=3, ge=1, le=5, description="Maximum crawl depth")
    include_subdomains: bool = Field(default=False, description="Whether to include subdomains in crawling")


class DomainQueryRequest(BaseModel):
    """Request to query the domain index"""
    domain: str = Field(..., description="Domain to look up")
    include_inactive: bool = Field(default=False, description="Include entries that haven't been verified recently")


class DomainQueryResult(BaseModel):
    """Result of domain index query"""
    domain: str = Field(..., description="Domain that was queried")
    found: bool = Field(..., description="Whether the domain was found in the index")
    unsubscribe_url: Optional[str] = Field(None, description="The unsubscribe URL for this domain")
    confidence: Optional[float] = Field(None, description="Confidence score of the discovered page")
    discovered_at: Optional[datetime] = Field(None, description="When this domain was discovered")
    last_verified: Optional[datetime] = Field(None, description="When this entry was last verified")
    query_time: datetime = Field(default_factory=datetime.utcnow, description="When the query was performed")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
