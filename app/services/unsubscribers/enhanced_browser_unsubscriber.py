"""
Enhanced browser unsubscriber that can explore pages and handle different page types.
"""

import logging
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from app.config import settings
from app.services.unsubscribers.base import BaseUnsubscriber
from app.types.unsubscribe import UnsubscribeMethod, UnsubscriberResult
from browser_use import Agent, Browser, Tools, ActionResult, BrowserSession
from app.services.llm.browser_llm_factory import get_configured_browser_llm
from app.models.domain_crawler import PageType

logger = logging.getLogger(__name__)


class UnsubscribeResult(BaseModel):
    """Structured output for unsubscribe operations."""
    success: bool = Field(..., description="Whether the unsubscription was successful")
    message: str = Field(..., description="Human-readable result message")
    discovered_url: Optional[str] = Field(None, description="Better unsubscribe URL discovered during exploration")
    confirmation_message: Optional[str] = Field(None, description="Confirmation message received from the site")
    page_type: str = Field(..., description="Type of page encountered (unsubscribe, privacy, contact, etc.)")
    login_required: bool = Field(False, description="Whether login was required to proceed")
    multiple_subscriptions: bool = Field(False, description="Whether multiple subscriptions were found and processed")
    actions_taken: List[str] = Field(default_factory=list, description="List of actions performed during unsubscription")


