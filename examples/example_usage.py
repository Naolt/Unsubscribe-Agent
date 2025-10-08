# example_usage.py
"""
Example usage of the Email Unsubscribe Service
"""

import asyncio
from app.config import settings  # This will initialize logging
from app.services.email_unsubscribe_service import create_email_unsubscribe_service
from app.types.email import EmailPayload, EmailBody
from example_email import example_email


async def main():
    """Example of processing a forwarded email for unsubscription"""

    # Create the service with default unsubscribers
    service = create_email_unsubscribe_service()
    
    # Example forwarded email payload
    email_payload = EmailPayload(
        subject="Fwd: Weekly Newsletter - Special Offers Inside!",
        from_email="friend@example.com",
        to_email="me@example.com",
        headers=[],
        body=EmailBody(
            text="", 
            html=example_email)
    )
    
    # Process the email
    result = await service.process_email(
        email_payload=email_payload,
        user_email="me@example.com",
        use_llm_only=False  # Set to True to skip body extraction and use only LLM
    )
    
    # Print results
    print(f"Overall Success: {result.success}")
    print(f"Total Links Found: {result.total_links_found}")
    print(f"Links Processed: {result.links_processed}")
    print(f"Successful Unsubscribes: {result.successful_unsubscribes}")
    print(f"Failed Unsubscribes: {result.failed_unsubscribes}")
    print(f"Message: {result.message}")
    
    # Print individual results
    for i, unsub_result in enumerate(result.results):
        print(f"\nLink {i+1}: {unsub_result.link}")
        print(f"  Success: {unsub_result.success}")
        print(f"  Method: {unsub_result.method}")
        print(f"  Message: {unsub_result.message}")


if __name__ == "__main__":
    asyncio.run(main())
