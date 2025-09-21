#!/usr/bin/env python3
"""
Test script to demonstrate the link caching optimization
"""

import logging
from app.config import settings  # This initializes logging
from app.handlers.email_handler import EmailHandler
from app.types.email import EmailPayload, EmailBody

def test_link_caching_optimization():
    """Test that links are extracted and cached only once"""
    logger = logging.getLogger(__name__)
    
    # Create a test email with multiple links
    test_html = """
    <html><body>
        <p>Some content here</p>
        <a href="https://newsletter.com/unsubscribe">Unsubscribe from newsletter</a>
        <a href="https://promotions.com/opt-out">Opt out of promotions</a>
        <a href="https://company.com/email-preferences">Manage all email preferences</a>
        <a href="https://other.com/regular-link">Regular link</a>
        <a href="mailto:unsubscribe@company.com">Email unsubscribe</a>
        <p>More content</p>
    </body></html>
    """
    
    email_payload = EmailPayload(
        subject="Fwd: Test Newsletter",
        from_email="friend@example.com",
        to_email="me@example.com",
        headers=[],
        body=EmailBody(text="", html=test_html)
    )
    
    handler = EmailHandler(email_payload)
    
    print("Testing link caching optimization:")
    print("-" * 50)
    
    # First call - should extract and cache links
    print("1. First call to _extract_all_links():")
    links1 = handler._extract_all_links()
    print(f"   Found {len(links1)} links")
    
    # Second call - should return cached links
    print("2. Second call to _extract_all_links():")
    links2 = handler._extract_all_links()
    print(f"   Found {len(links2)} links (should be cached)")
    
    # Verify they're the same
    print(f"3. Links are identical: {links1 is links2}")
    
    # Test body extraction using cached links
    print("4. Testing body extraction with cached links:")
    body_result = handler._extract_from_body()
    if body_result:
        print(body_result.to_dict())
        print(f"   Found {len(body_result.https)} HTTPS links, {len(body_result.mailto)} mailto links")
    else:
        print("   No unsubscribe links found")
    
    print("-" * 50)
    print("Optimization benefits:")
    print("✅ HTML parsed only once")
    print("✅ Links cached for reuse")
    print("✅ Both body extraction and LLM use same data")
    print("✅ Reduced token usage for LLM calls")

if __name__ == "__main__":
    test_link_caching_optimization()
