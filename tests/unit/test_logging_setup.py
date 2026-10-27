import json
import logging
from datetime import datetime

import pytest

from book_monitor.logging_setup import configure, redact

PASSWORD = "s3cr3t-p4ss"
log = logging.getLogger("test_logging_setup")


@pytest.fixture(autouse=True)
def restore_root_logger():
    root = logging.getLogger()
    handlers, level = root.handlers[:], root.level
    yield
    root.handlers[:] = handlers
    root.setLevel(level)


def _stdout_lines(capsys) -> list[str]:
    return capsys.readouterr().out.splitlines()


def test_each_record_is_one_valid_json_line_with_ts_level_message(capsys):
    configure("INFO", [PASSWORD])
    log.info("hello world")
    lines = _stdout_lines(capsys)
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record["level"] == "INFO"
    assert record["message"] == "hello world"
    assert datetime.fromisoformat(record["ts"]).utcoffset().total_seconds() == 0


def test_multiline_message_and_exception_traceback_stay_on_one_line(capsys):
    configure("INFO", [PASSWORD])
    try:
        raise RuntimeError("boom")
    except RuntimeError:
        log.exception("line one\nline two")
    lines = _stdout_lines(capsys)
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record["message"] == "line one\nline two"
    assert "RuntimeError: boom" in record["exception"]


def test_redact_replaces_every_occurrence_of_the_secret():
    text = f"user=x password={PASSWORD} again {PASSWORD}"
    assert redact(text, [PASSWORD]) == "user=x password=*** again ***"


def test_redact_with_empty_secret_leaves_text_untouched():
    assert redact("plain text", [""]) == "plain text"
    assert redact("plain text", []) == "plain text"


def test_logged_message_does_not_contain_the_password(capsys):
    configure("INFO", [PASSWORD])
    log.info("connecting with password %s", PASSWORD)
    out = capsys.readouterr().out
    assert PASSWORD not in out
    assert json.loads(out)["message"] == "connecting with password ***"


def test_password_with_json_special_characters_is_still_redacted(capsys):
    tricky = 'pa"ss\\word'
    configure("INFO", [tricky])
    log.info("using %s now", tricky)
    out = capsys.readouterr().out
    assert json.loads(out)["message"] == "using *** now"
    assert tricky not in out
    assert json.dumps(tricky)[1:-1] not in out


def test_logged_exception_message_does_not_contain_the_password(capsys):
    configure("INFO", [PASSWORD])
    try:
        raise RuntimeError(f"auth failed for {PASSWORD}")
    except RuntimeError:
        log.exception("db error")
    out = capsys.readouterr().out
    assert PASSWORD not in out
    assert "auth failed for ***" in json.loads(out)["exception"]


def test_records_below_the_configured_level_are_not_emitted(capsys):
    configure("WARNING", [PASSWORD])
    log.info("hidden")
    log.warning("shown")
    messages = [json.loads(line)["message"] for line in _stdout_lines(capsys)]
    assert messages == ["shown"]
