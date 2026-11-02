import os
import subprocess
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[2] / "src"


def test_python_m_book_monitor_exits_2_naming_the_missing_variables():
    env = {"PYTHONPATH": str(SRC), "SYSTEMROOT": os.environ.get("SYSTEMROOT", "")}
    result = subprocess.run(
        [sys.executable, "-m", "book_monitor"],
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 2
    assert "DB_HOST" in result.stdout
