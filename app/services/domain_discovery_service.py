import logging
from typing import List
from datetime import datetime
from pydantic import BaseModel, Field

from app.models.domain_index import (
    DomainIndexEntry, 
    DomainDiscoveryRequest, 
    DomainDiscoveryResult,
    DiscoveryStatus
)
from app.config import settings
from browser_use import Agent, Browser, ChatGoogle

logger = logging.getLogger(__name__)


class DiscoveredUnsubscribePage(BaseModel):
    """Represents a discovered unsubscribe page"""
    url: str = Field(..., description="The URL of the unsubscribe page")
    description: str = Field(..., description="Brief description of what the page does")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence that this is a valid unsubscribe page (0-1)")


class UnsubscribeDiscoveryResult(BaseModel):
    """Structured result from domain discovery"""
    found_pages: List[DiscoveredUnsubscribePage] = Field(default_factory=list, description="List of discovered unsubscribe pages")
    exploration_summary: str = Field(..., description="Summary of the exploration process")


class DomainDiscoveryService:
    """Service for discovering unsubscribe pages on domains using browser automation"""
    
    def __init__(self):
        logger.info("DomainDiscoveryService initialized")
    
    async def discover_domain(self, request: DomainDiscoveryRequest) -> DomainDiscoveryResult:
        """Discover unsubscribe pages for a given domain using browser automation"""
        logger.info(f"Starting domain discovery for {request.domain}")
        start_time = datetime.utcnow()
        
        result = DomainDiscoveryResult(
            domain=request.domain,
            status=DiscoveryStatus.IN_PROGRESS
        )
        
        try:
            # Use browser automation to intelligently discover unsubscribe pages
            entries = await self._discover_with_agent(request.domain, request.include_subdomains, request.max_pages)
            
            result.entries_found = entries
            result.status = DiscoveryStatus.COMPLETED if entries else DiscoveryStatus.FAILED
            
        except Exception as e:
            error_msg = f"Domain discovery failed for {request.domain}: {str(e)}"
            logger.error(error_msg)
            result.errors.append(error_msg)
            result.status = DiscoveryStatus.FAILED
        
        result.processing_time_seconds = (datetime.utcnow() - start_time).total_seconds()
        logger.info(f"Domain discovery completed for {request.domain}: {len(result.entries_found)} entries found")
        
        return result
    
    async def _discover_with_agent(self, domain: str, include_subdomains: bool, max_pages: int) -> List[DomainIndexEntry]:
        """Use browser automation to intelligently discover unsubscribe pages on a domain"""
        try:
            # Initialize LLM compatible with browser_use Agent
            llm = ChatGoogle(model="gemini-2.5-flash")
            
            # Launch browser
            logger.info(f"Headless: {settings.HEADLESS}")
            headless = settings.HEADLESS if settings.HEADLESS else True
            browser = Browser(headless=headless)
            
            # Define the task for the agent
            task = f"""
            You are an automated assistant tasked with discovering unsubscribe pages on websites.
            
            Your goal is to find unsubscribe or email preference management pages for the domain: {domain}
            
            Instructions:
            
            1. Start by visiting the main domain: https://{domain}
            2. Explore the website intelligently to find unsubscribe pages. Look for:
               - Footer links mentioning "unsubscribe", "opt-out", "email preferences"
               - Navigation menus with subscription management options
               - Links in email-related sections
               - Privacy policy or terms pages that might link to unsubscribe options
               - Account settings or profile pages
            
            3. If you find potential unsubscribe pages, visit them and verify they allow users to:
               - Unsubscribe from emails
               - Manage email preferences
               - Opt-out of communications
               - Update subscription settings
            
            4. Be efficient - don't spend too much time on pages that are clearly not unsubscribe related.
            5. Focus on finding the main unsubscribe page(s) for this domain.
            6. Maximum pages to explore: {max_pages}
            7. Include subdomains: {include_subdomains}
            
            Remember: You're looking for pages where users can manage their email subscriptions or unsubscribe from marketing emails.
            
            Provide a summary of your exploration process and list all valid unsubscribe pages you found.
            """
            
            # Create and run the agent with structured output
            agent = Agent(task=task, browser=browser, llm=llm, output_model_schema=UnsubscribeDiscoveryResult)
            history = await agent.run()
            
            # Extract structured result
            try:
                result_json = history.final_result()
                if result_json:
                    parsed_result = UnsubscribeDiscoveryResult.model_validate_json(result_json)
                    
                    # Convert to DomainIndexEntry objects
                    entries = []
                    for page in parsed_result.found_pages:
                        logger.info(f"Found unsubscribe page: {page.url} - {page.description} (confidence: {page.confidence})")
                        entries.append(DomainIndexEntry(
                            domain=domain,
                            unsubscribe_url=page.url,
                            last_verified=None  # Will be set when actually used
                        ))
                    
                    logger.info(f"Discovery completed for {domain}: found {len(entries)} unsubscribe pages")
                    logger.info(f"Exploration summary: {parsed_result.exploration_summary}")
                    return entries
                else:
                    logger.warning(f"No structured result returned for domain {domain}")
                    return []
                    
            except Exception as e:
                logger.error(f"Failed to parse structured result for {domain}: {e}")
                return []
                
        except Exception as e:
            logger.error(f"Exception during domain discovery for {domain}: {e}")
            return []
