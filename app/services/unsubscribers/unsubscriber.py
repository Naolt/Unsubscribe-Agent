from app.services.unsubscribers.base import BaseUnsubscriber
from app.types.unsubscribe import UnsubscribeMethod, UnsubscriberResult


class Unsubscriber:
    def __init__(self, executors: list[BaseUnsubscriber]):
        self.executors = executors

    def unsubscribe(self, method: UnsubscribeMethod, link: str, user_email: str | None = None) -> UnsubscriberResult:
        for executor in self.executors:
            if executor.can_handle(method):
                return executor.execute(link, user_email)
        return UnsubscriberResult(
            success=False,
            method=method,
            link=link,
            message="No executor available for this method",
        )
