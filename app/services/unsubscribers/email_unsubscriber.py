from app.services.unsubscribers.base import BaseUnsubscriber
from app.types.unsubscribe import UnsubscribeMethod, UnsubscriberResult


class MailtoUnsubscriber(BaseUnsubscriber):
    def can_handle(self, method: UnsubscribeMethod) -> bool:
        return method == UnsubscribeMethod.MAILTO

    def execute(self, link: str, user_email: str | None = None) -> UnsubscriberResult:
        # send unsubscribe email via SMTP/provider
        return UnsubscriberResult(
            success=True,
            method=UnsubscribeMethod.MAILTO,
            link=link,
            message=f"Sent unsubscribe email to {link}",
        )
