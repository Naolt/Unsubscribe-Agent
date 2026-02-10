from abc import ABC, abstractmethod
from typing import Optional

from app.types.unsubscribe import UnsubscriberResult, UnsubscribeMethod

__all__ = ["BaseUnsubscriber"]


class BaseUnsubscriber(ABC):
    @abstractmethod
    def can_handle(self, method: UnsubscribeMethod) -> bool:
        """Return True if this executor supports the given method."""

    @abstractmethod
    async def execute(self, link: str, user_email: Optional[str] = None) -> UnsubscriberResult:
        """Perform the unsubscribe and return a result."""
