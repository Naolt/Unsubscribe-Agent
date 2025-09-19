# app/handlers/email_handler.py

from typing import Optional
from app.types.email import EmailPayload, EmailHeader
from bs4 import BeautifulSoup
from app.services.llm_instance import gemini_llm
from langchain_core.prompts import ChatPromptTemplate

from app.types.unsubscribe import ExtractionResult, UnsubscribeLinks, UnsubscribeMethod


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
        header_result = self._extract_from_header()
        if header_result and header_result.has_any():
            link = header_result.mailto or header_result.https
            method = UnsubscribeMethod.MAILTO if header_result.mailto else UnsubscribeMethod.HTTPS
            return EmailHandlerResult(success=True, method=method, message=f"Found via {method}: {link}")
               

        # Step 2: fallback to footer parsing
        footer_result = self._extract_from_footer()
        if footer_result and footer_result.has_any():
            link = footer_result.mailto or footer_result.https
            method = UnsubscribeMethod.MAILTO if footer_result.mailto else UnsubscribeMethod.HTTPS
            return EmailHandlerResult(
                success=True,
                method=method,
                message=f"Found via {method}: {link}")

        # Step 3: try extracting with LLM as a last fallback
        llm_result = self._extract_with_llm()
        if llm_result and llm_result.has_any():
            link = llm_result.mailto or llm_result.https
            method = UnsubscribeMethod.MAILTO if llm_result.mailto else UnsubscribeMethod.HTTPS
            return EmailHandlerResult(
                success=True,
                method=method,
                message=f"Found via {method}: {link}")

        # Step 4: no unsubscribe link found
        return EmailHandlerResult(success=False, method=None, message="No unsubscribe link found")


    def _extract_from_header(self) -> ExtractionResult | None:
        """
        Extract unsubscribe links from List-Unsubscribe header.
        Returns an ExtractionResult with optional https and mailto values.
        """
        for header in self.payload.headers:
            if header.name.lower() == "list-unsubscribe":
                links = [l.strip("<> ").strip() for l in header.value.split(",")]
                https_link: Optional[str] = None
                mailto_link: Optional[str] = None
                for link in links:
                    if link.startswith("mailto:"):
                        mailto_link = link
                    elif link.startswith("http"):
                        https_link = link
                result = ExtractionResult(https=https_link, mailto=mailto_link)
                return result if result.has_any() else None
        return None


    def _extract_from_footer(self) -> ExtractionResult | None:
        """
        Extract unsubscribe links from the email footer.
        Returns an ExtractionResult with optional mailto and https values.
        """
        html = self.payload.body.html
        if not html:
            return None

        soup = BeautifulSoup(html, "lxml")
        https_link: Optional[str] = None
        mailto_link: Optional[str] = None

        # find all <a> tags with href
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            text = a.get_text(strip=True).lower()

            if "unsubscribe" in text or "unsubscribe" in href.lower():
                if href.startswith("mailto:"):
                    mailto_link = href
                elif href.startswith("http"):
                    https_link = href

        result = ExtractionResult(https=https_link, mailto=mailto_link)
        return result if result.has_any() else None

    def _extract_with_llm(self) -> ExtractionResult | None:
        """
        Extract unsubscribe links from the email footer using llm.
        Returns an ExtractionResult with optional mailto and https values.
        """
        html = self.payload.body.html

        if not html or len(html) < 5:
            return None


        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are an assistant that extracts unsubscribe links from an email body. Extract both HTTPS and mailto links separately. if there are mutiple choose the relevant one."),
            ("human", "{email_body}"),
        ])

        structured_llm = gemini_llm.with_structured_output(UnsubscribeLinks)

        chain = prompt | structured_llm

        structured: UnsubscribeLinks = chain.invoke({"email_body": html})

        # Map structured output to our internal ExtractionResult
        return ExtractionResult(https=structured.https, mailto=structured.mailto)