import logging
from collections.abc import Callable

from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

from book_monitor.config import Settings
from book_monitor.retry import RetryableError

logger = logging.getLogger(__name__)

STRUCTURAL_MARKER ="side_categories"

CHROME_ARGUMENTS = (
    "--headless=new",
    "--no-sandbox",
    "--disable-dev-shm-usage",
    "--disable-gpu",
    "--disable-extensions",
    "--blink-settings=imagesEnabled=false",
    "--window-size=800,600",
    "--renderer-process-limit=1",
)


class PageLoadError(RetryableError):
    pass


class BrowserSession:
    def __init__(
        self,
        settings: Settings,
        driver_factory: Callable[..., webdriver.Chrome] = webdriver.Chrome,
    ):
        self._settings = settings
        self._driver_factory = driver_factory
        self._driver = None
        self._pages_served = 0

    def get_html(self, url: str) -> str:
        if self._driver is None:
            self._driver = self._create_driver()
        try:
            self._driver.get(url)
            html = self._driver.page_source
        except WebDriverException as exc:
            self.close()
            raise PageLoadError(f"failed to load {url}: {exc.msg or type(exc).__name__}") from exc
        self._pages_served += 1
        if self._pages_served >= self._settings.chrome_recycle_pages:
            self.close()
        if STRUCTURAL_MARKER not in html:
            raise PageLoadError(f"unexpected page structure at {url}")
        return html

    def close(self) -> None:
        driver, self._driver = self._driver, None
        self._pages_served = 0
        if driver is None:
            return
        try:
            driver.quit()
        except WebDriverException as exc:
            logger.warning("failed to quit browser driver: %s", exc.msg or type(exc).__name__)

    def _create_driver(self):
        options = Options()
        for argument in CHROME_ARGUMENTS:
            options.add_argument(argument)
        options.binary_location = self._settings.chrome_bin
        options.page_load_strategy = "eager"
        service = Service(executable_path=self._settings.chromedriver_path)
        driver = self._driver_factory(service=service, options=options)
        driver.set_page_load_timeout(self._settings.page_timeout_seconds)
        return driver
