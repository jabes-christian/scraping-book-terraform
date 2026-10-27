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
| Tarefas operacionais (apply, VM, billing, destroy) | none - evidência manual | Evidência colada no relatório da task (saída de `gcloud`/`terraform`) | - | Live |

## Gate Check Commands

> Generated from codebase - confirm before Execute. Todos os comandos Python usam `.venv\Scripts\python.exe` (o shell do agente não herda a ativação do venv).

| Gate Level | When to Use | Command |
| ---------- | ----------- | ------- |
| Quick | Tasks com apenas unit tests | `.venv\Scripts\python.exe -m pytest -m "not integration and not docker and not infra and not e2e"` + `.venv\Scripts\python.exe -m ruff check .` |
| Full | Tasks com integration (exige Docker Desktop ligado e `.env` local) | Quick + `docker compose up -d --wait postgres` + `.venv\Scripts\python.exe -m pytest -m integration` |
| Docker | Tasks de Dockerfile/Compose | `docker compose build` + `.venv\Scripts\python.exe -m pytest -m docker` |
| Infra | Tasks de Terraform e startup script | `terraform fmt -check -recursive terraform` + por stack/módulo alterado: `terraform -chdir=<dir> init -backend=false`, `terraform -chdir=<dir> validate`, `terraform -chdir=<dir> test` + `.venv\Scripts\python.exe -m pytest -m infra` (quando houver) |
| E2E | T21 e antes do Verifier | `.venv\Scripts\python.exe -m pytest -m e2e` (site real; ~minutos) |
| Build | Fim de cada fase | Quick + os níveis aplicáveis à fase (Full / Docker / Infra) + `terraform fmt -check -recursive terraform` |

Pré-requisitos do ambiente: Docker Desktop ligado nas fases 3 e 4 (hoje o daemon está desligado); `.env` copiado de `.env.example` (gitignored); `docker-compose.override.yml` copiado do `.example` (gitignored) para publicar `127.0.0.1:5432` nos testes de integração; ADC ativo para tasks de Terraform com chamada real.

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

- [ ] Com `retries=3` e falha persistente: 4 chamadas no total, esperas exatamente [2, 4, 8] s, e a última exceção é propagada
- [ ] Sucesso na 3ª tentativa devolve o resultado sem esperas extras; exceção que não é `RetryableError` não é repetida
- [ ] Gate check passes: Quick
- [ ] Test count: ≥ 5 testes passam

**Tests**: unit
**Gate**: quick
**Commit**: `feat(robot): adiciona retry com backoff exponencial`

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

- [ ] Fixtures versionáveis salvas em UTF-8 e listadas no relatório da task, com os seletores confirmados (ou corrigidos, com a correção registrada)
- [ ] Gate check passes: Quick (os testes anteriores continuam passando)

**Tests**: none
**Gate**: quick
**Commit**: `test(robot): adiciona fixtures HTML reais do books.toscrape.com`

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

- [ ] `"£51.77"` → `Decimal("51.77")`; entradas inválidas (`""`, `"abc"`, `"£"`) levantam erro de parsing
- [ ] Gate check passes: Quick
- [ ] Test count: ≥ 4 testes passam

**Tests**: unit
**Gate**: quick
**Commit**: `feat(robot): converte texto de preço em Decimal`

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

- [ ] Sobre a fixture da home retorna as 50 categorias (excluindo o item "Books" agregador, conforme a estrutura real confirmada no T7) com URLs absolutas
- [ ] HTML sem a estrutura esperada levanta erro de parsing
- [ ] Gate check passes: Quick
- [ ] Test count: ≥ 3 testes passam

**Tests**: unit
**Gate**: quick
**Commit**: `feat(robot): extrai a lista de categorias da home`

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

- [ ] Para cada livro: categoria, título completo vindo do atributo `title` (não o texto truncado), `Decimal`, disponibilidade em texto e URL absoluta
- [ ] `total_results` extraído de "N results"; `next_url` absoluta quando há link "next" e `None` na última página; categoria com 0 results devolve 0 itens sem erro (HTML sintético)
- [ ] Preço ilegível levanta erro cuja mensagem contém a URL do livro; título com aspas/acentos permanece íntegro
- [ ] Gate check passes: Quick
- [ ] Test count: ≥ 9 testes passam

**Tests**: unit
**Gate**: quick
**Commit**: `feat(robot): extrai livros das páginas de listagem`

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

