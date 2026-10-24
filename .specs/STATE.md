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
- **Decision**: A execução é dividida em 10 fases, cada uma em uma branch criada da `main` após o merge da anterior (merge sem squash, um commit por task); tasks operacionais (apply, VM, billing, destroy) não geram commit e exigem OK explícito; `docs/` é escrito antes da validação ao vivo.
- **Reason**: PRs pequenos e revisáveis; nada com custo ou efeito externo roda sem aprovação; os runbooks são validados na prática (fase 10).
- **Trade-off**: Mais branches e merges manuais; correções da validação ao vivo viram commits extras na fase 10.
- **Scope**: `tasks.md` e todo o Execute.
- **Date**: 2026-10-24
- **Status**: active

## Handoff

- **Feature**: .specs/features/book-price-monitor
- **Phase / Task**: Tasks gerado (56 tasks, 10 fases), aguardando aprovação
- **Completed**: PRD, Spec e Design aprovados; `tasks.md` criado; rastreabilidade da Spec atualizada (71/71 requisitos mapeados)
- **In-progress** (file:line): none
- **Next step**: Após aprovação das Tasks e merge de `docs/sdd-planning` na `main`, criar `feat/robot-foundation` e iniciar a T1. Ligar o Docker Desktop antes da fase 3
- **Blockers**: none
- **Uncommitted files**: `.specs/features/book-price-monitor/tasks.md`, `spec.md` (coluna Tasks), `design.md` (status), `STATE.md`
- **Branch**: docs/sdd-planning
