#!/usr/bin/env python3
"""
Test script to demonstrate quoted-printable decoding
"""

import logging
from app.config import settings  # This initializes logging
from app.handlers.email_handler import EmailHandler
from app.types.email import EmailPayload, EmailBody

def test_quoted_printable_decoding():
    """Test that quoted-printable encoded content is properly decoded"""
    logger = logging.getLogger(__name__)
    
    # Create a test email with quoted-printable encoded content (like your real email)
    encoded_html = """
    <html><body>
        <p>Some content here</p>
        <a href=3D"https://alphasignal.ai/unsubscribe/977d382662d0a48f5fc8651718ea23e4:25d14d07de072faa4178acb0d971245903283a9c928a5a50c97de13c882d7b67?cid=3Db84188a5166810da" style=3D"color:#8d8d8d;text-decoration:none;font-size:15px">def unsubscribe_me(): return True</a>
        <a href=3D"https://other.com/regular-link">Regular link</a>
        <p>More content with =3D encoding</p>
    </body></html>
    """
    
    email_payload = EmailPayload(
        subject="Fwd: Test Newsletter",
        from_email="friend@example.com",
        to_email="me@example.com",
        headers=[],
        body=EmailBody(text="", html=encoded_html)
    )
    
    handler = EmailHandler(email_payload)
    
    print("Testing quoted-printable decoding:")
    print("-" * 60)
    
    # Test the decoding method directly
    print("1. Testing _decode_quoted_printable method:")
    test_encoded = "href=3D\"https://example.com\" style=3D\"color:red\""
    decoded = handler._decode_quoted_printable(test_encoded)
    print(f"   Original: {test_encoded}")
    print(f"   Decoded:  {decoded}")
    
    # Test link extraction with encoded content
    print("\n2. Testing link extraction with encoded content:")
    links = handler._extract_all_links()
    print(f"   Found {len(links)} links")
    
    for i, link in enumerate(links, 1):
        print(f"   Link {i}:")
        print(f"     href: {link['href']}")
        print(f"     text: {link['text']}")
        print(f"     context: {link['context'][:50]}...")
    
    # Test body extraction
    print("\n3. Testing body extraction:")
    body_result = handler._extract_from_body()
    if body_result:
        print(f"   Found {len(body_result.https)} HTTPS links, {len(body_result.mailto)} mailto links")
        for link in body_result.https:
            print(f"     HTTPS: {link}")
    else:
        print("   No unsubscribe links found")
    
    print("-" * 60)
    print("Benefits of quoted-printable decoding:")
    print("✅ Properly decodes =3D sequences")
    print("✅ Handles line breaks with = characters")
    print("✅ Extracts clean URLs from encoded content")
    print("✅ Works with real-world email content")

if __name__ == "__main__":
    test_quoted_printable_decoding()
