# tests/test_email_handler.py

from app.types.email import EmailPayload, EmailHeader, EmailBody
from app.handlers.email_handler import EmailHandler
from app.types.unsubscribe import UnsubscribeMethod


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
    assert result.method == UnsubscribeMethod.HTTPS

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
    assert result.method == UnsubscribeMethod.MAILTO

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
    assert result.method == UnsubscribeMethod.HTTPS

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
    assert result.method is None

def test_with_llm():
    payload = EmailPayload(
        subject="Test footer unsubscribe using llm",
        from_email="ads@example.com",
        to_email="me@example.com",
        headers=[],
        body=EmailBody(text="", html="<html><body>Click <a href='https://ads.example.com/unsub'>this one</a> to stop emails.</body></html>")
    )
    handler = EmailHandler(payload)
    result = handler.handle()
    assert result.success is True
    assert result.method == "https"

if __name__ == "__main__":
    test_with_list_unsubscribe_https()
    test_with_list_unsubscribe_mailto()
    test_with_footer_only()
    test_with_no_unsubscribe()
    test_with_llm()
    print("All tests passed!")
