from decimal import Decimal
from pathlib import Path

import pytest

from book_monitor.models import BookItem, Category
from book_monitor.parsing import ParseError, parse_listing

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
CATEGORY_BASE = "https://books.toscrape.com/catalogue/category/books"
DEFAULT = Category("Default", f"{CATEGORY_BASE}/default_15/index.html")
TRAVEL = Category("Travel", f"{CATEGORY_BASE}/travel_2/index.html")
EROTICA = Category("Erotica", f"{CATEGORY_BASE}/erotica_50/index.html")


def load(name):
    return (FIXTURES / name).read_text(encoding="utf-8")


def listing_html(books, results="<strong>{n}</strong> results.", next_href=None):
    pods = "".join(
        f'<article class="product_pod"><h3><a href="{href}" title="{title}">cut...</a></h3>'
        f'<div class="product_price"><p class="price_color">{price}</p>'
        f'<p class="instock availability"><i></i> In stock </p></div></article>'
        for href, title, price in books
    )
    nxt = f'<li class="next"><a href="{next_href}">next</a></li>' if next_href else ""
    total = results.format(n=len(books))
    return f"<html><body>{total}<ol>{pods}</ol><ul class='pager'>{nxt}</ul></body></html>"


def test_first_page_item_has_all_fields_with_full_title_and_absolute_url():
    listing = parse_listing(load("category_multi_first.html"), DEFAULT.url, DEFAULT)

    assert len(listing.items) == 20
    assert listing.items[0] == BookItem(
        category="Default",
        title=(
            "The Coming Woman: A Novel Based on the Life of the Infamous "
            "Feminist, Victoria Woodhull"
        ),
        price=Decimal("17.93"),
        availability="In stock",
        url=(
            "https://books.toscrape.com/catalogue/"
            "the-coming-woman-a-novel-based-on-the-life-of-the-infamous-"
            "feminist-victoria-woodhull_993/index.html"
        ),
    )


def test_no_title_is_the_truncated_listing_text():
    listing = parse_listing(load("category_multi_first.html"), DEFAULT.url, DEFAULT)

    assert not any(item.title.endswith("...") for item in listing.items)


def test_all_items_carry_category_decimal_price_and_absolute_url():
    listing = parse_listing(load("category_single.html"), TRAVEL.url, TRAVEL)

    assert len(listing.items) == 11
    assert {item.category for item in listing.items} == {"Travel"}
    assert all(isinstance(item.price, Decimal) for item in listing.items)
    prefix = "https://books.toscrape.com/catalogue/"
    assert all(item.url.startswith(prefix) for item in listing.items)
    assert all(".." not in item.url for item in listing.items)


@pytest.mark.parametrize(
    ("fixture", "category", "page_url", "total"),
    [
        ("category_multi_first.html", DEFAULT, DEFAULT.url, 152),
        ("category_multi_last.html", DEFAULT, f"{CATEGORY_BASE}/default_15/page-8.html", 152),
        ("category_single.html", TRAVEL, TRAVEL.url, 11),
        ("category_one_result.html", EROTICA, EROTICA.url, 1),
    ],
)
def test_total_results_comes_from_results_text(fixture, category, page_url, total):
    assert parse_listing(load(fixture), page_url, category).total_results == total


def test_next_url_is_absolute_when_next_link_exists():
    listing = parse_listing(load("category_multi_first.html"), DEFAULT.url, DEFAULT)

    assert listing.next_url == f"{CATEGORY_BASE}/default_15/page-2.html"


@pytest.mark.parametrize(
    ("fixture", "category", "page_url"),
    [
        ("category_multi_last.html", DEFAULT, f"{CATEGORY_BASE}/default_15/page-8.html"),
        ("category_single.html", TRAVEL, TRAVEL.url),
    ],
)
def test_next_url_is_none_on_last_page(fixture, category, page_url):
    assert parse_listing(load(fixture), page_url, category).next_url is None


def test_category_with_zero_results_returns_no_items_without_error():
    html = listing_html([], results="<strong>0</strong> results.")

    listing = parse_listing(html, TRAVEL.url, TRAVEL)

    assert (listing.items, listing.total_results, listing.next_url) == ([], 0, None)


def test_unreadable_price_raises_error_containing_book_url():
    html = listing_html([("../../../bad-book_1/index.html", "Bad Book", "N/A")])

    with pytest.raises(ParseError, match="https://books.toscrape.com/catalogue/bad-book_1/index.html"):
        parse_listing(html, TRAVEL.url, TRAVEL)


def test_title_with_quotes_and_accents_stays_intact():
    title = "L&#39;Étranger: «Ça va» &amp; “Noah’s” Ark"
    html = listing_html([("../../../a_1/index.html", title, "£10.00")])

    listing = parse_listing(html, TRAVEL.url, TRAVEL)

    assert listing.items[0].title == "L'Étranger: «Ça va» & “Noah’s” Ark"


def test_page_without_results_text_raises_parse_error():
    html = listing_html([("../../../a_1/index.html", "A", "£1.00")], results="")

    with pytest.raises(ParseError):
        parse_listing(html, TRAVEL.url, TRAVEL)
