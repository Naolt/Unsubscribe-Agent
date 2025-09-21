from datetime import datetime
from enum import Enum
from typing import Dict, Optional

from pydantic import BaseModel, Field


class ExtractionResult:
    def __init__(self, https: Optional[list[str]] = None, mailto: Optional[list[str]] = None):
        self.https = https or []
        self.mailto = mailto or []

    def has_any(self) -> bool:
        return bool(self.https or self.mailto)

    def get_all_links(self) -> list[str]:
        """Get all links as a single list"""
        all_links = []
        all_links.extend(self.https)
        all_links.extend(self.mailto)
        return all_links

    def to_dict(self) -> Dict["UnsubscribeMethod", list[str]]:
        mapping: Dict["UnsubscribeMethod", list[str]] = {}
        if self.mailto:
            mapping[UnsubscribeMethod.MAILTO] = self.mailto
        if self.https:
            mapping[UnsubscribeMethod.HTTPS] = self.https
        return mapping

class UnsubscribeMethod(str, Enum):
    MAILTO = "mailto"
    HTTPS = "https"

    def __repr__(self):
        return self.value

class UnsubscribeLinks(BaseModel):
    """Information about unsubscribe links found in an email body."""
    https: Optional[list[str]] = Field(
        None, description="List of HTTPS or HTTP URLs for unsubscribing, if found."
    )
    mailto: Optional[list[str]] = Field(
        None, description="List of 'mailto:' email addresses for unsubscribing, if found."
    )


class UnsubscriberResult:
    def __init__(
        self,
        success: bool,
        method: UnsubscribeMethod | None = None,
        link: str | None = None,
        message: str = "",
        timestamp: datetime | None = None,
    ):
        self.success = success
        self.method = method
        self.link = link
        self.message = message
        self.timestamp = timestamp or datetime.utcnow()

    def __repr__(self):
        return (
            f"<UnsubscriberResult success={self.success} "
            f"method={self.method} link={self.link} "
            f"message={self.message}>"
        )

