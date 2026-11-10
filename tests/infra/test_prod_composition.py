import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.infra

TERRAFORM = Path(__file__).resolve().parents[2] / "terraform"
PROD = TERRAFORM / "envs" / "prod"
MODULES = TERRAFORM / "modules"

RESOURCE_RE = re.compile(r'^\s*resource\s+"([^"]+)"\s+"([^"]+)"', re.MULTILINE)
CLOSED_SET = {
    "google_project_service",
    "google_compute_network",
    "google_compute_subnetwork",
    "google_compute_firewall",
    "google_service_account",
    "google_compute_instance",
    "google_billing_budget",
}
EXPECTED_MODULES = {"apis", "network", "identity", "compute_vm", "budget"}
EXPECTED_APIS = {
    "compute.googleapis.com",
    "iam.googleapis.com",
    "billingbudgets.googleapis.com",
    "iap.googleapis.com",
}


def _code(path: Path) -> str:
    lines = path.read_text(encoding="utf-8").splitlines()
    return "\n".join(line for line in lines if not line.lstrip().startswith("#"))


def _dir_code(directory: Path) -> str:
    return "\n".join(_code(tf_file) for tf_file in sorted(directory.glob("*.tf")))


def _module_block(name: str) -> str:
    match = re.search(
        rf'^module\s+"{name}"\s*\{{(.*?)^\}}', _code(PROD / "main.tf"), re.MULTILINE | re.DOTALL
    )
    assert match, f"module {name} não declarado em envs/prod/main.tf"
    return match.group(1)


def _resource_types(code: str) -> set[str]:
    return {resource_type for resource_type, _ in RESOURCE_RE.findall(code)}


def _composed_modules() -> set[str]:
    return set(re.findall(r'source\s*=\s*"\.\./\.\./modules/(\w+)"', _code(PROD / "main.tf")))


def test_prod_composes_exactly_the_five_modules():
    # TFP-12: nenhum módulo a mais nem a menos.
    assert _composed_modules() == EXPECTED_MODULES


def test_resource_types_are_exactly_the_closed_set():
    # TFP-07/08/09: lista fechada; NAT, LB, IP estático, snapshot, Cloud SQL,
    # Pub/Sub, Artifact Registry ou Secret Manager reprovam por não estarem nela.
    code = _dir_code(PROD) + "\n" + "\n".join(
        _dir_code(MODULES / name) for name in sorted(_composed_modules())
    )
    assert _resource_types(code) == CLOSED_SET


def test_prod_declares_no_resource_itself():
    # TFP-12: os recursos vivem nos módulos.
    assert _resource_types(_dir_code(PROD)) == set()


@pytest.mark.parametrize(
    "forbidden",
    [
        "google_compute_router_nat",
        "google_compute_address",
        "google_compute_forwarding_rule",
        "google_compute_snapshot",
        "google_sql_database_instance",
        "google_pubsub_topic",
        "google_artifact_registry_repository",
        "google_secret_manager_secret",
    ],
)
def test_closed_set_check_rejects_forbidden_types(forbidden):
    # Discriminação: um tipo proibido num módulo fugiria da lista fechada.
    code = f'resource "{forbidden}" "x" {{}}'
    assert _resource_types(code) - CLOSED_SET == {forbidden}


def test_exactly_one_instance():
    # TFP-07: uma única VM (sem count/for_each no módulo nem na chamada).
    compute_code = _dir_code(MODULES / "compute_vm")
    assert RESOURCE_RE.findall(compute_code).count(("google_compute_instance", "this")) == 1
    assert not re.search(r"^\s*(count|for_each)\s*=", compute_code, re.MULTILINE)
    assert not re.search(r"^\s*(count|for_each)\s*=", _module_block("compute_vm"), re.MULTILINE)


def test_prod_enables_exactly_the_four_apis():
    # TFP-01, AD-007: compute, iam, billingbudgets e iap (sem cloudresourcemanager/serviceusage).
    assert set(re.findall(r'"([\w.]+\.googleapis\.com)"', _module_block("apis"))) == EXPECTED_APIS


def test_every_api_keeps_disable_on_destroy_false():
    # TFP-13: o destroy nunca desliga uma API do projeto.
    apis_code = _dir_code(MODULES / "apis")
    assert re.search(r"^\s*disable_on_destroy\s*=\s*false\s*$", apis_code, re.MULTILINE)
    assert not re.search(r"disable_on_destroy\s*=\s*true", apis_code)


@pytest.mark.parametrize("name", ["network", "identity", "compute_vm", "budget"])
def test_modules_wait_for_the_apis(name):
    # TFP-01: criação só depois das APIs (consistência eventual).
    block = _module_block(name)
    assert re.search(r"^\s*depends_on\s*=\s*\[module\.apis\]\s*$", block, re.MULTILINE)
