import logging
from collections.abc import Callable, Mapping

from book_monitor import db
from book_monitor.browser import BrowserSession
from book_monitor.config import ConfigError, Settings
from book_monitor.logging_setup import configure, redact
from book_monitor.models import BookItem
from book_monitor.scraper import scrape_all

logger = logging.getLogger(__name__)

EXIT_SUCCESS = 0
EXIT_FAILURE = 1
EXIT_CONFIG = 2

Scraper = Callable[[Settings], list[BookItem]]


def scrape_with_browser(settings: Settings) -> list[BookItem]:
    session = BrowserSession(settings)
    try:
        return scrape_all(session, settings)
    finally:
        session.close()


def run(env: Mapping[str, str], scraper: Scraper = scrape_with_browser) -> int:
    """Run one monitoring execution; return 0 (success), 1 (failure) or 2 (configuration)."""
    try:
        settings = Settings.from_env(env)
    except ConfigError as exc:
        configure("INFO", [])
        logger.error("invalid configuration: %s", exc)
        return EXIT_CONFIG

    secrets = [settings.db_password]
    configure(settings.log_level, secrets)

    try:
        conn = db.connect_with_retry(settings, timeout=settings.db_connect_timeout_seconds)
    except db.DatabaseUnavailableError as exc:
        logger.error("%s", redact(str(exc), secrets))
        return EXIT_FAILURE

    exec_id: int | None = None
    try:
        db.ensure_schema(conn)
        abandoned = db.mark_abandoned(conn, settings.stale_after_hours)
        if abandoned:
            logger.warning("marked %d abandoned execution(s) as FAILED", abandoned)
        exec_id = db.start_execution(conn)
        logger.info("execution %d started", exec_id)
        items = scraper(settings)
        db.save_success(conn, exec_id, items)
        logger.info("execution %d succeeded with %d items", exec_id, len(items))
        return EXIT_SUCCESS
    except Exception as exc:
        # Redact before truncating so a secret cut at the limit is never left half-visible.
        error = redact(f"{type(exc).__name__}: {exc}", secrets)
        logger.error("execution failed: %s", error)
        if exec_id is not None:
            try:
                db.mark_failed(conn, exec_id, error)
            except Exception as mark_exc:
                logger.error(
                    "could not record the failure: %s", redact(str(mark_exc), secrets)
                )
        return EXIT_FAILURE
    finally:
        conn.close()
