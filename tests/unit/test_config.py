import ast
from pathlib import Path

import pytest

from book_monitor.config import ConfigError, Settings

SRC = Path(__file__).resolve().parents[2] / "src"

REQUIRED = {
    "DB_HOST": "postgres",
    "DB_NAME": "books",
    "DB_USER": "monitor",
    "DB_PASSWORD": "s3cret",
}

CLOUD_SDK_ROOTS = {"google", "googleapiclient", "boto3", "botocore", "azure"}


def _cloud_imports(source: str) -> list[str]:
    found = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            names = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            names = [node.module]
        else:
            continue
        found.extend(n for n in names if n.split(".")[0] in CLOUD_SDK_ROOTS)
    return found


@pytest.mark.parametrize("var", sorted(REQUIRED))
def test_missing_required_variable_raises_config_error_naming_it(var):
    env = {k: v for k, v in REQUIRED.items() if k != var}
    with pytest.raises(ConfigError, match=var):
        Settings.from_env(env)


@pytest.mark.parametrize("var", sorted(REQUIRED))
def test_empty_required_variable_raises_config_error_naming_it(var):
    env = {**REQUIRED, var: ""}
    with pytest.raises(ConfigError, match=var):
        Settings.from_env(env)


def test_optional_variables_fall_back_to_documented_defaults():
    s = Settings.from_env(REQUIRED)
    assert s.db_host == "postgres"
    assert s.db_name == "books"
    assert s.db_user == "monitor"
    assert s.db_password == "s3cret"
    assert s.db_port == 5432
    assert s.scrape_delay_seconds == 0.5
    assert s.scrape_max_retries == 3
    assert s.log_level == "INFO"
    assert s.base_url == "https://books.toscrape.com/"
    assert s.page_timeout_seconds == 30
    assert s.chrome_recycle_pages == 25
    assert s.stale_after_hours == 2
    assert s.db_connect_timeout_seconds == 60
    assert s.chrome_bin == "/usr/bin/chromium"
    assert s.chromedriver_path == "/usr/bin/chromedriver"


def test_every_variable_is_read_from_the_environment():
    env = {
        **REQUIRED,
        "DB_PORT": "5433",
        "SCRAPE_DELAY_SECONDS": "1.5",
        "SCRAPE_MAX_RETRIES": "5",
        "LOG_LEVEL": "DEBUG",
        "BASE_URL": "http://localhost:8000/",
        "PAGE_TIMEOUT_SECONDS": "10",
        "CHROME_RECYCLE_PAGES": "7",
        "STALE_AFTER_HOURS": "4",
        "DB_CONNECT_TIMEOUT_SECONDS": "5",
        "CHROME_BIN": "/opt/chrome",
        "CHROMEDRIVER_PATH": "/opt/driver",
    }
    s = Settings.from_env(env)
    assert s.db_port == 5433
    assert s.scrape_delay_seconds == 1.5
    assert s.scrape_max_retries == 5
    assert s.log_level == "DEBUG"
    assert s.base_url == "http://localhost:8000/"
    assert s.page_timeout_seconds == 10
    assert s.chrome_recycle_pages == 7
    assert s.stale_after_hours == 4
    assert s.db_connect_timeout_seconds == 5
    assert s.chrome_bin == "/opt/chrome"
    assert s.chromedriver_path == "/opt/driver"


@pytest.mark.parametrize(
    "var",
    [
        "DB_PORT",
        "SCRAPE_DELAY_SECONDS",
        "SCRAPE_MAX_RETRIES",
        "PAGE_TIMEOUT_SECONDS",
        "CHROME_RECYCLE_PAGES",
        "STALE_AFTER_HOURS",
        "DB_CONNECT_TIMEOUT_SECONDS",
    ],
)
def test_invalid_numeric_value_raises_config_error_naming_the_variable(var):
    with pytest.raises(ConfigError, match=var):
        Settings.from_env({**REQUIRED, var: "abc"})


@pytest.mark.parametrize(
    ("var", "value", "expected"),
    [
        ("DB_PORT", "0", "1-65535"),
        ("DB_PORT", "65536", "1-65535"),
        ("SCRAPE_MAX_RETRIES", "-1", ">= 0"),
        ("SCRAPE_DELAY_SECONDS", "-0.1", ">= 0"),
        ("PAGE_TIMEOUT_SECONDS", "0", "> 0"),
        ("DB_CONNECT_TIMEOUT_SECONDS", "0", "> 0"),
        ("STALE_AFTER_HOURS", "0", "> 0"),
        ("CHROME_RECYCLE_PAGES", "0", ">= 1"),
    ],
)
def test_out_of_range_value_raises_config_error_naming_variable_and_expected_range(
    var, value, expected
):
    with pytest.raises(ConfigError) as exc:
        Settings.from_env({**REQUIRED, var: value})
    assert var in str(exc.value)
    assert expected in str(exc.value)


@pytest.mark.parametrize(
    ("var", "value", "attr", "parsed"),
    [
        ("DB_PORT", "1", "db_port", 1),
        ("DB_PORT", "65535", "db_port", 65535),
        ("SCRAPE_MAX_RETRIES", "0", "scrape_max_retries", 0),
        ("SCRAPE_DELAY_SECONDS", "0", "scrape_delay_seconds", 0.0),
        ("PAGE_TIMEOUT_SECONDS", "1", "page_timeout_seconds", 1),
        ("DB_CONNECT_TIMEOUT_SECONDS", "1", "db_connect_timeout_seconds", 1),
        ("STALE_AFTER_HOURS", "1", "stale_after_hours", 1),
        ("CHROME_RECYCLE_PAGES", "1", "chrome_recycle_pages", 1),
    ],
)
def test_boundary_value_inside_range_is_accepted(var, value, attr, parsed):
    s = Settings.from_env({**REQUIRED, var: value})
    assert getattr(s, attr) == parsed


@pytest.mark.parametrize("value", ["VERBOSE", "WARN", "TRACE"])
def test_invalid_log_level_raises_config_error_naming_variable_and_accepted_values(value):
    with pytest.raises(ConfigError) as exc:
        Settings.from_env({**REQUIRED, "LOG_LEVEL": value})
    assert "LOG_LEVEL" in str(exc.value)
    assert "DEBUG, INFO, WARNING, ERROR, CRITICAL" in str(exc.value)


@pytest.mark.parametrize(
    ("value", "normalized"),
    [
        ("DEBUG", "DEBUG"),
        ("INFO", "INFO"),
        ("WARNING", "WARNING"),
        ("ERROR", "ERROR"),
        ("CRITICAL", "CRITICAL"),
        ("debug", "DEBUG"),
        ("Warning", "WARNING"),
    ],
)
def test_valid_log_level_is_accepted_and_normalized_to_uppercase(value, normalized):
    assert Settings.from_env({**REQUIRED, "LOG_LEVEL": value}).log_level == normalized


def test_src_does_not_import_cloud_provider_sdks():
    offenders = {}
    for path in SRC.rglob("*.py"):
        imports = _cloud_imports(path.read_text(encoding="utf-8"))
        if imports:
            offenders[str(path.relative_to(SRC))] = imports
    assert offenders == {}


def test_cloud_import_scan_detects_sdk_imports():
    source = "import boto3\nfrom google.cloud import storage\nimport os\n"
    assert _cloud_imports(source) == ["boto3", "google.cloud"]
