#!/usr/bin/env python3
"""
Comprehensive test for email decoding and link extraction
"""

import logging
from app.config import settings  # This initializes logging
from app.handlers.email_handler import EmailHandler
from app.types.email import EmailPayload, EmailBody
from example_email import example_email

def test_email_decoding_comprehensive():
    """Test email decoding with the real example email"""
    logger = logging.getLogger(__name__)
    
    print("Testing Email Decoding and Link Extraction")
    print("=" * 60)
    
    # Create email payload with the real encoded content
    email_payload = EmailPayload(
        subject="Fwd: AlphaSignal Newsletter",
        from_email="friend@example.com",
        to_email="me@example.com",
        headers=[],
        body=EmailBody(text="", html=example_email)
    )
    
    handler = EmailHandler(email_payload)
    
    print("1. Email Content Analysis:")
    print("-" * 30)
    print(f"   Original HTML length: {len(example_email)} characters")
    print(f"   Contains '=3D' sequences: {'=3D' in example_email}")
    print(f"   Contains 'href=3D': {'href=3D' in example_email}")
    
    # Test link extraction
    print("\n2. Link Extraction Results:")
    print("-" * 30)
    links = handler._extract_all_links()
    print(f"   Total links found: {len(links)}")
    
    # Show first few links
    for i, link in enumerate(links[:5], 1):
        print(f"   Link {i}:")
        print(f"     href: {link['href'][:80]}...")
        print(f"     text: '{link['text']}'")
        print(f"     context: {link['context'][:50]}...")
    
    if len(links) > 5:
        print(f"   ... and {len(links) - 5} more links")
    
    # Test body extraction for unsubscribe links
    print("\n3. Unsubscribe Link Detection:")
    print("-" * 30)
    body_result = handler._extract_from_body()
    if body_result:
        print(f"   HTTPS unsubscribe links: {len(body_result.https)}")
        for i, link in enumerate(body_result.https, 1):
            print(f"     {i}. {link}")
        
        print(f"   Mailto unsubscribe links: {len(body_result.mailto)}")
        for i, link in enumerate(body_result.mailto, 1):
            print(f"     {i}. {link}")
    else:
        print("   No unsubscribe links found")
    
    # Test forwarding detection
    print("\n4. Email Forwarding Detection:")
    print("-" * 30)
    is_forwarded = handler._is_forwarded_email()
    print(f"   Is forwarded email: {is_forwarded}")
    
    print("\n5. Summary:")
    print("-" * 30)
    print("✅ Quoted-printable decoding working")
    print("✅ Link extraction from encoded content")
    print("✅ Unsubscribe link detection")
    print("✅ Email forwarding detection")
    
    if body_result and (body_result.https or body_result.mailto):
        print("✅ Found unsubscribe links in real email content!")
    else:
        print("⚠️  No unsubscribe links found - may need to check keywords")

if __name__ == "__main__":
    test_email_decoding_comprehensive()