- [ ] Com driver falso: as opções contêm `--headless=new`, `--no-sandbox`, `--disable-dev-shm-usage`, `--disable-gpu`, `--blink-settings=imagesEnabled=false`, `binary_location` e `executable_path` vindos da config (nenhum download de driver)
- [ ] O driver é recriado na 25ª página e após `WebDriverException`; página sem o marcador estrutural levanta `PageLoadError` (retentável) e timeout configurado em `PAGE_TIMEOUT_SECONDS`
- [ ] Gate check passes: Quick
- [ ] Test count: ≥ 6 testes passam

**Tests**: unit
**Gate**: quick
**Commit**: `feat(robot): adiciona sessão do Chromium headless`

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

- [ ] Com sessão falsa servindo as fixtures: percorre todas as páginas até não haver "next" e a soma de itens bate com "N results"
- [ ] Divergência de contagem falha com `count mismatch` e o nome da categoria; URL repetida falha com `duplicate url` e a URL; categoria com 0 itens segue sem falhar
- [ ] Falha de página esgota 4 tentativas (esperas 2/4/8 s) e propaga o erro; `time.sleep` do delay é chamado com `SCRAPE_DELAY_SECONDS` entre páginas consecutivas
- [ ] Gate check passes: Quick (suíte completa da fase)
- [ ] Test count: ≥ 8 testes passam

**Tests**: unit
**Gate**: quick
**Commit**: `feat(robot): orquestra a coleta por categoria e paginação`

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

- [ ] `docker compose build`/`docker build` conclui; teste docker: `id -u` ≠ 0, `chromium --version` e `chromedriver --version` respondem (override de entrypoint) e a versão major do driver coincide com a do Chromium
- [ ] `.dockerignore` exclui `.venv`, `.git`, `.env`, `.specs`, `terraform`
- [ ] Gate check passes: Docker
- [ ] Test count: ≥ 3 testes passam

**Tests**: integration (marker `docker`)
**Gate**: docker
**Commit**: `build(docker): adiciona imagem do robô com Chromium`

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

- [ ] Teste: `.env.example` contém as chaves esperadas, `DB_PASSWORD` é o placeholder `change-me` e nenhuma outra linha parece segredo
- [ ] `git check-ignore .env` confirma `.env` ignorado e `.env.example` não (verificação de leitura; sem alterar o repositório)
- [ ] Gate check passes: Quick
- [ ] Test count: ≥ 2 testes passam

**Tests**: unit
**Gate**: quick
**Commit**: `chore(env): adiciona .env.example sem segredos`

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

- [ ] Teste sobre `docker compose config --format json`: volume nomeado em `/var/lib/postgresql/data`, `restart` do postgres, `mem_limit` de ambos com soma ≤ 752 MB, healthcheck presente, `postgres` sem `ports`, `robo` com `depends_on.postgres.condition == service_healthy` e `init` true
- [ ] `docker compose up -d --wait postgres` fica `healthy` e os dados sobrevivem a `docker compose up -d --force-recreate postgres` (tabela de teste criada e relida)
- [ ] Gate check passes: Docker
- [ ] Test count: ≥ 6 testes passam

**Tests**: integration (marker `docker`)
**Gate**: docker
**Commit**: `feat(docker): adiciona stack Compose com postgres e robô`

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

- [ ] Com o override, `127.0.0.1:5432` aceita conexão TCP e sem o override a porta não é publicada; `git check-ignore docker-compose.override.yml` confirma o arquivo real ignorado
- [ ] Gate check passes: Docker (testes anteriores continuam passando)

**Tests**: none
**Gate**: docker
**Commit**: `chore(docker): adiciona exemplo de override local do Compose`

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

- [ ] Aplicar o DDL duas vezes não falha (idempotente) e cria as três tabelas
- [ ] `price_history.price` é `numeric(10,2)` e `currency` assume `GBP` por padrão; `status` rejeita valor fora de `RUNNING/SUCCESS/FAILED`; `UNIQUE (execution_id, book_id)` impede duplicata
- [ ] Gate check passes: Full
- [ ] Test count: ≥ 5 testes passam

**Tests**: integration
**Gate**: full
**Commit**: `feat(db): adiciona schema idempotente`

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

