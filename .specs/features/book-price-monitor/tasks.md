# Book Price Monitor Tasks

## Execution Protocol (MANDATORY -- do not skip)

Implement these tasks with the `tlc-spec-driven` skill: **activate it by name and follow its Execute flow and Critical Rules.** Do not search for skill files by filesystem path. The skill is the source of truth for the full flow (per-task cycle, sub-agent delegation, adequacy review, Verifier, discrimination sensor).

**If the skill cannot be activated, STOP and tell the user - do not proceed without it.**

Regras do projeto que valem em toda a execução (do autor):

- **Git:** o agente NÃO executa comandos git. Ao fim de cada task, entrega os comandos exatos de `git add`/`git commit` para o autor rodar. A task é marcada como concluída neste arquivo (e a rastreabilidade da Spec é atualizada) **antes** do commit, e esses arquivos entram no mesmo commit da task.
- **Idioma dos commits:** tipo e escopo do Conventional Commits em inglês e a descrição em português (ex.: `feat(robot): adiciona modelos de domínio`). Código, logs e nomes técnicos continuam em inglês.
- **Tasks operacionais:** cada task [OPERACIONAL] tem um commit próprio na branch da fase, só com a atualização de `tasks.md` (ex.: `docs(tasks): registra apply do bootstrap (T26)`), feito antes do merge da fase.
- **Sem sub-agentes:** toda a execução, inclusive a verificação final, fica com o agente principal, task a task.
- **Ferramentas:** apenas o MCP Context7; nenhum outro MCP nem skill adicional.
- **Merge de fase:** pelo `gh` ou pelo site do GitHub (Pull Request com merge commit, sem squash).
- **Python:** Windows, Python 3.13; sempre `.venv\Scripts\python.exe` e `.venv\Scripts\python.exe -m pip`. Nunca instalar no Python global.
- **Custo:** `terraform apply`, `destroy` ou qualquer ação com custo ou efeito externo só com OK explícito do autor (tasks marcadas **[OPERACIONAL]**).
- **Terraform e gcloud executados pelo autor (AD-006):** o objetivo é aprender Terraform e GCP, então o agente NÃO executa nenhum comando `terraform` (`init`, `fmt`, `validate`, `test`, `plan`, `apply`, `destroy`, `output`, `import`, `state` etc.) nem `gcloud`. O agente escreve os arquivos (`.tf`, `.tftest.hcl`, templates, docs) e, em cada task, entrega: (1) os comandos exatos, com o diretório de execução (PowerShell, a partir da raiz do projeto); (2) uma explicação curta de cada comando e da saída esperada; (3) os conceitos de Terraform/GCP usados na task. O autor roda, cola a saída e o agente a analisa (em caso de erro, explica a causa e propõe a correção). A task só é marcada como concluída depois da saída do autor confirmar o gate. `pytest` e `ruff` continuam com o agente. Se a saída mostrar `x509: certificate signed by unknown authority` (inspeção TLS da rede corporativa), o agente explica a causa e as opções antes de propor qualquer contorno.
- **`-auto-approve`:** só é aceito na configuração de renderização do startup script (`terraform/modules/compute_vm/tests/render`, sem provider e sem recursos, só outputs locais). Nunca em `plan`/`apply` de `envs/` reais nem do bootstrap: ali o `apply` sempre pede confirmação interativa e OK explícito.
- **Pull Requests:** sempre pelo site do GitHub (o agente não sugere `gh`).
- **Segurança:** nenhum segredo hardcoded; nenhuma chave de service account versionada.
- **Context7:** consultar para Selenium, psycopg 3, provider Google e `terraform test` sempre que a sintaxe não estiver no Design.

---

**Design**: `.specs/features/book-price-monitor/design.md`
**Spec**: `.specs/features/book-price-monitor/spec.md`
**Status**: Approved (2026-10-24)

---

## Test Coverage Matrix

> Generated from codebase, project guidelines, and spec - confirm before Execute. Guidelines found: none - `README.md` não define padrões de teste e não há `AGENTS.md`, `CONTRIBUTING.md`, `pytest.ini` nem CI; strong defaults applied, alinhados à seção "Estratégia de verificação" do `design.md`. Não há testes existentes no repositório (greenfield).

| Code Layer | Required Test Type | Coverage Expectation | Location Pattern | Run Command |
| ---------- | ------------------ | -------------------- | ---------------- | ----------- |
| Robô, lógica pura: `config`, `logging_setup`, `models`, `retry`, `parsing`, `scraper` | unit | Todos os ramos; 1:1 com os ACs da Spec; todo edge case listado; parsing sobre HTML real salvo (`tests/fixtures/`) | `tests/unit/test_*.py` | Quick |
| `browser.py` | unit (driver falso) | Flags do Chrome (LOC-06), reciclagem do driver, `PageLoadError` retentável; o Chromium real é coberto pelo e2e (T21) | `tests/unit/test_browser.py` | Quick |
| `schema.sql`, `db.py`, `runner.py` | integration | Caminhos principais + erros contra PostgreSQL real do Compose; atomicidade (rollback); exit codes | `tests/integration/test_*.py` (marker `integration`) | Full |
| `Dockerfile`, `docker-compose.yml`, `.env.example` | docker (smoke) | Build; usuário não-root; Chromium/driver presentes; `docker compose config` valida `mem_limit`, volume, `restart`, healthcheck, ausência de `ports` | `tests/docker/test_*.py` (marker `docker`) | Docker |
| Fluxo ponta a ponta local | e2e | Os "Independent Test" da Spec: 1.000 itens, 2 execuções, senha ausente dos logs (site real, minutos) | `tests/e2e/test_*.py` (marker `e2e`) | E2E |
| Terraform: stacks e módulos | infra-test (`terraform test`, `mock_provider "google"`) | Toda `validation` com `expect_failures`; toda guarda de Free Tier; atributos-chave dos recursos; tipos de recurso proibidos ausentes | `terraform/**/tests/*.tftest.hcl` | Infra |
| `startup.sh.tftpl` | infra (renderização + `bash -n` + asserções estáticas) | Idempotência estática: uma entrada de cron, `.env` só se ausente, sem senha no texto, `flock`, logrotate | `tests/infra/test_*.py` (marker `infra`) + `*.tftest.hcl` | Infra |
| Higiene do repositório | unit | `git ls-files` sem `.env`, `*.tfvars`, `backend.hcl`, chaves JSON (OPS-05) | `tests/unit/test_repo_hygiene.py` | Quick |
| Docs (`docs/`, READMEs) | none - link check no T50 | Caminhos relativos resolvem | `docs/*.md` | manual / T50 |
| Tarefas operacionais (apply, VM, billing, destroy) | none - evidência manual | Evidência: saída de `gcloud`/`terraform` executados pelo autor (AD-006) e colada no chat; o agente analisa e registra no relatório da task | - | Live |

## Gate Check Commands

> Generated from codebase - confirm before Execute. Todos os comandos Python usam `.venv\Scripts\python.exe` (o shell do agente não herda a ativação do venv).

| Gate Level | When to Use | Command |
| ---------- | ----------- | ------- |
| Quick | Tasks com apenas unit tests | `.venv\Scripts\python.exe -m pytest -m "not integration and not docker and not infra and not e2e"` + `.venv\Scripts\python.exe -m ruff check .` |
| Full | Tasks com integration (exige Docker Desktop ligado) | Quick + `.venv\Scripts\python.exe -m pytest -m integration`. O `conftest.py` sobe e remove sozinho um projeto Compose isolado (`bookmonitor_it`, volume próprio, `127.0.0.1` em porta livre, credenciais de teste): não usa o `.env`, o `docker-compose.override.yml` nem o volume de desenvolvimento, e não exige `docker compose up` prévio |
| Docker | Tasks de Dockerfile/Compose | `docker compose build` + `.venv\Scripts\python.exe -m pytest -m docker` |
| Infra | Tasks de Terraform e startup script | **Executado pelo autor (AD-006)**, com o agente fornecendo os comandos, a explicação e a análise da saída: `terraform fmt -check -recursive terraform` + por stack/módulo alterado: `terraform -chdir=<dir> init -backend=false`, `terraform -chdir=<dir> validate`, `terraform -chdir=<dir> test`. O `pytest -m infra` (quando houver) continua com o agente: `.venv\Scripts\python.exe -m pytest -m infra`. O gate só passa com a saída do autor confirmando. **Tasks do startup script (T32-T34) e Build da Fase 7:** antes do `pytest -m infra`, o autor reexecuta a renderização (`init`, `apply -auto-approve` e `output -json | Set-Content -Encoding ascii .rendered-startup.json` em `terraform/modules/compute_vm/tests/render`, ver T32; o pytest valida o JSON pelo SHA-256 do template, não pela data). O gate Infra dessas tasks (e o Build da fase) só é cumprido se o teste de renderização PASSAR; `skip` (arquivo renderizado ausente) significa gate NÃO cumprido |
| E2E | T21 e antes do Verifier | `.venv\Scripts\python.exe -m pytest -m e2e -s` (site real; ~3-4 min; projeto Compose isolado `bookmonitor_e2e`, credenciais do `.env`). Em rede com inspeção TLS: `E2E_BASE_URL=http://books.toscrape.com/` (repassado ao robô como `BASE_URL`) |
| Build | Fim de cada fase | Quick + os níveis aplicáveis à fase (Full / Docker / Infra) + `terraform fmt -check -recursive terraform` (os comandos `terraform` são executados pelo autor, AD-006) |

Pré-requisitos do ambiente: Docker Desktop ligado nas fases 3 e 4 (hoje o daemon está desligado); `.env` copiado de `.env.example` (gitignored; usado pelo e2e e pelo Compose de desenvolvimento); `docker-compose.override.yml` copiado do `.example` (gitignored) só para acessar o Postgres de desenvolvimento pelo host (os testes de integração não dependem dele); ADC ativo para tasks de Terraform com chamada real (quota project `book-price-monitor-jc`); Terraform e gcloud instalados na máquina do autor, que executa os comandos (AD-006).

---

## Branch Plan

Cada fase = uma branch criada a partir da `main` já atualizada (a fase anterior mergeada). Merge sem squash (preserva um commit por task).

| Fase | Branch | Tasks | Conteúdo |
| ---- | ------ | ----- | -------- |
| 1 | `feat/robot-foundation` | T1-T6 | Dependências, tooling, models, config, logs, retry |
| 2 | `feat/robot-scraping` | T7-T12 | Fixtures, parsing, browser, scraper |
| 3 | `feat/docker-local` | T13-T16 | Dockerfile, `.env.example`, Compose |
| 4 | `feat/robot-persistence` | T17-T21 | Schema, `db.py`, runner, e2e local |
| 5 | `feat/tf-bootstrap` | T22-T26 | Stack do bucket de state + apply |
| 6 | `feat/tf-modules-base` | T27-T30 | Módulos apis, network, identity, budget |
| 7 | `feat/tf-compute-vm` | T31-T36 | Módulo compute_vm e startup script |
| 8 | `feat/tf-prod` | T37-T42 | `envs/prod` + plan real |
| 9 | `docs/operations` | T43-T50 | Runbooks, READMEs, Azure |
| 10 | `docs/live-run-fixes` | T51-T56 | Apply prod, validação na VM, billing, destroy |

---

## Execution Plan

Phases are ordered and run sequentially - each phase completes before the next begins, and tasks within a phase execute in order.

### Phase 1: Robot foundation

```
T1 → T2 → T3 → T4 → T5 → T6
```

### Phase 2: Robot scraping

```
T7 → T8 → T9 → T10 → T11 → T12
```

### Phase 3: Docker local

```
T13 → T14 → T15 → T16
```

### Phase 4: Robot persistence

```
T17 → T18 → T19 → T20 → T21
```

### Phase 5: Terraform bootstrap

```
T22 → T23 → T24 → T25 → T26
```

### Phase 6: Terraform base modules

```
T27 → T28 → T29 → T30
```

### Phase 7: Terraform compute VM

```
T31 → T32 → T33 → T34 → T35 → T36
```

### Phase 8: Terraform prod

```
T37 → T38 → T39 → T40 → T41 → T42
```

### Phase 9: Documentation

```
T43 → T44 → T45 → T46 → T47 → T48 → T49 → T50
```

### Phase 10: Live validation

```
T51 → T52 → T53 → T54 → T55 → T56
```

---

## Task Breakdown

### Phase 1: Robot foundation (`feat/robot-foundation`)

#### T1: Pinar dependências Python

**What**: Criar `requirements.txt` (`selenium==4.51.0`, `psycopg[binary]==3.3.6`, `beautifulsoup4==4.15.0`) e `requirements-dev.txt` (`-r requirements.txt`, `pytest==9.1.1`, `ruff==0.17.2`) e instalá-las no `.venv`.
**Where**: repo root
**Depends on**: None
**Reuses**: Versões consultadas no PyPI e registradas no Design
**Requirement**: CFG-07

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] `.venv\Scripts\python.exe -m pip install -r requirements-dev.txt` conclui sem erro e `.venv\Scripts\python.exe -m pip check` não acusa conflito (se alguma versão não existir no PyPI, parar e reportar antes de alterar o pin)
- [x] Teste unit: toda linha de pacote em ambos os arquivos usa `==` (ou `-r`), e o dev inclui `-r requirements.txt`
- [x] Gate check passes: Quick
- [x] Test count: ≥ 2 testes passam

**Tests**: unit
**Gate**: quick
**Commit**: `build(deps): fixa versões das dependências de runtime e dev`
**Status**: ✅ Concluída (3 testes)

---

#### T2: Configurar pytest e ruff

**What**: Criar `pyproject.toml` com `pythonpath = ["src"]`, `testpaths = ["tests"]`, markers `integration`, `docker`, `infra`, `e2e` (`--strict-markers`) e configuração do ruff (linha 100, regras `E,F,I,B,UP`).
**Where**: `pyproject.toml`
**Depends on**: T1
**Reuses**: Marcadores e níveis de gate da seção "Gate Check Commands"
**Requirement**: Habilitador dos gates do Design (sem ID de requisito)

**Tools**:

- MCP: `context7` (config do pytest/ruff, se necessário)
- Skill: NONE

**Done when**:

- [x] `.venv\Scripts\python.exe -m pytest --collect-only` roda sem erro (0 testes coletados aceitável aqui, ou os do T1) e rejeita marker desconhecido
- [x] `.venv\Scripts\python.exe -m ruff check .` passa
- [x] Gate check passes: Quick

**Tests**: none
**Gate**: quick
**Commit**: `chore(tooling): configura markers do pytest e o ruff`
**Status**: ✅ Concluída (3 testes do T1 seguem passando)

---

#### T3: Modelos de domínio

