from datetime import datetime
from enum import Enum
from typing import Dict, Optional

from pydantic import BaseModel, Field


class ExtractionResult:
    def __init__(self, https: Optional[str] = None, mailto: Optional[str] = None):
        self.https = https
        self.mailto = mailto

    def has_any(self) -> bool:
        return bool(self.https or self.mailto)

    def to_dict(self) -> Dict["UnsubscribeMethod", str]:
        mapping: Dict["UnsubscribeMethod", str] = {}
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
    https: Optional[str] = Field(
        None, description="The HTTPS or HTTP URL for unsubscribing, if found."
    )
    mailto: Optional[str] = Field(
        None, description="The 'mailto:' email address for unsubscribing, if found."
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