- [ ] `ensure_schema` cria o schema em banco vazio e é reentrante
- [ ] `mark_abandoned` marca como `FAILED` com erro `abandoned` só execuções `RUNNING` com `started_at` anterior a 2 h (uma de 3 h é marcada; uma de 1 h e uma `SUCCESS` ficam intactas)
- [ ] `connect_with_retry` contra host inacessível desiste ao fim do timeout (reduzido no teste) com exceção cuja mensagem não contém a senha
- [ ] Gate check passes: Full
- [ ] Test count: ≥ 6 testes passam

**Tests**: integration
**Gate**: full
**Commit**: `feat(db): adiciona reconexão, criação do schema e limpeza de execuções abandonadas`

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

- [ ] `start_execution` cria linha `RUNNING` com `started_at`; `save_success` grava N livros e N linhas de preço e deixa `SUCCESS`, `finished_at` e `items_count == N` na mesma transação
- [ ] Falha injetada no meio de `save_success` não deixa linha de `price_history` nem `SUCCESS` (rollback); `mark_failed` grava `FAILED`, `finished_at` e erro truncado em 2.000 caracteres sem tocar em `price_history`
- [ ] Duas execuções no mesmo dia geram duas execuções independentes, cada uma com suas linhas; reexecutar o mesmo livro atualiza `books` (mesma URL) sem duplicá-lo; título com aspas e acentos volta íntegro
- [ ] Gate check passes: Full
- [ ] Test count: ≥ 8 testes passam

**Tests**: integration
**Gate**: full
**Commit**: `feat(db): adiciona ciclo de vida da execução e gravação transacional de preços`

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

- [ ] Sem `DB_PASSWORD`: retorna 2, a mensagem cita `DB_PASSWORD` e nenhuma conexão é aberta
- [ ] Scraper falso com sucesso: retorna 0, `executions` com `SUCCESS` e `items_count` correto; scraper que levanta erro: retorna 1, `FAILED` com erro, zero linhas de `price_history`
- [ ] Banco inacessível: retorna 1 sem linha em `executions` e sem a senha na saída; a senha de teste não aparece em stdout/stderr nem em `executions.error` mesmo quando incluída na mensagem da exceção
- [ ] Gate check passes: Full
- [ ] Test count: ≥ 7 testes passam

**Tests**: integration
**Gate**: full
**Commit**: `feat(robot): liga runner e entrypoint com códigos de saída`

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

- [ ] Duas execuções terminam com exit code 0; `executions` tem 2 linhas `SUCCESS` com `items_count == 1000` e `price_history` tem 2.000 linhas; `books` tem 1.000 linhas
- [ ] Nenhuma ocorrência do valor de `DB_PASSWORD` na saída das execuções
- [ ] Após `docker compose up -d --force-recreate postgres`, as contagens permanecem (DB-08)
- [ ] Gate check passes: E2E + Full (se o site divergir de 1.000 itens, a task não é concluída: investigar e reportar)
- [ ] Test count: ≥ 3 testes e2e passam

**Tests**: integration (marker `e2e`)
**Gate**: full
**Commit**: `test(e2e): verifica a execução local via Compose de ponta a ponta`

---

### Phase 5: Terraform bootstrap (`feat/tf-bootstrap`)

#### T22: Esqueleto da stack bootstrap

**What**: Criar `versions.tf` (`required_version >= 1.9`, provider `google ~> 7.0`) e `providers.tf` (`user_project_override = true`, `billing_project = var.project_id`) e gerar `.terraform.lock.hcl`.
**Where**: `terraform/bootstrap/`
**Depends on**: T21
**Reuses**: Seção Terraform do Design; Context7 para a versão do provider
**Requirement**: TFB-01 (base), TFP-13 (convenção)

**Tools**:

- MCP: `context7` (provider google)
- Skill: NONE

**Done when**:

- [ ] `terraform -chdir=terraform/bootstrap init -backend=false` e `validate` passam; `.terraform.lock.hcl` gerado para versionar
- [ ] `terraform fmt -check -recursive terraform` passa
- [ ] Gate check passes: Infra

**Tests**: none
**Gate**: infra
**Commit**: `feat(tf-bootstrap): adiciona provider e restrições de versão`

---

#### T23: Variáveis do bootstrap

**What**: Criar `variables.tf` com `project_id` (obrigatória, validação de não vazio e formato), `region` (`us-central1`), `bucket_name` (opcional), `force_destroy` (`false`).
**Where**: `terraform/bootstrap/variables.tf`
**Depends on**: T22
**Reuses**: Design (tabela do bootstrap)
**Requirement**: TFB-03, TFB-05

**Tools**:

