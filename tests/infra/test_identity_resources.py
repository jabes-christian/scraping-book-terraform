import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.infra

IDENTITY = Path(__file__).resolve().parents[2] / "terraform" / "modules" / "identity"
RESOURCE_RE = re.compile(r'^\s*resource\s+"([^"]+)"\s+"([^"]+)"', re.MULTILINE)


def _declared_resources() -> set[tuple[str, str]]:
    found = set()
    for tf_file in IDENTITY.glob("*.tf"):
        found.update(RESOURCE_RE.findall(tf_file.read_text(encoding="utf-8")))
    return found


def test_identity_declares_only_the_service_account():
    # TFP-06: sem binding de IAM (google_*_iam_*) e sem google_service_account_key.
    assert _declared_resources() == {("google_service_account", "this")}