**What**: Criar `src/book_monitor/__init__.py` e `models.py` com `BookItem` (dataclass `frozen`, `price: Decimal`), `Category`, `Listing` e o enum `Status` (`RUNNING`, `SUCCESS`, `FAILED`).
**Where**: `src/book_monitor/models.py`
**Depends on**: T2
**Reuses**: Assinaturas do Design (componente `models.py`)
**Requirement**: SCR-03 (forma dos dados)

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] `BookItem` é imutável (atribuição levanta `FrozenInstanceError`) e guarda `price` como `Decimal`
- [x] `Status` expõe exatamente `RUNNING`, `SUCCESS`, `FAILED`
- [x] Gate check passes: Quick
- [x] Test count: ≥ 3 testes passam

**Tests**: unit
**Gate**: quick
**Commit**: `feat(robot): adiciona modelos de domínio`
**Status**: ✅ Concluída (4 testes novos; 7 no total)

---

#### T4: Configuração por variáveis de ambiente

**What**: Implementar `Settings.from_env(env)` e `ConfigError` em `config.py`, com todas as variáveis da Spec e do Design e seus padrões.
**Where**: `src/book_monitor/config.py`
**Depends on**: T3
**Reuses**: Lista de variáveis e padrões do Design (`BASE_URL`, `PAGE_TIMEOUT_SECONDS`, `CHROME_RECYCLE_PAGES` etc.)
**Requirement**: CFG-01, CFG-02, CFG-04, CFG-08

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Cada variável obrigatória ausente (`DB_HOST`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`) levanta `ConfigError` cujo texto cita o nome da variável (um teste por variável, valor vazio incluso)
- [x] Padrões corretos quando opcionais ausentes (`DB_PORT=5432`, `SCRAPE_DELAY_SECONDS=0.5`, `SCRAPE_MAX_RETRIES=3`, `LOG_LEVEL=INFO` etc.); valor numérico inválido levanta `ConfigError`
- [x] Faixas validadas (CFG-08): `DB_PORT` 1-65535; `SCRAPE_MAX_RETRIES` ≥ 0; `SCRAPE_DELAY_SECONDS` ≥ 0; `PAGE_TIMEOUT_SECONDS`, `DB_CONNECT_TIMEOUT_SECONDS` e `STALE_AFTER_HOURS` > 0; `CHROME_RECYCLE_PAGES` ≥ 1; fora da faixa levanta `ConfigError` citando a variável e o valor esperado; um teste de limite inválido e um de limite válido por faixa (ex.: retries -1 falha, 0 passa)
- [x] `LOG_LEVEL` fora de {`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`} levanta `ConfigError` citando a variável e os valores aceitos; minúsculas são aceitas e normalizadas para maiúsculas (CFG-08, extensão)
- [x] Teste de varredura (AST) garante que nenhum arquivo de `src/` importa SDK de nuvem (`google.cloud`, `boto3`, `azure` etc.) - CFG-04; reexecutado em todo gate seguinte
- [x] Gate check passes: Quick
- [x] Test count: ≥ 10 testes passam

**Tests**: unit
**Gate**: quick
**Commit**: `feat(robot): carrega e valida configurações do ambiente`
**Status**: ✅ Concluída (35 testes novos; 42 no total; extensão do CFG-08 com `LOG_LEVEL` em commit separado, +9 testes)

---

#### T5: Logs JSON e redação de segredos

**What**: Implementar `configure(level, secrets)` (formatter JSON de uma linha por evento em stdout) e `redact(text, secrets)` em `logging_setup.py`.
**Where**: `src/book_monitor/logging_setup.py`
**Depends on**: T4
**Reuses**: Decisão de formatter próprio sem biblioteca (Design)
**Requirement**: CFG-03, CFG-06

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Cada registro emitido é uma linha JSON válida contendo ao menos `ts`, `level`, `message`
- [x] `redact` troca toda ocorrência do segredo por `***`, inclusive em mensagem de exceção; segredo vazio não corrompe o texto
- [x] Um log emitido com a senha na mensagem não a contém na saída capturada
- [x] Gate check passes: Quick
- [x] Test count: ≥ 6 testes passam

**Tests**: unit
**Gate**: quick
**Commit**: `feat(robot): adiciona logs JSON com redação de segredos`
**Status**: ✅ Concluída (8 testes novos; 50 no total)

---

#### T6: Retry com backoff

**What**: Implementar `retry(fn, retries, base_delay=2, on_retry=...)` e `RetryableError` em `retry.py`, com `sleep` injetável.
**Where**: `src/book_monitor/retry.py`
**Depends on**: T5
**Reuses**: Parâmetros 2 s/4 s/8 s da Spec
**Requirement**: SCR-06

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Com `retries=3` e falha persistente: 4 chamadas no total, esperas exatamente [2, 4, 8] s, e a última exceção é propagada
- [x] Sucesso na 3ª tentativa devolve o resultado sem esperas extras; exceção que não é `RetryableError` não é repetida
- [x] Gate check passes: Quick
- [x] Test count: ≥ 5 testes passam

**Tests**: unit
**Gate**: quick
**Commit**: `feat(robot): adiciona retry com backoff exponencial`
**Status**: ✅ Concluída (5 testes novos; 65 no total)

---

### Phase 2: Robot scraping (`feat/robot-scraping`)

#### T7: Capturar fixtures HTML reais

**What**: Baixar do site real (GET de leitura) e salvar em `tests/fixtures/` a home, uma categoria com várias páginas (primeira e última página), uma categoria de página única e uma página com título truncado na listagem; confirmar os seletores do Design (`article.product_pod`, `p.price_color`, `li.next a`, `div.side_categories`, "N results").
**Where**: `tests/fixtures/`
**Depends on**: T6
**Reuses**: Risco "seletores não verificados" do Design
**Requirement**: Habilitador de SCR-01..05, SCR-07, EDG-03 (sem ID próprio)

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Fixtures versionáveis salvas em UTF-8 e listadas no relatório da task, com os seletores confirmados (ou corrigidos, com a correção registrada)
- [x] Gate check passes: Quick (os testes anteriores continuam passando)

**Tests**: none
**Gate**: quick
**Commit**: `test(robot): adiciona fixtures HTML reais do books.toscrape.com`
**Status**: ✅ Concluída (65 testes seguem passando). Fixtures em `tests/fixtures/` (UTF-8, GET de leitura em 2026-10-30): `home.html` (50 categorias + "Books", 1000 results, link next), `category_multi_first.html` (Default, 152 results, 20 itens, next), `category_multi_last.html` (Default `page-8`, 12 itens, só previous), `category_single.html` (Travel, 11 results, página única, 7 títulos truncados com "..."), `category_one_result.html` (Erotica, 1 item). Seletores confirmados: `article.product_pod`, `p.price_color` (texto `£45.17`), `li.next a` (href relativo, ex. `page-2.html`), `div.side_categories` (primeiro `li` é "Books" agregador, 50 categorias abaixo), `p.availability` (texto com espaços em volta, "In stock"), título completo no atributo `title` do `h3 a`. Correção: o site usa o singular "1 result." (a regex do Design era `results`; virou `results?`, registrado no `design.md`) e o número fica em `<strong>`, então a regex roda sobre o texto. Categoria com 0 results não existe no site (T10 usa HTML sintético).

---

#### T8: Parse de preço

**What**: Implementar `parse_price(text) -> Decimal` em `parsing.py`.
**Where**: `src/book_monitor/parsing.py`
**Depends on**: T7
**Reuses**: Fixtures do T7 (strings de preço reais)
**Requirement**: SCR-07, DB-09 (valor numérico)

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] `"£51.77"` → `Decimal("51.77")`; entradas inválidas (`""`, `"abc"`, `"£"`) levantam erro de parsing
- [x] Gate check passes: Quick
- [x] Test count: ≥ 4 testes passam

**Tests**: unit
**Gate**: quick
**Commit**: `feat(robot): converte texto de preço em Decimal`
**Status**: ✅ Concluída (5 testes novos; 70 no total). `ParseError(ValueError)` criado em `parsing.py` para os próximos parsers. SCR-07 e DB-09 marcados `In progress (T8)` na rastreabilidade da Spec (completam na T10 e na T17/T19).

---

#### T9: Parse da lista de categorias

**What**: Implementar `parse_categories(html, base_url) -> list[Category]` (nome e URL absoluta), sem lista fixa no código.
**Where**: `src/book_monitor/parsing.py` (modify)
**Depends on**: T8
**Reuses**: Fixture da home (T7)
**Requirement**: SCR-01

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Sobre a fixture da home retorna as 50 categorias (excluindo o item "Books" agregador, conforme a estrutura real confirmada no T7) com URLs absolutas
- [x] HTML sem a estrutura esperada levanta erro de parsing
- [x] Gate check passes: Quick
- [x] Test count: ≥ 3 testes passam

**Tests**: unit
**Gate**: quick
**Commit**: `feat(robot): extrai a lista de categorias da home`
**Status**: ✅ Concluída (5 testes novos; 75 no total). Seletor `div.side_categories ul ul li a` (o "Books" agregador fica no `ul` externo e sai sem filtro por nome). SCR-01 marcado `In progress (T9)` na Spec (completa na T12).

---

#### T10: Parse de página de listagem

**What**: Implementar `parse_listing(html, page_url, category) -> Listing(items, total_results, next_url)`.
**Where**: `src/book_monitor/parsing.py` (modify)
**Depends on**: T9
**Reuses**: `parse_price` (T8), fixtures de categoria (T7)
**Requirement**: SCR-02, SCR-03, SCR-04, SCR-07, EDG-01, EDG-03

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Para cada livro: categoria, título completo vindo do atributo `title` (não o texto truncado), `Decimal`, disponibilidade em texto e URL absoluta
- [x] `total_results` extraído de "N results"; `next_url` absoluta quando há link "next" e `None` na última página; categoria com 0 results devolve 0 itens sem erro (HTML sintético)
- [x] Preço ilegível levanta erro cuja mensagem contém a URL do livro; título com aspas/acentos permanece íntegro
- [x] Gate check passes: Quick
- [x] Test count: ≥ 9 testes passam

**Tests**: unit
**Gate**: quick
**Commit**: `feat(robot): extrai livros das páginas de listagem`
**Status**: ✅ Concluída (14 testes novos; 89 no total). `parse_listing` recebe o `Category` e grava `category.name` em cada `BookItem`. "N results" é lido pelo `<strong>` seguido de "result(s)" (cobre o singular "1 result."). SCR-03 e SCR-07 viram `Implemented`; SCR-02, SCR-04, EDG-01 e EDG-03 `In progress (T10)`.

---

#### T11: Sessão do navegador

**What**: Implementar `BrowserSession` com Chromium headless (flags do Design, `Service(executable_path)`, `page_load_strategy='eager'`), validação do marcador estrutural, `PageLoadError` retentável e reciclagem do driver a cada `CHROME_RECYCLE_PAGES` páginas e após `WebDriverException`.
**Where**: `src/book_monitor/browser.py`
**Depends on**: T10
**Reuses**: `retry` (T6), `Settings` (T4); Context7 para a API do Selenium
**Requirement**: SCR-09, LOC-06, SCR-06

**Tools**:

- MCP: `context7` (Selenium: `ChromeOptions`, `Service`, `page_load_strategy`)
- Skill: NONE

**Done when**:

- [x] Com driver falso: as opções contêm `--headless=new`, `--no-sandbox`, `--disable-dev-shm-usage`, `--disable-gpu`, `--blink-settings=imagesEnabled=false`, `binary_location` e `executable_path` vindos da config (nenhum download de driver)
- [x] O driver é recriado na 25ª página e após `WebDriverException`; página sem o marcador estrutural levanta `PageLoadError` (retentável) e timeout configurado em `PAGE_TIMEOUT_SECONDS`
- [x] Gate check passes: Quick
- [x] Test count: ≥ 6 testes passam

**Tests**: unit
**Gate**: quick
**Commit**: `feat(robot): adiciona sessão do Chromium headless`
**Status**: ✅ Concluída (8 testes novos; 97 no total). `BrowserSession(settings, driver_factory=webdriver.Chrome)` com `get_html(url)` e `close()`; marcador estrutural `side_categories` (presente em todas as páginas reais, inclusive categoria de 1 item). `WebDriverException` (inclui `TimeoutException`) descarta o driver e vira `PageLoadError(RetryableError)`. Precisão da Spec: "recriado na 25ª página" foi lido como "o driver atende `CHROME_RECYCLE_PAGES` páginas e é descartado em seguida; a próxima página usa um driver novo". Falha no `quit()` do driver é registrada em log `warning` (`failed to quit browser driver: <mensagem da exceção>`) e ignorada. SCR-06 marcado `In progress (T6, T11)`; SCR-09 e LOC-06 `In progress (T11)`. O Chromium real só é exercitado no e2e (T21).

---

#### T12: Orquestração da coleta

**What**: Implementar `scrape_all(session, settings) -> list[BookItem]`: categorias, paginação, espera entre páginas, conferência de contagem por categoria e detecção de URL duplicada.
**Where**: `src/book_monitor/scraper.py`
**Depends on**: T11
**Reuses**: `parsing` (T9-T10), `BrowserSession` (T11), `retry` (T6)
**Requirement**: SCR-01, SCR-02, SCR-04, SCR-05, SCR-06, SCR-08, EDG-01, EDG-02

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Com sessão falsa servindo as fixtures: percorre todas as páginas até não haver "next" e a soma de itens bate com "N results"
- [x] Divergência de contagem falha com `count mismatch` e o nome da categoria; URL repetida falha com `duplicate url` e a URL; categoria com 0 itens segue sem falhar
- [x] Falha de página esgota 4 tentativas (esperas 2/4/8 s) e propaga o erro; `time.sleep` do delay é chamado com `SCRAPE_DELAY_SECONDS` entre páginas consecutivas
- [x] Gate check passes: Quick (suíte completa da fase)
- [x] Test count: ≥ 8 testes passam

**Tests**: unit
**Gate**: quick
**Commit**: `feat(robot): orquestra a coleta por categoria e paginação`
**Status**: ✅ Concluída (8 testes novos; 105 no total). `scrape_all(session, settings, sleep=time.sleep)` e `ScrapeError` (`count mismatch: <categoria> (...)`, `duplicate url: <url>`). As fixtures cobrem as páginas únicas (Travel e Erotica); a paginação multipágina usa HTML sintético, porque só a primeira e a última página de Default foram capturadas na T7. Spec: SCR-01, 02, 04, 05, 06, 08, EDG-01 e EDG-02 viram `Implemented`; SCR-09 e EDG-03 seguem em andamento (T21/T53 e T19).

---

### Phase 3: Docker local (`feat/docker-local`)

#### T13: Dockerfile do robô

**What**: Criar `Dockerfile` (`python:3.13-slim-bookworm`, `chromium`, `chromium-driver`, `fonts-liberation`, usuário não-root uid 10001, `pip install -r requirements.txt` antes de copiar `src/`, `ENTRYPOINT ["python","-m","book_monitor"]`) e `.dockerignore`.
**Where**: `Dockerfile`
**Depends on**: T12
**Reuses**: Design (componente Docker)
**Requirement**: LOC-02

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] `docker compose build`/`docker build` conclui; teste docker: `id -u` ≠ 0, `chromium --version` e `chromedriver --version` respondem (override de entrypoint) e a versão major do driver coincide com a do Chromium
- [x] `.dockerignore` exclui `.venv`, `.git`, `.env`, `.specs`, `terraform`
- [x] Gate check passes: Docker
- [x] Test count: ≥ 3 testes passam

**Tests**: integration (marker `docker`)
**Gate**: docker
**Commit**: `build(docker): adiciona imagem do robô com Chromium`
**Status**: ✅ Concluída (6 testes docker novos; 105 unit seguem passando). Imagem `python:3.13-slim-bookworm` com Chromium 156 e chromedriver da mesma major (Debian 12), usuário `robo` uid 10001, `PYTHONPATH=/app/src` (o pacote não é instalado via pip), `CHROME_BIN`/`CHROMEDRIVER_PATH` como `ENV`. Como o Compose só nasce na T15, o gate usou `docker build -t book-monitor-robo:test .` (feito pela fixture do teste) no lugar de `docker compose build`. `.dockerignore` também exclui `tests`, caches e `.env.*` (menos `.env.example`). O `ENTRYPOINT` ainda não roda (o `__main__.py` vem na T20); os testes sobrescrevem o entrypoint.

---

#### T14: Template de variáveis `.env.example`

**What**: Criar `.env.example` com `DB_NAME`, `DB_USER`, `DB_PASSWORD=change-me`, `SCRAPE_DELAY_SECONDS`, `SCRAPE_MAX_RETRIES`, `LOG_LEVEL`; copiar para `.env` local (gitignored).
**Where**: `.env.example`
**Depends on**: T13
**Reuses**: Variáveis do Design
**Requirement**: LOC-05

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Teste: `.env.example` contém as chaves esperadas, `DB_PASSWORD` é o placeholder `change-me` e nenhuma outra linha parece segredo
- [x] `git check-ignore .env` confirma `.env` ignorado e `.env.example` não (verificação de leitura; sem alterar o repositório)
- [x] Gate check passes: Quick
- [x] Test count: ≥ 2 testes passam

**Tests**: unit
**Gate**: quick
**Commit**: `chore(env): adiciona .env.example sem segredos`
**Status**: ✅ Concluída (3 testes novos; 108 unit passam). `.env.example` com as 6 chaves (`DB_NAME=books`, `DB_USER=books`, `DB_PASSWORD=change-me`, `SCRAPE_DELAY_SECONDS=0.5`, `SCRAPE_MAX_RETRIES=3`, `LOG_LEVEL=INFO`). `.env` local criado a partir dele com senha aleatória (não exibida). `git check-ignore -q`: `.env` ignorado (exit 0) e `.env.example` não (exit 1). LOC-05 fica `In progress (T14)` (completa na T15).

---

#### T15: Docker Compose

**What**: Criar `docker-compose.yml` com `postgres` (`postgres:17-alpine`, `restart: unless-stopped`, volume nomeado `pgdata`, `mem_limit: 192m`, `-c shared_buffers=32MB -c max_connections=10 -c work_mem=2MB`, healthcheck `pg_isready`, sem `ports`) e `robo` (`build: .`, `depends_on` com `service_healthy`, `env_file: .env`, `DB_HOST=postgres`, `mem_limit: 560m`, `init: true`, `restart: "no"`).
**Where**: `docker-compose.yml`
**Depends on**: T14
**Reuses**: Tabela de serviços do Design
**Requirement**: LOC-01, LOC-03, LOC-04, LOC-05, VM-06, DB-08

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Teste sobre `docker compose config --format json`: volume nomeado em `/var/lib/postgresql/data`, `restart` do postgres, `mem_limit` de ambos com soma ≤ 752 MB, healthcheck presente, `postgres` sem `ports`, `robo` com `depends_on.postgres.condition == service_healthy` e `init` true
- [x] `docker compose up -d --wait postgres` fica `healthy` e os dados sobrevivem a `docker compose up -d --force-recreate postgres` (tabela de teste criada e relida)
- [x] Gate check passes: Docker
- [x] Test count: ≥ 6 testes passam

**Tests**: integration (marker `docker`)
**Gate**: docker
**Commit**: `feat(docker): adiciona stack Compose com postgres e robô`
**Status**: ✅ Concluída (8 testes docker novos; 14 docker e 108 unit passam). `docker-compose.yml` com `postgres:17-alpine` (volume `pgdata`, 192m, tuning, healthcheck `pg_isready -h 127.0.0.1` para só ficar `healthy` depois da inicialização, sem `ports`) e `robo` (`build: .`, `image: book-monitor-robo`, 560m, `init`, `restart: "no"`, `DB_HOST=postgres`); soma dos limites = 752 MB. `docker compose config` entrega `mem_limit` como string de bytes, então o teste converte com `int()`. Os testes usam o projeto `bookmonitor_test` e senha de teste via ambiente, e fazem `down -v` no fim (não tocam no volume nem no `.env` de desenvolvimento). Persistência verificada com `up -d --wait` + `--force-recreate`. O `robo` exige o `.env` local (`env_file`). Spec: LOC-03 e LOC-04 `Implemented`; LOC-01, LOC-05, VM-06 e DB-08 `In progress`.

---

#### T16: Override local do Compose

**What**: Criar `docker-compose.override.yml.example` que publica `127.0.0.1:5432` do `postgres` para os testes de integração; copiar para `docker-compose.override.yml` local (gitignored).
**Where**: `docker-compose.override.yml.example`
**Depends on**: T15
**Reuses**: Nota do Design sobre acesso do host em dev
**Requirement**: Habilitador do gate Full (sem ID de requisito)

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Com o override, `127.0.0.1:5432` aceita conexão TCP e sem o override a porta não é publicada; `git check-ignore docker-compose.override.yml` confirma o arquivo real ignorado
- [x] Gate check passes: Docker (testes anteriores continuam passando)

**Tests**: none
**Gate**: docker
**Commit**: `chore(docker): adiciona exemplo de override local do Compose`
**Status**: ✅ Concluída (sem testes novos; 14 docker e 108 unit passam). `docker-compose.override.yml.example` publica `127.0.0.1:5432:5432` do `postgres`; o `docker-compose.override.yml` local foi copiado dele. Verificado em projeto Compose descartável: sem o override a porta fica só `5432/tcp` (não publicada) e a conexão TCP do host é recusada; com o override aparece `127.0.0.1:5432->5432/tcp` e a conexão é aceita. `git check-ignore`: o override real é ignorado (exit 0) e o `.example` não (exit 1). Ajuste no `tests/docker/test_compose.py`: o helper passou a usar `-f docker-compose.yml`, pois o Compose carrega o override sozinho e o teste "postgres sem `ports`" falharia no seu ambiente; nenhuma asserção foi alterada.

---

### Phase 4: Robot persistence (`feat/robot-persistence`)

#### T17: Schema do banco

**What**: Criar `src/book_monitor/schema.sql` (DDL idempotente do Design: `executions`, `books`, `price_history`, índice) e o `conftest.py` de integração (conexão via `.env`, `DB_HOST` padrão `127.0.0.1`, schema limpo por teste).
**Where**: `src/book_monitor/schema.sql`
**Depends on**: T16
**Reuses**: DDL do Design
**Requirement**: DB-01, DB-09

**Tools**:

- MCP: `context7` (psycopg 3: conexão e execução de script)
- Skill: NONE

**Done when**:

- [x] Aplicar o DDL duas vezes não falha (idempotente) e cria as três tabelas
- [x] `price_history.price` é `numeric(10,2)` e `currency` assume `GBP` por padrão; `status` rejeita valor fora de `RUNNING/SUCCESS/FAILED`; `UNIQUE (execution_id, book_id)` impede duplicata
- [x] Gate check passes: Full
- [x] Test count: ≥ 5 testes passam

**Tests**: integration
**Gate**: full
**Commit**: `feat(db): adiciona schema idempotente`
**Status**: ✅ Concluída (7 testes de integração novos; 108 unit seguem passando). `schema.sql` é o DDL do Design sem alterações. O `conftest.py` de integração sobe um projeto Compose próprio (`bookmonitor_it`, volume próprio, `127.0.0.1` em porta livre via override temporário, `down -v` ao fim da sessão) em vez de usar o `.env` e a porta 5432 do desenvolvimento; a fixture `pg_env` entrega as variáveis `DB_*` (reaproveitadas na T18) e `conn` entrega uma conexão autocommit com o schema `public` recriado vazio a cada teste. Por isso o gate Full dispensa o `docker compose up -d --wait postgres` do ambiente de desenvolvimento. DB-01 e DB-09 ficam `In progress`.

---

#### T18: Conexão, schema e execuções abandonadas

**What**: Implementar em `db.py` `connect_with_retry(settings, timeout=60)`, `ensure_schema(conn)` e `mark_abandoned(conn, hours)`.
**Where**: `src/book_monitor/db.py`
**Depends on**: T17
**Reuses**: `Settings` (T4), `redact` (T5)
**Requirement**: DB-01, DB-06, DB-07

**Tools**:

- MCP: `context7` (psycopg 3: `connect`, autocommit)
- Skill: NONE

**Done when**:

- [x] `ensure_schema` cria o schema em banco vazio e é reentrante
- [x] `mark_abandoned` marca como `FAILED` com erro `abandoned` só execuções `RUNNING` com `started_at` anterior a 2 h (uma de 3 h é marcada; uma de 1 h e uma `SUCCESS` ficam intactas)
- [x] `connect_with_retry` contra host inacessível desiste ao fim do timeout (reduzido no teste) com exceção cuja mensagem não contém a senha
- [x] Gate check passes: Full
- [x] Test count: ≥ 6 testes passam

**Tests**: integration
**Gate**: full
**Commit**: `feat(db): adiciona reconexão, criação do schema e limpeza de execuções abandonadas`
**Status**: ✅ Concluída (9 testes de integração novos; 16 de integração e 108 unit passam). `connect_with_retry(settings, timeout=60, interval=1.0)` devolve conexão autocommit, tenta de novo em `OperationalError` até o prazo e então levanta `DatabaseUnavailableError` (mensagem com host:porta e o motivo redigido, `from None` para não encadear a exceção original). `ensure_schema` executa o `schema.sql` (script sem parâmetros). `mark_abandoned` devolve a quantidade de execuções marcadas. Os testes de reconexão usam `monkeypatch` em `psycopg.connect` (falha duas vezes e depois conecta; erro do driver contendo a senha). O runner (T20) passa `settings.db_connect_timeout_seconds` como `timeout`. DB-01 e DB-06 viram `Implemented`; DB-07 `In progress` (completa na T20).

---

#### T19: Execuções e gravação transacional

**What**: Implementar em `db.py` `start_execution(conn) -> int`, `save_success(conn, exec_id, items)` (uma transação: upsert em `books`, linhas em `price_history`, `UPDATE executions SET SUCCESS`) e `mark_failed(conn, exec_id, error)` (truncado em 2.000 caracteres).
**Where**: `src/book_monitor/db.py` (modify)
**Depends on**: T18
**Reuses**: Upsert SQL e padrão `with conn.transaction()` do Design
**Requirement**: DB-02, DB-03, DB-04, DB-05, DB-09, EDG-03, EDG-04

**Tools**:

- MCP: `context7` (psycopg 3: `transaction()`, `executemany`)
- Skill: NONE

**Done when**:

- [x] `start_execution` cria linha `RUNNING` com `started_at`; `save_success` grava N livros e N linhas de preço e deixa `SUCCESS`, `finished_at` e `items_count == N` na mesma transação
- [x] Falha injetada no meio de `save_success` não deixa linha de `price_history` nem `SUCCESS` (rollback); `mark_failed` grava `FAILED`, `finished_at` e erro truncado em 2.000 caracteres sem tocar em `price_history`
- [x] Duas execuções no mesmo dia geram duas execuções independentes, cada uma com suas linhas; reexecutar o mesmo livro atualiza `books` (mesma URL) sem duplicá-lo; título com aspas e acentos volta íntegro
- [x] Gate check passes: Full
- [x] Test count: ≥ 8 testes passam

**Tests**: integration
**Gate**: full
**Commit**: `feat(db): adiciona ciclo de vida da execução e gravação transacional de preços`
**Status**: ✅ Concluída (8 testes de integração novos; 24 de integração e 108 unit passam). `start_execution`, `save_success` (um `executemany` do upsert do Design dentro de `conn.transaction()`, mais o `UPDATE` para `SUCCESS`) e `mark_failed` (erro cortado em 2.000 caracteres; a redação de segredos fica no runner, T20). A falha no meio da gravação é injetada com um preço que estoura `numeric(10,2)` no 2º item (`NumericValueOutOfRange`): o rollback desfaz também o upsert de `books`. `items_count` é `len(items)`. Spec: DB-02, DB-03, DB-04, DB-09 e EDG-03 viram `Implemented`; DB-05 e EDG-04 `In progress (T19)` (completam na T20).

---

#### T20: Runner e entrypoint

**What**: Implementar `runner.run(env) -> int` e `__main__.py`: carrega config (exit 2 sem tocar o banco), configura logs com redação, conecta, `ensure_schema`, `mark_abandoned`, `start_execution`, coleta, grava e devolve 0/1; scraper injetável para teste.
**Where**: `src/book_monitor/runner.py`
**Depends on**: T19
**Reuses**: `config`, `logging_setup`, `db`, `scraper`
**Requirement**: CFG-02, CFG-03, CFG-05, DB-05, DB-07, EDG-04

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Sem `DB_PASSWORD`: retorna 2, a mensagem cita `DB_PASSWORD` e nenhuma conexão é aberta
- [x] Scraper falso com sucesso: retorna 0, `executions` com `SUCCESS` e `items_count` correto; scraper que levanta erro: retorna 1, `FAILED` com erro, zero linhas de `price_history`
- [x] Banco inacessível: retorna 1 sem linha em `executions` e sem a senha na saída; a senha de teste não aparece em stdout/stderr nem em `executions.error` mesmo quando incluída na mensagem da exceção
- [x] Gate check passes: Full
- [x] Test count: ≥ 7 testes passam

**Tests**: integration
**Gate**: full
**Commit**: `feat(robot): liga runner e entrypoint com códigos de saída`
**Status**: ✅ Concluída (8 testes de integração e 1 unit novos; 32 de integração e 109 unit passam). `runner.run(env, scraper=scrape_with_browser) -> int` (0/1/2) e `__main__.py` (`sys.exit(run(os.environ))`). Fluxo: config (exit 2 sem tocar o banco, log JSON com o nome da variável) → logs com redação → `connect_with_retry` (`DB_CONNECT_TIMEOUT_SECONDS`) → `ensure_schema` → `mark_abandoned` → `start_execution` → scraper → `save_success`; qualquer exceção depois do `start_execution` vira `mark_failed` com `Tipo: mensagem` redigido antes do corte de 2.000 caracteres. Banco inacessível devolve 1 sem criar execução (o teste confirma que `start_execution` e o scraper não são chamados, já que não há banco para consultar). O teste da senha altera temporariamente a senha do usuário do banco de teste para autenticar de verdade e a restaura em `finally`. O teste unit `test_main.py` roda `python -m book_monitor` sem variáveis e confirma exit 2. Spec: CFG-02, CFG-03, CFG-05, DB-05, DB-07 e EDG-04 viram `Implemented`.

---

#### T21: Verificação ponta a ponta local

**What**: Escrever o teste e2e que roda `docker compose run --rm robo` duas vezes contra o site real e valida o "Independent Test" da Spec; executar (exige Docker Desktop ligado).
**Where**: `tests/e2e/test_local_run.py`
**Depends on**: T20
**Reuses**: Compose (T15) e imagem (T13)
**Requirement**: LOC-01, LOC-02, LOC-06, SCR-09, DB-08

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Duas execuções terminam com exit code 0; `executions` tem 2 linhas `SUCCESS` com `items_count == 1000` e `price_history` tem 2.000 linhas; `books` tem 1.000 linhas
- [x] Nenhuma ocorrência do valor de `DB_PASSWORD` na saída das execuções
- [x] Após `docker compose up -d --force-recreate postgres`, as contagens permanecem (DB-08)
- [x] Gate check passes: E2E + Full (se o site divergir de 1.000 itens, a task não é concluída: investigar e reportar)
- [x] Test count: ≥ 3 testes e2e passam

**Tests**: integration (marker `e2e`)
**Gate**: full
**Commit**: `test(e2e): verifica a execução local via Compose de ponta a ponta`
**Status**: ✅ Concluída (3 testes e2e novos; 3 e2e, 32 de integração e 109 unit passam). `tests/e2e/test_local_run.py` usa o projeto Compose isolado `bookmonitor_e2e` (volume próprio, `down -v` ao fim; o volume de desenvolvimento não é tocado), credenciais do `.env` local (o `env_file` do `robo` precisa da mesma senha com que o Postgres foi inicializado) e roda `docker compose run --rm -T robo` duas vezes contra o site real (GETs de leitura, delay de 0,5 s). **Causa do ajuste:** a primeira tentativa falhou (exit 1, `unexpected page structure` já na home) porque a rede corporativa faz inspeção TLS (Netskope) e o container não confia na CA interceptadora (`CERTIFICATE_VERIFY_FAILED: self-signed certificate in certificate chain`); o Chromium mostrava uma página de erro sem o marcador. Não é defeito do robô. O teste lê `E2E_BASE_URL` (padrão: HTTPS do site) e repassa ao robô como `BASE_URL`; as execuções abaixo rodaram com `E2E_BASE_URL=http://books.toscrape.com/`, sem alterar código do robô, Dockerfile nem flags do Chrome. **A validação por HTTPS fica para a T53, na VM** (sem inspeção TLS). Resultado: 2 execuções `SUCCESS` com 1.000 itens, `books` 1.000 e `price_history` 2.000; senha ausente da saída; contagens preservadas após `--force-recreate` do Postgres. **Referência para o orçamento de memória da e2-micro (VM-08)**, máximos sobre as duas execuções: duração 93,2 s e 88,9 s; pico de memória do `robo` 478,5 MiB (`docker stats`, sem cache) e 560,0 MiB (cgroup `memory.peak`, inclui cache de página, igual ao `mem_limit` de 560m e sem OOM); pico do `postgres` 55,8 MiB (`docker stats`) e 135,4 MiB (cgroup, inclui cache), contra o limite de 192m. O `docker stats` amostra a cada ~1-2 s e pode perder picos curtos; o `memory.peak` é o máximo real. Medido no Docker Desktop (WSL2); a e2-micro tem 1 GB de RAM e 2 GB de swap previstos. Spec: LOC-02 e LOC-06 viram `Implemented`; LOC-01, SCR-09 e DB-08 seguem `In progress` (completam em T48, T53 e T54).

---

### Phase 5: Terraform bootstrap (`feat/tf-bootstrap`)

#### T22: Esqueleto da stack bootstrap

**What**: Criar `versions.tf` (`required_version >= 1.9`, provider `google ~> 7.0`) e `providers.tf` (`project = var.project_id`, `user_project_override = true`, `billing_project = var.project_id`), mais uma declaração mínima de `variable "project_id"` em `variables.tf` (o `validate` falha sem ela; a T23 completa o arquivo), e gerar `.terraform.lock.hcl`.
**Where**: `terraform/bootstrap/`
**Depends on**: T21
**Reuses**: Seção Terraform do Design; Context7 para a versão do provider
**Requirement**: TFB-01 (base), TFP-13 (convenção)

**Tools**:

- MCP: `context7` (provider google)
- Skill: NONE

**Done when**:

- [x] `terraform -chdir=terraform/bootstrap init -backend=false` e `validate` passam; `.terraform.lock.hcl` gerado para versionar
- [x] `terraform fmt -check -recursive terraform` passa
- [x] Gate check passes: Infra

**Tests**: none
**Gate**: infra
**Commit**: `feat(tf-bootstrap): adiciona provider e restrições de versão`
**Status**: ✅ Concluída. Gate Infra executado pelo autor (AD-006): `fmt -check` sem saída, `init -backend=false` instalou `hashicorp/google v7.46.2` e gerou o `.terraform.lock.hcl`, `validate` com `Success!`. O `providers.tf` também define `project = var.project_id` (o Design só cita `user_project_override`/`billing_project`) e `variables.tf` traz só a declaração mínima de `project_id`, pois o `validate` falha sem ela; a T23 completa o arquivo. Spec: TFB-01 e TFP-13 seguem `In progress` (completam nas tasks seguintes).

---

#### T23: Variáveis do bootstrap

**What**: Completar `variables.tf` (a T22 já declara `project_id` sem validação, exigido pelo `providers.tf`) com `project_id` (obrigatória, validação de não vazio e formato), `region` (`us-central1`), `bucket_name` (opcional), `force_destroy` (`false`).
**Where**: `terraform/bootstrap/variables.tf`
**Depends on**: T22
**Reuses**: Design (tabela do bootstrap)
**Requirement**: TFB-03, TFB-05

**Tools**:

- MCP: `context7` (`terraform test`, `expect_failures`)
- Skill: NONE

**Done when**:

- [x] Teste `terraform test`: `project_id` vazio ou inválido falha na validação (`expect_failures`) antes de qualquer chamada de API; valor válido passa
- [x] Nenhum valor real de projeto no arquivo
- [x] Gate check passes: Infra
- [x] Test count: ≥ 3 testes (`run` blocks) passam

**Tests**: infra-test
**Gate**: infra
**Commit**: `feat(tf-bootstrap): adiciona variáveis de entrada validadas`
**Status**: ✅ Concluída (8 `run` blocks passam). Gate Infra executado pelo autor (AD-006): `fmt -check` sem saída, `validate` com `Success!`, `terraform test` com `8 passed, 0 failed` (`terraform/bootstrap/tests/variables.tftest.hcl`, com `mock_provider "google"`, sem ADC). Cobertura: padrões e `bucket_name` customizado válidos; `project_id` vazio, com maiúscula, curto e com hífen final falham; `region` fora do Free Tier e `bucket_name` inválido falham. **Adição ao escopo (aprovada explicitamente pelo autor; segue o AD-003):** `region` só aceita `us-central1`, `us-east1` e `us-west1` (regiões do Free Tier do Cloud Storage). Spec: TFB-03 e TFB-05 `Implemented`.

---

#### T24: Bucket do state

**What**: Criar `main.tf` com `google_project_service.storage` (`disable_on_destroy = false`) e `google_storage_bucket.tfstate` (`${project_id}-tfstate` ou `bucket_name`, `US-CENTRAL1`, `STANDARD`, versionamento, acesso uniforme, `public_access_prevention = "enforced"`, `force_destroy = var.force_destroy`, lifecycle que mantém as 5 versões não correntes mais novas).
**Where**: `terraform/bootstrap/main.tf`
**Depends on**: T23
**Reuses**: Design (tabela do bootstrap)
**Requirement**: TFB-01, TFB-02, TFP-13

**Tools**:

- MCP: `context7` (`google_storage_bucket`, lifecycle `num_newer_versions`)
- Skill: NONE

**Done when**:

- [x] `terraform test` (plan com `mock_provider`) afirma: local `US-CENTRAL1`, versionamento ligado, `uniform_bucket_level_access` true, prevenção de acesso público `enforced`, `disable_on_destroy` false, `force_destroy` false por padrão e nome derivado do `project_id`
- [x] O plano contém apenas `google_project_service` e `google_storage_bucket`
- [x] Gate check passes: Infra
- [x] Test count: ≥ 5 asserções em `run` blocks passam

**Tests**: infra-test
**Gate**: infra
**Commit**: `feat(tf-bootstrap): adiciona bucket versionado do tfstate`
**Status**: ✅ Concluída (6 `run` blocks novos, 13 asserções; 14 `run` blocks no total passam). Gate Infra executado pelo autor (AD-006): `fmt -check` sem saída, `validate` com `Success!`, `terraform test` com `14 passed, 0 failed`. Além do `terraform test` (`terraform/bootstrap/tests/main.tftest.hcl`, `mock_provider "google"`), `tests/infra/test_bootstrap_resources.py` (pytest, marker `infra`) garante estaticamente que o bootstrap declara só `google_project_service.storage` e `google_storage_bucket.tfstate`, pois o `terraform test` não enumera os recursos do plano; a confirmação no plano real fica para a T26. **Causa do ajuste:** a primeira execução falhou porque `action` e `condition` de `lifecycle_rule` são sets (não aceitam `[0]`); o teste passou a usar `one(one(lifecycle_rule).action)`. Spec: TFB-01 e TFB-02 seguem `In progress` (validação real na T26); TFP-13 segue `In progress`.

---

#### T25: Outputs do bootstrap

**What**: Criar `outputs.tf` com `bucket_name` e `backend_hcl_snippet` (conteúdo pronto para `backend.hcl`).
**Where**: `terraform/bootstrap/outputs.tf`
**Depends on**: T24
**Reuses**: Design
**Requirement**: TFB-04

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] `terraform test` afirma que `bucket_name` é o nome do bucket e que o snippet contém `bucket = "<nome>"` e `prefix`
- [x] Gate check passes: Infra
- [x] Test count: ≥ 2 asserções passam