- MCP: `context7` (`terraform test`, `expect_failures`)
- Skill: NONE

**Done when**:

- [ ] Teste `terraform test`: `project_id` vazio ou inválido falha na validação (`expect_failures`) antes de qualquer chamada de API; valor válido passa
- [ ] Nenhum valor real de projeto no arquivo
- [ ] Gate check passes: Infra
- [ ] Test count: ≥ 3 testes (`run` blocks) passam

**Tests**: infra-test
**Gate**: infra
**Commit**: `feat(tf-bootstrap): adiciona variáveis de entrada validadas`

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

- [ ] `terraform test` (plan com `mock_provider`) afirma: local `US-CENTRAL1`, versionamento ligado, `uniform_bucket_level_access` true, prevenção de acesso público `enforced`, `disable_on_destroy` false, `force_destroy` false por padrão e nome derivado do `project_id`
- [ ] O plano contém apenas `google_project_service` e `google_storage_bucket`
- [ ] Gate check passes: Infra
- [ ] Test count: ≥ 5 asserções em `run` blocks passam

**Tests**: infra-test
**Gate**: infra
**Commit**: `feat(tf-bootstrap): adiciona bucket versionado do tfstate`

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

- [ ] `terraform test` afirma que `bucket_name` é o nome do bucket e que o snippet contém `bucket = "<nome>"` e `prefix`
- [ ] Gate check passes: Infra
- [ ] Test count: ≥ 2 asserções passam

**Tests**: infra-test
**Gate**: infra
**Commit**: `feat(tf-bootstrap): expõe nome do bucket e trecho do backend`

---

#### T26: [OPERACIONAL] Plan e apply do bootstrap

**What**: Com `terraform.tfvars` local (gitignored) e ADC: `terraform plan` (somente leitura) mostrado ao autor; **somente com OK explícito**, `terraform apply`; verificar o bucket com `gcloud storage buckets describe`.
**Where**: `terraform/bootstrap/` (execução; nenhum arquivo versionado novo)
**Depends on**: T25
**Reuses**: ADC e `billing_project` configurados (PRD §11)
**Requirement**: TFB-01, TFB-02, TFB-04 (validação real)

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Plano mostrado e aprovado pelo autor; plano contém exatamente 2 recursos (API Storage e bucket)
- [ ] Após o apply: bucket em `US-CENTRAL1`, versionamento habilitado, acesso público bloqueado (saída do `gcloud` registrada); `terraform output` entrega o nome do bucket
- [ ] `backend.hcl` real criado localmente (gitignored) a partir do snippet
- [ ] Conclusão marcada em `tasks.md` e commit próprio contendo somente esse arquivo (mensagem abaixo)

**Tests**: none
**Gate**: infra
**Commit**: `docs(tasks): registra apply do bootstrap (T26)` (só `tasks.md`, na própria branch da fase, antes do merge)

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

- [ ] `terraform test`: uma instância por serviço informado, todas com `disable_on_destroy == false` e `disable_dependent_services == false`
- [ ] Gate check passes: Infra
- [ ] Test count: ≥ 3 asserções passam

**Tests**: infra-test
**Gate**: infra
**Commit**: `feat(tf-modules): adiciona módulo apis`

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

- [ ] `terraform test`: `auto_create_subnetworks == false`, região `us-central1`, regra permite só `tcp` porta `22` com `source_ranges == [allowed_ssh_cidr]` e `target_tags` correta
- [ ] `allowed_ssh_cidr = "0.0.0.0/0"` e CIDR malformado falham na validação (`expect_failures`)
- [ ] Gate check passes: Infra
- [ ] Test count: ≥ 5 asserções passam

**Tests**: infra-test
**Gate**: infra
**Commit**: `feat(tf-modules): adiciona módulo network com SSH restrito`

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

- [ ] `terraform test`: o plano contém a SA e nenhum recurso `google_*_iam_*` nem `google_service_account_key`; output `email` presente
- [ ] Gate check passes: Infra
- [ ] Test count: ≥ 3 asserções passam

**Tests**: infra-test
**Gate**: infra
**Commit**: `feat(tf-modules): adiciona módulo identity com service account sem chave`

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

- [ ] `terraform test`: `currency_code == "BRL"`, `units == "5"`, exatamente 3 thresholds (0.5, 0.9, 1.0), filtro por `projects/<número>`, ausência de `all_updates_rule` e de qualquer recurso Pub/Sub/Monitoring
- [ ] Gate check passes: Infra
- [ ] Test count: ≥ 5 asserções passam

