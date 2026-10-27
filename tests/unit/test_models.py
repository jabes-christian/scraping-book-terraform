import dataclasses
from decimal import Decimal

import pytest

from book_monitor.models import BookItem, Status


def _item() -> BookItem:
    return BookItem(
        category="Travel",
        title="It's Only the Himalayas",
        price=Decimal("45.17"),
        availability="In stock",
        url="https://books.toscrape.com/catalogue/its-only-the-himalayas_981/index.html",
    )


def test_book_item_is_immutable():
    item = _item()
    with pytest.raises(dataclasses.FrozenInstanceError):
        item.price = Decimal("1.00")


def test_book_item_keeps_price_as_decimal():
    item = _item()
    assert isinstance(item.price, Decimal)
    assert item.price == Decimal("45.17")


def test_book_item_has_exactly_the_scr03_fields():
    names = [f.name for f in dataclasses.fields(BookItem)]
    assert names == ["category", "title", "price", "availability", "url"]


def test_status_exposes_exactly_running_success_failed():
    assert {s.name: s.value for s in Status} == {
        "RUNNING": "RUNNING",
        "SUCCESS": "SUCCESS",
        "FAILED": "FAILED",
    }
