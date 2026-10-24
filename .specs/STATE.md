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

## Handoff

- **Feature**: .specs/features/book-price-monitor
- **Phase / Task**: Design concluído, aguardando aprovação
- **Completed**: none
- **In-progress** (file:line): none
- **Next step**: Após aprovação do design, criar `tasks.md`
- **Blockers**: none
- **Uncommitted files**: prd.md, spec.md, design.md, STATE.md
- **Branch**: docs/sdd-planning