**Tests**: infra-test
**Gate**: infra
**Commit**: `feat(tf-modules): adiciona módulo budget`

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

- [ ] `terraform test` com `expect_failures`: `machine_type = "e2-small"`, `boot_disk_size_gb = 31` e zona `europe-west1-b` falham; valores válidos passam
- [ ] `db_password` marcada `sensitive`
- [ ] Gate check passes: Infra
- [ ] Test count: ≥ 5 `run` blocks passam

**Tests**: infra-test
**Gate**: infra
**Commit**: `feat(tf-modules): adiciona entradas do compute_vm com guardas do Free Tier`

---

#### T32: Startup script, parte 1 (swap, pacotes, Docker) e harness de renderização

**What**: Criar `startup.sh.tftpl` com `set -euo pipefail`, log em `/var/log/book-monitor-startup.log`, swap file condicional + `fstab` + `vm.swappiness` em `/etc/sysctl.d`, instalação condicional de `git cron logrotate curl ca-certificates` e Docker CE + plugin Compose; criar `locals.tf` que renderiza o template e o helper de teste que renderiza e roda `bash -n` (decisão do mecanismo na task, p.ex. `terraform console`).
**Where**: `terraform/modules/compute_vm/startup.sh.tftpl`
**Depends on**: T31
**Reuses**: Passos 1-3 do Design (startup script)
**Requirement**: VM-02, VM-01 (parcial)

**Tools**:

- MCP: `context7` (Docker apt repository oficial para Debian 12)
- Skill: NONE

**Done when**:

- [ ] Script renderizado passa em `bash -n`; swap só é criado se `/swapfile` não estiver ativo; swap e sysctl aparecem antes de qualquer `docker`
- [ ] Texto renderizado não contém senha nem placeholder de segredo
- [ ] Gate check passes: Infra (inclui `pytest -m infra`)
- [ ] Test count: ≥ 5 testes passam

**Tests**: infra-test
**Gate**: infra
**Commit**: `feat(tf-compute-vm): adiciona swap e instalação do Docker ao startup script`

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

- [ ] Renderizado passa em `bash -n`; asserções estáticas: `.env` só é criado sob `[ ! -f ]`, senha lida do endpoint de metadata com cabeçalho `Metadata-Flavor: Google` e nunca embutida no texto, `chmod 600`, falha de `git fetch` com checkout existente apenas registra e segue
- [ ] `repo_url` e `repo_ref` do template aparecem no clone; `build` ocorre antes de `up -d postgres`
- [ ] Gate check passes: Infra
- [ ] Test count: ≥ 6 testes passam

**Tests**: infra-test
**Gate**: infra
**Commit**: `feat(tf-compute-vm): adiciona sincronização do código, .env e build ao startup script`

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

- [ ] Renderizado passa em `bash -n`; exatamente uma linha de cron, escrita por sobrescrita; `flock -n` presente; `cron_schedule` padrão `0 6 * * *`
- [ ] Logrotate contém `daily` e `rotate 7`
- [ ] Gate check passes: Infra
- [ ] Test count: ≥ 5 testes passam

**Tests**: infra-test
**Gate**: infra
**Commit**: `feat(tf-compute-vm): adiciona cron e rotação de logs ao startup script`

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

- [ ] `terraform test`: `machine_type == "e2-micro"`, `scheduling.preemptible == false`, disco `pd-standard` ≤ 30 GB, imagem Debian 12, IP externo efêmero (sem `nat_ip`), metadata contém `startup-script` e `book-db-password`
- [ ] O plano contém apenas a instância (nenhum disco extra, IP estático, snapshot ou NAT)
- [ ] Gate check passes: Infra
- [ ] Test count: ≥ 7 asserções passam

**Tests**: infra-test
**Gate**: infra
**Commit**: `feat(tf-compute-vm): adiciona instância e2-micro dentro do Free Tier`

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

- [ ] `terraform test` afirma o texto exato do comando `gcloud compute ssh`
- [ ] Gate check passes: Infra (fase completa: `fmt`, `validate`, `test`, `pytest -m infra`)
- [ ] Test count: ≥ 2 asserções passam

**Tests**: infra-test
**Gate**: infra
**Commit**: `feat(tf-compute-vm): expõe nome da instância, zona e comando SSH`

---

### Phase 8: Terraform prod (`feat/tf-prod`)

#### T37: Esqueleto de `envs/prod`

