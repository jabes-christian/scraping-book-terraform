from pathlib import Path

ENV_EXAMPLE = Path(__file__).resolve().parents[2] / ".env.example"
EXPECTED_KEYS = {
    "DB_NAME",
    "DB_USER",
    "DB_PASSWORD",
    "SCRAPE_DELAY_SECONDS",
    "SCRAPE_MAX_RETRIES",
    "LOG_LEVEL",
}
SECRET_HINTS = ("PASSWORD", "SECRET", "TOKEN", "KEY", "CREDENTIAL")


def _entries() -> dict[str, str]:
    entries = {}
    for line in ENV_EXAMPLE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            key, _, value = line.partition("=")
            entries[key] = value
    return entries


def test_contains_exactly_the_expected_keys():
    assert set(_entries()) == EXPECTED_KEYS


def test_db_password_is_the_placeholder():
    assert _entries()["DB_PASSWORD"] == "change-me"


def test_no_other_line_looks_like_a_secret():
    for key, value in _entries().items():
        if key == "DB_PASSWORD":
            continue
        assert not any(hint in key for hint in SECRET_HINTS), key
        assert len(value) < 20 and " " not in value, key
