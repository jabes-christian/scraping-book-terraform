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
- **Phase / Task**: Fase 7 concluída (T31-T36); gate Build verde: Quick (109 testes unit, ruff) + `pytest -m infra` (32, 0 skip) + Infra executado pelo autor (`fmt -check -recursive terraform` e `validate` + `terraform test` nos 5 módulos e no bootstrap: compute_vm 27, apis 4, network 9, identity 3, budget 6, bootstrap 17 `run` blocks passando). Fase 8 (T37-T42, `feat/tf-prod`) ainda não iniciada
- **Completed**: Fases 1 a 6 mergeadas; Fase 7 implementada em `terraform/modules/compute_vm/`: `variables.tf` (T31, com adição aprovada: `db_password` só `[A-Za-z0-9_.-]` e mínimo 16 caracteres, porque o Compose altera caracteres especiais ao ler o `.env`), `startup.sh.tftpl` + `locals.tf` (T32-T34: swap, pacotes, Docker, código sob `flock`, `.env` só se ausente, build, cron e logrotate), `main.tf` (T35: `google_compute_instance.this`, nome fixo `book-monitor` num `local`) e `outputs.tf` (T36). Testes: `tests/main.tftest.hcl` (27 `run` blocks, `mock_provider`), `tests/render/main.tf` (config só com `output`, sem provider), `tests/infra/test_startup_script.py`, `test_compute_vm_variables.py` e `test_compute_vm_resources.py`. Rastreabilidade da Spec: TFP-07, 08, 10, 11, 12 e VM-01, 02, 03, 04, 05, 07, 09, 10 `In progress` (completam em T38-T41 e nas tasks operacionais T51-T55)
- **Achados da Fase 5 e 6**: seguem valendo (ver `tasks.md`, T26 e T27-T30): aspas em `"-out=x.tfplan"` no PowerShell 5.1; `>` grava UTF-16 (usar `Set-Content -Encoding ascii`); blocos aninhados com `one(...)` e sets com `toset([...])`; `override_during = plan` em `run` com `command = plan`; validação com `split("/", x)[1]` precisa de `try(..., false)`; o `terraform test` não enumera recursos do plano (lista fechada via pytest estático); o `backend.hcl` real está em `terraform/envs/prod/backend.hcl` (gitignored) e o state do bootstrap é local em `terraform/bootstrap/terraform.tfstate` (gitignored; não apagar: o destroy da T56 depende dele)
- **Achados da Fase 7** (para as fases seguintes): (1) mecanismo de renderização do startup script (aprovado): o autor roda, na raiz, `terraform -chdir=terraform/modules/compute_vm/tests/render apply -auto-approve` e `... output -json script | Set-Content -Encoding ascii .rendered-startup.json` (o `-auto-approve` só é aceito nessa config, sem recursos); o pytest (`tests/infra/test_startup_script.py`) lê o JSON, roda `bash -n` com o bash do Git e falha se o JSON estiver mais velho que o `.tftpl`; **`skip` por JSON ausente = gate Infra não cumprido**; (2) o template é só ASCII (o `Set-Content -Encoding ascii` troca acentos por `?`) e usa `$VAR` sem chaves para o bash; `${nome}` é do Terraform e `$${`/`%%{` são literais; as 6 chaves do `templatefile` (`swap_size_mb`, `repo_url`, `repo_ref`, `db_name`, `db_user`, `cron_schedule`) devem ser iguais em `locals.tf` e `tests/render/main.tf` (teste estático confere); (3) em `google_compute_instance`, `boot_disk`, `scheduling` e `network_interface` são listas de um item (`one(...)`), e o `project` é computado: o output `ssh_command` usa `google_compute_instance.this.project` e o teste simula o valor com `override_resource` + `override_during = plan`; (4) a metadata herda `sensitive` da `db_password` (a CLI mostra `(sensitive value)`); (5) `envs/prod` precisa passar ao `compute_vm` as entradas `subnetwork`, `network_tag`, `service_account_email`, `repo_url`, `repo_ref`, `db_password` (obrigatórias, sem default) e opcionalmente `db_name`, `db_user`, `zone`, `cron_schedule`, `swap_size_mb`, `boot_disk_size_gb`; a `db_password` do `terraform.tfvars` deve seguir a validação (16+ caracteres de `[A-Za-z0-9_.-]`); (6) a senha do Postgres é fixada na primeira inicialização do volume (trocar a variável não altera o banco); o startup script falha antes de criar o `.env` se a metadata não responder
- **In-progress** (file:line): none
- **Next step**: Após o merge de `feat/tf-compute-vm` na `main` (PR pelo site do GitHub), atualizar a `main` local, criar `feat/tf-prod` e iniciar a T37 (esqueleto de `envs/prod`: `versions.tf`, `providers.tf`, `backend.tf`). T37-T41 são só código e testes; a T42 é o `plan` real (leitura, exige OK e ADC) e não faz `apply`
- **Blockers**: none
- **Uncommitted files**: none após os commits do fechamento da Fase 7
- **Branch**: feat/tf-compute-vm
