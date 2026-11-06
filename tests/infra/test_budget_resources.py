import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.infra

BUDGET = Path(__file__).resolve().parents[2] / "terraform" / "modules" / "budget"
RESOURCE_RE = re.compile(r'^\s*resource\s+"([^"]+)"\s+"([^"]+)"', re.MULTILINE)


def _code(tf_file: Path) -> str:
    lines = tf_file.read_text(encoding="utf-8").splitlines()
    return "\n".join(line for line in lines if not line.lstrip().startswith("#"))


def _declared_resources() -> set[tuple[str, str]]:
    found = set()
    for tf_file in BUDGET.glob("*.tf"):
        found.update(RESOURCE_RE.findall(_code(tf_file)))
    return found


def test_budget_declares_only_the_billing_budget():
    # TFP-09: sem Pub/Sub nem Monitoring (canal de notificação, tópico etc.).
    assert _declared_resources() == {("google_billing_budget", "this")}


def test_budget_omits_all_updates_rule():
    # TFP-09: alerta por e-mail padrão, sem all_updates_rule.
    code = "\n".join(_code(tf_file) for tf_file in BUDGET.glob("*.tf"))
    assert "all_updates_rule" not in code
