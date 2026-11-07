import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.infra

ROOT = Path(__file__).resolve().parents[2]
MODULE = ROOT / "terraform" / "modules" / "compute_vm"
TEMPLATE = MODULE / "startup.sh.tftpl"
LOCALS = MODULE / "locals.tf"
RENDER_TF = MODULE / "tests" / "render" / "main.tf"
RENDERED_JSON = ROOT / ".rendered-startup.json"

RENDER_HINT = (
    "Gate Infra NAO cumprido: gere o script renderizado (a partir da raiz): "
    "terraform -chdir=terraform/modules/compute_vm/tests/render init; "
    "terraform -chdir=terraform/modules/compute_vm/tests/render apply -auto-approve; "
    "terraform -chdir=terraform/modules/compute_vm/tests/render output -json script "
    "| Set-Content -Encoding ascii .rendered-startup.json"
)
GIT_BASH = (
    Path(r"C:\Program Files\Git\usr\bin\bash.exe"),
    Path(r"C:\Program Files\Git\bin\bash.exe"),
)


def _template_keys(source: Path) -> set[str]:
    text = source.read_text(encoding="utf-8")
    block = re.search(r"templatefile\([^{]*\{(.*?)\n\s*\}\)", text, re.DOTALL)
    assert block, f"templatefile(...) não encontrado em {source.name}"
    return set(re.findall(r"^\s*(\w+)\s*=", block.group(1), re.MULTILINE))


def _find_bash() -> str | None:
    for candidate in GIT_BASH:
        if candidate.exists():
            return str(candidate)
    found = shutil.which("bash")
    # Nunca o launcher do WSL (System32\bash.exe).
    if found and "system32" not in found.lower():
        return found
    return None


def _code_lines(script: str) -> list[str]:
    return [
        line.strip()
        for line in script.splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]


def _first_index(lines: list[str], needle: str) -> int:
    for index, line in enumerate(lines):
        if needle in line:
            return index
    raise AssertionError(f"linha com {needle!r} não encontrada")


@pytest.fixture(scope="module")
def script() -> str:
    if not RENDERED_JSON.exists():
        pytest.skip(RENDER_HINT)
    if RENDERED_JSON.stat().st_mtime < TEMPLATE.stat().st_mtime:
        pytest.fail("O script renderizado está mais velho que o template. " + RENDER_HINT)
    rendered = json.loads(RENDERED_JSON.read_text(encoding="ascii"))
    assert isinstance(rendered, str)
    return rendered


# --- Estáticos (não dependem do arquivo renderizado) ---


def test_template_is_ascii_only():
    # O Set-Content -Encoding ascii do PowerShell 5.1 trocaria acentos por "?".
    TEMPLATE.read_text(encoding="ascii")


def test_locals_and_render_config_pass_the_same_keys():
    assert _template_keys(LOCALS) == _template_keys(RENDER_TF)


def test_every_template_variable_is_passed_to_templatefile():
    used = set(re.findall(r"(?<!\$)\$\{(\w+)\}", TEMPLATE.read_text(encoding="ascii")))
    assert used <= _template_keys(LOCALS)


# --- Sobre o script renderizado (exigem .rendered-startup.json) ---


def test_rendered_script_passes_bash_n(script):
    bash = _find_bash()
    if bash is None:
        pytest.skip("bash do Git não encontrado: gate Infra NAO cumprido")
    result = subprocess.run([bash, "-n"], input=script.encode(), capture_output=True)
    assert result.returncode == 0, result.stderr.decode()


def test_rendered_script_is_strict_and_logs_to_file(script):
    lines = _code_lines(script)
    assert lines[0] == "set -euo pipefail"
    assert "LOG_FILE=/var/log/book-monitor-startup.log" in lines


def test_swap_is_created_only_when_not_active_with_configured_size(script):
    lines = _code_lines(script)
    guard_line = 'if ! swapon --show=NAME --noheadings | grep -qx "$SWAP_FILE"; then'
    guard = _first_index(lines, guard_line)
    assert guard < _first_index(lines, 'fallocate -l 2048M "$SWAP_FILE"')
    assert guard < _first_index(lines, 'swapon "$SWAP_FILE"')
    assert "if ! grep -q '^/swapfile ' /etc/fstab; then" in lines
    assert "echo 'vm.swappiness=60' > /etc/sysctl.d/99-book-monitor.conf" in lines


def test_swap_and_sysctl_come_before_any_docker_command(script):
    lines = _code_lines(script)
    swap = _first_index(lines, 'swapon "$SWAP_FILE"')
    sysctl = _first_index(lines, "sysctl -p /etc/sysctl.d/99-book-monitor.conf")
    first_docker = min(i for i, line in enumerate(lines) if "docker" in line)
    assert swap < sysctl < first_docker


