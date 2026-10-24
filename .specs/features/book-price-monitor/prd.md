# Book Price Monitor — PRD

Status: **aprovado** (2026-10-23, com ajustes) · Branch: `docs/sdd-planning`

## 1. Problema e motivação

Projeto de estudo. O objetivo real é aprender **Terraform + GCP** levando um mini RPA do desenvolvimento local até produção. O robô é deliberadamente simples; a infraestrutura como código é o foco.

## 2. Usuário

Uma pessoa (o autor), estudando. Não há usuários finais, UI nem SLA.

## 3. Produto

Robô Python + Selenium (Chrome headless) que raspa `books.toscrape.com` (categoria, título, preço, disponibilidade, URL) e grava no PostgreSQL:

- **histórico de preços** por execução (uma linha por livro por execução);
- **log de execuções** (início, fim, status, qtd. de itens, erro).

Execução agendada 1x/dia. Configuração 100% por variáveis de ambiente; código agnóstico de nuvem (replicação futura da infra no Azure).

## 4. Ambientes

| Ambiente | Como roda | Agendamento |
| --- | --- | --- |
| Local | Docker Compose: `robo` + `postgres`; o robô roda com `docker compose run --rm robo` | manual |
| Produção (GCP, cenário 1 "lift and shift") | 1 VM Compute Engine roda o mesmo Compose; Postgres em container com volume persistente | cron na VM |

Terraform provisiona: VPC/subnet, firewall (SSH só do IP do autor), service account de menor privilégio, VM com startup script (Docker + stack + cron), bucket GCS para remote state, budget alert. Estrutura modular (`modules/`, `envs/`, `variables`, `tfvars`, `outputs`) pensada para reaproveitar no Azure.

## 5. Fora de escopo

Cloud Run, Cloud SQL, Pub/Sub, qualquer serviço gerenciado fora da lista acima, CI/CD, dashboard/UI, alertas de preço, scraping de outros sites, Azure (só a estrutura deve permitir), HA/multi-VM.

## 6. Restrição central: somente Free Tier

### Fatos validados (docs oficiais, `docs.cloud.google.com/free/docs/free-cloud-features`, consultado em 2026-10-23)

| Recurso | Limite gratuito |
| --- | --- |
| Compute Engine | 1 VM `e2-micro` não-preemptível/mês, em `us-west1`, `us-central1` ou `us-east1` (horas combinadas = total de horas do mês) |
| Disco | 30 GB-mês de **standard persistent disk** (pd-standard) |
| Egress de rede | 1 GB/mês da América do Norte para qualquer destino (exceto China e Austrália) |
| Cloud Storage | 5 GB-mês regional, só `us-east1`/`us-west1`/`us-central1`; 5.000 ops Classe A e 50.000 Classe B/mês |
| Secret Manager | 6 versões ativas, 10.000 acessos/mês (não usaremos; ver decisão abaixo) |
| Logging | 50 GiB/mês por projeto |
| Budgets/alertas | A página não informa custo; budgets do Cloud Billing não geram cobrança por si |

Free Tier exige conta de billing ativa; o que exceder é cobrado (ou abatido do crédito de US$ 300 em conta Free Trial). Cotas não acumulam.

### Conta de faturamento: cobrança real

A conta de faturamento é **paga, em BRL, sem créditos** (trial expirado). Qualquer recurso fora do Free Tier gera cobrança real no cartão. Isso reforça a proibição de recursos pagos, o budget alert e a documentação do `terraform destroy`.

### Riscos de custo identificados

1. **IPv4 externo — NÃO CONFIRMADO.** Fontes conflitam: uma página de docs afirma (segundo busca) que o IP externo não é cobrado no free tier; materiais de 2026 dizem ~US$ 0,005/h (~US$ 3,65/mês). Não consegui abrir a seção de preços oficial (conteúdo truncado). **Decisão do autor:** aceita o IP externo efêmero e verificará no Billing Report nos primeiros dias.
2. **Disco default do console é `pd-balanced` (cobrado).** O Terraform deve fixar `pd-standard` e ≤ 30 GB.
3. **Egress > 1 GB/mês** é cobrado. O scraping é ingress (pull de imagens/pacotes também); o único egress relevante é SSH e eventual `docker pull` do Docker Hub (ingress). Risco baixo.
4. **Cloud NAT, Load Balancer, IP estático reservado ocioso, snapshots** não são gratuitos: **proibidos** no design.
5. **Mais de uma e2-micro** consome as horas gratuitas: máximo de uma VM.

### Restrição técnica: e2-micro (0,25 vCPU compartilhada, ~1 GB RAM)

Chrome + Chromedriver + Postgres competem por ~1 GB. O design tratará: swap file na VM, flags do Chrome headless (`--no-sandbox`, `--disable-dev-shm-usage`, `--disable-gpu`, janela mínima, bloqueio de imagens), `mem_limit` por container, scraping sequencial (1 aba), Postgres com `shared_buffers` reduzido. O robô só roda durante a janela do cron (container efêmero via `docker compose run --rm`), não fica residente.

## 7. Requisitos não funcionais