**Tests**: infra-test
**Gate**: infra
**Commit**: `feat(tf-bootstrap): expõe nome do bucket e trecho do backend`
**Status**: ✅ Concluída (3 `run` blocks novos, 5 asserções; 17 `run` blocks no total passam). Gate Infra executado pelo autor (AD-006): `fmt -check` sem saída, `validate` com `Success!`, `terraform test` com `17 passed, 0 failed` (`terraform/bootstrap/tests/outputs.tftest.hcl`). O snippet traz `bucket = "<nome>"` e `prefix = "envs/prod"` (o mesmo valor que o `backend.tf` de `envs/prod` fixa; valores iguais não conflitam na configuração parcial). Spec: TFB-04 segue `In progress` (validação real na T26).

---

#### T26: [OPERACIONAL] Plan e apply do bootstrap

**What**: Com `terraform.tfvars` local (gitignored) e ADC: `terraform plan` (somente leitura) mostrado ao autor; **somente com OK explícito**, `terraform apply`; verificar o bucket com `gcloud storage buckets describe`.
**Where**: `terraform/bootstrap/` (execução; nenhum arquivo versionado novo)
**Nota (Context7, provider 7.x; relevante para a T56):** `deletion_policy` do `google_project_service` (padrão `"DELETE"`; aparece no plano da T26) controla se o Terraform pode remover o recurso: `"DELETE"` permite, `"PREVENT"` faz o `destroy`/`apply` falhar, `"ABANDON"` tira do state sem chamar a API. Na rotina de exclusão do provider, a política é checada primeiro e, em seguida, `disable_on_destroy = false` faz o `destroy` apenas remover o recurso do state, sem desabilitar a API (a doc diz: com `false`, o serviço continua habilitado mesmo com `deletion_policy = "DELETE"`). Conclusão: no `destroy` do bootstrap, `storage.googleapis.com` permanece habilitada e o recurso some só do state; é o comportamento desejado (AD-003). O `google_storage_bucket` também tem `deletion_policy = "DELETE"` no plano, mas com `force_destroy = false` o `destroy` falha se o bucket tiver objetos (o state de `envs/prod` e suas versões): na T56, aplicar antes `force_destroy = true` (variável) e só então destruir, como prevê `docs/destroy.md`.
**Execução**: pelo autor (AD-006). O agente orienta a criação do `terraform.tfvars` local (`project_id = "book-price-monitor-jc"`), fornece os comandos de `plan`/`apply`/`output` e `gcloud`, explica cada um e analisa a saída colada; o `apply` só após a revisão do plano pelo autor.
**Depends on**: T25
**Reuses**: ADC e `billing_project` configurados (PRD §11)
**Requirement**: TFB-01, TFB-02, TFB-04 (validação real)

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Plano mostrado e aprovado pelo autor; plano contém exatamente 2 recursos (API Storage e bucket)
- [x] Após o apply: bucket em `US-CENTRAL1`, versionamento habilitado, acesso público bloqueado (saída do `gcloud` registrada); `terraform output` entrega o nome do bucket
- [x] `backend.hcl` real criado localmente (gitignored) a partir do snippet
- [x] Conclusão marcada em `tasks.md` e commit próprio contendo somente esse arquivo (mensagem abaixo)

