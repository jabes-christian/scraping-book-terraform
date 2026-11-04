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

### AD-006
- **Decision**: Comandos `terraform` (init, fmt, validate, test, plan, apply, destroy, output, import, state etc.) e `gcloud` são executados pelo autor, nunca pelo agente. O agente escreve os arquivos (`.tf`, `.tftest.hcl`, templates, docs) e, em cada task, entrega os comandos exatos com o diretório de execução (PowerShell, a partir da raiz), a explicação do que cada um faz e da saída esperada, e os conceitos de Terraform/GCP da task; o autor cola a saída e o agente a analisa. A task só é concluída depois da saída confirmar o gate. `pytest` e `ruff` continuam com o agente. Pull Requests sempre pelo site do GitHub (sem `gh`); o `.terraform.lock.hcl` gerado pelo `init` do autor entra no commit da task.
- **Reason**: O projeto é de estudo; o autor quer aprender Terraform e GCP na prática.
- **Trade-off**: Execução mais lenta (ida e volta com a saída colada); o agente não vê o ambiente real, só o que o autor cola.
- **Scope**: Gate Infra, tasks T22-T56 (em especial as [OPERACIONAL]: T26, T42, T51-T56). A Spec não muda (os ACs já dizem "o autor executa"). Restringe o AD-005 em um ponto: o merge de fase passa a ser só pelo site do GitHub (antes: `gh` ou site).
- **Date**: 2026-11-03
- **Status**: active

## Handoff

- **Feature**: .specs/features/book-price-monitor
- **Phase / Task**: Fase 5 concluída (T22-T26); gate Build verde: Quick (109 testes unit, ruff) + `pytest -m infra` (1) + Infra executado pelo autor (`fmt -check`, `validate`, `terraform test` com 17 `run` blocks passando). T26 (apply) executada pelo autor em 2026-11-03/04: bucket `book-price-monitor-jc-tfstate` criado e verificado com `gcloud`. Fase 6 (T27-T31) ainda não iniciada
- **Completed**: Fases 1 a 4 mergeadas; Fase 5 implementada em `terraform/bootstrap/`: `versions.tf`/`providers.tf` (provider `google ~> 7.0`, resolvido para v7.46.2; `project`, `user_project_override`, `billing_project`) e `.terraform.lock.hcl` (T22), `variables.tf` com validações e guarda de região do Free Tier (T23), `main.tf` com API Storage e bucket versionado (T24), `outputs.tf` (T25), apply real (T26). Testes: `tests/variables.tftest.hcl`, `main.tftest.hcl`, `outputs.tftest.hcl` (`mock_provider`) e `tests/infra/test_bootstrap_resources.py` (pytest, só 2 tipos de recurso). O `backend.hcl` real está em `terraform/envs/prod/backend.hcl` (gitignored) e o state do bootstrap é local em `terraform/bootstrap/terraform.tfstate` (gitignored; não apagar: o destroy da T56 depende dele). Rastreabilidade da Spec: TFB-01 a TFB-05 `Implemented`; TFP-13 `In progress` (T27, T37, T39); demais itens da Fase 4 como antes
- **Achados da Fase 5** (para as fases seguintes): (1) no PowerShell 5.1 é preciso aspas em argumentos como `"-out=x.tfplan"`; (2) `>` grava UTF-16 no PowerShell 5.1, então arquivos lidos pelo Terraform devem usar `Set-Content -Encoding ascii`; (3) em `google_storage_bucket`, `lifecycle_rule.action` e `.condition` são sets: nos testes use `one(one(x.lifecycle_rule).action)`, nunca `[0]`; (4) `deletion_policy = "DELETE"` (padrão 7.x) com `disable_on_destroy = false`: o destroy só remove a API do state e a deixa habilitada; o bucket com `force_destroy = false` falha no destroy se tiver objetos, então a T56 aplica `force_destroy = true` antes (detalhes no `tasks.md`, T26); (5) o `terraform test` não enumera recursos do plano: a lista fechada de tipos é verificada por pytest estático (`tests/infra/`), padrão a repetir nos módulos e em `envs/prod`; (6) o provider 8.x já existe, mas o Design mantém `~> 7.0`; (7) o bucket novo tem soft delete padrão de 7 dias (`soft_delete_policy`, sem custo relevante)
- **In-progress** (file:line): none
- **Next step**: Após o merge de `feat/tf-bootstrap` na `main` (PR pelo site do GitHub), atualizar a `main` local, criar `feat/tf-modules-base` e iniciar a T27 (módulo `apis`). Nada com custo nas T27-T31 (só `terraform test` com `mock_provider`)
- **Blockers**: none
- **Uncommitted files**: none após os commits do fechamento da Fase 5
- **Branch**: feat/tf-bootstrap
