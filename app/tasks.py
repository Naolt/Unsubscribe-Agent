"""
Celery tasks for the unsubscribe agent.
Handles queued email processing and unsubscription tasks.
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List

from app.celery_app import celery_app
from app.config import settings
from app.services.email_unsubscribe_service import create_email_unsubscribe_service
from app.types.email import EmailPayload, EmailBody, EmailHeader
from app.models.domain_unsubscribe import DomainUnsubscribeTaskResult

logger = logging.getLogger(__name__)


@celery_app.task(bind=True)
def process_email_task(self, email_data: Dict[str, Any], user_email: Optional[str] = None) -> Dict[str, Any]:
    """
    Queue task for processing email unsubscriptions.
    
    This task replaces the synchronous processing in the webhook endpoint.
    It converts the email data to the proper types and processes it using
    the existing EmailUnsubscribeService.
    
    Args:
        email_data: Dictionary containing email information (subject, from_email, etc.)
        user_email: Optional user email address for context
        
    Returns:
        Dictionary with processing results
    """
    try:
        logger.info(f"Processing email task {self.request.id}")
        logger.debug(f"Email data: {email_data}")
        
        # Convert dictionary back to EmailPayload object
        email_payload = EmailPayload(**email_data)
        
        # Create service and process using existing logic
        service = create_email_unsubscribe_service()
        result = asyncio.run(service.process_email(
            email_payload=email_payload, 
            user_email=user_email,
            use_llm_only=settings.USE_LLM_ONLY if settings.USE_LLM_ONLY else False
        ))
        
        logger.info(f"Email task {self.request.id} completed successfully")
        logger.info(f"Results: {result.successful_unsubscribes} successful, {result.failed_unsubscribes} failed")
        
        return {
            'success': result.success,
            'message': result.message,
            'total_links_found': result.total_links_found,
            'links_processed': result.links_processed,
            'successful_unsubscribes': result.successful_unsubscribes,
            'failed_unsubscribes': result.failed_unsubscribes,
            'task_id': self.request.id,
            'results': [
                {
                    'success': r.success,
                    'method': r.method.value if r.method else None,
                    'link': r.link,
                    'message': r.message
                }
                for r in result.results
            ]
        }
        
    except Exception as exc:
        logger.error(f"Email task {self.request.id} failed: {exc}")
        logger.exception("Full exception details:")
        
        # Return error information instead of re-raising to avoid retries
        return {
            'success': False,
            'message': f'Task failed: {str(exc)}',
            'error': str(exc),
            'task_id': self.request.id,
            'total_links_found': 0,
            'links_processed': 0,
            'successful_unsubscribes': 0,
            'failed_unsubscribes': 0,
            'results': []
        }


@celery_app.task(bind=True)
def process_domain_unsubscribe_task(self, domain: str, user_email: str, unsubscribe_urls: List[str]) -> Dict[str, Any]:
    """
    Background task for domain-based unsubscription.
    
    This task:
    1. Processes discovered unsubscribe URLs for a domain
    2. Uses browser automation to attempt unsubscription
    3. Updates domain index with results
    4. Returns comprehensive results
    
    Args:
        domain: Domain name (e.g., example.com)
        user_email: User's email address for unsubscription
        unsubscribe_urls: List of discovered unsubscribe URLs
        
    Returns:
        Dictionary with processing results
    """
    try:
        logger.info(f"Processing domain unsubscription task {self.request.id}")
        logger.info(f"Domain: {domain}, User: {user_email}, URLs: {len(unsubscribe_urls)}")
        
        # Import here to avoid circular imports
        from app.services.domain_unsubscribe_service import DomainUnsubscribeService
        from app.models.domain_crawler import DomainDiscoveryResult, UnsubscribeCandidate
        
        # Create a mock discovery result from the URLs
        # This allows us to use the intelligent service
        candidates = []
        for i, url in enumerate(unsubscribe_urls):
            candidate = UnsubscribeCandidate(
                url=url,
                confidence=0.9 - (i * 0.1),  # Decreasing confidence
                reason=f"URL {i+1} from domain discovery",
                found_on_page=url,
                has_email_form=True,
                has_unsubscribe_text=True
            )
            candidates.append(candidate)
        
        # Create discovery result
        discovery_result = DomainDiscoveryResult(
            domain=domain,
            status="completed",
            confident_result=candidates[0] if candidates else None,
            possible_candidates=candidates[1:] if len(candidates) > 1 else [],
            crawl_summary={"urls_provided": len(unsubscribe_urls)},
            errors=[]
        )
        
        # Use the intelligent domain unsubscribe service
        service = DomainUnsubscribeService()
        task_result = asyncio.run(service.process_domain_unsubscribe(domain, user_email, discovery_result))
        
        # Update task ID
        task_result.task_id = self.request.id
        
        # Update domain index with results
        asyncio.run(service.update_domain_index_with_results(domain, task_result.results))
        
        logger.info(f"Domain unsubscription task {self.request.id} completed")
        logger.info(f"Results: {task_result.successful_unsubscribes} successful, {task_result.failed_unsubscribes} failed")
        
        return task_result.dict()
        
    except Exception as exc:
        logger.error(f"Domain unsubscription task {self.request.id} failed: {exc}")
        logger.exception("Full exception details:")
        
        # Return error information
        return {
            'success': False,
            'message': f'Task failed: {str(exc)}',
            'error': str(exc),
            'domain': domain,
            'user_email': user_email,
            'task_id': self.request.id,
            'unsubscribe_urls_found': len(unsubscribe_urls) if unsubscribe_urls else 0,
            'urls_attempted': 0,
            'successful_unsubscribes': 0,
            'failed_unsubscribes': 0,
            'results': []
        }


@celery_app.task(bind=True)
def health_check_task(self) -> Dict[str, Any]:
    """
    Health check task to monitor worker status.
    
    Returns:
        Dictionary with worker health information
    """
    try:
        return {
            'status': 'healthy',
            'worker': self.request.hostname,
            'task_id': self.request.id,
            'timestamp': datetime.utcnow().isoformat()
        }
    except Exception as exc:
        logger.error(f"Health check failed: {exc}")
        return {
            'status': 'unhealthy',
            'error': str(exc),
            'worker': self.request.hostname,
            'task_id': self.request.id
        }
