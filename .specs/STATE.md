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

### AD-007
- **Decision**: O acesso SSH à VM é feito exclusivamente por túnel IAP (`gcloud compute ssh --tunnel-through-iap`). O firewall libera `tcp:22` somente da faixa do IAP `35.235.240.0/20` para a tag `book-monitor` (regra `book-monitor-allow-iap-ssh`); a variável `allowed_ssh_cidr` deixa de existir (módulo `network` e `envs/prod`); `iap.googleapis.com` entra na lista de APIs de `envs/prod` (4 APIs); o output `ssh_command` passa a incluir `--tunnel-through-iap`. Nenhuma role IAM nova no Terraform: se o túnel falhar por permissão, decide-se na T52 com o erro em mãos.
- **Reason**: A máquina do autor fica numa rede corporativa com Netskope (o IP de saída, 163.116.228.50, é do proxy, compartilhado e possivelmente diferente do IP real da conexão na porta 22) e o IP residencial é dinâmico; um `/32` não é confiável.
- **Trade-off**: Depende do IAP e do `gcloud` para qualquer acesso à VM; a VM mantém o IP externo efêmero (precisa de saída para a internet, sem NAT), mas a porta 22 deixa de aceitar origens fora da faixa do IAP. Substitui o CIDR do usuário e o ajuste de escopo `/24` da T28. Não confirmado por documentação: se o papel Owner já tem `iap.tunnelInstances.accessViaIAP` e se `iap.googleapis.com` é obrigatória para o túnel TCP.
- **Scope**: Spec (TFP-01, TFP-04, TFP-05, TFP-10, TFP-11), Design (rede, APIs, outputs), módulos `network` e `compute_vm`, `envs/prod`, T42 e tasks operacionais T51-T52.
- **Date**: 2026-11-09
- **Status**: active

## Handoff