**Tests**: none
**Gate**: infra
**Commit**: `docs(tasks): registra apply do bootstrap (T26)` (só `tasks.md`, na própria branch da fase, antes do merge)
**Status**: ✅ Concluída (2026-11-03/04, executada pelo autor, AD-006). **Plano** (`terraform plan "-out=bootstrap.tfplan"`; as aspas são necessárias no PowerShell 5.1): `Plan: 2 to add, 0 to change, 0 to destroy` (`google_project_service.storage` e `google_storage_bucket.tfstate`), revisado e aprovado pelo autor. **Apply** (`terraform apply "bootstrap.tfplan"`): `Apply complete! Resources: 2 added, 0 changed, 0 destroyed` (API em 4 s, bucket em 3 s); `state list` mostra os 2 recursos; `output -raw bucket_name` = `book-price-monitor-jc-tfstate`. **Evidência do `gcloud storage buckets describe`:** `location: US-CENTRAL1` (`location_type: region`), `default_storage_class: STANDARD`, `versioning_enabled: true`, `uniform_bucket_level_access: true`, `public_access_prevention: enforced`, `lifecycle_config` = `Delete` com `isLive: false` e `numNewerVersions: 5`, `soft_delete_policy.retentionDurationSeconds: '604800'` (7 dias, padrão do provider 7.x). `gcloud services list --enabled` lista `storage.googleapis.com`. **`backend.hcl`** criado em `terraform/envs/prod/backend.hcl` (`Set-Content -Encoding ascii`, para evitar UTF-16 do `>` do PowerShell 5.1), ignorado pelo git (`.gitignore:34`). O `terraform.tfstate` do bootstrap é local (`terraform/bootstrap/`, ignorado) e não pode ser apagado: o `destroy` da T56 depende dele. Gate de fase (Build): Quick (109 unit, ruff) + pytest `-m infra` (1) + Infra (`fmt -check`, `validate`, `terraform test` 17 passam, executados pelo autor). Spec: TFB-01, TFB-02 e TFB-04 `Implemented`; TFP-13 segue `In progress` (T27, T37, T39).

