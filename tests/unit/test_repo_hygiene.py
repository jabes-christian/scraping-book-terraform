import fnmatch
import re
import subprocess
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[2]
PROD = ROOT / "terraform" / "envs" / "prod"

# OPS-05: nomes que nunca podem estar versionados (os *.example são permitidos).
FORBIDDEN_PATTERNS = (
    ".env",
    "*.tfvars",
    "*.tfvars.json",
    "backend.hcl",
    "*.tfstate",
    "*.tfstate.*",
    "*.json.key",
    "*-sa-key.json",
    "credentials*.json",
    "gcp-key*.json",
)
REAL_VALUES = ("book-price-monitor-jc", "jabes-christian")


def find_forbidden(tracked: list[str]) -> list[str]:
    return [
        path
        for path in tracked
        if any(fnmatch.fnmatchcase(PurePosixPath(path).name, p) for p in FORBIDDEN_PATTERNS)
    ]


def _tracked_files() -> list[str]:
    result = subprocess.run(
        ["git", "-C", str(ROOT), "ls-files"],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.splitlines()


def _required_variables() -> set[str]:
    text = (PROD / "variables.tf").read_text(encoding="utf-8")
    blocks = re.findall(r'^variable\s+"(\w+)"\s*\{(.*?)^\}', text, re.MULTILINE | re.DOTALL)
    return {
        name for name, body in blocks if not re.search(r"^\s*default\s*=", body, re.MULTILINE)
    }


def test_forbidden_tracked_files_are_detected():
    # OPS-05, cenário negativo: lista sintética com um arquivo proibido de cada tipo.
    tracked = [
        ".env",
        "terraform/envs/prod/terraform.tfvars",
        "terraform/envs/prod/backend.hcl",
        "terraform/bootstrap/terraform.tfstate",
        "terraform/bootstrap/terraform.tfstate.backup",
        "keys/robot-sa-key.json",
        "keys/credentials.json",
    ]
    assert find_forbidden(tracked) == tracked


def test_example_files_are_not_flagged():
    # OPS-05, cenário positivo: só os *.example são permitidos.
    tracked = [
        ".env.example",
        "terraform/envs/prod/terraform.tfvars.example",
        "terraform/envs/prod/backend.hcl.example",
        "terraform/envs/prod/variables.tf",
    ]
    assert find_forbidden(tracked) == []


def test_current_repository_tracks_no_forbidden_file():
    # OPS-05: o repositório atual está limpo.
    assert find_forbidden(_tracked_files()) == []


def test_tfvars_example_covers_required_variables_without_the_password():
    # TFP-10: cobre as variáveis obrigatórias; a senha vai só por TF_VAR_db_password.
    text = (PROD / "terraform.tfvars.example").read_text(encoding="utf-8")
    assigned = set(re.findall(r"^(\w+)\s*=", text, re.MULTILINE))
    assert _required_variables() - {"db_password"} <= assigned
    assert "db_password" not in assigned
    assert "TF_VAR_db_password" in text


def test_examples_hold_only_placeholders():
    # TFP-02, TFP-10: nenhum valor real nos exemplos.
    for name in ("terraform.tfvars.example", "backend.hcl.example"):
        text = (PROD / name).read_text(encoding="utf-8")
        assert "your-project-id" in text
        assert not any(real in text for real in REAL_VALUES)


def test_backend_example_has_bucket_and_prefix_placeholders():
    # TFP-02: backend.hcl.example traz bucket (placeholder) e prefix envs/prod.
    text = (PROD / "backend.hcl.example").read_text(encoding="utf-8")
    assert re.search(r'^bucket\s*=\s*"your-project-id-tfstate"', text, re.MULTILINE)
    assert re.search(r'^prefix\s*=\s*"envs/prod"', text, re.MULTILINE)
