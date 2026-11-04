import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.infra

BOOTSTRAP = Path(__file__).resolve().parents[2] / "terraform" / "bootstrap"
RESOURCE_RE = re.compile(r'^\s*resource\s+"([^"]+)"\s+"([^"]+)"', re.MULTILINE)


def _declared_resources() -> set[tuple[str, str]]:
    found = set()
    for tf_file in BOOTSTRAP.glob("*.tf"):
        found.update(RESOURCE_RE.findall(tf_file.read_text(encoding="utf-8")))
    return found


def test_bootstrap_declares_only_storage_api_and_state_bucket():
    assert _declared_resources() == {
        ("google_project_service", "storage"),
        ("google_storage_bucket", "tfstate"),
    }
