# app/services/email_unsubscribe_service.py

import logging
from typing import List, Optional
from app.handlers.email_handler import EmailHandler, EmailHandlerResult
from app.services.unsubscribers.unsubscriber import Unsubscriber
from app.types.email import EmailPayload
from app.types.unsubscribe import UnsubscribeMethod, UnsubscriberResult

# Set up logger for this module
logger = logging.getLogger(__name__)


class EmailUnsubscribeResult:
    """Result of processing an email for unsubscription"""
    def __init__(
        self,
        success: bool,
        total_links_found: int,
        links_processed: int,
        successful_unsubscribes: int,
        failed_unsubscribes: int,
        results: List[UnsubscriberResult],
        message: str = ""
    ):
        self.success = success
        self.total_links_found = total_links_found
        self.links_processed = links_processed
        self.successful_unsubscribes = successful_unsubscribes
        self.failed_unsubscribes = failed_unsubscribes
        self.results = results
        self.message = message

    def __repr__(self):
        return (
            f"<EmailUnsubscribeResult success={self.success} "
            f"found={self.total_links_found} processed={self.links_processed} "
            f"successful={self.successful_unsubscribes} failed={self.failed_unsubscribes}>"
        )


class EmailUnsubscribeService:
    """
    Service that processes emails to unsubscribe from all found links.
    Uses the existing Unsubscriber class to handle different unsubscribe methods.
    """
    
    def __init__(self, unsubscriber: Unsubscriber):
        self.unsubscriber = unsubscriber
        logger.info("EmailUnsubscribeService initialized")

    async def process_email(
        self, 
        email_payload: EmailPayload, 
        user_email: Optional[str] = None,
        use_llm_only: bool = False
    ) -> EmailUnsubscribeResult:
        """
        Process an email to unsubscribe from all found links.
        
        Args:
            email_payload: The email to process
            user_email: User's email address (for context/login)
            use_llm_only: If True, skip body extraction and use only LLM for link extraction
        
        Returns:
            EmailUnsubscribeResult with consolidated results
        """
        logger.info(f"Starting email processing with use_llm_only={use_llm_only}")
        
        # Step 1: Extract unsubscribe links from email
        email_handler = EmailHandler(email_payload)
        handler_result = email_handler.handle(use_llm_only=use_llm_only)
        
        if not handler_result.success:
            logger.warning(f"Email handler failed: {handler_result.message}")
            return EmailUnsubscribeResult(
                success=False,
                total_links_found=0,
                links_processed=0,
                successful_unsubscribes=0,
                failed_unsubscribes=0,
                results=[],
                message=handler_result.message
            )
        
        # Step 2: Get separated links from the handler result
        https_links = handler_result.https_links
        mailto_links = handler_result.mailto_links
        all_links = handler_result.all_links
        
        logger.info(f"Found {len(https_links)} HTTPS links and {len(mailto_links)} mailto links")
        
        if not all_links:
            logger.warning("No unsubscribe links found in email")
            return EmailUnsubscribeResult(
                success=False,
                total_links_found=0,
                links_processed=0,
                successful_unsubscribes=0,
                failed_unsubscribes=0,
                results=[],
                message="No unsubscribe links found in email"
            )
        
        # Step 3: Process all links using the existing Unsubscriber
        logger.info("Starting unsubscribe processing")
        results = []
        successful_count = 0
        failed_count = 0
        
        # Process all HTTPS links
        logger.info(f"Processing {len(https_links)} HTTPS links")
        for i, link in enumerate(https_links, 1):
            logger.info(f"Processing HTTPS link {i}/{len(https_links)}: {link}")
            result = await self.unsubscriber.unsubscribe(UnsubscribeMethod.HTTPS, link, user_email)
            results.append(result)
            
            if result.success:
                successful_count += 1
                logger.info(f"HTTPS link {i} processed successfully")
            else:
                failed_count += 1
                logger.warning(f"HTTPS link {i} failed: {result.message}")
        
        # # Process all mailto links
        # logger.info(f"Processing {len(mailto_links)} mailto links")
        # for i, link in enumerate(mailto_links, 1):
        #     logger.info(f"Processing mailto link {i}/{len(mailto_links)}: {link}")
        #     result = await self.unsubscriber.unsubscribe(UnsubscribeMethod.MAILTO, link, user_email)
        #     results.append(result)
            
        #     if result.success:
        #         successful_count += 1
        #         logger.info(f"Mailto link {i} processed successfully")
        #     else:
        #         failed_count += 1
        #         logger.warning(f"Mailto link {i} failed: {result.message}")
        
        # Step 4: Determine overall success
        overall_success = successful_count > 0
        
        logger.info(f"Unsubscribe processing completed: {successful_count} successful, {failed_count} failed")
        
        return EmailUnsubscribeResult(
            success=overall_success,
            total_links_found=len(all_links),
            links_processed=len(results),
            successful_unsubscribes=successful_count,
            failed_unsubscribes=failed_count,
            results=results,
            message=f"Processed {len(all_links)} links: {successful_count} successful, {failed_count} failed"
        )


# Factory function to create service with default unsubscribers
def create_email_unsubscribe_service() -> EmailUnsubscribeService:
    """Create an email unsubscribe service with default unsubscriber implementations"""
    from app.services.unsubscribers.browser_use_unsubscriber import BrowserUseUnsubscriber
    from app.services.unsubscribers.email_unsubscriber import MailtoUnsubscriber
    
    # Create unsubscriber instances
    browser_unsubscriber = BrowserUseUnsubscriber()
    mailto_unsubscriber = MailtoUnsubscriber()
    
    # Create unsubscriber orchestrator with all implementations
    unsubscriber = Unsubscriber([browser_unsubscriber, mailto_unsubscriber])
    
    return EmailUnsubscribeService(unsubscriber)
