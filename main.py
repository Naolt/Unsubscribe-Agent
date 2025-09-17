from browser_use import Agent, Browser, ChatGoogle, Tools, ActionResult, BrowserSession
from dotenv import load_dotenv
import asyncio
import os

load_dotenv()

tools = Tools()

@tools.action(description='Login to email provider')
async def login_to_provider(browser_session: BrowserSession) -> ActionResult:
    """
    Login to the email provider. currently it gives time for the user to login manually.
    """
    
    await asyncio.sleep(30)

    return ActionResult(extracted_content="Waited the user to login for 30 seconds")
        

async def unsubscribe_by_request(user_request: str) -> str:
    """Run the agent to attempt an unsubscribe flow for the given request and return a status message."""
    try:
        llm = ChatGoogle(model="gemini-2.5-flash")
        browser = Browser(
            headless=False,
            keep_alive=True,
        )

        prompt = """
        You are a helpful assistant that helps users unsubscribe from marketing or notification emails across common email providers (e.g., Gmail, Outlook, Yahoo).

        Follow this generic, provider-agnostic flow:
        1) Sign-in: Ensure the user is logged in to their email account. use the "login_to_provider" tool to confirm sign-in. Otherwise, navigate the provider's standard sign-in flow.
        2) Find messages: Use the inbox search to locate emails from the target sender/service. Search by sender name, domain, or subject keywords. Prefer official/legitimate emails.
        3) Locate unsubscribe controls: Open a relevant message and look for any of the following:
           - Built-in provider unsubscribe (e.g., Gmail's native "Unsubscribe" banner/button)
           - "Unsubscribe" link in the email footer
           - "Manage email preferences"/"Notification settings" links
           - A link to the sender account settings page that controls email preferences
        4) Complete opt-out: Follow the link(s) and choose the option that stops all marketing or promotional emails. If prompted for a reason, select a reasonable option or skip if optional.
        5) Confirm result: Look for a confirmation message on the page and/or a confirmation email. If available,capture a brief confirmation note in your final result.
        6) Edge cases:
           - If no unsubscribe option exists and emails appear transactional/required, explain the limitation.
           - If the user is not subscribed, return exactly: "User is not subscribed".
           - If a page asks for re-authentication, prefer the provider's official sign-in.
           - Avoid suspicious links and do not enter credentials on untrusted domains.

        Here is the user's request:
        {user_request}
        """.format(user_request=user_request)

        agent = Agent(
            task=prompt,
            browser=browser,
            llm=llm,
            tools=tools,
        )

        history = await agent.run()

        # Minimal surface: final result when available, otherwise success/error summary
        try:
            final_text = history.final_result()
        except Exception:
            final_text = None

        try:
            success = history.is_successful()
        except Exception:
            success = None

        if success is True:
            if isinstance(final_text, str) and final_text.strip():
                return final_text
            return "Success"
        if success is False:
            try:
                errs = history.errors()
                first_err = next((e for e in errs if e), None)
                if first_err:
                    return f"Failed: {first_err}"
            except Exception:
                pass
            return "Failed"

        # Unknown/not completed: return whatever final text we have or a neutral message
        return final_text or "Result unavailable"
    except Exception as exc:
        return f"Failed: {exc}"


async def main():
    await unsubscribe_by_request("Unsubscribe from atlassian")


if __name__ == "__main__":
    asyncio.run(main())