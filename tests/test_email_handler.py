# tests/test_email_handler.py

from app.types.email import EmailPayload, EmailHeader, EmailBody
from app.handlers.email_handler import EmailHandler

def test_with_list_unsubscribe_https():
    payload = EmailPayload(
        subject="Test email with unsubscribe",
        from_email="news@example.com",
        to_email="me@example.com",
        headers=[EmailHeader(name="List-Unsubscribe", value="<https://example.com/unsub?id=123>")],
        body=EmailBody(text="", html="<p>Hello, unsubscribe <a href='https://example.com/unsub?id=123'>here</a></p>")
    )
    handler = EmailHandler(payload)
    result = handler.handle()
    
    assert result.success is True
    assert result.method == "https"
    assert "https://example.com/unsub?id=123" in result.message

def test_with_list_unsubscribe_mailto():
    payload = EmailPayload(
        subject="Test mailto unsubscribe",
        from_email="news@example.com",
        to_email="me@example.com",
        headers=[EmailHeader(name="List-Unsubscribe", value="<mailto:unsubscribe@example.com>")],
        body=EmailBody(text="", html="")
    )
    handler = EmailHandler(payload)
    result = handler.handle()

    assert result.success is True
    assert result.method == "mailto"
    assert "unsubscribe@example.com" in result.message

def test_with_footer_only():
    payload = EmailPayload(
        subject="Test footer unsubscribe",
        from_email="ads@example.com",
        to_email="me@example.com",
        headers=[],
        body=EmailBody(text="", html="<html><body>Click <a href='https://ads.example.com/unsub'>unsubscribe</a> to stop emails.</body></html>")
    )
    handler = EmailHandler(payload)
    result = handler.handle()

    assert result.success is True
    assert result.method == "https"
    assert "FOUND_UNSUBSCRIBE_FOOTER_LINK" in result.message

def test_with_no_unsubscribe():
    payload = EmailPayload(
        subject="Transactional email",
        from_email="support@example.com",
        to_email="me@example.com",
        headers=[],
        body=EmailBody(text="Thanks for your order.", html="<p>Your order has shipped.</p>")
    )
    handler = EmailHandler(payload)
    result = handler.handle()

    assert result.success is False
    assert result.method == "none"
    assert result.message == "No unsubscribe link found"

if __name__ == "__main__":
    test_with_list_unsubscribe_https()
    test_with_list_unsubscribe_mailto()
    test_with_footer_only()
    test_with_no_unsubscribe()
    print("All tests passed!")
