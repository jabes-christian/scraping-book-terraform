import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.infra

MODULE = Path(__file__).resolve().parents[2] / "terraform" / "modules" / "compute_vm"
RESOURCE_RE = re.compile(r'^\s*resource\s+"([^"]+)"\s+"([^"]+)"', re.MULTILINE)


def _code(tf_file: Path) -> str:
    lines = tf_file.read_text(encoding="utf-8").splitlines()
    return "\n".join(line for line in lines if not line.lstrip().startswith("#"))


def _all_code() -> str:
    return "\n".join(_code(tf_file) for tf_file in MODULE.glob("*.tf"))


def test_module_declares_only_the_instance():
    # TFP-08: nenhum disco extra, IP estático, snapshot, NAT ou balanceador.
    found = set(RESOURCE_RE.findall(_all_code()))
    assert found == {("google_compute_instance", "this")}


@pytest.mark.parametrize(
    "forbidden",
    ["nat_ip", "attached_disk", "scratch_disk", "google_compute_address", "snapshot"],
)
def test_module_has_no_paid_extras(forbidden):
    # TFP-08: IP efêmero (access_config vazio) e nenhum extra cobrado.
    assert forbidden not in _all_code()
