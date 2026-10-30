import re
from decimal import Decimal
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from book_monitor.models import Category

PRICE_PATTERN = re.compile(r"£(\d+(?:\.\d+)?)")


class ParseError(ValueError):
    pass


def parse_price(text: str) -> Decimal:
    match = PRICE_PATTERN.fullmatch(text.strip())
    if match is None:
        raise ParseError(f"invalid price: {text!r}")
    return Decimal(match.group(1))


def parse_categories(html: str, base_url: str) -> list[Category]:
    soup = BeautifulSoup(html, "html.parser")
    links = soup.select("div.side_categories ul ul li a")
    if not links:
        raise ParseError("category list not found in page")
    return [
        Category(name=link.get_text(strip=True), url=urljoin(base_url, link["href"]))
        for link in links
    ]
