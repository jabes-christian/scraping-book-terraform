import time
from collections.abc import Callable

from book_monitor.browser import BrowserSession
from book_monitor.config import Settings
from book_monitor.models import BookItem
from book_monitor.parsing import parse_categories, parse_listing
from book_monitor.retry import retry


class ScrapeError(Exception):
    pass


def scrape_all(
    session: BrowserSession,
    settings: Settings,
    sleep: Callable[[float], None] = time.sleep,
) -> list[BookItem]:
    fetched = 0

    def fetch(url: str) -> str:
        nonlocal fetched
        if fetched:
            sleep(settings.scrape_delay_seconds)
        fetched += 1
        return retry(lambda: session.get_html(url), settings.scrape_max_retries, sleep=sleep)

    categories = parse_categories(fetch(settings.base_url), settings.base_url)
    items: list[BookItem] = []
    seen_urls: set[str] = set()
    for category in categories:
        collected = 0
        url = category.url
        while True:
            listing = parse_listing(fetch(url), url, category)
            for item in listing.items:
                if item.url in seen_urls:
                    raise ScrapeError(f"duplicate url: {item.url}")
                seen_urls.add(item.url)
            items.extend(listing.items)
            collected += len(listing.items)
            if listing.next_url is None:
                break
            url = listing.next_url
        if collected != listing.total_results:
            raise ScrapeError(
                f"count mismatch: {category.name} "
                f"(collected {collected}, site shows {listing.total_results})"
            )
    return items