class EnhancedBrowserUnsubscriber(BaseUnsubscriber):
    """
    Enhanced browser unsubscriber that can:
    1. Explore pages to find unsubscribe options
    2. Handle different page types (privacy, contact, etc.)
    3. Detect login requirements
    4. Update domain index with successful URLs
    """
    
    def can_handle(self, method: UnsubscribeMethod) -> bool:
        return method == UnsubscribeMethod.HTTPS

    async def execute(self, link: str, user_email: str | None = None, domain: str | None = None) -> UnsubscriberResult:
        """
        Enhanced unsubscribe execution with exploration capabilities.

        Args:
            link: The URL to visit (might be unsubscribe, privacy, contact, etc.)
            user_email: User's email address
            domain: Domain name for context and index updating

        Returns:
            UnsubscriberResult with success/failure and discovered unsubscribe URL
        """
        try:
            # Initialize LLM and browser
            llm = get_configured_browser_llm()
            logger.info(f"Using enhanced browser unsubscriber with {settings.BROWSER_LLM_PROVIDER}")
            
            headless = settings.HEADLESS if settings.HEADLESS else True
            browser = Browser(headless=headless)

            # Create enhanced prompt for exploration
            prompt = self._create_exploration_prompt(link, user_email, domain)
            
            # Create and run the agent with structured output
            agent = Agent(task=prompt, browser=browser, llm=llm, output_model_schema=UnsubscribeResult)
            history = await agent.run()

            # Extract structured results
            final_text = self._extract_final_text(history)
            success = self._extract_success(history)
            
            # Parse structured result
            structured_result = None
            if final_text:
                try:
                    structured_result = UnsubscribeResult.model_validate_json(final_text)
                except Exception as e:
                    logger.warning(f"Failed to parse structured result: {e}")
            
            # Use structured result if available, otherwise fallback to basic extraction
            if structured_result:
                discovered_url = structured_result.discovered_url
                message = structured_result.message
                success = structured_result.success
            else:
                discovered_url = self._extract_discovered_url(final_text)
                message = final_text or "Unsubscribe attempt completed"
                success = success or False

            # Create result with structured information
            result = UnsubscriberResult(
                success=success,
                method=UnsubscribeMethod.HTTPS,
                link=discovered_url or link,  # Use discovered URL if found
                message=message,
            )
            
            # Store structured result information as attributes for later use
            if structured_result:
                result.page_type = structured_result.page_type
                result.login_required = structured_result.login_required
                result.multiple_subscriptions = structured_result.multiple_subscriptions
                result.actions_taken = structured_result.actions_taken
                result.confirmation_message = structured_result.confirmation_message

            # Update domain index if successful and URL was discovered
            if success and discovered_url and domain and discovered_url != link:
                await self._update_domain_index(domain, discovered_url, user_email)

            return result

        except Exception as exc:
            logger.error(f"Enhanced browser unsubscriber failed: {exc}")
            return UnsubscriberResult(
                success=False,
                method=UnsubscribeMethod.HTTPS,
                link=link,
                message=f"Exception during enhanced unsubscribe: {exc}",
            )

    def _create_exploration_prompt(self, link: str, user_email: str | None, domain: str | None) -> str:
        """Create an enhanced prompt for page exploration and unsubscription."""
        
        model_type = "local AI model" if settings.BROWSER_LLM_PROVIDER == "ollama" else "AI model"
        
        return f"""
You are an automated assistant powered by a {model_type}, tasked with unsubscribing from marketing or notification emails.

**Context:**
- User email: {user_email}
- Initial URL: {link}
- Domain: {domain or 'Unknown'}

**Your Mission:**
Find and complete the unsubscription process for the user. The initial URL might be:
- A direct unsubscribe page
- A privacy policy page
- A contact page
- A general website page
- Any other type of page

**Step-by-Step Process:**

1. **Visit the initial URL** and analyze what type of page it is.

2. **If it's an unsubscribe page:**
   - Look for email input fields and enter: {user_email}
   - Look for unsubscribe buttons/links and click them
   - Handle any confirmation dialogs
   - Look for "unsubscribe all" or "stop all emails" options
   - Capture confirmation messages

3. **If it's NOT an unsubscribe page (privacy, contact, homepage, etc.):**
   - Look for links to unsubscribe pages (footer, navigation, privacy policy)
   - Look for text like: "unsubscribe", "email preferences", "opt-out", "stop emails"
   - Click on relevant links to navigate to unsubscribe pages
   - If you find an unsubscribe page, follow step 2

4. **Handle different scenarios:**
   - **Login required**: If you encounter login forms, STOP immediately and report "Login required - cannot proceed"
   - **No unsubscribe option**: If no unsubscribe options exist, report "No unsubscribe options found"
   - **Multiple subscriptions**: Try to unsubscribe from all available subscriptions
   - **Confirmation required**: Handle any confirmation steps

5. **Success criteria:**
   - Successfully submitted unsubscription request
   - Received confirmation message
   - Found and used a direct unsubscribe URL

**Important Rules:**
- NEVER enter login credentials or personal information beyond the email
- If login is required, stop and report it
- Be efficient - don't waste time on irrelevant pages
- If you discover a better unsubscribe URL, note it in your final response
- Always try to unsubscribe from ALL available subscriptions, not just one

**Final Response:**
You must provide a structured JSON response with the following fields:
- success: boolean - whether unsubscription was successful
- message: string - what happened during the process
- discovered_url: string or null - if you found a better unsubscribe URL, include it here
- confirmation_message: string or null - any confirmation messages you received
- page_type: string - type of page encountered (unsubscribe, privacy, contact, homepage, etc.)
- login_required: boolean - whether login was required to proceed
- multiple_subscriptions: boolean - whether multiple subscriptions were found and processed
- actions_taken: array of strings - list of actions you performed

Example response:
{{
  "success": true,
  "message": "Successfully unsubscribed from all marketing emails",
  "discovered_url": "https://example.com/preferences/unsubscribe",
  "confirmation_message": "You have been unsubscribed from all marketing emails",
  "page_type": "unsubscribe",
  "login_required": false,
  "multiple_subscriptions": true,
  "actions_taken": ["visited privacy page", "clicked unsubscribe link", "entered email", "clicked unsubscribe button"]
}}

**Edge Cases:**
- If the page is completely unrelated to email subscriptions, report "No email subscription options found"
- If you encounter CAPTCHAs or complex verification, report "Complex verification required"
- If the site appears suspicious or untrusted, report "Site appears untrusted"
"""

    def _extract_final_text(self, history) -> Optional[str]:
        """Extract final text from browser history."""
        try:
            return history.final_result()
        except Exception:
            return None

    def _extract_success(self, history) -> Optional[bool]:
        """Extract success status from browser history."""
        try:
            return history.is_successful()
        except Exception:
            return None

    def _extract_discovered_url(self, final_text: Optional[str]) -> Optional[str]:
        """Extract discovered unsubscribe URL from final text."""
        if not final_text:
            return None
            
        # Look for DISCOVERED_URL in the response
        lines = final_text.split('\n')
        for line in lines:
            if line.strip().startswith('DISCOVERED_URL:'):
                url = line.split('DISCOVERED_URL:', 1)[1].strip()
                if url and url != 'None' and url.startswith('http'):
                    return url
        return None

    async def _update_domain_index(self, domain: str, discovered_url: str, user_email: str | None):
        """Update domain index with discovered unsubscribe URL."""
        try:
            from app.services.crawler import DomainStorageService
            from app.models.domain_crawler import UnsubscribeCandidate
            
            # Create unsubscribe candidate
            candidate = UnsubscribeCandidate(
                url=discovered_url,
                confidence=0.9,  # High confidence since it was successfully used
                reason=f"Successfully used for unsubscription by {user_email}",
                found_on_page=discovered_url,
                has_email_form=True,
                has_unsubscribe_text=True
            )
            
            # Update domain index
            storage_service = DomainStorageService()
            storage_service.add_domain_entry(domain, candidate)
            logger.info(f"Updated domain index for {domain} with discovered URL: {discovered_url}")
            
        except Exception as exc:
            logger.error(f"Failed to update domain index: {exc}")

    async def execute_with_exploration(self, link: str, user_email: str | None = None, domain: str | None = None) -> Dict[str, Any]:
        """
        Execute unsubscription with detailed exploration results.
        
        Returns:
            Dictionary with detailed results including discovered URLs and page analysis
        """
        result = await self.execute(link, user_email, domain)
        
        return {
            'success': result.success,
            'message': result.message,
            'original_url': link,
            'final_url': result.link,
            'discovered_url': result.link if result.link != link else None,
            'method': result.method.value if result.method else None,
            'domain': domain
        }
