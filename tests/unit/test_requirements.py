from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _lines(name: str) -> list[str]:
    text = (ROOT / name).read_text(encoding="utf-8")
    return [line.strip() for line in text.splitlines() if line.strip()]


def _package_lines(name: str) -> list[str]:
    return [line for line in _lines(name) if not line.startswith("-r ")]


def test_runtime_requirements_are_pinned_with_double_equals():
    packages = _package_lines("requirements.txt")
    assert packages, "requirements.txt has no packages"
    assert all("==" in line for line in packages), packages


def test_dev_requirements_are_pinned_with_double_equals():
    packages = _package_lines("requirements-dev.txt")
    assert packages, "requirements-dev.txt has no packages"
    assert all("==" in line for line in packages), packages


def test_dev_requirements_include_runtime_requirements():
    assert "-r requirements.txt" in _lines("requirements-dev.txt")