def test_base_packages_are_installed_only_when_missing(script):
    assert "for pkg in git cron logrotate curl ca-certificates; do" in script
    assert 'if ! dpkg -s "$pkg" >/dev/null 2>&1; then' in script
    assert 'if [ -n "$missing" ]; then' in script


def test_docker_comes_from_official_apt_repository_and_is_conditional(script):
    assert (
        "if ! command -v docker >/dev/null 2>&1 || ! docker compose version >/dev/null 2>&1; then"
        in script
    )
    assert "https://download.docker.com/linux/debian/gpg" in script
    assert "URIs: https://download.docker.com/linux/debian" in script
    packages = "docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin"
    assert packages in script


def test_rendered_script_has_no_secret_and_no_leftover_placeholder(script):
    assert "change-me" not in script
    assert not re.search(r"(?i)password\s*=\s*[^\s$\"']", script)
    assert "${" not in script  # nada de interpolação pendente
    assert "%{" not in script


# --- Parte 2: código, .env e build (VM-01, VM-05, VM-09, VM-10) ---

CLONE = (
    'git clone --depth 1 --branch "v1.2.3" '
    '"https://github.com/example/book-price-monitor.git" "$APP_DIR"'
)


def _block(lines: list[str], start: str, end: str) -> list[str]:
    begin = _first_index(lines, start)
    stop = next(i for i in range(begin + 1, len(lines)) if lines[i] == end)
    return lines[begin + 1 : stop]


def test_code_sync_runs_under_flock_with_repo_url_and_ref(script):
    lines = _code_lines(script)
    assert "LOCK_FILE=/var/lock/book-monitor.lock" in lines
    assert "flock -w 900 9" in lines
    assert ') 9>"$LOCK_FILE"' in lines
    assert 'if [ ! -d "$APP_DIR/.git" ]; then' in lines
    assert CLONE in lines
    assert 'git -C "$APP_DIR" fetch --depth 1 origin "v1.2.3"' in script


def test_failed_fetch_with_existing_checkout_only_logs_and_continues(script):
    lines = _code_lines(script)
    elif_fetch = 'elif git -C "$APP_DIR" fetch --depth 1 origin "v1.2.3"; then'
    fetch = _first_index(lines, elif_fetch)
    reset = _first_index(lines, 'git -C "$APP_DIR" reset --hard FETCH_HEAD')
    otherwise = lines.index("else", fetch)
    assert fetch < reset < otherwise
    # O ramo else só registra (não há exit nem comando que falhe).
    assert lines[otherwise + 1] == 'echo "WARN: git fetch failed; keeping the existing checkout"'
    assert lines[otherwise + 2] == "fi"


def test_env_file_is_created_only_if_absent_with_mode_600(script):
    lines = _code_lines(script)
    body = _block(lines, 'if [ ! -f "$ENV_FILE" ]; then', "fi")
    assert 'echo "DB_NAME=booksdb" > "$ENV_FILE"' in body
    assert 'echo "DB_USER=booksuser" >> "$ENV_FILE"' in body
    assert 'echo "DB_PASSWORD=$DB_PASSWORD_VALUE" >> "$ENV_FILE"' in body
    assert 'chmod 600 "$ENV_FILE"' in body
    assert "umask 077" in body
    # Nada escreve no .env fora do bloco condicional.
    outside = [line for line in lines if '"$ENV_FILE"' in line and line not in body]
    assert outside == ['if [ ! -f "$ENV_FILE" ]; then']


def test_password_is_read_from_metadata_and_never_embedded(script):
    lines = _code_lines(script)
    url = "http://metadata.google.internal/computeMetadata/v1/instance/attributes/book-db-password"
    assert f"METADATA_URL={url}" in lines
    fetch = [line for line in lines if line.startswith("DB_PASSWORD_VALUE=$(curl")]
    assert len(fetch) == 1
    assert '-H "Metadata-Flavor: Google" "$METADATA_URL"' in fetch[0]
    assert [line for line in lines if "DB_PASSWORD=" in line] == [
        'echo "DB_PASSWORD=$DB_PASSWORD_VALUE" >> "$ENV_FILE"'
    ]


def test_build_runs_before_postgres_up_and_waits_for_healthcheck(script):
    lines = _code_lines(script)
    build = _first_index(lines, "docker compose build")
    prune = _first_index(lines, "docker image prune -f")
    up = _first_index(lines, "docker compose up -d")
    assert build < prune < up
    assert lines[up] == "docker compose up -d --wait --wait-timeout 180 postgres"
    assert 'cd "$APP_DIR"' in lines[:up]


def test_password_is_read_before_any_write_to_env_file(script):
    # Falha do curl (set -e) aborta antes de criar um .env vazio.
    lines = _code_lines(script)
    read = _first_index(lines, "DB_PASSWORD_VALUE=$(curl")
    first_write = _first_index(lines, '> "$ENV_FILE"')
    assert read < first_write
