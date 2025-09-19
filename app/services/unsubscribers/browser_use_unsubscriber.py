from app.config import settings
from app.services.unsubscribers.base import BaseUnsubscriber
from app.types.unsubscribe import UnsubscribeMethod, UnsubscriberResult
from browser_use import Agent, Browser, ChatGoogle, Tools, ActionResult, BrowserSession

class BrowserUseUnsubscriber(BaseUnsubscriber):
    def can_handle(self, method: UnsubscribeMethod) -> bool:
        return method == UnsubscribeMethod.HTTPS

    async def execute(self, link: str, user_email: str | None = None) -> UnsubscriberResult:
        """
        Perform unsubscribe using BrowserUse agent.

        Args:
            link: The HTTPS unsubscribe link.
            user_email: Optional email address (if needed for login or context).

        Returns:
            UnsubscriberResult: Success/failure info, method, link, and message.
        """
        try:
            # 1. Initialize LLM compatible with browser_use Agent
            llm = ChatGoogle(model="gemini-2.5-flash")

            # 2. Launch browser
            browser = Browser(headless=False)

            # 3. Define the prompt for the agent
            prompt = f"""
                        You are an automated assistant tasked with unsubscribing from marketing or notification emails. 
            You are given a single HTTPS link that may lead to an unsubscribe page. 
            You also have the email of the user who wants to unsubscribe. Your goal is to unsubscribe the user fully and safely. 

            User email: {user_email}
            Unsubscribe link: {link}

            Instructions:

            1. Visit the provided unsubscribe link if not opened.
            2. If the page asks for an email, use the provided user's email.
            3. If prompted for a reason, select a reasonable option or skip if optional.
            4. Aim to stop all subscriptions, not just one.
            5. Capture any confirmation messages or notifications that indicate successful unsubscription.
            6. Edge cases:
            - If no unsubscribe option exists, explain the limitation.
            - If the page requests authentication, the agent cannot sign in. Stop the flow and 
            return a message indicating that authentication is required.
            - Avoid suspicious links and never enter credentials on untrusted sites.
            """

            # 4. Create and run the agent
            agent = Agent(task=prompt, browser=browser, llm=llm)
            history = await agent.run()

            # 5. Extract result
            try:
                final_text = history.final_result()
            except Exception:
                final_text = None

            try:
                success = history.is_successful()
            except Exception:
                success = None

            # 6. Map to UnsubscriberResult
            if success is True:
                return UnsubscriberResult(
                    success=True,
                    method=UnsubscribeMethod.HTTPS,
                    link=link,
                    message=final_text or "Unsubscribe successful",
                )
            elif success is False:
                return UnsubscriberResult(
                    success=False,
                    method=UnsubscribeMethod.HTTPS,
                    link=link,
                    message=f"Unsubscribe failed: {final_text or 'Unknown error'}",
                )

            return UnsubscriberResult(
                success=False,
                method=UnsubscribeMethod.HTTPS,
                link=link,
                message=final_text or "Unsubscribe result unavailable",
            )

        except Exception as exc:
            return UnsubscriberResult(
                success=False,
                method=UnsubscribeMethod.HTTPS,
                link=link,
                message=f"Exception during unsubscribe: {exc}",
            )
