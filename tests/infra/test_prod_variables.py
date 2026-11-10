import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.infra

VARIABLES = (
    Path(__file__).resolve().parents[2]
    / "terraform"
    / "envs"
    / "prod"
    / "variables.tf"
)


def _variable_block(name: str) -> str:
    text = VARIABLES.read_text(encoding="utf-8")
    match = re.search(rf'^variable\s+"{name}"\s*\{{(.*?)^\}}', text, re.MULTILINE | re.DOTALL)
    assert match, f"variável {name} não declarada"
    return match.group(1)


@pytest.mark.parametrize(
    "name",
    ["project_id", "billing_account_id", "repo_url", "db_password"],
)
def test_required_variables_have_no_default(name):
    # TFP-10: valores do ambiente do autor e a senha nunca têm padrão no código.
    assert not re.search(r"^\s*default\s*=", _variable_block(name), re.MULTILINE)


def test_db_password_is_sensitive():
    # TFP-10: a senha do banco é sensitive = true.
    assert re.search(r"^\s*sensitive\s*=\s*true\s*$", _variable_block("db_password"), re.MULTILINE)
