import os
import pytest

from app.services.unsubscribers.browser_use_unsubscriber import BrowserUseUnsubscriber
from app.types.unsubscribe import UnsubscribeMethod, UnsubscriberResult


requires_integration_success = pytest.mark.skipif(
    os.getenv("RUN_INTEGRATION") != "1" or not os.getenv("TEST_UNSUB_URL_SUCCESS"),
    reason="Set RUN_INTEGRATION=1 and TEST_UNSUB_URL_SUCCESS to run this test.",
)

requires_integration_fail = pytest.mark.skipif(
    os.getenv("RUN_INTEGRATION") != "1" or not os.getenv("TEST_UNSUB_URL_FAIL"),
    reason="Set RUN_INTEGRATION=1 and TEST_UNSUB_URL_FAIL to run this test.",
)


@pytest.mark.integration
@requires_integration_success
@pytest.mark.asyncio
async def test_browser_use_unsubscriber_real_agent_success():
    # WARNING: Uses the real Agent and opens a browser window.
    url = os.environ["TEST_UNSUB_URL_SUCCESS"]
    user_email = os.getenv("TEST_USER_EMAIL")  # optional

    unsubscriber = BrowserUseUnsubscriber()

    result: UnsubscriberResult = await unsubscriber.execute(link=url, user_email=user_email)

    assert result.method == UnsubscribeMethod.HTTPS
    assert result.link == url
    assert result.success is True
    assert isinstance(result.message, (str, type(None)))


@pytest.mark.integration
@requires_integration_fail
@pytest.mark.asyncio
async def test_browser_use_unsubscriber_real_agent_failure():
    # WARNING: Uses the real Agent and opens a browser window.
    url = os.environ["TEST_UNSUB_URL_FAIL"]
    user_email = os.getenv("TEST_USER_EMAIL")  # optional

    unsubscriber = BrowserUseUnsubscriber()

    result: UnsubscriberResult = await unsubscriber.execute(link=url, user_email=user_email)

    assert result.method == UnsubscribeMethod.HTTPS
    assert result.link == url
    assert result.success is False
    assert isinstance(result.message, (str, type(None)))


