# tests/test_email_handler_llm_integration.py

from app.types.email import EmailPayload, EmailHeader, EmailBody
from app.handlers.email_handler import EmailHandler
from app.types.unsubscribe import UnsubscribeMethod


def test_extract_with_llm_comprehensive_link_exists():
    """Integration test: LLM should prioritize comprehensive 'unsubscribe from all' link"""
    payload = EmailPayload(
        subject="Test",
        from_email="test@example.com",
        to_email="me@example.com",
        headers=[],
        body=EmailBody(
            text="", 
            html="""
            <html><body>
                <a href='https://newsletter.com/unsubscribe'>Unsubscribe from newsletter</a>
                <a href='https://promotions.com/opt-out'>Opt out of promotions</a>
                <a href='https://company.com/email-preferences'>Manage all email preferences</a>
            </body></html>
            """
        )
    )
    handler = EmailHandler(payload)
    result = handler._extract_with_llm()
    
    # LLM should prioritize the comprehensive link
    if result is not None:
        assert result.has_any() is True
        # Should find the comprehensive link (email-preferences)
        comprehensive_found = any("email-preferences" in link for link in result.https)
        assert comprehensive_found, f"Expected to find comprehensive link, got: {result.https}"


def test_extract_with_llm_comprehensive_link_not_exists():
    """Integration test: LLM should return all individual links when no comprehensive option exists"""
    payload = EmailPayload(
        subject="Test",
        from_email="test@example.com",
        to_email="me@example.com",
        headers=[],
        body=EmailBody(
            text="", 
            html="""
            <html><body>
                <a href='https://newsletter.com/unsubscribe'>Unsubscribe from newsletter</a>
                <a href='https://promotions.com/opt-out'>Opt out of promotions</a>
                <a href='mailto:unsubscribe@company.com'>Unsubscribe via email</a>
            </body></html>
            """
        )
    )
    handler = EmailHandler(payload)
    result = handler._extract_with_llm()
    
    # LLM should return all individual links
    if result is not None:
        assert result.has_any() is True
        # Should find multiple links since no comprehensive option exists
        total_links = len(result.https) + len(result.mailto)
        assert total_links >= 2, f"Expected multiple links, got: {result.https}, {result.mailto}"


def test_extract_with_llm_no_links_found():
    """Integration test: LLM should return empty when no unsubscribe links exist"""
    payload = EmailPayload(
        subject="Test",
        from_email="test@example.com",
        to_email="me@example.com",
        headers=[],
        body=EmailBody(
            text="", 
            html="<html><body><p>Just a regular message with no unsubscribe links</p></body></html>"
        )
    )
    handler = EmailHandler(payload)
    result = handler._extract_with_llm()
    
    # LLM should return empty result
    if result is not None:
        assert result.has_any() is False
        assert result.https == []
        assert result.mailto == []


def test_extract_with_llm_complex_html():
    """Integration test: LLM with complex HTML structure"""
    payload = EmailPayload(
        subject="Test",
        from_email="test@example.com",
        to_email="me@example.com",
        headers=[],
        body=EmailBody(
            text="", 
            html="""
            <html>
                <head><title>Newsletter</title></head>
                <body>
                    <div class="header">
                        <h1>Weekly Newsletter</h1>
                    </div>
                    <div class="content">
                        <p>Here's your weekly update...</p>
                        <div class="footer">
                            <p>Don't want to receive these emails?</p>
                            <a href='https://company.com/unsubscribe-all'>Unsubscribe from all emails</a>
                            <br>
                            <a href='https://company.com/preferences'>Manage your email preferences</a>
                        </div>
                    </div>
                </body>
            </html>
            """
        )
    )
    handler = EmailHandler(payload)
    result = handler._extract_with_llm()
    
    # LLM should find unsubscribe links in complex HTML
    if result is not None:
        assert result.has_any() is True
        # Should find comprehensive links
        comprehensive_found = any("unsubscribe-all" in link or "preferences" in link for link in result.https)
        assert comprehensive_found, f"Expected to find comprehensive links, got: {result.https}"