**What**: Criar `versions.tf`, `providers.tf` (`user_project_override`, `billing_project`) e `backend.tf` (`backend "gcs" { prefix = "envs/prod" }`, bucket por configuração parcial).
**Where**: `terraform/envs/prod/`
**Depends on**: T36
**Reuses**: Esqueleto do bootstrap (T22)
**Requirement**: TFP-02, TFP-13 (convenção)

**Tools**:

- MCP: `context7` (backend gcs, configuração parcial)
- Skill: NONE

**Done when**:

- [ ] `terraform -chdir=terraform/envs/prod init -backend=false` e `validate` passam; o bloco `backend "gcs"` não contém `bucket` nem variáveis
- [ ] `.terraform.lock.hcl` gerado para versionar
- [ ] Gate check passes: Infra

**Tests**: none
**Gate**: infra
**Commit**: `feat(tf-prod): adiciona providers e backend gcs parcial`

---

#### T38: Variáveis de `envs/prod`

**What**: Criar `variables.tf` com `project_id`, `billing_account_id`, `allowed_ssh_cidr`, `repo_url`, `repo_ref` (`main`), `db_name`, `db_user`, `db_password` (`sensitive`), `cron_schedule`, `swap_size_mb` e demais padrões do Design.
**Where**: `terraform/envs/prod/variables.tf`
**Depends on**: T37
**Reuses**: Variáveis dos módulos
**Requirement**: TFP-10, TFP-05

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] `terraform test`: `allowed_ssh_cidr = "0.0.0.0/0"` falha; `db_password` é `sensitive`; faltando `project_id`/`billing_account_id` não há valor padrão
- [ ] Gate check passes: Infra
- [ ] Test count: ≥ 3 `run` blocks passam

**Tests**: infra-test
**Gate**: infra
**Commit**: `feat(tf-prod): adiciona variáveis de entrada com validações`

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

- [ ] `terraform test` sobre o plano com `mock_provider`: conjunto de tipos de recurso é exatamente {`google_project_service`, `google_compute_network`, `google_compute_subnetwork`, `google_compute_firewall`, `google_service_account`, `google_compute_instance`, `google_billing_budget`} (lista fechada; qualquer NAT, LB, IP estático, snapshot, Cloud SQL, Pub/Sub, Artifact Registry ou Secret Manager reprova)
- [ ] Exatamente 1 instância; as 3 APIs; todas com `disable_on_destroy == false`
- [ ] Gate check passes: Infra
- [ ] Test count: ≥ 6 asserções passam

**Tests**: infra-test
**Gate**: infra
**Commit**: `feat(tf-prod): compõe os módulos no ambiente prod`

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

- [ ] `terraform test` afirma os três outputs e o texto do `ssh_command`
- [ ] Gate check passes: Infra
- [ ] Test count: ≥ 2 asserções passam

**Tests**: infra-test
**Gate**: infra
**Commit**: `feat(tf-prod): expõe comando SSH e outputs da instância`

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

- [ ] Os `.example` não contêm valores reais (placeholders como `your-project-id`, `change-me`) e cobrem todas as variáveis obrigatórias
- [ ] Teste de higiene falha se um arquivo proibido estiver rastreado (cenário positivo e negativo com lista sintética) e passa no repositório atual
- [ ] Gate check passes: Quick + Infra
- [ ] Test count: ≥ 4 testes passam

**Tests**: unit
**Gate**: quick
**Commit**: `chore(tf-prod): adiciona exemplos de tfvars e backend com teste de higiene do repositório`

---

#### T42: [OPERACIONAL] Plan real de `envs/prod`

**What**: Com `terraform.tfvars` e `backend.hcl` locais e ADC: `terraform init -backend-config=backend.hcl` e `terraform plan` (somente leitura; senha por `TF_VAR_db_password`); mostrar o plano ao autor. **Não aplicar.**
**Where**: `terraform/envs/prod/` (execução; nenhum arquivo versionado novo)
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

Execution is strictly sequential - there is no intra-phase parallelism. Cada fase corresponde a uma branch criada da `main` após o merge da anterior. **Sem sub-agentes** (decisão do autor): toda a execução fica com o agente principal, task a task; não oferecer lotes de sub-agentes. O Verifier final do skill roda inline, como passada independente (`validate.md`), e não em sub-agente. As tasks **[OPERACIONAL]** (T26, T42, T51-T56) exigem OK explícito do autor antes de agir.

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
