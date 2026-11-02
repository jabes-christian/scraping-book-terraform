# STATE

## Decisions

### AD-001
- **Decision**: O código do robô chega à VM por `git clone`/`git pull` HTTPS do repositório público, com `docker compose build` na própria VM, a cada boot.
- **Reason**: Artifact Registry cobra acima de 0,5 GB (a imagem com Chromium passa disso) e Docker Hub público expõe a imagem; a conta de faturamento é paga e sem créditos.
- **Trade-off**: Build lento na e2-micro; `repo_ref=main` implanta qualquer commit no próximo boot; exige repositório público e nenhum segredo no código.
- **Scope**: Terraform `compute_vm`, startup script, qualquer ambiente futuro (Azure incluído).
- **Date**: 2026-10-23
- **Status**: active

### AD-002
- **Decision**: Segredos de produção (senha do Postgres) trafegam por atributo de metadata da instância e são gravados em `.env` (chmod 600) pelo startup script; Secret Manager fica como evolução.
- **Reason**: Menos recursos e complexidade num projeto de estudo; Secret Manager é grátis só até 6 versões.
- **Trade-off**: Legível por quem tem acesso ao projeto e de dentro da VM; presente no state do Terraform.
- **Scope**: Todas as stacks Terraform e o runtime da VM.
- **Date**: 2026-10-23
- **Status**: active

### AD-003
- **Decision**: Terraform em `terraform/{bootstrap,modules,envs/prod}`; backend GCS por configuração parcial (`backend.hcl`); `disable_on_destroy = false` em todo `google_project_service`; guardas de Free Tier em `validation` de variáveis.
- **Reason**: Reaproveitar a estrutura no Azure, impedir que o `destroy` desligue APIs habilitadas fora do Terraform e falhar no `plan` antes de gerar custo.
- **Trade-off**: Dois `apply` (bootstrap + prod); state do bootstrap fica local.
- **Scope**: Toda a infraestrutura.
- **Date**: 2026-10-23
- **Status**: active

### AD-004
- **Decision**: A execução é dividida em 10 fases, cada uma em uma branch criada da `main` após o merge da anterior (merge sem squash, um commit por task); tasks operacionais (apply, VM, billing, destroy) exigem OK explícito e têm commit próprio, só com `tasks.md`, na branch da fase antes do merge (ex.: `docs(tasks): registra apply do bootstrap (T26)`); `docs/` é escrito antes da validação ao vivo.
- **Reason**: PRs pequenos e revisáveis; nada com custo ou efeito externo roda sem aprovação; os runbooks são validados na prática (fase 10).
- **Trade-off**: Mais branches e merges manuais; correções da validação ao vivo viram commits extras na fase 10.
- **Scope**: `tasks.md` e todo o Execute.
- **Date**: 2026-10-24
- **Status**: active

### AD-005
- **Decision**: Commits com tipo e escopo do Conventional Commits em inglês e descrição em português (ex.: `feat(robot): adiciona modelos de domínio`); código, logs e nomes técnicos seguem em inglês. A execução não usa sub-agentes (tudo no agente principal, task a task, incluindo o Verifier inline); o único MCP é o Context7, sem skills adicionais; o merge de fase pode ser feito pelo `gh` ou pelo site do GitHub.
- **Reason**: Preferência do autor; o `gh` pode não estar instalado.
- **Trade-off**: Execução mais lenta e com mais contexto no agente principal; a descrição em português substitui a regra "commits em inglês" do PRD §9.
- **Scope**: Todos os commits e a forma de executar `tasks.md`.
- **Date**: 2026-10-24
- **Status**: active

## Handoff

- **Feature**: .specs/features/book-price-monitor
- **Phase / Task**: Fase 4 concluída (T17-T21); gate Build verde: Quick (109 testes unit, ruff) + Full (32 testes `-m integration`) + Docker (`docker compose build`, 14 testes `-m docker`) + E2E (3 testes `-m e2e`, site real). Infra e `terraform fmt` não se aplicam (não há `terraform/`). Fase 5 (T22-T26) ainda não iniciada
- **Completed**: Fases 1 a 3 mergeadas; Fase 4 implementada: `schema.sql` (T17), `db.py` com `connect_with_retry`/`ensure_schema`/`mark_abandoned` (T18) e `start_execution`/`save_success`/`mark_failed` (T19), `runner.py` e `__main__.py` (T20), e2e local (T21). Os testes de integração usam o projeto Compose isolado `bookmonitor_it` (volume e porta próprios, credenciais de teste, subido e removido pelo `conftest.py`); o e2e usa `bookmonitor_e2e` com as credenciais do `.env`. O volume de desenvolvimento nunca é tocado. A definição do gate Full no `tasks.md` foi atualizada para isso. Rastreabilidade da Spec: DB-01 a DB-07, DB-09, CFG-02, CFG-03, CFG-05, EDG-03, EDG-04, LOC-02 e LOC-06 `Implemented`; LOC-01 (T48), SCR-09 (T53), DB-08 (T54), LOC-05 (T48) e VM-06 (T52) `In progress`
- **Achados da T21** (para as fases seguintes): (1) a rede corporativa faz inspeção TLS (Netskope) e o container não confia na CA, então o robô falha por HTTPS nesta máquina; o e2e rodou com `E2E_BASE_URL=http://books.toscrape.com/` e a validação por HTTPS fica para a T53, na VM; (2) referência de memória (Docker Desktop, 2 execuções de 1.000 itens, 93,2 s e 88,9 s): `robo` pico de 478,5 MiB (`docker stats`) e 560,0 MiB no cgroup com cache, igual ao `mem_limit` de 560m e sem OOM; `postgres` 55,8 MiB (`docker stats`) e 135,4 MiB no cgroup, contra o limite de 192m. O `robo` opera perto do teto de 560m; conferir na e2-micro (T53, VM-08) com swap ativo
- **In-progress** (file:line): none
- **Next step**: Após o merge de `feat/robot-persistence` na `main`, atualizar a `main` local, criar `feat/tf-bootstrap` e iniciar a T22 (esqueleto do bootstrap Terraform; exige `terraform` instalado e Context7 para a versão do provider `google`). Nada com custo até a T26 (apply, só com OK explícito)
- **Blockers**: none
- **Uncommitted files**: `.specs/STATE.md` (commit do handoff, depois do commit da T21)
- **Branch**: feat/robot-persistence