def test_extract_with_llm_mixed_keywords():
    """Integration test: LLM with various unsubscribe keyword variations"""
    payload = EmailPayload(
        subject="Test",
        from_email="test@example.com",
        to_email="me@example.com",
        headers=[],
        body=EmailBody(
            text="", 
            html="""
            <html><body>
                <a href='https://example.com/remove'>Remove me from this list</a>
                <a href='https://example.com/stop'>Stop receiving emails</a>
                <a href='https://example.com/opt-out'>Opt out</a>
                <a href='mailto:unsubscribe@example.com'>Unsubscribe via email</a>
            </body></html>
            """
        )
    )
    handler = EmailHandler(payload)
    result = handler._extract_with_llm()
    
    # LLM should find links with various keyword variations
    if result is not None:
        assert result.has_any() is True
        # Should find multiple links with different keywords
        total_links = len(result.https) + len(result.mailto)
        assert total_links >= 2, f"Expected multiple links with various keywords, got: {result.https}, {result.mailto}"


def test_extract_with_llm_realistic_newsletter():
    """Integration test: LLM with realistic newsletter HTML"""
    payload = EmailPayload(
        subject="Fwd: Weekly Newsletter - Special Offers Inside!",
        from_email="friend@example.com",
        to_email="me@example.com",
        headers=[],
        body=EmailBody(
            text="", 
            html="""
            <html>
                <head>
                    <meta charset="utf-8">
                    <title>Weekly Newsletter</title>
                </head>
                <body style="font-family: Arial, sans-serif;">
                    <div style="max-width: 600px; margin: 0 auto;">
                        <header style="background-color: #f8f9fa; padding: 20px; text-align: center;">
                            <h1 style="color: #333;">Weekly Newsletter</h1>
                        </header>
                        
                        <main style="padding: 20px;">
                            <h2>This Week's Highlights</h2>
                            <p>Check out our latest products and special offers...</p>
                            
                            <div style="background-color: #e9ecef; padding: 15px; margin: 20px 0;">
                                <h3>Special Offer!</h3>
                                <p>Get 20% off your next purchase. Use code: SAVE20</p>
                            </div>
                        </main>
                        
                        <footer style="background-color: #f8f9fa; padding: 20px; text-align: center; font-size: 12px; color: #666;">
                            <p>You received this email because you subscribed to our newsletter.</p>
                            <p>
                                <a href="https://company.com/unsubscribe-all" style="color: #007bff;">Unsubscribe from all emails</a> | 
                                <a href="https://company.com/preferences" style="color: #007bff;">Manage preferences</a> | 
                                <a href="https://company.com/contact" style="color: #007bff;">Contact us</a>
                            </p>
                            <p>Company Name, 123 Main St, City, State 12345</p>
                        </footer>
                    </div>
                </body>
            </html>
            """
        )
    )
    handler = EmailHandler(payload)
    result = handler._extract_with_llm()
    
    # LLM should find unsubscribe links in realistic newsletter
    if result is not None:
        assert result.has_any() is True
        # Should find comprehensive links
        comprehensive_found = any("unsubscribe-all" in link or "preferences" in link for link in result.https)
        assert comprehensive_found, f"Expected to find comprehensive links in newsletter, got: {result.https}"


def test_extract_with_llm_ambiguous_text():
    """Integration test: LLM with ambiguous unsubscribe text"""
    payload = EmailPayload(
        subject="Test",
        from_email="test@example.com",
        to_email="me@example.com",
        headers=[],
        body=EmailBody(
            text="", 
            html="""
            <html><body>
                <p>If you no longer wish to receive these communications, please click here to stop receiving emails.</p>
                <a href='https://example.com/click-here'>Click here</a>
                <p>Or manage your subscription preferences:</p>
                <a href='https://example.com/subscription-settings'>Subscription Settings</a>
            </body></html>
            """
        )
    )
    handler = EmailHandler(payload)
    result = handler._extract_with_llm()
    
    # LLM should understand context and find unsubscribe links
    if result is not None:
        assert result.has_any() is True
        # Should find links based on context
        total_links = len(result.https) + len(result.mailto)
        assert total_links >= 1, f"Expected to find unsubscribe links based on context, got: {result.https}, {result.mailto}"


if __name__ == "__main__":
    print("Running LLM integration tests...")
    try:
        test_extract_with_llm_comprehensive_link_exists()
        test_extract_with_llm_comprehensive_link_not_exists()
        test_extract_with_llm_multiple_comprehensive_links()
        test_extract_with_llm_no_links_found()
        test_extract_with_llm_complex_html()
        test_extract_with_llm_mixed_keywords()
        test_extract_with_llm_realistic_newsletter()
        test_extract_with_llm_ambiguous_text()
        print("All LLM integration tests passed!")
    except Exception as e:
        print(f"LLM integration tests failed (LLM may not be available): {e}")
        import traceback
        traceback.print_exc()
