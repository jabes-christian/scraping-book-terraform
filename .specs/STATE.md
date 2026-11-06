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
- **Phase / Task**: Fase 6 concluída (T27-T30); gate Build verde: Quick (109 testes unit, ruff) + `pytest -m infra` (4) + Infra executado pelo autor nos 4 módulos (`fmt -check`, `validate`, `terraform test`: apis 4, network 9, identity 3, budget 6 `run` blocks passando). Fase 7 (T31-T36, `feat/tf-compute-vm`) ainda não iniciada
- **Completed**: Fases 1 a 5 mergeadas; Fase 6 implementada em `terraform/modules/`: `apis` (T27), `network` (T28, com adição aprovada: prefixo mínimo /24 em `allowed_ssh_cidr`), `identity` (T29), `budget` (T30). Cada módulo tem `versions.tf`, `variables.tf`, `main.tf`, `outputs.tf`, `.terraform.lock.hcl` e `tests/main.tftest.hcl` (`mock_provider`); `tests/infra/test_identity_resources.py` e `test_budget_resources.py` garantem estaticamente a lista fechada de recursos. Rastreabilidade da Spec: TFP-01, 03, 04, 05, 06, 09, 12 `In progress` (composição em `envs/prod`: T38, T39, T51, T55); TFP-13 `In progress` (T37, T39); TFB-01 a TFB-05 `Implemented`. Da Fase 5 seguem valendo: o `backend.hcl` real está em `terraform/envs/prod/backend.hcl` (gitignored) e o state do bootstrap é local em `terraform/bootstrap/terraform.tfstate` (gitignored; não apagar: o destroy da T56 depende dele); bucket `book-price-monitor-jc-tfstate` criado pela T26
- **Achados da Fase 5**: (1) no PowerShell 5.1 é preciso aspas em argumentos como `"-out=x.tfplan"`; (2) `>` grava UTF-16 no PowerShell 5.1, então arquivos lidos pelo Terraform devem usar `Set-Content -Encoding ascii`; (3) em `google_storage_bucket`, `lifecycle_rule.action` e `.condition` são sets: nos testes use `one(one(x.lifecycle_rule).action)`, nunca `[0]`; (4) `deletion_policy = "DELETE"` (padrão 7.x) com `disable_on_destroy = false`: o destroy só remove a API do state e a deixa habilitada; o bucket com `force_destroy = false` falha no destroy se tiver objetos, então a T56 aplica `force_destroy = true` antes (detalhes no `tasks.md`, T26); (5) o `terraform test` não enumera recursos do plano: a lista fechada de tipos é verificada por pytest estático (`tests/infra/`); (6) o provider 8.x já existe, mas o Design mantém `~> 7.0`; (7) o bucket novo tem soft delete padrão de 7 dias (`soft_delete_policy`, sem custo relevante)
- **Achados da Fase 6** (para as fases seguintes): (1) `override_resource`/`override_data` só valem no apply por padrão; em `run` com `command = plan` use `override_during = plan` para atributos computados (e-mail da SA, número do projeto, nome do budget); (2) `allow` do firewall, `amount`, `specified_amount` e `budget_filter` são blocos: use `one(...)`, e `source_ranges`/`target_tags`/`projects` são sets (compare com `toset([...])`); (3) validação que indexa `split("/", x)[1]` precisa de `try(..., false)`, senão valor sem `/` vira erro de avaliação em vez de falha de validação; (4) pytest estático da lista de recursos por módulo já existe em bootstrap, identity e budget; para `apis`/`network` não foi criado, fica para o teste de `envs/prod`; (5) a fase 6 é T27-T30; a T31 pertence à Fase 7
- **In-progress** (file:line): none
- **Next step**: Após o merge de `feat/tf-modules-base` na `main` (PR pelo site do GitHub), atualizar a `main` local, criar `feat/tf-compute-vm` e iniciar a T31 (variáveis e guardas do `compute_vm`). Nada com custo nas T31-T36 (só `terraform test` com `mock_provider` e `pytest -m infra`)
- **Blockers**: none
- **Uncommitted files**: none após os commits do fechamento da Fase 6
- **Branch**: feat/tf-modules-base
