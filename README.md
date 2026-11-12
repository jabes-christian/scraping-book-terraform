# Book Price Monitor

Projeto de estudo: um robô em Python + Selenium que monitora os preços de [books.toscrape.com](https://books.toscrape.com), grava o histórico no PostgreSQL e roda em Docker Compose, localmente e numa VM da GCP provisionada com Terraform. O robô é simples de propósito; o foco do projeto é **levar um mini RPA do desenvolvimento local até produção com infraestrutura como código**, dentro do Free Tier.

## Visão geral

- **Robô** (`src/book_monitor/`): Chrome headless percorre as 50 categorias do site e coleta título, preço, disponibilidade e URL de cada livro (1.000 itens por coleta).
- **Banco** (PostgreSQL em container): `price_history` guarda um preço por livro por execução, `books` guarda o catálogo e `executions` registra início, fim, status e erro de cada coleta.
- **Local**: `docker compose run --rm robo`, execução manual.
- **Produção (GCP)**: uma VM `e2-micro` roda o mesmo Compose, com cron diário (06:00 UTC). O código chega à VM por `git clone` do repositório e a imagem é construída lá mesmo.
- **Terraform**: rede, VM, identidade, orçamento e o bucket do state remoto, em módulos reaproveitáveis para o Azure.

```
Local:     você ──► docker compose run robo ──► postgres (container)

Produção:  cron (VM e2-micro) ──► docker compose run robo ──► postgres (container + volume)
           Terraform ──► VPC, firewall (SSH só por IAP), VM, service account, orçamento
                     └─► bucket GCS (state remoto)
```

## Pré-requisitos

| Para... | Você precisa de |
| ------- | --------------- |
| Rodar localmente | Python 3.13 (com `.venv`), Docker Desktop e `git` |
| Provisionar a produção | Terraform `>= 1.9`, `gcloud` CLI, um projeto GCP com faturamento ativo |

Os comandos dos guias são PowerShell, executados a partir da raiz do projeto, e usam sempre o Python do ambiente virtual (`.venv\Scripts\python.exe`).

## Do local à produção

1. **Rodar localmente.** Instale as dependências, crie o `.env`, suba o Postgres e rode uma coleta: [docs/local-development.md](docs/local-development.md).
2. **Preparar o GCP.** Autenticação (ADC), bucket do state (bootstrap) e variáveis de `envs/prod`: [docs/gcp-setup.md](docs/gcp-setup.md).
3. **Entender a infraestrutura.** Módulos, ordem de aplicação e guardas de Free Tier: [terraform/README.md](terraform/README.md).
4. **Operar.** Atualizar o código da VM ([docs/update-code.md](docs/update-code.md)), acompanhar custo e disco ([docs/cost-and-billing.md](docs/cost-and-billing.md)).
5. **Destruir.** Remover tudo o que gera custo: [docs/destroy.md](docs/destroy.md).

## Documentação

| Documento | Conteúdo |
| --------- | -------- |
| [docs/local-development.md](docs/local-development.md) | Ambiente local: `.env`, Docker Compose, consulta às tabelas, testes e markers |
| [docs/gcp-setup.md](docs/gcp-setup.md) | Preparação do GCP e do Terraform: ADC, bootstrap, `backend.hcl`, senha do banco, SSH por IAP, problemas comuns |
| [terraform/README.md](terraform/README.md) | Estrutura, módulos, entradas e saídas, guardas de Free Tier, testes do Terraform |
| [docs/update-code.md](docs/update-code.md) | Como o código chega à VM e como atualizá-lo (`repo_ref`) |
| [docs/cost-and-billing.md](docs/cost-and-billing.md) | Free Tier, Billing Report, orçamento (só notifica) e uso de disco |
| [docs/destroy.md](docs/destroy.md) | `terraform destroy` de `envs/prod` e do bootstrap, na ordem correta |
| [docs/azure-mapping.md](docs/azure-mapping.md) | Equivalentes no Azure de cada módulo GCP e as diferenças |

## Estrutura do repositório

```
src/book_monitor/   # robô (config, scraping, banco, runner)
tests/              # unit, integration, docker, infra e e2e
terraform/          # bootstrap, módulos e envs/prod
docs/               # runbooks
.specs/             # especificação, design, tarefas e decisões (SDD)
Dockerfile, docker-compose.yml, .env.example
```

## Segurança e custo

- Nada de segredos no repositório: só os arquivos `*.example` são versionados (`.env.example`, `terraform.tfvars.example`, `backend.hcl.example`). `.env`, `*.tfvars`, `backend.hcl`, `*.tfstate` e `*.tfplan` ficam locais e estão no `.gitignore`.
- A conta de faturamento é paga: o orçamento de R$ 5 apenas **notifica**, não limita o gasto. O corte real é o `terraform destroy`.
- O repositório precisa ser público (a VM clona sem credenciais) e não pode conter segredos.

## Decisões e especificação

O projeto segue o fluxo Spec-Driven Development. Os requisitos, o design, as tarefas e as decisões de arquitetura (AD-001 a AD-007) estão em [`.specs/`](.specs/): [spec](.specs/features/book-price-monitor/spec.md), [design](.specs/features/book-price-monitor/design.md), [tarefas](.specs/features/book-price-monitor/tasks.md) e [STATE](.specs/STATE.md).
