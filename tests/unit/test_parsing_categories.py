from pathlib import Path

import pytest

from book_monitor.models import Category
from book_monitor.parsing import ParseError, parse_categories

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
BASE_URL = "https://books.toscrape.com/"


@pytest.fixture
def home_html():
    return (FIXTURES / "home.html").read_text(encoding="utf-8")


def test_home_fixture_yields_fifty_categories_without_books_aggregator(home_html):
    categories = parse_categories(home_html, BASE_URL)

    assert len(categories) == 50
    assert "Books" not in [c.name for c in categories]


def test_categories_have_stripped_names_and_absolute_urls(home_html):
    categories = parse_categories(home_html, BASE_URL)

    assert categories[0] == Category(
        name="Travel",
        url="https://books.toscrape.com/catalogue/category/books/travel_2/index.html",
    )
    assert categories[-1] == Category(
        name="Crime",
        url="https://books.toscrape.com/catalogue/category/books/crime_51/index.html",
    )
    assert all(c.url.startswith(BASE_URL) for c in categories)


def test_urls_are_resolved_against_the_given_base_url(home_html):
    categories = parse_categories(home_html, "http://mirror.test:8080/")

    assert categories[0].url == (
        "http://mirror.test:8080/catalogue/category/books/travel_2/index.html"
    )


@pytest.mark.parametrize(
    "html",
    [
        "<html><body><p>nothing here</p></body></html>",
        '<div class="side_categories"><ul class="nav nav-list"><li>'
        '<a href="x/index.html">Books</a></li></ul></div>',
    ],
)
def test_html_without_expected_structure_raises_parse_error(html):
    with pytest.raises(ParseError):
        parse_categories(html, BASE_URL)
