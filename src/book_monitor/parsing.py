import re
from decimal import Decimal

PRICE_PATTERN = re.compile(r"£(\d+(?:\.\d+)?)")


class ParseError(ValueError):
    pass


def parse_price(text: str) -> Decimal:
    match = PRICE_PATTERN.fullmatch(text.strip())
    if match is None:
        raise ParseError(f"invalid price: {text!r}")
    return Decimal(match.group(1))
