# tests/test_email_handler.py

from app.types.email import EmailPayload, EmailHeader, EmailBody
from app.handlers.email_handler import EmailHandler
from app.types.unsubscribe import UnsubscribeMethod


def test_is_forwarded_email_subject_patterns():
    """Test _is_forwarded_email with various subject patterns"""
    handler = EmailHandler(EmailPayload(subject="Fwd: Test", from_email="test@example.com", to_email="me@example.com", headers=[], body=EmailBody()))
    assert handler._is_forwarded_email() is True
    
    handler = EmailHandler(EmailPayload(subject="FW: Test", from_email="test@example.com", to_email="me@example.com", headers=[], body=EmailBody()))
    assert handler._is_forwarded_email() is True
    
    handler = EmailHandler(EmailPayload(subject="Re: Test", from_email="test@example.com", to_email="me@example.com", headers=[], body=EmailBody()))
    assert handler._is_forwarded_email() is True
    
    handler = EmailHandler(EmailPayload(subject="Forwarded Message", from_email="test@example.com", to_email="me@example.com", headers=[], body=EmailBody()))
    assert handler._is_forwarded_email() is True


def test_is_forwarded_email_body_patterns():
    """Test _is_forwarded_email with body patterns"""
    handler = EmailHandler(EmailPayload(
        subject="Test", 
        from_email="test@example.com", 
        to_email="me@example.com", 
        headers=[], 
        body=EmailBody(text="Begin forwarded message", html="")
    ))
    assert handler._is_forwarded_email() is True
    
    handler = EmailHandler(EmailPayload(
        subject="Test", 
        from_email="test@example.com", 
        to_email="me@example.com", 
        headers=[], 
        body=EmailBody(text="", html="<p>Original message</p>")
    ))
    assert handler._is_forwarded_email() is True
    
    handler = EmailHandler(EmailPayload(
        subject="Test", 
        from_email="test@example.com", 
        to_email="me@example.com", 
        headers=[], 
        body=EmailBody(text="", html="<p>From: sender@example.com<br>To: recipient@example.com</p>")
    ))
    assert handler._is_forwarded_email() is True


def test_is_forwarded_email_negative():
    """Test _is_forwarded_email returns False for non-forwarded emails"""
    handler = EmailHandler(EmailPayload(
        subject="Regular Newsletter", 
        from_email="news@example.com", 
        to_email="me@example.com", 
        headers=[], 
        body=EmailBody(text="Hello world", html="<p>Hello world</p>")
    ))
    assert handler._is_forwarded_email() is False


def test_extract_from_body_single_https():
    """Test _extract_from_body with single HTTPS link"""
    payload = EmailPayload(
        subject="Test",
        from_email="test@example.com",
        to_email="me@example.com",
        headers=[],
        body=EmailBody(text="", html="<a href='https://example.com/unsubscribe'>Unsubscribe</a>")
    )
    handler = EmailHandler(payload)
    result = handler._extract_from_body()
    
    assert result is not None
    assert result.https == ["https://example.com/unsubscribe"]
    assert result.mailto == []
    assert result.has_any() is True


def test_extract_from_body_multiple_https():
    """Test _extract_from_body with multiple HTTPS links"""
    payload = EmailPayload(
        subject="Test",
        from_email="test@example.com",
        to_email="me@example.com",
        headers=[],
        body=EmailBody(
            text="", 
            html="""
            <a href='https://newsletter.com/unsubscribe'>Unsubscribe from newsletter</a>
            <a href='https://promotions.com/opt-out'>Opt out of promotions</a>
            <a href='https://company.com/email-preferences'>Manage preferences</a>
            """
        )
    )
    handler = EmailHandler(payload)
    result = handler._extract_from_body()
    
    assert result is not None
    assert len(result.https) == 3
    assert "https://newsletter.com/unsubscribe" in result.https
    assert "https://promotions.com/opt-out" in result.https
    assert "https://company.com/email-preferences" in result.https
    assert result.mailto == []


def test_extract_from_body_mailto():
    """Test _extract_from_body with mailto links"""
    payload = EmailPayload(
        subject="Test",
        from_email="test@example.com",
        to_email="me@example.com",
        headers=[],
        body=EmailBody(text="", html="<a href='mailto:unsubscribe@example.com'>Unsubscribe</a>")
    )
    handler = EmailHandler(payload)
    result = handler._extract_from_body()
    
    assert result is not None
    assert result.https == []
    assert result.mailto == ["mailto:unsubscribe@example.com"]
    assert result.has_any() is True


def test_extract_from_body_mixed_links():
    """Test _extract_from_body with both HTTPS and mailto links"""
    payload = EmailPayload(
        subject="Test",
        from_email="test@example.com",
        to_email="me@example.com",
        headers=[],
        body=EmailBody(
            text="", 
            html="""
            <a href='https://example.com/unsubscribe'>Unsubscribe online</a>
            <a href='mailto:unsubscribe@example.com'>Unsubscribe via email</a>
            """
        )
    )
    handler = EmailHandler(payload)
    result = handler._extract_from_body()
    
    assert result is not None
    assert result.https == ["https://example.com/unsubscribe"]
    assert result.mailto == ["mailto:unsubscribe@example.com"]
    assert result.has_any() is True


