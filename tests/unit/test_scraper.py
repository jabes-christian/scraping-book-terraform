from pathlib import Path

import pytest

from book_monitor.browser import PageLoadError
from book_monitor.config import Settings
from book_monitor.scraper import ScrapeError, scrape_all

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
BASE = "https://books.toscrape.com/"
CAT = f"{BASE}catalogue/category/books"
HOME = BASE
ENV = {"DB_HOST": "h", "DB_NAME": "n", "DB_USER": "u", "DB_PASSWORD": "p"}


def settings(**env):
    return Settings.from_env({**ENV, **env})


def fixture(name):
    return (FIXTURES / name).read_text(encoding="utf-8")


def home_html(*categories):
    links = "".join(f'<li><a href="{url}">{name}</a></li>' for name, url in categories)
    return (
        '<div class="side_categories"><ul class="nav nav-list"><li>'
        f'<a href="catalogue/category/books_1/index.html">Books</a><ul>{links}</ul>'
        "</li></ul></div>"
    )


def listing_html(books, total, next_href=None):
    pods = "".join(
        f'<article class="product_pod"><h3><a href="{href}" title="{title}">cut...</a></h3>'
        f'<p class="price_color">£10.00</p><p class="instock availability">In stock</p>'
        "</article>"
        for href, title in books
    )
    nxt = f'<li class="next"><a href="{next_href}">next</a></li>' if next_href else ""
    return (
        f"<html><body><strong>{total}</strong> results.<ol>{pods}</ol>"
        f"<ul>{nxt}</ul></body></html>"
    )


def book(n, title):
    return (f"../../../book_{n}/index.html", title)


class FakeSession:
    """Serves pages by URL; a list value is a sequence of outcomes (exception or html)."""

    def __init__(self, pages):
        self.pages = pages
        self.requests = []

    def get_html(self, url):
        self.requests.append(url)
        outcome = self.pages[url]
        if isinstance(outcome, list):
            outcome = outcome.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def run(pages, sleeps=None, **env):
    session = FakeSession(pages)
    sleeps = [] if sleeps is None else sleeps
    items = scrape_all(session, settings(**env), sleep=sleeps.append)
    return items, session, sleeps


TRAVEL_URL = f"{CAT}/travel_2/index.html"
EROTICA_URL = f"{CAT}/erotica_50/index.html"


def test_walks_categories_from_home_and_collects_every_fixture_item():
    pages = {
        HOME: home_html(("Travel", TRAVEL_URL), ("Erotica", EROTICA_URL)),
        TRAVEL_URL: fixture("category_single.html"),
        EROTICA_URL: fixture("category_one_result.html"),
    }

    items, session, _ = run(pages)

    assert session.requests == [HOME, TRAVEL_URL, EROTICA_URL]
    assert [item.category for item in items] == ["Travel"] * 11 + ["Erotica"]


def test_follows_next_links_until_none_and_sums_all_pages():
    p1, p2, p3 = (f"{CAT}/x_1/{name}" for name in ("index.html", "page-2.html", "page-3.html"))
    pages = {
        HOME: home_html(("X", p1)),
        p1: listing_html([book(1, "A"), book(2, "B")], 5, "page-2.html"),
        p2: listing_html([book(3, "C"), book(4, "D")], 5, "page-3.html"),
        p3: listing_html([book(5, "E")], 5),
    }

    items, session, _ = run(pages)

    assert session.requests == [HOME, p1, p2, p3]
    assert [item.title for item in items] == ["A", "B", "C", "D", "E"]


def test_count_mismatch_fails_with_category_name():
    url = f"{CAT}/x_1/index.html"
    pages = {
        HOME: home_html(("Mystery", url)),
        url: listing_html([("../../../a_1/index.html", "A")], 2),
    }

    with pytest.raises(ScrapeError, match="count mismatch: Mystery"):
        run(pages)


def test_duplicate_book_url_fails_with_the_url():
    url1, url2 = f"{CAT}/x_1/index.html", f"{CAT}/y_2/index.html"
    same_book = [("../../../a_1/index.html", "A")]
    pages = {
        HOME: home_html(("X", url1), ("Y", url2)),
        url1: listing_html(same_book, 1),
        url2: listing_html(same_book, 1),
    }

    with pytest.raises(ScrapeError, match="duplicate url: https://books.toscrape.com/catalogue/a_1/index.html"):
        run(pages)


def test_empty_category_is_recorded_without_failing_the_run():
    empty = f"{CAT}/empty_1/index.html"
    pages = {
        HOME: home_html(("Empty", empty), ("Travel", TRAVEL_URL)),
        empty: listing_html([], 0),
        TRAVEL_URL: fixture("category_single.html"),
    }

    items, session, _ = run(pages)

    assert session.requests == [HOME, empty, TRAVEL_URL]
    assert len(items) == 11


def test_persistent_page_failure_makes_four_attempts_with_2_4_8_waits_then_propagates():
    pages = {HOME: [PageLoadError("down")] * 4}

    sleeps = []
    with pytest.raises(PageLoadError, match="down"):
        run(pages, sleeps)

    assert sleeps == [2, 4, 8]


def test_transient_page_failure_is_retried_and_collection_continues():
    pages = {
        HOME: home_html(("Travel", TRAVEL_URL)),
        TRAVEL_URL: [PageLoadError("slow"), fixture("category_single.html")],
    }

    items, session, sleeps = run(pages, SCRAPE_DELAY_SECONDS="0.5")

    assert len(items) == 11
    assert session.requests == [HOME, TRAVEL_URL, TRAVEL_URL]
    assert sleeps == [0.5, 2]


def test_waits_scrape_delay_between_consecutive_pages_only():
    pages = {
        HOME: home_html(("Travel", TRAVEL_URL), ("Erotica", EROTICA_URL)),
        TRAVEL_URL: fixture("category_single.html"),
        EROTICA_URL: fixture("category_one_result.html"),
    }

    _, session, sleeps = run(pages, SCRAPE_DELAY_SECONDS="1.5")

    assert len(session.requests) == 3
    assert sleeps == [1.5, 1.5]