---

### Phase 6: Terraform base modules (`feat/tf-modules-base`)

#### T27: Módulo `apis`

**What**: Criar o módulo com `google_project_service` via `for_each`, `disable_on_destroy = false` e `disable_dependent_services = false`; output `services`.
**Where**: `terraform/modules/apis/`
**Depends on**: T26
**Reuses**: Design (tabela de módulos)
**Requirement**: TFP-01, TFP-12, TFP-13

**Tools**:

- MCP: `context7` (`google_project_service`)
- Skill: NONE

**Done when**:

- [x] `terraform test`: uma instância por serviço informado, todas com `disable_on_destroy == false` e `disable_dependent_services == false`
- [x] Gate check passes: Infra
- [x] Test count: ≥ 3 asserções passam

**Tests**: infra-test
**Gate**: infra
**Commit**: `feat(tf-modules): adiciona módulo apis`
**Status**: ✅ Concluída (4 `run` blocks, 7 asserções). Gate Infra executado pelo autor (AD-006): `fmt -check` sem saída, `init -backend=false` (provider `google` v7.46.2, `.terraform.lock.hcl` gerado), `validate` com `Success!`, `terraform test` com `4 passed, 0 failed` (`terraform/modules/apis/tests/main.tftest.hcl`, `mock_provider "google"`). Cobertura: uma instância por serviço indexada pelo nome da API, `project` repassado, `disable_on_destroy` e `disable_dependent_services` falsos em todas, output `services` igual à entrada, caso de um único serviço. Spec: TFP-01 e TFP-12 `In progress` (módulos restantes e `envs/prod`); TFP-13 segue `In progress` (T37, T39).

---

#### T28: Módulo `network`

**What**: Criar VPC customizada, subnet `10.10.0.0/24` e firewall ingress `tcp:22` de `allowed_ssh_cidr` para a tag `book-monitor`, com validação de CIDR.
**Where**: `terraform/modules/network/`
**Depends on**: T27
**Reuses**: Design
**Requirement**: TFP-03, TFP-04, TFP-05, TFP-12

**Tools**:

- MCP: `context7` (`google_compute_firewall`)
- Skill: NONE

**Done when**:

- [x] `terraform test`: `auto_create_subnetworks == false`, região `us-central1`, regra permite só `tcp` porta `22` com `source_ranges == [allowed_ssh_cidr]` e `target_tags` correta
- [x] `allowed_ssh_cidr = "0.0.0.0/0"` e CIDR malformado falham na validação (`expect_failures`)
- [x] **Adição ao escopo (aprovada explicitamente pelo autor):** terceira `validation` em `allowed_ssh_cidr` exige prefixo `/24` ou mais específico; `10.0.0.0/8` falha (`expect_failures`) e `/24` e `/32` passam
- [x] Gate check passes: Infra
- [x] Test count: ≥ 5 asserções passam

**Tests**: infra-test
**Gate**: infra
**Commit**: `feat(tf-modules): adiciona módulo network com SSH restrito`
**Status**: ✅ Concluída (9 `run` blocks: 11 asserções e 4 `expect_failures`). Gate Infra executado pelo autor (AD-006): `fmt -check` sem saída, `init -backend=false` (provider `google` v7.46.2, `.terraform.lock.hcl` gerado), `validate` com `Success!`, `terraform test` com `9 passed, 0 failed` (`terraform/modules/network/tests/main.tftest.hcl`, `mock_provider "google"`). Cobertura: VPC custom, sub-rede `10.10.0.0/24` em `us-central1`, firewall INGRESS só `tcp:22` com `source_ranges == [allowed_ssh_cidr]` e `target_tags == [book-monitor]`, output `network_tag`; `0.0.0.0/0`, `abc`, `/33` e `/8` falham na validação; `/24` e `/32` passam. **Adição ao escopo (aprovada explicitamente pelo autor):** terceira `validation` exige prefixo ≥ `/24`, com `try()` para valores sem `/`. A ausência de NAT, LB e IP estático não é verificada por `terraform test`; fica para o pytest estático de `envs/prod`. Spec: TFP-03, TFP-04 e TFP-05 `In progress` (composição em `envs/prod`: T38, T39, T51); TFP-12 segue `In progress`.

---

#### T29: Módulo `identity`

**What**: Criar `google_service_account` dedicada, sem nenhum binding de IAM e sem chave.
**Where**: `terraform/modules/identity/`
**Depends on**: T28
**Reuses**: Design
**Requirement**: TFP-06, TFP-12

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] `terraform test`: o plano contém a SA e nenhum recurso `google_*_iam_*` nem `google_service_account_key`; output `email` presente
- [x] Gate check passes: Infra
- [x] Test count: ≥ 3 asserções passam

**Tests**: infra-test
**Gate**: infra
**Commit**: `feat(tf-modules): adiciona módulo identity com service account sem chave`
**Status**: ✅ Concluída (3 `run` blocks, 4 asserções). Gate Infra executado pelo autor (AD-006): `fmt -check` sem saída, `init -backend=false` (provider `google` v7.46.2, `.terraform.lock.hcl` gerado), `validate` com `Success!`, `terraform test` com `3 passed, 0 failed` (`terraform/modules/identity/tests/main.tftest.hcl`, `mock_provider "google"`). `tests/infra/test_identity_resources.py` (pytest, marker `infra`, 2 testes `infra` no total) garante estaticamente que o módulo declara só `google_service_account.this`, sem `google_*_iam_*` nem `google_service_account_key` (o `terraform test` não enumera recursos do plano). **Causa do ajuste:** a primeira execução do `email_output` falhou com `Unknown condition value`, pois `override_resource` só vale no apply por padrão; o teste passou a usar `override_during = plan`. Spec: TFP-06 `In progress` (composição em `envs/prod`: T39, T51); TFP-12 segue `In progress`.

---

#### T30: Módulo `budget`

**What**: Criar `google_billing_budget` filtrado pelo projeto (`data.google_project` → número), `specified_amount` de 5 BRL e `threshold_rules` 0.5/0.9/1.0, sem `all_updates_rule`.
**Where**: `terraform/modules/budget/`
**Depends on**: T29
**Reuses**: Design (seção Budget por e-mail); Context7 para `google_billing_budget`
**Requirement**: TFP-09, TFP-12

**Tools**:

- MCP: `context7` (`google_billing_budget`)
- Skill: NONE

**Done when**:

- [x] `terraform test`: `currency_code == "BRL"`, `units == "5"`, exatamente 3 thresholds (0.5, 0.9, 1.0), filtro por `projects/<número>`, ausência de `all_updates_rule` e de qualquer recurso Pub/Sub/Monitoring
- [x] Gate check passes: Infra
- [x] Test count: ≥ 5 asserções passam

**Tests**: infra-test
**Gate**: infra
**Commit**: `feat(tf-modules): adiciona módulo budget`
**Status**: ✅ Concluída (6 `run` blocks, 11 asserções). Gate Infra executado pelo autor (AD-006): `fmt -check` sem saída, `init -backend=false` (provider `google` v7.46.2, `.terraform.lock.hcl` gerado), `validate` com `Success!`, `terraform test` com `6 passed, 0 failed` (`terraform/modules/budget/tests/main.tftest.hcl`, `mock_provider "google"`, `override_data` com `override_during = plan` para o número do projeto). `tests/infra/test_budget_resources.py` (pytest, marker `infra`) garante estaticamente que o módulo declara só `google_billing_budget.this` (sem Pub/Sub nem Monitoring) e que `all_updates_rule` não aparece no código. Spec: TFP-09 `In progress` (composição em `envs/prod` e confirmação real do e-mail: T39, T51, T55); TFP-12 segue `In progress`. **Gate Build da Fase 6** (Quick: 109 unit e ruff limpo; `pytest -m infra`: 4; Infra dos 4 módulos e `fmt -check` executados pelo autor, todos verdes): fase concluída.

---

### Phase 7: Terraform compute VM (`feat/tf-compute-vm`)

#### T31: Variáveis e guardas do `compute_vm`

**What**: Criar `variables.tf` do módulo com as entradas do Design e validações de Free Tier (`machine_type == "e2-micro"`, `boot_disk_size_gb <= 30`, zona em `us-central1-`/`us-east1-`/`us-west1-`), `db_password` com `sensitive = true`.
**Where**: `terraform/modules/compute_vm/variables.tf`
**Depends on**: T30
**Reuses**: Design (tabela do módulo e guardas)
**Requirement**: TFP-07, TFP-10, TFP-12

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] `terraform test` com `expect_failures`: `machine_type = "e2-small"`, `boot_disk_size_gb = 31` e zona `europe-west1-b` falham; valores válidos passam
- [x] `db_password` marcada `sensitive`
- [x] Gate check passes: Infra
- [x] Test count: ≥ 5 `run` blocks passam

