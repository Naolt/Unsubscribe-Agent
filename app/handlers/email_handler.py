# app/handlers/email_handler.py

import logging
import quopri
from typing import Optional
from app.types.email import EmailPayload, EmailHeader
from bs4 import BeautifulSoup
from app.services.llm_instance import get_gemini_llm, get_llm
from langchain_core.prompts import ChatPromptTemplate

from app.types.unsubscribe import ExtractionResult, UnsubscribeLinks, UnsubscribeMethod

# Set up logger for this module
logger = logging.getLogger(__name__)


class EmailHandlerResult:
    def __init__(self, success: bool, method: UnsubscribeMethod | None = None, message: str = "", 
                 https_links: list[str] = None, mailto_links: list[str] = None, all_links: list[str] = None):
        self.success = success
        self.method = method
        self.message = message
        self.https_links = https_links or []
        self.mailto_links = mailto_links or []
        self.all_links = all_links or []

    def __repr__(self):
        return f"<EmailHandlerResult success={self.success} method={self.method} message={self.message} https={len(self.https_links)} mailto={len(self.mailto_links)} all={len(self.all_links)}>"

class EmailHandler:
    def __init__(self, payload: EmailPayload):
        self.payload = payload
        self._extracted_links = None  # Cache for extracted links
        logger.info(f"EmailHandler initialized for email from {payload.from_email} with subject: {payload.subject}")

    def handle(self, use_llm_only: bool = False) -> EmailHandlerResult:
        logger.info(f"Starting email handling with use_llm_only={use_llm_only}")
        
        # Check if this is a forwarded email
        is_forwarded = self._is_forwarded_email()
        logger.info(f"Email forwarding check result: {is_forwarded}")
        
        if not is_forwarded:
            logger.warning("Email is not forwarded - rejecting processing")
            return EmailHandlerResult(success=False, method=None, message="Email is not forwarded")
        
        if use_llm_only:
            logger.info("Using LLM-only extraction mode")
            # Skip body extraction and go directly to LLM
            llm_result = self._extract_with_llm()
            if llm_result and llm_result.has_any():
                # Get separated links from LLM
                https_links = llm_result.https
                mailto_links = llm_result.mailto
                all_links = llm_result.get_all_links()
                
                logger.info(f"LLM extraction successful: found {len(https_links)} HTTPS links, {len(mailto_links)} mailto links")
                
                # Return the first link found for backward compatibility
                first_link = all_links[0] if all_links else None
                method = UnsubscribeMethod.MAILTO if first_link and first_link.startswith("mailto:") else UnsubscribeMethod.HTTPS
                return EmailHandlerResult(
                    success=True,
                    method=method,
                    message=f"Found {len(all_links)} links via LLM {method}: {first_link} (and {len(all_links)-1} more)",
                    https_links=https_links,
                    mailto_links=mailto_links,
                    all_links=all_links)
            
            # No links found via LLM
            logger.warning("LLM extraction found no unsubscribe links")
            return EmailHandlerResult(success=False, method=None, message="No unsubscribe link found via LLM")
        
        # Step 1: Extract from email body (for forwarded emails)
        logger.info("Starting body extraction")
        body_result = self._extract_from_body()
        if body_result and body_result.has_any():
            # Get separated links from the extraction result
            https_links = body_result.https
            mailto_links = body_result.mailto
            all_links = body_result.get_all_links()
            
            logger.info(f"Body extraction successful: found {len(https_links)} HTTPS links, {len(mailto_links)} mailto links")
            
            # Return the first link found for backward compatibility
            first_link = all_links[0] if all_links else None
            method = UnsubscribeMethod.MAILTO if first_link and first_link.startswith("mailto:") else UnsubscribeMethod.HTTPS
            return EmailHandlerResult(
                success=True,
                method=method,
                message=f"Found {len(all_links)} links via {method}: {first_link} (and {len(all_links)-1} more)",
                https_links=https_links,
                mailto_links=mailto_links,
                all_links=all_links)

        # Step 2: try extracting with LLM as a last fallback
        logger.info("Body extraction failed, trying LLM as fallback")
        llm_result = self._extract_with_llm()
        if llm_result and llm_result.has_any():
            # Get separated links from LLM
            https_links = llm_result.https
            mailto_links = llm_result.mailto
            all_links = llm_result.get_all_links()
            
            logger.info(f"LLM fallback successful: found {len(https_links)} HTTPS links, {len(mailto_links)} mailto links")
            
            # Return the first link found for backward compatibility
            first_link = all_links[0] if all_links else None
            method = UnsubscribeMethod.MAILTO if first_link and first_link.startswith("mailto:") else UnsubscribeMethod.HTTPS
            return EmailHandlerResult(
                success=True,
                method=method,
                message=f"Found {len(all_links)} links via LLM {method}: {first_link} (and {len(all_links)-1} more)",
                https_links=https_links,
                mailto_links=mailto_links,
                all_links=all_links)

        # Step 3: no unsubscribe link found
        logger.warning("No unsubscribe links found in email")
        return EmailHandlerResult(success=False, method=None, message="No unsubscribe link found")

    def _is_forwarded_email(self) -> bool:
        """
        Check if the email is a forwarded email by looking for common forwarding patterns.
        """
        logger.debug("Checking if email is forwarded")
        
        # Check subject for forwarding indicators
        subject = self.payload.subject or ""
        subject_lower = subject.lower()
        
        forwarding_subject_patterns = [
            "fwd:", "fw:", "re:", "forwarded message", "forwarded:", 
            "begin forwarded message", "original message"
        ]
        
        if any(pattern in subject_lower for pattern in forwarding_subject_patterns):
            logger.debug(f"Email identified as forwarded based on subject pattern: {subject}")
            return True
        
        # Check email body for forwarding indicators
        body_text = ""
        if self.payload.body.text:
            body_text += self._decode_quoted_printable(self.payload.body.text).lower()
        if self.payload.body.html:
            # Extract text from HTML for pattern matching
            decoded_html = self._decode_quoted_printable(self.payload.body.html)
            soup = BeautifulSoup(decoded_html, "lxml")
            body_text += soup.get_text().lower()
        
        forwarding_body_patterns = [
            "begin forwarded message",
            "original message",
            "forwarded message",
            "from:",
            "sent:",
            "to:",
            "subject:",
            "date:",
            "-----original message-----",
            "-----forwarded message-----"
        ]
        
        is_forwarded = any(pattern in body_text for pattern in forwarding_body_patterns)
        logger.debug(f"Email forwarding check based on body patterns: {is_forwarded}")
        return is_forwarded

    def _decode_quoted_printable(self, content: str) -> str:
        """
        Decode quoted-printable encoded content from emails.
        Handles =3D sequences and line breaks with = characters.
        """
        if not content:
            return content
            
        try:
            # Decode quoted-printable encoding
            decoded = quopri.decodestring(content.encode('utf-8')).decode('utf-8')
            logger.debug(f"Decoded quoted-printable content: {len(content)} -> {len(decoded)} chars")
            return decoded
        except Exception as e:
            logger.warning(f"Failed to decode quoted-printable content: {e}")
            return content

    def _extract_all_links(self) -> list[dict]:
        """
        Extract all link elements from the email HTML once and cache them.
        Returns a list of dictionaries with href, text, and context.
        """
        if self._extracted_links is not None:
            return self._extracted_links
            
        logger.debug("Extracting all links from email HTML")
        
        html = self.payload.body.html
        if not html:
            logger.debug("No HTML content found in email body")
            self._extracted_links = []
            return self._extracted_links

        # Decode quoted-printable encoding if present
        decoded_html = self._decode_quoted_printable(html)
        soup = BeautifulSoup(decoded_html, "lxml")
        link_elements = soup.find_all("a", href=True)
        
        links_data = []
        for link in link_elements:
            href = link.get("href", "").strip()
            text = link.get_text(strip=True)
            # Include some context from parent elements if available
            parent_text = ""
            if link.parent:
                parent_text = link.parent.get_text(strip=True)[:100]  # Limit context
            
            links_data.append({
                "href": href,
                "text": text,
                "context": parent_text
            })

        logger.info(f"Extracted {len(links_data)} total links from email")
        self._extracted_links = links_data
        return self._extracted_links

    def _extract_from_body(self) -> ExtractionResult | None:
        """
        Extract all unsubscribe links from the email body using cached links.
        Returns an ExtractionResult with all found mailto and https values.
        """
        logger.debug("Starting body extraction using cached links")
        
        # Get cached links
        all_links = self._extract_all_links()
        if not all_links:
            logger.debug("No links found in email body")
            return None

        https_links = []
        mailto_links = []

        # Expanded unsubscribe keywords
        unsubscribe_keywords = [
            "unsubscribe", "opt-out", "opt out", "remove me", "stop receiving",
            "cancel subscription", "leave this list", "manage preferences",
            "email preferences", "account settings", "update subscription",
            "change preferences", "modify subscription", "end subscription"
        ]

        logger.debug(f"Processing {len(all_links)} cached links for body extraction")
        
        for link_data in all_links:
            href = link_data["href"]
            text = link_data["text"].lower()
            context = link_data["context"].lower()
            
            logger.debug(f"Checking link: {href} with text: '{text}'")

            # Check if link text, href, or context contains unsubscribe keywords
            is_unsubscribe_link = (
                any(keyword in text for keyword in unsubscribe_keywords) or
                any(keyword in href.lower() for keyword in unsubscribe_keywords) or
                any(keyword in context for keyword in unsubscribe_keywords)
            )

            if is_unsubscribe_link:
                logger.debug(f"Found unsubscribe link: {href}")
                if href.startswith("mailto:"):
                    mailto_links.append(href)
                elif href.startswith("http"):
                    https_links.append(href)

        logger.info(f"Body extraction completed: {len(https_links)} HTTPS links, {len(mailto_links)} mailto links")
        
        # Return all found links (no filtering/selection)
        result = ExtractionResult(https=https_links, mailto=mailto_links)
        return result if result.has_any() else None


    def _extract_with_llm(self) -> ExtractionResult | None:
        """
        Extract unsubscribe links from the email body using LLM.
        OPTIMIZED: Uses cached links instead of full HTML.
        Returns an ExtractionResult with optional mailto and https values.
        """
        logger.debug("Starting LLM extraction (optimized with cached links)")
        
        # Get cached links
        all_links = self._extract_all_links()
        if not all_links:
            logger.debug("No links found, skipping LLM call")
            return None

        logger.info(f"Calling LLM for unsubscribe link extraction with {len(all_links)} cached links")
        
        try:
            prompt = ChatPromptTemplate.from_messages([
                ("system", """You are an assistant that extracts unsubscribe links from a list of email links. 

PRIORITY ORDER:
1. If there's a link that unsubscribes from ALL emails/services (look for text like "unsubscribe from all", "all emails", "all communications", "email preferences", "account settings"), return ONLY that comprehensive link
2. If no comprehensive link exists, return ALL individual unsubscribe links found

Look for links with text, href, or context containing: unsubscribe, opt-out, remove me, stop receiving, manage preferences, email preferences, account settings, etc.

Return HTTPS and mailto links as separate lists."""),
                ("human", "Links to analyze:\n{links_data}"),
            ])

            structured_llm = get_llm().with_structured_output(UnsubscribeLinks)

            chain = prompt | structured_llm

            # Format cached links data for LLM
            formatted_links = "\n".join([
                f"Link {i+1}: href='{link['href']}' text='{link['text']}' context='{link['context']}'"
                for i, link in enumerate(all_links)
            ])

            structured: UnsubscribeLinks = chain.invoke({"links_data": formatted_links})
            
            logger.info(f"LLM extraction completed: {len(structured.https or [])} HTTPS links, {len(structured.mailto or [])} mailto links")

            # Map structured output to our internal ExtractionResult
            return ExtractionResult(https=structured.https, mailto=structured.mailto)
            
        except Exception as e:
            logger.error(f"LLM extraction failed: {str(e)}")
            return None