- **Segurança:** sem segredo hardcoded; sem chave de service account versionada (VM usa a SA anexada, sem key JSON; Terraform usa ADC); senhas em `.env` local e em metadata/variáveis na VM; `.env.example` versionado. SSH apenas do IP do autor. `*.tfvars` já está no `.gitignore` → versionar apenas `*.tfvars.example`.
- **Portabilidade:** zero SDK GCP no código Python; só `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, etc.
- **Observabilidade:** logs do robô em stdout (estruturados), tabela de execuções no banco.
- **Idempotência/falha:** uma falha de scraping registra a execução como `FAILED` com erro, sem derrubar o Postgres nem deixar dados parciais inconsistentes.
- **Custo:** budget alert de **R$ 5** (moeda da conta), e-mail em 50%, 90% e 100%, sem Pub/Sub nem automações; documentação de `terraform destroy`.
- **Dependências Python:** versões pinadas em `requirements.txt` (e `requirements-dev.txt` para testes/lint); a imagem Docker instala a partir dos mesmos arquivos. O `.venv` serve para desenvolvimento e testes fora do container; a execução oficial (local e produção) é via Docker Compose.

## 7.1 Dívida técnica registrada

- **Segredos via metadata da instância** são legíveis por quem tem acesso ao projeto e, de dentro da VM, por qualquer processo com acesso ao servidor de metadata. Aceito para o estudo. Evolução futura: Secret Manager.

## 8. Critérios de sucesso do projeto

- [ ] `docker compose run --rm robo` local executa o robô e popula as tabelas (~1.000 livros, 50 categorias), com o `postgres` do Compose no ar.
- [ ] Infra de produção sobe com **1 `terraform apply` na stack de bootstrap** (uma única vez; cria o bucket do remote state) **+ 1 `terraform apply` em `envs/prod`**. As APIs necessárias (Compute Engine, Billing Budgets etc.) são habilitadas pelo próprio Terraform via `google_project_service`. Pré-requisitos manuais: `terraform.tfvars` (a partir do `.example`) e ADC (`gcloud auth application-default login`).
- [ ] O cron da VM executa o robô 1x/dia e a execução aparece no log de execuções.
- [ ] A VM não é encerrada por OOM durante o scraping.
- [ ] Billing do mês fica em US$ 0 (ou apenas o IPv4, se confirmado como cobrado).
- [ ] `terraform destroy` remove tudo que gera custo (documentado e testado).
- [ ] Estrutura de módulos reaproveitável para Azure (documentada em um README de infra).

## 9. Decisões já tomadas (padrões adotados — contestem se discordarem)

| Decisão | Padrão adotado | Motivo |
| --- | --- | --- |
| Região | `us-central1` | Elegível para VM e bucket; reduz risco de divergência de região |
| Imagem | Debian 12 / Ubuntu 24.04 LTS minimal | Docker oficial disponível; leve |
| Chrome | Dentro do container `robo` (imagem Python slim + chromium/chromedriver) | Reprodutível local = prod |
| Segredos na VM | Metadata da instância → arquivo `.env` (chmod 600) pelo startup script | Secret Manager é grátis até 6 versões, mas adiciona complexidade; dívida técnica registrada (7.1) |
| Remote state | Bucket GCS com versionamento; bootstrap em stack separada | Evita ovo-e-galinha |
| Terraform | `>= 1.5`, provider `google` pinado | Verificar versão atual via docs na fase de Design |
| Idioma | Código e commits em inglês; docs em português | Conventional Commits |

## 10. Perguntas resolvidas

1. **IPv4 externo:** IP externo efêmero aceito; autor verifica o Billing Report nos primeiros dias.
2. **Escopo do scraping:** todas as 50 categorias. O Design avalia raspar só as páginas de listagem (título, preço, disponibilidade, URL), sem abrir a página de cada livro, para reduzir tempo e memória.
3. **Budget alert:** R$ 5; e-mail em 50%, 90% e 100%.
4. **Projeto GCP:** existente. `project_id` e `billing_account_id` são variáveis; valores reais no `terraform.tfvars` (não versionado), só `terraform.tfvars.example` no repositório.

## 11. Ambiente já configurado

**GCP (manual):** projeto `book-price-monitor-jc` com billing ativo; região/zona `us-central1` / `us-central1-a`; Terraform autentica via ADC (sem chave JSON) com quota project = o projeto. APIs `cloudresourcemanager` e `serviceusage` já habilitadas manualmente; Compute Engine e as demais estão desabilitadas de propósito e o Terraform as habilita.

**Local:** Python 3.13, `.venv/` na raiz (executar sempre por `.venv\Scripts\python.exe`; nunca instalar no Python global), Terraform e gcloud CLI instalados, Context7 autenticado.

## 12. Notas para o Design

- Imagem Docker do robô com Python 3.13, igual ao ambiente local.
- Acesso SSH à VM via `gcloud compute ssh`, com firewall restrito ao IP do autor.
- Budget alert via Terraform com ADC pode exigir `billing_project` e `user_project_override = true` no provider, além da API `billingbudgets.googleapis.com`. Validar via Context7.
- Definir `disable_on_destroy` nos `google_project_service`, considerando que `cloudresourcemanager` e `serviceusage` foram habilitadas fora do Terraform.

## 13. Pendências de pesquisa

- Confirmar a cobrança do IPv4 externo em e2-micro (via Billing Report, pelo autor).
