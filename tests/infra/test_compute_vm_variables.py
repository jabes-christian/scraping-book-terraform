import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.infra

VARIABLES = (
    Path(__file__).resolve().parents[2]
    / "terraform"
    / "modules"
    / "compute_vm"
    / "variables.tf"
)


def _variable_block(name: str) -> str:
    text = VARIABLES.read_text(encoding="utf-8")
    match = re.search(rf'^variable\s+"{name}"\s*\{{(.*?)^\}}', text, re.MULTILINE | re.DOTALL)
    assert match, f"variável {name} não declarada"
    return match.group(1)


def test_db_password_is_sensitive():
    # TFP-10: a senha do banco é sensitive = true.
    assert re.search(r"^\s*sensitive\s*=\s*true\s*$", _variable_block("db_password"), re.MULTILINE)


def test_db_password_has_no_default():
    # TFP-10: nenhuma senha embutida no código.
    assert not re.search(r"^\s*default\s*=", _variable_block("db_password"), re.MULTILINE)
