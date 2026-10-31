import json
import re
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.docker

ROOT = Path(__file__).resolve().parents[2]
IMAGE = "book-monitor-robo:test"


def _docker(*args: str) -> str:
    result = subprocess.run(
        ["docker", *args], capture_output=True, text=True, check=True, timeout=900
    )
    return result.stdout.strip()


def _run(entrypoint: str, *args: str) -> str:
    return _docker("run", "--rm", "--entrypoint", entrypoint, IMAGE, *args)


def _major(version_output: str) -> str:
    match = re.search(r"(\d+)\.\d+\.\d+\.\d+", version_output)
    assert match, f"no version in: {version_output!r}"
    return match.group(1)


@pytest.fixture(scope="module", autouse=True)
def image() -> str:
    _docker("build", "-t", IMAGE, str(ROOT))
    return IMAGE


def test_process_runs_as_non_root():
    assert _run("id", "-u") == "10001"


def test_chromium_responds():
    assert _run("chromium", "--version").startswith("Chromium ")


def test_chromedriver_responds():
    assert _run("chromedriver", "--version").startswith("ChromeDriver ")


def test_driver_major_matches_chromium_major():
    chromium = _major(_run("chromium", "--version"))
    driver = _major(_run("chromedriver", "--version"))
    assert driver == chromium


def test_entrypoint_runs_the_robot_module():
    raw = _docker("image", "inspect", IMAGE, "--format", "{{json .Config.Entrypoint}}")
    entrypoint = json.loads(raw)
    assert entrypoint == ["python", "-m", "book_monitor"]


def test_dockerignore_excludes_local_and_secret_paths():
    lines = (ROOT / ".dockerignore").read_text(encoding="utf-8").splitlines()
    patterns = {line.strip() for line in lines}
    assert {".venv", ".git", ".env", ".specs", "terraform"} <= patterns
