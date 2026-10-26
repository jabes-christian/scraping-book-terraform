from collections.abc import Callable, Mapping
from dataclasses import dataclass, field


class ConfigError(Exception):
    def __init__(self, var: str, message: str):
        super().__init__(f"{var}: {message}")
        self.var = var


def _get(env: Mapping[str, str], name: str) -> str | None:
    value = env.get(name)
    if value is None or not value.strip():
        return None
    return value


def _required(env: Mapping[str, str], name: str) -> str:
    value = _get(env, name)
    if value is None:
        raise ConfigError(name, "required environment variable is missing or empty")
    return value


def _optional[T](
    env: Mapping[str, str],
    name: str,
    default: T,
    cast: Callable[[str], T],
    in_range: Callable[[T], bool] | None = None,
    expected: str = "",
) -> T:
    value = _get(env, name)
    if value is None:
        return default
    try:
        parsed = cast(value)
    except ValueError:
        raise ConfigError(name, f"invalid value, expected {cast.__name__}") from None
    if in_range is not None and not in_range(parsed):
        raise ConfigError(name, f"value out of range, expected {expected}")
    return parsed


@dataclass(frozen=True)
class Settings:
    db_host: str
    db_name: str
    db_user: str
    db_password: str = field(repr=False)
    db_port: int
    scrape_delay_seconds: float
    scrape_max_retries: int
    log_level: str
    base_url: str
    page_timeout_seconds: int
    chrome_recycle_pages: int
    stale_after_hours: int
    db_connect_timeout_seconds: int
    chrome_bin: str
    chromedriver_path: str

    @classmethod
    def from_env(cls, env: Mapping[str, str]) -> "Settings":
        return cls(
            db_host=_required(env, "DB_HOST"),
            db_name=_required(env, "DB_NAME"),
            db_user=_required(env, "DB_USER"),
            db_password=_required(env, "DB_PASSWORD"),
            db_port=_optional(env, "DB_PORT", 5432, int, lambda v: 1 <= v <= 65535, "1-65535"),
            scrape_delay_seconds=_optional(
                env, "SCRAPE_DELAY_SECONDS", 0.5, float, lambda v: v >= 0, ">= 0"
            ),
            scrape_max_retries=_optional(
                env, "SCRAPE_MAX_RETRIES", 3, int, lambda v: v >= 0, ">= 0"
            ),
            log_level=_optional(env, "LOG_LEVEL", "INFO", str),
            base_url=_optional(env, "BASE_URL", "https://books.toscrape.com/", str),
            page_timeout_seconds=_optional(
                env, "PAGE_TIMEOUT_SECONDS", 30, int, lambda v: v > 0, "> 0"
            ),
            chrome_recycle_pages=_optional(
                env, "CHROME_RECYCLE_PAGES", 25, int, lambda v: v >= 1, ">= 1"
            ),
            stale_after_hours=_optional(env, "STALE_AFTER_HOURS", 2, int, lambda v: v > 0, "> 0"),
            db_connect_timeout_seconds=_optional(
                env, "DB_CONNECT_TIMEOUT_SECONDS", 60, int, lambda v: v > 0, "> 0"
            ),
            chrome_bin=_optional(env, "CHROME_BIN", "/usr/bin/chromium", str),
            chromedriver_path=_optional(env, "CHROMEDRIVER_PATH", "/usr/bin/chromedriver", str),
        )