- **Feature**: .specs/features/book-price-monitor
- **Phase / Task**: Fase 8 concluída (T37-T42); gate Build verde: Quick (115 testes unit, ruff) + `pytest -m infra` (58, 0 skip) + Infra executado pelo autor (`fmt -check -recursive terraform`, `validate` e `terraform test`: network 3, compute_vm 27, envs/prod 15 `run` blocks passando) + plan real de `envs/prod` (T42): `Plan: 10 to add, 0 to change, 0 to destroy`, sem `apply`. Fase 9 (T43-T50, `docs/operations`) ainda não iniciada
- **Completed**: Fases 1 a 7 mergeadas; Fase 8 implementada em `terraform/envs/prod/`: `versions.tf`, `providers.tf`, `backend.tf` (backend `gcs` parcial, só `prefix`), `variables.tf`, `main.tf` (compõe `apis` com 4 APIs e `network`, `identity`, `compute_vm`, `budget` com `depends_on = [module.apis]`), `outputs.tf`, `terraform.tfvars.example`, `backend.hcl.example`, `tests/{variables,main,outputs}.tftest.hcl`; `tests/unit/test_repo_hygiene.py` e `tests/infra/test_prod_{variables,composition}.py`. Mudança de escopo AD-007 (SSH só por túnel IAP) aplicada em network, compute_vm, envs/prod, Spec e Design. Ajuste do mecanismo de renderização da T32 (hash do template no lugar do `mtime`). Rastreabilidade da Spec: TFP-02, 05, 08, 10 e 13 `Implemented`; TFP-01, 03, 04, 06, 07, 09, 11 e 12 `In progress` (completam em T49, T51 e T55)
- **Achados da Fase 5 e 6**: seguem valendo (ver `tasks.md`, T26 e T27-T30): aspas em `"-out=x.tfplan"` no PowerShell 5.1; `>` grava UTF-16 (usar `Set-Content -Encoding ascii`); blocos aninhados com `one(...)` e sets com `toset([...])`; `override_during = plan` em `run` com `command = plan`; validação com `split("/", x)[1]` precisa de `try(..., false)`; o `terraform test` não enumera recursos do plano (lista fechada via pytest estático); o `backend.hcl` real está em `terraform/envs/prod/backend.hcl` (gitignored) e o state do bootstrap é local em `terraform/bootstrap/terraform.tfstate` (gitignored; não apagar: o destroy da T56 depende dele)
- **Achados da Fase 7** (seguem valendo): o template do startup script é só ASCII e usa `$VAR` sem chaves para o bash (`${nome}` é do Terraform; `$${`/`%%{` são literais); as 6 chaves do `templatefile` devem ser iguais em `locals.tf` e `tests/render/main.tf`; em `google_compute_instance`, `boot_disk`, `scheduling` e `network_interface` são listas de um item (`one(...)`) e o `project` é computado (o teste usa `override_resource` + `override_during = plan`); a metadata herda `sensitive` da `db_password`; a senha do Postgres é fixada na primeira inicialização do volume; o startup script falha antes de criar o `.env` se a metadata não responder. **Renderização (substitui o mecanismo por `mtime`)**: o autor roda, na raiz, `terraform -chdir=terraform/modules/compute_vm/tests/render apply -auto-approve` e `... output -json | Set-Content -Encoding ascii .rendered-startup.json` (todos os outputs); o pytest compara o `template_sha256` do JSON com o SHA-256 do `startup.sh.tftpl` atual, então trocar de branch não invalida o JSON; **`skip` por JSON ausente = gate Infra não cumprido**
- **Achados da Fase 8** (para as fases seguintes): (1) AD-007: o SSH é só por IAP (`gcloud compute ssh ... --tunnel-through-iap`, firewall `book-monitor-allow-iap-ssh` de `35.235.240.0/20`, 4 APIs com `iap.googleapis.com`); não confirmado em documentação se o Owner já tem `iap.tunnelInstances.accessViaIAP`: se o túnel falhar por permissão na T52, decidir lá (candidato: `google_iap_tunnel_instance_iam_member`, que sairia da lista fechada de 7 tipos); (2) `init -backend=false` em `envs/prod` desconfigura o backend GCS: antes de `plan`/`apply` rodar `terraform -chdir=terraform/envs/prod init -reconfigure "-backend-config=backend.hcl"`; (3) `override_data`/`override_resource` em escopo de arquivo aceitam alvos de módulo filho (`module.budget.data.google_project.this`, `module.compute_vm.google_compute_instance.this`); (4) `terraform.tfvars` local de `envs/prod` está preenchido e gitignored; a senha vai só por `$env:TF_VAR_db_password` (24 caracteres `[A-Za-z0-9]`, definida na sessão do PowerShell): **guardar a senha no gerenciador do autor, pois a T51 precisa da mesma** (a senha do Postgres é fixada na primeira inicialização do volume); `prod.tfplan` contém a senha em texto e deve ser apagado; (5) o plano mostrou as 4 APIs como criação (nenhuma estava gerenciada), então o primeiro `apply` pode dar 403 transitório por consistência eventual: reexecutar; (6) o `display_name` do budget é `book-price-monitor-book-price-monitor-jc` (repetição cosmética do prefixo + `project_id`; corrigir só se o autor quiser); (7) a rede corporativa (Netskope) deixou `init`/`plan` no GCS funcionarem sem erro de certificado
- **In-progress** (file:line): none
- **Next step**: Merge de `feat/tf-prod` na `main` pelo Pull Request no site do GitHub (sem squash), atualizar a `main` local, criar `docs/operations` e iniciar a T43 (`docs/gcp-setup.md`). Os runbooks devem refletir o AD-007 (SSH por IAP, sem `allowed_ssh_cidr`)
- **Blockers**: none
- **Uncommitted files**: none após os commits de fechamento da Fase 8 (`terraform.tfvars`, `backend.hcl`, `.rendered-startup.json` e `*.tfstate` são gitignored; apagar `prod.tfplan`)
- **Branch**: feat/tf-prod
