# app/handlers/email_handler.py

# from enum import Enum
from enum import Enum
from typing import Dict, Optional
from app.types.email import EmailPayload, EmailHeader
from bs4 import BeautifulSoup
from services.llm_instance import llm

class UnsubscribeMethod(str, Enum):
    MAILTO = "mailto"
    HTTPS = "https"

    def __repr__(self):
        return self.value


class EmailHandlerResult:
    def __init__(self, success: bool, method: UnsubscribeMethod | None  = None, message: str = ""):
        self.success = success
        self.method = method
        self.message = message

    def __repr__(self):
        return f"<EmailHandlerResult success={self.success} method={self.method} message={self.message}>"

class EmailHandler:
    def __init__(self, payload: EmailPayload):
        self.payload = payload

    def handle(self)->EmailHandlerResult:
        # Step 1: check List-Unsubscribe header
        header_link = self._extract_from_header()
        if header_link:
            method = "mailto" if header_link.startswith("mailto:") else "https"
            return EmailHandlerResult(success=True, method=method, message=f"Unsubscribe link found: {header_link}")
               

        # Step 2: fallback to footer parsing
        footer_link = self._extract_from_footer()
        if footer_link:
            return EmailHandlerResult(
                success=True,
                method="https",
                message=f"FOUND_UNSUBSCRIBE_FOOTER_LINK: {footer_link}")

        # Step 3: no unsubscribe link found
        return EmailHandlerResult(success=False, method="none", message="No unsubscribe link found")


    def _extract_from_header(self) -> Dict[UnsubscribeMethod, str] | None:
        """
        Extract unsubscribe links from List-Unsubscribe header.
        Returns a dictionary with optional 'https' and 'mailto' keys.
        """
        for header in self.payload.headers:
            if header.name.lower() == "list-unsubscribe":
                links = [l.strip("<> ").strip() for l in header.value.split(",")]
                result = {}
                for link in links:
                    if link.startswith("mailto:"):
                        result[UnsubscribeMethod.MAILTO.value] = link
                    elif link.startswith("http"):
                        result[UnsubscribeMethod.HTTPS.value] = link
                return result or None
        return None


    def _extract_from_footer(self) -> Dict[UnsubscribeMethod, str] | None:
        """
        Extract unsubscribe links from the email footer.
        Returns a dictionary with optional 'mailto' and 'https' keys.
        """
        html = self.payload.body.html
        if not html:
            return None

        soup = BeautifulSoup(html, "lxml")
        result: Dict[UnsubscribeMethod, str] = {}

        # find all <a> tags with href
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            text = a.get_text(strip=True).lower()

            if "unsubscribe" in text or "unsubscribe" in href.lower():
                if href.startswith("mailto:"):
                    result[UnsubscribeMethod.MAILTO.value] = href
                elif href.startswith("http"):
                    result[UnsubscribeMethod.HTTPS.value] = href

        return result or None

    def _extract_with_llm(self) -> Dict[UnsubscribeMethod, str] | None:
        