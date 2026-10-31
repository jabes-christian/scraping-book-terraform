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
- **Phase / Task**: Fase 3 concluída (T13-T16); gate Build verde: Quick (108 testes unit, ruff) + Docker (`docker compose build`, 14 testes `-m docker`). Full não se aplica à fase (ainda não há testes de integração, só a partir da T17); Infra e `terraform fmt` não se aplicam (não há `terraform/`). Fase 4 (T17-T21) ainda não iniciada
- **Completed**: Fases 1 e 2 mergeadas; Fase 3 implementada: `Dockerfile` e `.dockerignore` (T13), `.env.example` (T14), `docker-compose.yml` (T15) e `docker-compose.override.yml.example` (T16); `.env` e `docker-compose.override.yml` locais criados (gitignored, senha do `.env` aleatória). Os testes docker usam o projeto Compose `bookmonitor_test` e `-f docker-compose.yml` (não carregam o override local). Rastreabilidade da Spec: LOC-03 e LOC-04 `Implemented`; LOC-01, LOC-02, LOC-05, VM-06 e DB-08 `In progress` (completam em T21/T48/T52/T54)
- **In-progress** (file:line): none
- **Next step**: Após o merge de `feat/docker-local` na `main`, atualizar a `main` local, criar `feat/robot-persistence` e iniciar a T17 (schema do banco). Docker Desktop precisa estar ligado e o `.env` e o `docker-compose.override.yml` locais já existem (gate Full: `docker compose up -d --wait postgres` + `pytest -m integration`). O `ENTRYPOINT` da imagem só funciona após o `__main__.py` da T20
- **Blockers**: none
- **Uncommitted files**: `.specs/STATE.md`, `.specs/features/book-price-monitor/tasks.md`, `docker-compose.override.yml.example`, `tests/docker/test_compose.py` (commit da T16)
- **Branch**: feat/docker-local
