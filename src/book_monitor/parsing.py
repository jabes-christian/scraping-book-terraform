import re
from decimal import Decimal
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from book_monitor.models import BookItem, Category, Listing

PRICE_PATTERN = re.compile(r"£(\d+(?:\.\d+)?)")
RESULTS_PATTERN = re.compile(r"\s*results?\b")


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


def _total_results(soup: BeautifulSoup) -> int:
    for strong in soup.find_all("strong"):
        count = strong.get_text(strip=True)
        following = strong.next_sibling
        if count.isdigit() and isinstance(following, str) and RESULTS_PATTERN.match(following):
            return int(count)
    raise ParseError("results count not found in page")


def _parse_item(pod, page_url: str, category: Category) -> BookItem:
    link = pod.select_one("h3 a")
    price = pod.select_one("p.price_color")
    availability = pod.select_one("p.availability")
    if link is None or price is None or availability is None:
        raise ParseError(f"incomplete book entry on {page_url}")
    url = urljoin(page_url, link["href"])
    try:
        parsed_price = parse_price(price.get_text())
    except ParseError as exc:
        raise ParseError(f"{url}: {exc}") from exc
    return BookItem(
        category=category.name,
        title=link["title"],
        price=parsed_price,
        availability=availability.get_text(strip=True),
        url=url,
    )


def parse_listing(html: str, page_url: str, category: Category) -> Listing:
    soup = BeautifulSoup(html, "html.parser")
    next_link = soup.select_one("li.next a")
    return Listing(
        items=[_parse_item(pod, page_url, category) for pod in soup.select("article.product_pod")],
        total_results=_total_results(soup),
        next_url=urljoin(page_url, next_link["href"]) if next_link else None,
    )
