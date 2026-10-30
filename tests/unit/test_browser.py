import logging
from pathlib import Path

import pytest
from selenium.common.exceptions import TimeoutException, WebDriverException

from book_monitor.browser import BrowserSession, PageLoadError
from book_monitor.config import Settings
from book_monitor.retry import RetryableError

HOME_HTML = (Path(__file__).resolve().parents[1] / "fixtures" / "home.html").read_text(
    encoding="utf-8"
)
ENV = {
    "DB_HOST": "h",
    "DB_NAME": "n",
    "DB_USER": "u",
    "DB_PASSWORD": "p",
    "CHROME_BIN": "/opt/chromium",
    "CHROMEDRIVER_PATH": "/opt/chromedriver",
}


class FakeDriver:
    def __init__(self, page_source=HOME_HTML, get_error=None, quit_error=None):
        self.page_source = page_source
        self.get_error = get_error
        self.quit_error = quit_error
        self.fetched = []
        self.page_load_timeout = None
        self.quit_calls = 0

    def set_page_load_timeout(self, seconds):
        self.page_load_timeout = seconds

    def get(self, url):
        if self.get_error is not None:
            raise self.get_error
        self.fetched.append(url)

    def quit(self):
        self.quit_calls += 1
        if self.quit_error is not None:
            raise self.quit_error


class Factory:
    def __init__(self, *drivers):
        self.drivers = list(drivers)
        self.created = []
        self.calls = []

    def __call__(self, *, service, options):
        self.calls.append((service, options))
        driver = self.drivers.pop(0) if self.drivers else FakeDriver()
        self.created.append(driver)
        return driver


def make_session(factory, **env):
    return BrowserSession(Settings.from_env({**ENV, **env}), driver_factory=factory)


def test_chrome_options_use_low_resource_headless_flags_and_configured_paths():
    factory = Factory()

    make_session(factory).get_html("https://books.toscrape.com/")

    service, options = factory.calls[0]
    assert {
        "--headless=new",
        "--no-sandbox",
        "--disable-dev-shm-usage",
        "--disable-gpu",
        "--blink-settings=imagesEnabled=false",
    } <= set(options.arguments)
    assert options.binary_location == "/opt/chromium"
    assert options.page_load_strategy == "eager"
    assert service.path == "/opt/chromedriver"


def test_page_timeout_comes_from_settings():
    factory = Factory()

    make_session(factory, PAGE_TIMEOUT_SECONDS="17").get_html("https://books.toscrape.com/")

    assert factory.created[0].page_load_timeout == 17


def test_get_html_returns_page_source_of_requested_url():
    factory = Factory()

    html = make_session(factory).get_html("https://books.toscrape.com/")

    assert html == HOME_HTML
    assert factory.created[0].fetched == ["https://books.toscrape.com/"]


def test_driver_is_reused_until_recycle_limit_then_recreated():
    factory = Factory()
    session = make_session(factory, CHROME_RECYCLE_PAGES="3")

    for _ in range(3):
        session.get_html("https://books.toscrape.com/")
    assert len(factory.created) == 1
    assert factory.created[0].quit_calls == 1

    session.get_html("https://books.toscrape.com/")
    assert len(factory.created) == 2
    assert factory.created[1].fetched == ["https://books.toscrape.com/"]


@pytest.mark.parametrize("error", [WebDriverException("boom"), TimeoutException("slow")])
def test_webdriver_exception_recreates_driver_and_raises_retryable_page_load_error(error):
    broken = FakeDriver(get_error=error, quit_error=WebDriverException("already dead"))
    factory = Factory(broken)
    session = make_session(factory)

    with pytest.raises(PageLoadError) as info:
        session.get_html("https://books.toscrape.com/")
    assert isinstance(info.value, RetryableError)
    assert broken.quit_calls == 1

    assert session.get_html("https://books.toscrape.com/") == HOME_HTML
    assert len(factory.created) == 2


def test_failed_quit_logs_warning_with_the_exception_and_does_not_raise(caplog):
    broken = FakeDriver(quit_error=WebDriverException("already dead"))
    session = make_session(Factory(broken))
    session.get_html("https://books.toscrape.com/")

    with caplog.at_level(logging.WARNING, logger="book_monitor.browser"):
        session.close()

    warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warnings) == 1
    assert "failed to quit browser driver" in warnings[0].getMessage()
    assert "already dead" in warnings[0].getMessage()


def test_page_without_structural_marker_raises_retryable_page_load_error():
    factory = Factory(FakeDriver(page_source="<html><body>Service Unavailable</body></html>"))

    with pytest.raises(PageLoadError, match="https://books.toscrape.com/x") as info:
        make_session(factory).get_html("https://books.toscrape.com/x")

    assert isinstance(info.value, RetryableError)