**Tests**: infra-test
**Gate**: infra
**Commit**: `feat(tf-modules): adiciona entradas do compute_vm com guardas do Free Tier`
**Status**: ✅ Concluída (6 `run` blocks). Gate Infra executado pelo autor (AD-006): `fmt -check` sem saída, `init -backend=false` (provider `google` v7.46.2, `.terraform.lock.hcl` gerado), `validate` com `Success!`, `terraform test` com `6 passed, 0 failed` (`terraform/modules/compute_vm/tests/main.tftest.hcl`, `mock_provider "google"`). `tests/infra/test_compute_vm_variables.py` (pytest, marker `infra`; 6 passam no total) garante `db_password` com `sensitive = true` e sem `default`. Além das variáveis do Design, o módulo declara `machine_type` (padrão e fixo `e2-micro`, exigido pela guarda da task). O `ssh_command` (T36) usará `google_compute_instance.this.project`, sem variável `project_id`. Spec: TFP-07 e TFP-10 `In progress` (T35, T38, T39, T41, T51); TFP-12 segue `In progress`. **Adição ao escopo aprovada pelo autor (após a T33):** `db_password` ganhou duas `validation` (somente `[A-Za-z0-9_.-]` e no mínimo 16 caracteres), porque o Compose altera `$`, `#`, aspas, espaço e `\` ao ler o `.env` e o banco subiria com senha diferente da do Terraform; +3 `run` blocks (senha válida, caractere proibido `$`, senha curta) e a senha de teste das variáveis globais passou a `Senha-De-Teste_1234`.

---

#### T32: Startup script, parte 1 (swap, pacotes, Docker) e harness de renderização

**What**: Criar `startup.sh.tftpl` com `set -euo pipefail`, log em `/var/log/book-monitor-startup.log`, swap file condicional + `fstab` + `vm.swappiness` em `/etc/sysctl.d`, instalação condicional de `git cron logrotate curl ca-certificates` e Docker CE + plugin Compose; criar `locals.tf` que renderiza o template (`local.startup_script`) e o mecanismo de renderização (aprovado, respeita o AD-006): (1) camada `terraform test` (`mock_provider`), com asserções sobre `local.startup_script`, rodada pelo autor; (2) config mínima `tests/render/main.tf` (sem provider, só `templatefile` com valores fixos e `output "script"`) que o autor executa (`init`, `apply -auto-approve`, `output -json script | Set-Content -Encoding ascii .rendered-startup.json`, a partir da raiz); o pytest (`tests/infra/test_startup_script.py`, marker `infra`) lê o JSON, grava o script em arquivo temporário, roda `bash -n` com o bash do Git (`C:\Program Files\Git\usr\bin\bash.exe`; nunca o `System32\bash.exe` do WSL) e faz as asserções estáticas. O JSON renderizado e o state do `render/` ficam no `.gitignore`. O pytest compara o `mtime` do JSON com o do `.tftpl` e falha se o JSON estiver mais velho; sem o JSON, dá `skip` com mensagem indicando os comandos. Um teste estático confere que as chaves passadas ao `templatefile` em `locals.tf` e em `render/main.tf` são as mesmas.
**Where**: `terraform/modules/compute_vm/startup.sh.tftpl`, `locals.tf`, `tests/render/main.tf`, `tests/main.tftest.hcl`, `tests/infra/test_startup_script.py`, `.gitignore`
**Depends on**: T31
**Reuses**: Passos 1-3 do Design (startup script)
**Requirement**: VM-02, VM-01 (parcial)

**Tools**:

- MCP: `context7` (Docker apt repository oficial para Debian 12)
- Skill: NONE

**Done when**:

- [x] Script renderizado passa em `bash -n`; swap só é criado se `/swapfile` não estiver ativo; swap e sysctl aparecem antes de qualquer `docker`
- [x] Texto renderizado não contém senha nem placeholder de segredo
- [x] Gate check passes: Infra (inclui `pytest -m infra` com o teste de renderização PASSANDO; `skip` = gate não cumprido)
- [x] Test count: ≥ 5 testes passam

**Tests**: infra-test
**Gate**: infra
**Commit**: `feat(tf-compute-vm): adiciona swap e instalação do Docker ao startup script`
**Status**: ✅ Concluída (4 `run` blocks novos, 10 no `terraform test`; 10 testes novos em `tests/infra/test_startup_script.py`, 16 no `pytest -m infra`, todos PASSANDO, 0 skip). Gate Infra executado pelo autor (AD-006): `fmt -check` sem saída, `validate` com `Success!`, `terraform test` com `10 passed, 0 failed`, renderização (`init`, `apply -auto-approve` com 0 recursos, `output -json script | Set-Content -Encoding ascii .rendered-startup.json`; arquivo ignorado pelo git). `bash -n` com o bash do Git sobre o script renderizado: OK. `locals.tf` já passa as 6 chaves do template (`swap_size_mb`, `repo_url`, `repo_ref`, `db_name`, `db_user`, `cron_schedule`) para as T33/T34 não alterarem a assinatura; `tests/render/main.tf` usa as mesmas. O template é só ASCII (o `Set-Content -Encoding ascii` trocaria acentos por `?`). Quick: 109 unit, ruff limpo. Spec: VM-02 e VM-01 `In progress` (T33, T52).
**Ajuste do mecanismo de renderização (aprovado pelo autor, feito na Fase 8, commit `test(tf-compute-vm)`)**: a checagem de data (`mtime`) do `.rendered-startup.json` invalidava o JSON a cada troca de branch. Agora `tests/render/main.tf` expõe também `template_sha256` (`filesha256` do `startup.sh.tftpl`), o autor grava `terraform output -json` (todos os outputs, formato `{"script": {"value": ...}, "template_sha256": {"value": ...}}`) e o pytest compara o hash com o SHA-256 do template atual: só uma mudança real no conteúdo do template invalida o JSON. JSON ausente continua sendo `skip` (gate não cumprido); JSON em formato antigo ou com hash diferente falha com a dica de regeneração. 3 testes novos (hash igual aceito, hash diferente reprova, formato antigo reprova).

---

#### T33: Startup script, parte 2 (código, `.env`, build)

**What**: Estender o template: clone/atualização sob `flock` (`git clone --depth 1 --branch`, ou `fetch` + `reset --hard FETCH_HEAD` com falha tolerada se há checkout), `.env` criado só se ausente a partir da metadata `book-db-password` (chmod 600), `docker compose build`, `docker image prune -f`, `up -d postgres` e espera pelo healthcheck.
**Where**: `terraform/modules/compute_vm/startup.sh.tftpl` (modify)
**Depends on**: T32
**Reuses**: Passos 4-6 do Design
**Requirement**: VM-01, VM-05, VM-09, VM-10

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Renderizado (reexecutado pelo autor) passa em `bash -n`; asserções estáticas no pytest e no `terraform test` (`local.startup_script`): `.env` só é criado sob `[ ! -f ]`, senha lida do endpoint de metadata com cabeçalho `Metadata-Flavor: Google` e nunca embutida no texto, `chmod 600`, falha de `git fetch` com checkout existente apenas registra e segue
- [x] `repo_url` e `repo_ref` do template aparecem no clone; `build` ocorre antes de `up -d postgres`
- [x] Gate check passes: Infra (renderização reexecutada; teste de renderização PASSANDO, `skip` = gate não cumprido)
- [x] Test count: ≥ 6 testes passam

**Tests**: infra-test
**Gate**: infra
**Commit**: `feat(tf-compute-vm): adiciona sincronização do código, .env e build ao startup script`
**Status**: ✅ Concluída (3 `run` blocks novos; 16 no `terraform test`; 6 testes novos em `tests/infra/test_startup_script.py`, 22 no `pytest -m infra`, todos PASSANDO, 0 skip). Gate Infra executado pelo autor (AD-006): `fmt -check` sem saída, `validate` com `Success!`, `terraform test` com `16 passed, 0 failed`, renderização reexecutada (`apply -auto-approve` com 0 recursos e `output -json script` gravado em `.rendered-startup.json`). Clone/atualização sob `flock -w 900 9` (`fetch` falho com checkout existente só registra); `.env` só sob `[ ! -f "$ENV_FILE" ]`, com `umask 077` e `chmod 600`; a senha é lida da metadata (`Metadata-Flavor: Google`) em `DB_PASSWORD_VALUE=$(curl ...)` antes de qualquer escrita no `.env` (teste garante a ordem; falha do `curl` com `set -e` não deixa `.env` vazio); `build` -> `prune` -> `up -d --wait --wait-timeout 180 postgres`. Adição ao escopo da T31 aprovada pelo autor: validação de `db_password` (ver T31). Quick: 109 unit, ruff limpo. Spec: VM-01, VM-05, VM-09 e VM-10 `In progress` (T34, T52, T54).

---

#### T34: Startup script, parte 3 (cron e logrotate)

**What**: Estender o template: `/etc/cron.d/book-monitor` sobrescrito (`>`) com `${cron_schedule} root flock -n /var/lock/book-monitor.lock docker compose -f /opt/book-monitor/docker-compose.yml run --rm -T robo >> /var/log/book-monitor/run.log 2>&1`, diretório de log e `/etc/logrotate.d/book-monitor` (`daily`, `rotate 7`, `compress`, `copytruncate`, `missingok`).
**Where**: `terraform/modules/compute_vm/startup.sh.tftpl` (modify)
**Depends on**: T33
**Reuses**: Passos 7-8 do Design
**Requirement**: VM-03, VM-04, VM-05, VM-07

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Renderizado (reexecutado pelo autor) passa em `bash -n`; exatamente uma linha de cron, escrita por sobrescrita; `flock -n` presente; `cron_schedule` padrão `0 6 * * *`
- [x] Logrotate contém `daily` e `rotate 7`
- [x] Gate check passes: Infra (renderização reexecutada; teste de renderização PASSANDO, `skip` = gate não cumprido)
- [x] Test count: ≥ 5 testes passam

**Tests**: infra-test
**Gate**: infra
**Commit**: `feat(tf-compute-vm): adiciona cron e rotação de logs ao startup script`
**Status**: ✅ Concluída (3 `run` blocks novos; 19 no `terraform test`; 4 testes novos em `tests/infra/test_startup_script.py`, 26 no `pytest -m infra`, todos PASSANDO, 0 skip). Gate Infra executado pelo autor (AD-006): `fmt -check` sem saída, `validate` com `Success!`, `terraform test` com `19 passed, 0 failed`, renderização reexecutada (0 recursos; `.rendered-startup.json` regerado). `/etc/cron.d/book-monitor` sobrescrito com `cat >` (heredoc `'CRON'`, uma só linha, `chmod 644`), `flock -n /var/lock/book-monitor.lock`, saída em `/var/log/book-monitor/run.log`; `cron_schedule` padrão `0 6 * * *`. `/etc/logrotate.d/book-monitor` com `daily`, `rotate 7`, `compress`, `copytruncate`, `missingok`. Cron e logrotate vêm depois do `up -d --wait postgres`. Quick: 109 unit, ruff limpo. Spec: VM-03, VM-04, VM-05 e VM-07 `In progress` (T52, T54).

---

#### T35: Recurso da VM

**What**: Criar `main.tf` com `google_compute_instance` (`e2-micro`, `debian-cloud/debian-12`, boot `pd-standard`, `access_config {}` efêmero, não-preemptível, `shielded_instance_config`, `deletion_protection = false`, tag de rede, SA anexada, metadata `startup-script` e `book-db-password`).
**Where**: `terraform/modules/compute_vm/main.tf`
**Depends on**: T34
**Reuses**: `local.startup_script` (T32), variáveis (T31)
**Requirement**: TFP-07, TFP-08, TFP-12

**Tools**:

- MCP: `context7` (`google_compute_instance`)
- Skill: NONE

**Done when**:

- [x] `terraform test`: `machine_type == "e2-micro"`, `scheduling.preemptible == false`, disco `pd-standard` ≤ 30 GB, imagem Debian 12, IP externo efêmero (sem `nat_ip`), metadata contém `startup-script` e `book-db-password`
- [x] O plano contém apenas a instância (nenhum disco extra, IP estático, snapshot ou NAT)
- [x] Gate check passes: Infra
- [x] Test count: ≥ 7 asserções passam

**Tests**: infra-test
**Gate**: infra
**Commit**: `feat(tf-compute-vm): adiciona instância e2-micro dentro do Free Tier`
**Status**: ✅ Concluída (6 `run` blocks novos com 18 asserções; 25 no `terraform test`; `tests/infra/test_compute_vm_resources.py` com 6 testes, 32 no `pytest -m infra`). Gate Infra executado pelo autor (AD-006): `fmt -check` sem saída, `validate` com `Success!`, `terraform test` com `25 passed, 0 failed` (a renderização do startup script não mudou). `google_compute_instance.this` (`book-monitor`): `e2-micro`, `debian-cloud/debian-12`, boot `pd-standard` com `boot_disk_size_gb`, `access_config {}` (IP efêmero), `scheduling` `preemptible = false`/`MIGRATE`/`STANDARD`, `shielded_instance_config` completo, SA anexada (escopo `cloud-platform`; a SA não tem roles), metadata só com `startup-script` e `book-db-password`. A lista fechada de recursos (só a instância; sem `nat_ip`, `attached_disk`, `scratch_disk`, `google_compute_address`, `snapshot`) é garantida por pytest estático, pois o `terraform test` não enumera o plano (achado da Fase 5). O nome `book-monitor` é um `local` (o Design não lista `instance_name` como entrada). Quick: 109 unit, ruff limpo. Spec: TFP-07 e TFP-08 `In progress` (composição e plan real: T39, T41, T51); TFP-12 segue `In progress`.

---

#### T36: Outputs do `compute_vm`

**What**: Criar `outputs.tf` com `instance_name`, `zone` e `ssh_command` (`gcloud compute ssh <vm> --zone <zone> --project <id>`).
**Where**: `terraform/modules/compute_vm/outputs.tf`
**Depends on**: T35
**Reuses**: Design
**Requirement**: TFP-11, TFP-12

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] `terraform test` afirma o texto exato do comando `gcloud compute ssh`
- [x] Gate check passes: Infra (fase completa: `fmt`, `validate`, `test`, `pytest -m infra`)
- [x] Test count: ≥ 2 asserções passam

**Tests**: infra-test
**Gate**: infra
**Commit**: `feat(tf-compute-vm): expõe nome da instância, zona e comando SSH`
**Status**: ✅ Concluída (2 `run` blocks novos, 3 asserções; 27 no `terraform test` do `compute_vm`). `outputs.tf` com `instance_name`, `zone` e `ssh_command` (`gcloud compute ssh <vm> --zone <zone> --project <id>`, com o project vindo de `google_compute_instance.this.project`, sem variável nova); os testes usam `override_resource` com `override_during = plan` para o `project` e afirmam o texto exato. Spec: TFP-11 `In progress` (T40, T51); TFP-12 segue `In progress` (T39, T49). **Gate Build da Fase 7** (Quick: 109 unit e ruff limpo; `pytest -m infra`: 32, 0 skip; executado pelo autor: `fmt -check -recursive terraform` sem saída e `validate` + `test` verdes nos 5 módulos e no bootstrap: compute_vm 27, apis 4, network 9, identity 3, budget 6, bootstrap 17): fase concluída.

---

### Phase 8: Terraform prod (`feat/tf-prod`)

#### T37: Esqueleto de `envs/prod`

**What**: Criar `versions.tf`, `providers.tf` (`user_project_override`, `billing_project`), `backend.tf` (`backend "gcs" { prefix = "envs/prod" }`, bucket por configuração parcial) e um `variables.tf` mínimo só com `project_id` (o `providers.tf` o referencia; mesmo precedente da T22). A T38 completa o arquivo.
**Where**: `terraform/envs/prod/` (`versions.tf`, `providers.tf`, `backend.tf`, `variables.tf`)
**Depends on**: T36
**Reuses**: Esqueleto do bootstrap (T22)
**Requirement**: TFP-02, TFP-13 (convenção)

**Tools**:

- MCP: `context7` (backend gcs, configuração parcial)
- Skill: NONE

**Done when**:

- [x] `terraform -chdir=terraform/envs/prod init -backend=false` e `validate` passam; o bloco `backend "gcs"` não contém `bucket` nem variáveis
- [x] `.terraform.lock.hcl` gerado para versionar
- [x] Gate check passes: Infra

**Tests**: none
**Gate**: infra
**Commit**: `feat(tf-prod): adiciona providers e backend gcs parcial`
**Status**: ✅ Concluída. Gate Infra executado pelo autor (AD-006): `fmt -check -recursive terraform` sem saída, `init -backend=false` com `successfully initialized` (`hashicorp/google v7.46.2`, lock gerado) e `validate` com `Success!`. Arquivos em `terraform/envs/prod/`: `versions.tf`, `providers.tf` (`user_project_override`, `billing_project`), `backend.tf` (`backend "gcs"` só com `prefix = "envs/prod"`, sem `bucket`) e `variables.tf` mínimo com `project_id` (precedente da T22; a T38 completa). **Evidência antecipada da T42** (o autor rodou `init "-backend-config=backend.hcl"` na T37; sem `plan` nem `apply`): `Successfully configured the backend "gcs"!`, o que confirma ADC, `backend.hcl` real e acesso ao bucket do state pela rede corporativa (inspeção TLS) sem erro de certificado. O `plan` real segue pendente na T42. Spec: TFP-02 `In progress` (T41, T42); TFP-13 segue `In progress` (T39).

---

#### T38: Variáveis de `envs/prod`

**What**: Completar o `variables.tf` (já criado na T37 só com `project_id`) acrescentando `billing_account_id`, `allowed_ssh_cidr`, `repo_url`, `repo_ref` (`main`), `db_name`, `db_user`, `db_password` (`sensitive`), `cron_schedule`, `swap_size_mb` e demais padrões do Design.
**Where**: `terraform/envs/prod/variables.tf`
**Depends on**: T37
**Reuses**: Variáveis dos módulos
**Requirement**: TFP-10, TFP-05

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] `terraform test`: `allowed_ssh_cidr = "0.0.0.0/0"` falha; `db_password` é `sensitive`; faltando `project_id`/`billing_account_id` não há valor padrão
- [x] Gate check passes: Infra
- [x] Test count: ≥ 3 `run` blocks passam

**Tests**: infra-test
**Gate**: infra
**Commit**: `feat(tf-prod): adiciona variáveis de entrada com validações`
**Status**: ✅ Concluída (11 `run` blocks em `terraform/envs/prod/tests/variables.tftest.hcl`; 6 testes em `tests/infra/test_prod_variables.py`). Gate Infra executado pelo autor (AD-006): `fmt -check -recursive terraform` sem saída, `validate` com `Success!` e `terraform test` com `11 passed, 0 failed` (o `init -backend=false` não foi repetido: o `.terraform` da T37 já tinha o provider). `variables.tf` completo: `project_id`, `billing_account_id` (formato `XXXXXX-XXXXXX-XXXXXX`), `region` e `zone` (Free Tier; a zona deve pertencer à região), `allowed_ssh_cidr` (CIDR válido, não `0.0.0.0/0`, prefixo ≥ /24), `repo_url` (HTTPS), `repo_ref` (`main`), `db_name`, `db_user`, `db_password` (`sensitive`; `[A-Za-z0-9_.-]`, mínimo 16), `cron_schedule`, `swap_size_mb`, `boot_disk_size_gb` (≤ 30). Sem `budget_alert_email` (o módulo `budget` usa os destinatários IAM da conta de faturamento, T30). `issensitive(var.db_password)` funciona em `assert`. As variáveis sem `default` (`project_id`, `billing_account_id`, `allowed_ssh_cidr`, `repo_url`, `db_password`) e o `sensitive` são garantidos também por pytest estático (o `terraform test` não enumera "sem default"). Quick: ruff limpo; `pytest` do arquivo novo com 6 passed. Spec: TFP-05 e TFP-10 seguem `In progress` (T41, T51 para o TFP-10; validação real na T42).

---

#### T39: Composição dos módulos

**What**: Criar `main.tf` compondo `apis` (compute, iam, billingbudgets) → `network`, `identity`, `compute_vm`, `budget`, com `depends_on = [module.apis]`.
**Where**: `terraform/envs/prod/main.tf`
**Depends on**: T38
**Reuses**: Módulos das fases 6 e 7
**Requirement**: TFP-01, TFP-03, TFP-04, TFP-06, TFP-07, TFP-08, TFP-09, TFP-12, TFP-13

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] `terraform test` sobre o plano com `mock_provider`: conjunto de tipos de recurso é exatamente {`google_project_service`, `google_compute_network`, `google_compute_subnetwork`, `google_compute_firewall`, `google_service_account`, `google_compute_instance`, `google_billing_budget`} (lista fechada; qualquer NAT, LB, IP estático, snapshot, Cloud SQL, Pub/Sub, Artifact Registry ou Secret Manager reprova)
- [x] Exatamente 1 instância; as 3 APIs; todas com `disable_on_destroy == false`
- [x] Gate check passes: Infra
- [x] Test count: ≥ 6 asserções passam

**Tests**: infra-test
**Gate**: infra
**Commit**: `feat(tf-prod): compõe os módulos no ambiente prod`
**Status**: ✅ Concluída (4 `run` blocks novos com 5 asserções em `terraform/envs/prod/tests/main.tftest.hcl`; 15 no `terraform test` do `envs/prod`; 18 testes em `tests/infra/test_prod_composition.py`). Gate Infra executado pelo autor (AD-006): `fmt -check -recursive terraform` sem saída, `init -backend=false` (5 módulos locais e provider v7.46.2), `validate` com `Success!` e `terraform test` com `15 passed, 0 failed`. `main.tf` compõe `apis` (compute, iam, billingbudgets) e, com `depends_on = [module.apis]`, `network`, `identity`, `compute_vm` (recebe `subnetwork`, `network_tag` e `email` das saídas) e `budget`; nenhum recurso no próprio `envs/prod`. Como o `terraform test` não enumera o plano (achado da Fase 5), a lista fechada de 7 tipos, os 8 tipos proibidos, a instância única (sem `count`/`for_each`), as 3 APIs, o `disable_on_destroy = false` e o `depends_on` são garantidos por pytest estático; o `terraform test` cobre as APIs, o nome/zona da VM e a tag de rede por saídas dos módulos. `override_data` em `module.budget.data.google_project.this` (`override_during = plan`) funciona em módulo filho. O `init -backend=false` desta task desfez o backend GCS da T37: a T42 repete o `init "-backend-config=backend.hcl"`. Quick: 109 unit, ruff limpo. Spec: sem mudança de status (TFP-01, 03, 04, 06, 07, 08, 09, 12 e 13 seguem `In progress`; completam nas tasks operacionais T42, T51 e T55).

---

#### T40: Outputs de `envs/prod`

**What**: Criar `outputs.tf` com `instance_name`, `zone` e `ssh_command`.
**Where**: `terraform/envs/prod/outputs.tf`
**Depends on**: T39
**Reuses**: Outputs do `compute_vm`
**Requirement**: TFP-11

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] `terraform test` afirma os três outputs e o texto do `ssh_command`
- [x] Gate check passes: Infra
- [x] Test count: ≥ 2 asserções passam

**Tests**: infra-test
**Gate**: infra
**Commit**: `feat(tf-prod): expõe comando SSH e outputs da instância`
**Status**: ✅ Concluída (2 `run` blocks novos com 4 asserções em `terraform/envs/prod/tests/outputs.tftest.hcl`; 17 `run` blocks no `terraform test` do `envs/prod`). Gate Infra executado pelo autor (AD-006): `fmt -check -recursive terraform` sem saída, `validate` com `Success!` e `terraform test` com `17 passed, 0 failed`. `outputs.tf` repassa `instance_name`, `zone` e `ssh_command` do módulo `compute_vm`; o teste afirma o texto exato `gcloud compute ssh book-monitor --zone us-central1-a --project projeto-teste-123` e que o comando segue a zona informada (`us-east1-b`). `override_resource` em escopo de arquivo sobre `module.compute_vm.google_compute_instance.this` (`override_during = plan`) simula o `project` computado; `override_data` do budget como na T39. Sem pytest novo nesta task. Spec: TFP-11 segue `In progress` (T51).

---

#### T41: Exemplos de configuração e higiene do repositório

**What**: Criar `terraform.tfvars.example` e `backend.hcl.example` (só placeholders) e o teste de higiene que lista `git ls-files` e reprova `.env`, `*.tfvars`, `backend.hcl`, `*.tfstate`, chaves JSON de service account.
**Where**: `terraform/envs/prod/`
**Depends on**: T40
**Reuses**: `.gitignore` já versionado
**Requirement**: TFP-02, TFP-10, OPS-05

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Os `.example` não contêm valores reais (placeholders como `your-project-id`, `change-me`) e cobrem todas as variáveis obrigatórias
- [x] Teste de higiene falha se um arquivo proibido estiver rastreado (cenário positivo e negativo com lista sintética) e passa no repositório atual
- [x] Gate check passes: Quick + Infra
- [x] Test count: ≥ 4 testes passam

**Tests**: unit
**Gate**: quick
**Commit**: `chore(tf-prod): adiciona exemplos de tfvars e backend com teste de higiene do repositório`
**Status**: ✅ Concluída (6 testes em `tests/unit/test_repo_hygiene.py`). Gate: Quick com 115 passed (109 + 6), ruff limpo, `pytest -m infra` com 59 passed (0 skip) e `terraform fmt -check -recursive terraform` executado pelo autor (AD-006) sem saída. `terraform.tfvars.example` (só placeholders; opcionais comentados; `db_password` fora do arquivo, com a orientação de `$env:TF_VAR_db_password`) e `backend.hcl.example` (`bucket = "your-project-id-tfstate"`, `prefix = "envs/prod"`). O teste de higiene reprova, numa lista sintética, `.env`, `*.tfvars`, `backend.hcl`, `*.tfstate`, `*.tfstate.*`, `*-sa-key.json` e `credentials*.json`, aceita os `*.example` e passa no `git ls-files` real. Spec: OPS-05 `In progress` (T43); TFP-02 e TFP-10 seguem `In progress` (T42, T51).

---

#### T42: [OPERACIONAL] Plan real de `envs/prod`

**What**: Com `terraform.tfvars` e `backend.hcl` locais e ADC: `terraform init -backend-config=backend.hcl` e `terraform plan` (somente leitura; senha por `TF_VAR_db_password`); mostrar o plano ao autor. **Não aplicar.**
**Where**: `terraform/envs/prod/` (execução; nenhum arquivo versionado novo)
**Execução**: pelo autor (AD-006). O agente fornece os comandos (`init -backend-config`, `plan`), explica a saída esperada e analisa o plano colado; não há `apply`.
**Depends on**: T41
**Reuses**: Bucket do T26
**Requirement**: TFP-01, TFP-02, TFP-08 (validação real)

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Autor deu OK para o `init`/`plan` (acessam o bucket e a API GCP em modo leitura)
- [ ] O plano lista somente os recursos esperados (3 APIs, rede, subnet, firewall, SA, 1 e2-micro, budget); nenhum recurso proibido; senha não aparece em texto no plano
- [ ] Conclusão marcada em `tasks.md` e commit próprio contendo somente esse arquivo (mensagem abaixo)

**Tests**: none
**Gate**: infra
**Commit**: `docs(tasks): registra plan real de envs/prod (T42)` (só `tasks.md`, na própria branch da fase, antes do merge)

---

### Phase 9: Documentation (`docs/operations`)

#### T43: Runbook de preparação do GCP

**What**: Documentar ADC (`gcloud auth application-default login`), `billing_project` com `user_project_override`, fluxo `tfvars` → bootstrap → `backend.hcl` → `envs/prod`, e a regra de versionar apenas `*.example`.
**Where**: `docs/gcp-setup.md`
**Depends on**: T42
**Reuses**: PRD §11-12 e Design (providers)
**Requirement**: OPS-04, OPS-05

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Passo a passo executável do zero, com comandos PowerShell exatos e sem valores reais
- [ ] Gate check passes: Quick (suíte anterior intacta)

**Tests**: none
**Gate**: quick
**Commit**: `docs(ops): adiciona runbook de preparação do GCP e ADC`

---

#### T44: Runbook de destruição

**What**: Documentar `terraform destroy` de `envs/prod` e do bootstrap (incluindo `force_destroy = true`/esvaziamento do bucket versionado), a ordem correta, o que `disable_on_destroy = false` preserva e o aviso sobre a rede `default`.
**Where**: `docs/destroy.md`
**Depends on**: T43
**Reuses**: Riscos do Design
**Requirement**: OPS-01

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Cobre prod e bootstrap, ordem, esvaziamento do bucket e verificação final (`gcloud compute instances list` vazio)
- [ ] Gate check passes: Quick

**Tests**: none
**Gate**: quick
**Commit**: `docs(ops): adiciona runbook de terraform destroy`

---

#### T45: Custo, billing e disco

**What**: Documentar a verificação do Billing Report para o IPv4 externo, que o budget apenas notifica (não limita), o atraso dos dados de billing e a inspeção manual do uso de disco (`df -h`, alerta aos 90%).
**Where**: `docs/cost-and-billing.md`
**Depends on**: T44
**Reuses**: PRD §6 e riscos do Design
**Requirement**: OPS-02, OPS-03, EDG-05

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Três tópicos presentes: IPv4/Billing Report, budget não limita gasto, disco 90%
- [ ] Gate check passes: Quick

**Tests**: none
**Gate**: quick
**Commit**: `docs(ops): adiciona guia de custo e verificação de billing`

---

#### T46: Atualização do código na VM

**What**: Documentar o ciclo de atualização (boot reaplica `git fetch` + `reset --hard`), o fluxo manual via `gcloud compute ssh` (`git fetch`, rebuild, verificação), a troca de `repo_ref` por `terraform apply`, o aviso de que a senha do Postgres é fixada na primeira inicialização do volume, e a perda de edições manuais.
**Where**: `docs/update-code.md`
**Depends on**: T45
**Reuses**: AD-001, riscos do Design
**Requirement**: OPS-06

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Fluxo manual com comandos exatos e as ressalvas de `repo_ref=main`
- [ ] Gate check passes: Quick

**Tests**: none
**Gate**: quick
**Commit**: `docs(ops): adiciona runbook de atualização do código`

---

#### T47: Mapa GCP → Azure

**What**: Documentar a correspondência entre os módulos GCP e os equivalentes no Azure (rede, compute, identidade, orçamento, state).
**Where**: `docs/azure-mapping.md`
**Depends on**: T46
**Reuses**: Estrutura de módulos do Design
**Requirement**: AZR-01

**Tools**:

- MCP: `context7` (provider `azurerm`, para nomear os recursos equivalentes)
- Skill: NONE

**Done when**:

- [ ] Tabela cobre os cinco itens (rede, compute, identidade, orçamento, state) com o recurso Azure correspondente e as diferenças relevantes
- [ ] Gate check passes: Quick

**Tests**: none
**Gate**: quick
**Commit**: `docs(azure): mapeia módulos GCP para equivalentes no Azure`

---

#### T48: Desenvolvimento local

**What**: Documentar a execução local: Docker Desktop, `.env`, `docker compose run --rm robo`, override para testes de integração, markers do pytest e como consultar as tabelas.
**Where**: `docs/local-development.md`
**Depends on**: T47
**Reuses**: Gates da seção "Gate Check Commands"
**Requirement**: LOC-01, LOC-05 (documentação)

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Comandos copiados e validados contra o ambiente real (mesmos usados no T21)
- [ ] Gate check passes: Quick

**Tests**: none
**Gate**: quick
**Commit**: `docs(local): adiciona guia de desenvolvimento local`

---

#### T49: README de infraestrutura

**What**: Documentar a estrutura `terraform/{bootstrap,modules,envs/prod}`, ordem de aplicação, guardas de Free Tier, decisões AD-001..003 e como reaproveitar os módulos no Azure.
**Where**: `terraform/README.md`
**Depends on**: T48
**Reuses**: Design e `docs/azure-mapping.md`
**Requirement**: AZR-01 (documentação de estrutura), TFP-12 (documentação)

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Lista cada módulo com entradas/saídas principais e liga aos runbooks de `docs/`
- [ ] Gate check passes: Quick

**Tests**: none
**Gate**: quick
**Commit**: `docs(terraform): adiciona README de infraestrutura`

---

#### T50: README raiz e verificação de links

**What**: Reescrever `README.md` como porta de entrada (visão geral, pré-requisitos, caminho local → produção, índice de `docs/`) e adicionar o teste que valida que todo link relativo dos `.md` resolve.
**Where**: `README.md`
**Depends on**: T49
**Reuses**: Todos os docs anteriores
**Requirement**: OPS-01..06, AZR-01 (índice)

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] README aponta para todos os documentos de `docs/` e `terraform/README.md`
- [ ] Teste de links falha com link quebrado sintético e passa no repositório
- [ ] Gate check passes: Build (Quick + Infra + `fmt`)
- [ ] Test count: ≥ 2 testes novos passam

**Tests**: unit
**Gate**: build
**Commit**: `docs(readme): adiciona visão geral do projeto e teste de links`

---

### Phase 10: Live validation (`docs/live-run-fixes`)

Tarefas operacionais: todas exigem OK explícito do autor antes de agir. Correções de documentação ou de código descobertas aqui viram commits `docs:`/`fix:` (descrição em português) na branch `docs/live-run-fixes` (ou em branch própria, se mexer em código) e re-executam o gate da camada afetada. Cada task operacional tem seu próprio commit só com `tasks.md`.

#### T51: [OPERACIONAL] Apply de `envs/prod`

**What**: Após revisão final do plano e **OK explícito do autor**, `terraform apply` em `envs/prod`; conferir recursos com `gcloud`.
**Where**: `terraform/envs/prod/` (execução)
**Execução**: pelo autor (AD-006). O agente fornece os comandos de `apply` e `gcloud`, explica a saída esperada e analisa o resultado colado.
**Depends on**: T50
**Reuses**: Runbooks `docs/gcp-setup.md`
**Requirement**: TFP-01, TFP-03..07, TFP-09, TFP-11

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Apply termina sem erro (reexecutar uma vez se 403 transitório de API recém-habilitada); `gcloud compute instances list` mostra 1 e2-micro `pd-standard` em `us-central1-a`
- [ ] `gcloud billing budgets describe` confirma R$ 5 e thresholds 50/90/100%; outputs exibem o comando SSH
- [ ] Conclusão marcada em `tasks.md` e commit próprio contendo somente esse arquivo (mensagem abaixo)

**Tests**: none
**Gate**: infra
**Commit**: `docs(tasks): registra apply de envs/prod (T51)` (só `tasks.md`, na própria branch da fase, antes do merge)

---

#### T52: [OPERACIONAL] Verificar o boot da VM

**What**: Via `gcloud compute ssh`: inspecionar o log do startup, Docker, swap, `.env` (permissão 600), `postgres` saudável, entrada de cron única e logrotate.
**Where**: VM (leitura)
**Execução**: pelo autor (AD-006). O agente fornece os comandos (`gcloud compute ssh` e as inspeções na VM), explica a saída esperada e analisa o resultado colado.
**Depends on**: T51
**Reuses**: Startup script (T32-T34)
**Requirement**: VM-01, VM-02, VM-03, VM-06, VM-07

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] `/var/log/book-monitor-startup.log` sem erro; `free -m` mostra swap de 1 GB; `stat` do `.env` = 600; `docker ps` mostra `postgres` healthy; `/etc/cron.d/book-monitor` tem 1 entrada
- [ ] Falhas viram correções com teste de regressão na camada afetada (T32-T34)

**Tests**: none
**Gate**: infra
**Commit**: `docs(tasks): registra verificação do boot da VM (T52)` (só `tasks.md`, na própria branch da fase, antes do merge)

---

#### T53: [OPERACIONAL] Execução manual do robô e OOM

**What**: Na VM, `docker compose run --rm robo` completo, monitorando memória (`docker stats`, `free -m`) e conferindo `dmesg` por OOM; ajustar `mem_limit`/swap se necessário.
**Where**: VM (execução)
**Execução**: pelo autor (AD-006). O agente fornece os comandos (`gcloud compute ssh`, `docker compose run --rm robo`, `docker stats`, `free -m`, `dmesg`), explica a saída esperada e analisa o resultado colado.
**Depends on**: T52
**Reuses**: Orçamento de memória do Design
**Requirement**: VM-08, SCR-09 (em produção)

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Execução termina com `SUCCESS` e 1.000 itens; `dmesg | grep -i "out of memory"` vazio; pico de memória registrado
- [ ] Se houve OOM: ajuste aplicado em `docker-compose.yml`/swap em commit separado (`fix(docker): ajusta limites de memória`) e nova execução bem-sucedida (o gate Docker volta a passar)

**Tests**: none
**Gate**: docker
**Commit**: `docs(tasks): registra execução manual do robô e checagem de OOM (T53)` (só `tasks.md`, na própria branch da fase, antes do merge)

---

#### T54: [OPERACIONAL] Cron, reboot e atualização

**What**: Confirmar a execução do cron das 06:00 UTC no dia seguinte (nova linha em `executions` criada pelo cron); reiniciar a VM e conferir `postgres` de volta, dados preservados e uma só entrada de cron; testar `git pull` no boot (inclusive com GitHub inacessível simulado, se viável).
**Where**: VM (execução)
**Execução**: pelo autor (AD-006). O agente fornece os comandos (`gcloud compute ssh/instances reset`, consultas ao banco, `git`), explica a saída esperada e analisa o resultado colado.
**Depends on**: T53
**Reuses**: `docs/update-code.md`
**Requirement**: VM-03, VM-04, VM-05, VM-06, VM-09, VM-10, DB-08

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] `executions` mostra linha `SUCCESS` do cron; `run.log` presente; execução concorrente simulada é pulada por `flock`
- [ ] Após reboot: dados e `.env` intactos, cron único, `postgres` ativo; startup atualiza o código (VM-09)
- [ ] Conclusão marcada em `tasks.md` e commit próprio contendo somente esse arquivo (mensagem abaixo)

**Tests**: none
**Gate**: infra
**Commit**: `docs(tasks): registra validação de cron, reboot e atualização (T54)` (só `tasks.md`, na própria branch da fase, antes do merge)

---

#### T55: [OPERACIONAL] Billing e e-mails do budget

**What**: Conferir no Billing Report, após alguns dias, se o IPv4 externo é cobrado e se os e-mails de budget chegam; registrar o resultado.
**Where**: `docs/cost-and-billing.md` (modify)
**Execução**: pelo autor (AD-006) nas consultas de `gcloud` e no Billing Report do console; o agente fornece os comandos, explica o que observar, analisa o resultado colado e registra no documento.
**Depends on**: T54
**Reuses**: `docs/cost-and-billing.md` (T45)
**Requirement**: OPS-02, TFP-09 (validação real)

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Resultado do IPv4 e do e-mail registrado no documento (ou decisão de trocar para canal do Monitoring registrada em STATE.md se o e-mail não chegar)
- [ ] Gate check passes: Quick

**Tests**: none
**Gate**: quick
**Commit**: `docs(ops): registra resultado da verificação de billing (T55)`

---

#### T56: [OPERACIONAL] Teste de destruição

**What**: Com **OK explícito do autor**, executar o runbook `docs/destroy.md`: `terraform destroy` de `envs/prod` e, por último, do bootstrap; confirmar que nada que gera custo permanece. Reaplicar depois é decisão do autor.
**Where**: `terraform/envs/prod/` (execução)
**Execução**: pelo autor (AD-006). O agente fornece os comandos de `destroy` e `gcloud` (na ordem do runbook), explica a saída esperada e analisa o resultado colado.
**Depends on**: T55
**Reuses**: `docs/destroy.md`
**Requirement**: OPS-01 (validação real)

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Destroy conclui sem erro; `gcloud compute instances list` e `gcloud storage buckets list` não mostram recursos do projeto; APIs `cloudresourcemanager` e `serviceusage` continuam habilitadas
- [ ] Runbook corrigido onde divergiu da prática, em commit separado (`docs(ops): corrige runbook de destruição`) quando houver ajuste

**Tests**: none
**Gate**: infra
**Commit**: `docs(tasks): registra teste de destruição (T56)` (só `tasks.md`, na própria branch da fase, antes do merge)

---

## Phase Execution Map

```
Phase 1 → Phase 2 → Phase 3 → Phase 4 → Phase 5 → Phase 6 → Phase 7 → Phase 8 → Phase 9 → Phase 10
```

Execution is strictly sequential - there is no intra-phase parallelism. Cada fase corresponde a uma branch criada da `main` após o merge da anterior. **Sem sub-agentes** (decisão do autor): toda a execução fica com o agente principal, task a task; não oferecer lotes de sub-agentes. O Verifier final do skill roda inline, como passada independente (`validate.md`), e não em sub-agente. As tasks **[OPERACIONAL]** (T26, T42, T51-T56) exigem OK explícito do autor antes de agir e, por AD-006, os comandos `terraform`/`gcloud` são sempre executados pelo autor (o agente fornece comandos, explicação e análise da saída).

---

## Requirement Coverage

| Requisito | Tasks | Requisito | Tasks |
| --- | --- | --- | --- |
| SCR-01 | T9, T12 | TFP-01 | T27, T39, T42, T51 |
| SCR-02 | T10, T12 | TFP-02 | T37, T41, T42 |
| SCR-03 | T3, T10 | TFP-03 | T28, T39, T51 |
| SCR-04 | T10, T12 | TFP-04 | T28, T39, T51 |
| SCR-05 | T12 | TFP-05 | T28, T38 |
| SCR-06 | T6, T11, T12 | TFP-06 | T29, T39, T51 |
| SCR-07 | T8, T10 | TFP-07 | T31, T35, T39, T51 |
| SCR-08 | T12 | TFP-08 | T35, T39, T42 |
| SCR-09 | T11, T21, T53 | TFP-09 | T30, T39, T51, T55 |
| DB-01 | T17, T18 | TFP-10 | T31, T38, T41 |
| DB-02 | T19 | TFP-11 | T36, T40, T51 |
| DB-03 | T19 | TFP-12 | T27-T31, T35, T36, T39, T49 |
| DB-04 | T19 | TFP-13 | T22, T24, T27, T37, T39 |
| DB-05 | T19, T20 | VM-01 | T32, T33, T52 |
| DB-06 | T18 | VM-02 | T32, T52 |
| DB-07 | T18, T20 | VM-03 | T34, T52, T54 |
| DB-08 | T15, T21, T54 | VM-04 | T34, T54 |
| DB-09 | T8, T17, T19 | VM-05 | T33, T34, T54 |
| CFG-01 | T4 | VM-06 | T15, T52, T54 |
| CFG-02 | T4, T20 | VM-07 | T34, T52 |
| CFG-03 | T5, T20 | VM-08 | T53 |
| CFG-04 | T4 | VM-09 | T33, T54 |
| CFG-05 | T20 | VM-10 | T33, T54 |
| CFG-06 | T5 | OPS-01 | T44, T50, T56 |
| CFG-07 | T1 | OPS-02 | T45, T50, T55 |
| LOC-01 | T15, T21, T48 | OPS-03 | T45, T50 |
| LOC-02 | T13, T21 | OPS-04 | T43, T50 |
| LOC-03 | T15 | OPS-05 | T41, T43 |
| LOC-04 | T15 | OPS-06 | T46, T50 |
| LOC-05 | T14, T15, T48 | AZR-01 | T47, T49, T50 |
| LOC-06 | T11, T21 | EDG-01 | T10, T12 |
| TFB-01 | T22, T24, T26 | EDG-02 | T12 |
| TFB-02 | T24, T26 | EDG-03 | T10, T19 |
| TFB-03 | T23 | EDG-04 | T19, T20 |
| TFB-04 | T25, T26 | EDG-05 | T45 |
| TFB-05 | T23 | CFG-08 | T4 |

---

## Pre-approval Validation

### Check 1: Task Granularity

Cada task entrega um arquivo, uma função ou um módulo coeso; `Where` aponta um arquivo ou o diretório do componente (módulos Terraform e esqueletos com 2-3 arquivos obrigatoriamente coesos: `versions.tf`+`providers.tf`, `main/variables/outputs`). Divisões deliberadas: `db.py` em duas tasks (T18/T19), `parsing.py` em três (T8-T10) e o startup script em três (T32-T34). Nenhuma task tem mais de um componente de comportamento.

### Check 2: Diagram-Definition Cross-Check

Cada fase é uma cadeia linear; todo `Depends on` dentro da fase é o predecessor imediato e coincide com a seta. A primeira task de cada fase depende da última da fase anterior (dependência para trás; sem seta, por desenho). Verificação determinística: `validate_tasks.py` (resultado registrado na apresentação).

| Fase | Cadeia no diagrama | `Depends on` nas tasks | Status |
| ---- | ------------------ | ---------------------- | ------ |
| 1 | T1→T2→T3→T4→T5→T6 | T2:T1, T3:T2, T4:T3, T5:T4, T6:T5 | ✅ Match |
| 2 | T7→T8→T9→T10→T11→T12 | T8:T7 ... T12:T11 | ✅ Match |
| 3 | T13→T14→T15→T16 | T14:T13, T15:T14, T16:T15 | ✅ Match |
| 4 | T17→T18→T19→T20→T21 | T18:T17 ... T21:T20 | ✅ Match |
| 5 | T22→T23→T24→T25→T26 | T23:T22 ... T26:T25 | ✅ Match |
| 6 | T27→T28→T29→T30 | T28:T27, T29:T28, T30:T29 | ✅ Match |
| 7 | T31→T32→T33→T34→T35→T36 | T32:T31 ... T36:T35 | ✅ Match |
| 8 | T37→T38→T39→T40→T41→T42 | T38:T37 ... T42:T41 | ✅ Match |
| 9 | T43→T44→...→T50 | T44:T43 ... T50:T49 | ✅ Match |
| 10 | T51→T52→...→T56 | T52:T51 ... T56:T55 | ✅ Match |

### Check 3: Test Co-location Validation

| Task | Code Layer | Matrix Requires | Task Says | Status |
| ---- | ---------- | --------------- | --------- | ------ |
| T1 | requirements (CFG-07) | unit (higiene) | unit | ✅ OK |
| T2 | pyproject (config) | none - build gate | none | ✅ OK |
| T3-T6 | lógica pura | unit | unit | ✅ OK |
| T7 | fixtures (dados) | none | none | ✅ OK |
| T8-T10, T12 | lógica pura | unit | unit | ✅ OK |
| T11 | browser.py | unit (driver falso) | unit | ✅ OK |
| T13, T15 | Dockerfile / Compose | docker (smoke) | integration (marker `docker`) | ✅ OK |
| T14 | `.env.example` | unit | unit | ✅ OK |
| T16 | override example | none | none | ✅ OK |
| T17-T20 | schema / db / runner | integration | integration | ✅ OK |
| T21 | fluxo local | e2e | integration (marker `e2e`) | ✅ OK |
| T22, T37 | esqueleto Terraform | none - build gate (`init`/`validate`) | none | ✅ OK |
| T23-T25, T27-T31, T35, T36, T38-T40 | Terraform | infra-test | infra-test | ✅ OK |
| T32-T34 | startup script | infra (render + `bash -n`) | infra-test | ✅ OK |
| T41, T50 | higiene / links | unit | unit | ✅ OK |
| T26, T42, T51-T56 | operacional | none - evidência manual | none | ✅ OK |
| T43-T49 | docs | none (link check no T50) | none | ✅ OK |

Avisos esperados do script (`Tests: none`): T2, T7, T16, T22, T26, T37, T42-T49, T51-T56, todos conferidos acima contra a matriz.