def test_extract_from_body_expanded_keywords():
    """Test _extract_from_body with expanded unsubscribe keywords"""
    payload = EmailPayload(
        subject="Test",
        from_email="test@example.com",
        to_email="me@example.com",
        headers=[],
        body=EmailBody(
            text="", 
            html="""
            <a href='https://example.com/remove'>Remove me from this list</a>
            <a href='https://example.com/stop'>Stop receiving emails</a>
            <a href='https://example.com/preferences'>Manage preferences</a>
            <a href='https://example.com/opt-out'>Opt out</a>
            """
        )
    )
    handler = EmailHandler(payload)
    result = handler._extract_from_body()
    
    assert result is not None
    assert len(result.https) == 4
    assert "https://example.com/remove" in result.https
    assert "https://example.com/stop" in result.https
    assert "https://example.com/preferences" in result.https
    assert "https://example.com/opt-out" in result.https


def test_extract_from_body_no_links():
    """Test _extract_from_body with no unsubscribe links"""
    payload = EmailPayload(
        subject="Test",
        from_email="test@example.com",
        to_email="me@example.com",
        headers=[],
        body=EmailBody(text="", html="<p>Just a regular message</p>")
    )
    handler = EmailHandler(payload)
    result = handler._extract_from_body()
    
    assert result is None


def test_extract_from_body_no_html():
    """Test _extract_from_body with no HTML content"""
    payload = EmailPayload(
        subject="Test",
        from_email="test@example.com",
        to_email="me@example.com",
        headers=[],
        body=EmailBody(text="", html=None)
    )
    handler = EmailHandler(payload)
    result = handler._extract_from_body()
    
    assert result is None




def test_extract_with_llm_no_html():
    """Test _extract_with_llm with no HTML content"""
    payload = EmailPayload(
        subject="Test",
        from_email="test@example.com",
        to_email="me@example.com",
        headers=[],
        body=EmailBody(text="", html="")
    )
    handler = EmailHandler(payload)
    result = handler._extract_with_llm()
    
    assert result is None


def test_extract_with_llm_short_html():
    """Test _extract_with_llm with very short HTML content"""
    payload = EmailPayload(
        subject="Test",
        from_email="test@example.com",
        to_email="me@example.com",
        headers=[],
        body=EmailBody(text="", html="<p>Hi</p>")
    )
    handler = EmailHandler(payload)
    result = handler._extract_with_llm()
    
    assert result is None


def test_extract_with_llm_no_href():
    """Test _extract_with_llm with HTML that has no href attributes"""
    payload = EmailPayload(
        subject="Test",
        from_email="test@example.com",
        to_email="me@example.com",
        headers=[],
        body=EmailBody(text="", html="<html><body><p>Just text content with no links</p><div>More content</div></body></html>")
    )
    handler = EmailHandler(payload)
    result = handler._extract_with_llm()
    
    assert result is None


def test_handle_forwarded_email_success():
    """Test handle() method with successful forwarded email processing"""
    payload = EmailPayload(
        subject="Fwd: Newsletter",
        from_email="friend@example.com",
        to_email="me@example.com",
        headers=[],
        body=EmailBody(text="", html="<a href='https://example.com/unsubscribe'>Unsubscribe</a>")
    )
    handler = EmailHandler(payload)
    result = handler.handle()
    
    assert result.success is True
    assert result.method == UnsubscribeMethod.HTTPS


def test_handle_non_forwarded_email():
    """Test handle() method rejects non-forwarded emails"""
    payload = EmailPayload(
        subject="Regular Newsletter",
        from_email="news@example.com",
        to_email="me@example.com",
        headers=[],
        body=EmailBody(text="", html="<a href='https://example.com/unsubscribe'>Unsubscribe</a>")
    )
    handler = EmailHandler(payload)
    result = handler.handle()
    
    assert result.success is False
    assert result.message == "Email is not forwarded"


if __name__ == "__main__":
    # Unit tests (fast, no external dependencies)
    test_is_forwarded_email_subject_patterns()
    test_is_forwarded_email_body_patterns()
    test_is_forwarded_email_negative()
    test_extract_from_body_single_https()
    test_extract_from_body_multiple_https()
    test_extract_from_body_mailto()
    test_extract_from_body_mixed_links()
    test_extract_from_body_expanded_keywords()
    test_extract_from_body_no_links()
    test_extract_from_body_no_html()
    test_extract_with_llm_no_html()
    test_extract_with_llm_short_html()
    test_extract_with_llm_no_href()
    test_handle_forwarded_email_success()
    test_handle_non_forwarded_email()
    
    print("All unit tests passed!")
    print("Note: LLM integration tests are in test_email_handler_llm_integration.py")
