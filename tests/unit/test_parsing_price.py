import re
from decimal import Decimal
from pathlib import Path

import pytest

from book_monitor.parsing import ParseError, parse_price

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def test_parses_pound_price_into_decimal():
    price = parse_price("£51.77")

    assert price == Decimal("51.77")
    assert isinstance(price, Decimal)


@pytest.mark.parametrize("text", ["", "abc", "£"])
def test_invalid_price_raises_parse_error(text):
    with pytest.raises(ParseError):
        parse_price(text)


def test_every_real_price_in_home_fixture_parses():
    html = (FIXTURES / "home.html").read_text(encoding="utf-8")
    texts = re.findall(r'<p class="price_color">([^<]*)</p>', html)

    assert len(texts) == 20
    for text in texts:
        assert parse_price(text) == Decimal(text.removeprefix("£"))
