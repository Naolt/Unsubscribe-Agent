import pytest

from app.services.unsubscribers.browser_use_unsubscriber import BrowserUseUnsubscriber
from app.types.unsubscribe import UnsubscribeMethod, UnsubscriberResult


class _FakeHistory:
    def __init__(self, final_text: str | None, success: bool | None):
        self._final_text = final_text
        self._success = success

    def final_result(self):
        if isinstance(self._final_text, Exception):
            raise self._final_text
        return self._final_text

    def is_successful(self):
        if isinstance(self._success, Exception):
            raise self._success
        return self._success


class _FakeAgent:
    def __init__(self, task, browser, llm):  # noqa: D401 - mirrors real signature
        self.task = task
        self.browser = browser
        self.llm = llm
        self._history: _FakeHistory | None = None

    def set_history(self, history: _FakeHistory):
        self._history = history

    async def run(self):
        # no-op; history injected by test via monkeypatch
        return self._history


class _FakeBrowser:
    def __init__(self, headless: bool = True):
        self.headless = headless


@pytest.mark.asyncio
async def test_browser_use_unsubscriber_success(monkeypatch):
    # Arrange fakes
    fake_agent = _FakeAgent(task="", browser=_FakeBrowser(headless=True), llm=object())
    fake_agent.set_history(_FakeHistory(final_text="Unsubscribed OK", success=True))

    # Monkeypatch Agent ctor to return our fake with preset history
    import app.services.unsubscribers.browser_use_unsubscriber as mod

    def _agent_ctor(task, browser, llm):
        return fake_agent

    monkeypatch.setattr(mod, "Agent", _agent_ctor)
    monkeypatch.setattr(mod, "Browser", lambda headless=False: _FakeBrowser(headless=headless))
    monkeypatch.setattr(mod, "gemini_llm", object())  # stub LLM

    unsubscriber = BrowserUseUnsubscriber()

    # Act
    result: UnsubscriberResult = await unsubscriber.execute(
        link="https://example.com/unsub", user_email="user@example.com"
    )

    # Assert
    assert result.success is True
    assert result.method == UnsubscribeMethod.HTTPS
    assert result.link == "https://example.com/unsub"
    assert "Unsubscribed" in (result.message or "")


@pytest.mark.asyncio
async def test_browser_use_unsubscriber_failure(monkeypatch):
    fake_agent = _FakeAgent(task="", browser=_FakeBrowser(headless=True), llm=object())
    fake_agent.set_history(_FakeHistory(final_text="Failed due to form error", success=False))

    import app.services.unsubscribers.browser_use_unsubscriber as mod

    monkeypatch.setattr(mod, "Agent", lambda task, browser, llm: fake_agent)
    monkeypatch.setattr(mod, "Browser", lambda headless=False: _FakeBrowser(headless=headless))
    monkeypatch.setattr(mod, "gemini_llm", object())

    unsubscriber = BrowserUseUnsubscriber()
    result = await unsubscriber.execute(link="https://example.com/unsub")

    assert result.success is False
    assert result.method == UnsubscribeMethod.HTTPS
    assert result.link == "https://example.com/unsub"
    assert "Failed" in (result.message or "")


@pytest.mark.asyncio
async def test_browser_use_unsubscriber_exception(monkeypatch):
    # Make Agent.run raise by returning history whose methods raise
    class _ExplodingAgent(_FakeAgent):
        async def run(self):
            raise RuntimeError("browser crashed")

    exploding_agent = _ExplodingAgent(task="", browser=_FakeBrowser(), llm=object())

    import app.services.unsubscribers.browser_use_unsubscriber as mod

    monkeypatch.setattr(mod, "Agent", lambda task, browser, llm: exploding_agent)
    monkeypatch.setattr(mod, "Browser", lambda headless=False: _FakeBrowser(headless=headless))
    monkeypatch.setattr(mod, "gemini_llm", object())

    unsubscriber = BrowserUseUnsubscriber()
    result = await unsubscriber.execute(link="https://example.com/unsub")

    assert result.success is False
    assert result.method == UnsubscribeMethod.HTTPS
    assert result.link == "https://example.com/unsub"
    assert "Exception" in (result.message or "")


