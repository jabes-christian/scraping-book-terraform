from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum


class Status(StrEnum):
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


@dataclass(frozen=True)
class Category:
    name: str
    url: str


@dataclass(frozen=True)
class BookItem:
    category: str
    title: str
    price: Decimal
    availability: str
    url: str


@dataclass(frozen=True)
class Listing:
    items: list[BookItem]
    total_results: int
    next_url: str | None
