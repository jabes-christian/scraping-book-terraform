# Book Price Monitor Specification

Fonte: [prd.md](prd.md) (aprovado). Escopo: **Complex** (domínio novo: Terraform + GCP, restrição de Free Tier, hardware mínimo).

## Problem Statement

O autor quer aprender Terraform + GCP na prática, levando um mini RPA do desenvolvimento local até produção. O robô raspa `books.toscrape.com` diariamente e guarda o histórico de preços no PostgreSQL. A infra de produção (1 VM e2-micro dentro do Free Tier) é provisionada integralmente por Terraform, com módulos reaproveitáveis no Azure. A conta de faturamento é paga e sem créditos: qualquer recurso fora do Free Tier gera cobrança real.

## Goals

- [ ] Uma execução do robô coleta os ~1.000 livros das 50 categorias e grava histórico + log de execução.
- [ ] O mesmo `docker-compose.yml` roda localmente e na VM, sem alterar código.
- [ ] Produção sobe com 1 `apply` de bootstrap + 1 `apply` em `envs/prod`, e é removida por `terraform destroy`.
- [ ] Custo mensal de recursos faturáveis = R$ 0 (exceto o IPv4 externo, se cobrado), com budget alert de R$ 5.

## Out of Scope

| Feature | Reason |
| --- | --- |
| Cloud Run, Cloud SQL, Pub/Sub, Cloud NAT, Load Balancer, Artifact Registry, Secret Manager | Serviços fora do Free Tier ou fora do cenário 1 (Secret Manager é dívida técnica registrada) |
| CI/CD, dashboard/UI, alertas de preço, outros sites | Fora do objetivo de estudo |
| Infra Azure | Só a estrutura de módulos deve permitir reaproveitamento |
| HA, multi-VM, backup/snapshot do disco | Snapshots são cobrados; dados são reproduzíveis re-raspando |
| Criação do projeto GCP e da conta de faturamento | Já existem; entram como variáveis |
| Raspar a página individual de cada livro | Listagem já traz os campos necessários (decisão de Design confirma) |

---

## Assumptions & Open Questions

| Assumption / decision | Chosen default | Rationale | Confirmed? |
| --- | --- | --- | --- |
| Moeda dos preços | Armazenar valor em `NUMERIC(10,2)` + coluna `currency` = `GBP` | O site exibe £; guardar a moeda evita ambiguidade futura | y (PRD) |
| Chave natural do livro | URL absoluta da página do livro | Estável e única no site; título pode repetir | n |
| Granularidade do histórico | 1 linha em `price_history` por livro por execução (inclui execuções sem mudança de preço) | Simples, consulta direta; ~1.000 linhas/dia ≈ 365 mil/ano, dezenas de MB | n |
| Atomicidade da execução | Linhas de preço gravadas em uma única transação ao fim da coleta; falha = nenhuma linha de preço da execução | Evita histórico parcial inconsistente; 1.000 itens cabem na memória | n |
| Retry de rede | Até 3 tentativas por requisição, espera de 2 s, 4 s e 8 s | Valores concretos e testáveis; `SCRAPE_MAX_RETRIES` configurável | n |
| Intervalo entre requisições | 0,5 s (`SCRAPE_DELAY_SECONDS`) | Cortesia com o site e menor pico de CPU na e2-micro | n |
| Horário do cron | 06:00 UTC diário (`cron_schedule` variável) | Horário calmo; fuso da VM em UTC | n |
| Execução abandonada | Execução `RUNNING` há mais de 2 h é marcada `FAILED` (erro `abandoned`) no início da próxima | Cobre OOM-kill/reboot no meio da coleta, sem job externo | n |
| Retenção dos dados | Indefinida (sem expurgo) | 30 GB sobram por muitos anos; não precisa de TTL | n |
| Entrega da imagem do robô na VM | Startup script clona o repositório via HTTPS e roda `docker compose build` na VM | Artifact Registry é pago acima de 0,5 GB e a imagem com Chromium passa disso; Docker Hub público expõe a imagem. **Exige repositório público** ou outra forma de entrega | **n — depende do autor** |
| Papel da service account da VM | Somente `roles/logging.writer`; sem outras roles de projeto | Menor privilégio; a VM não chama APIs GCP | n |
| Entrega de e-mail do budget | Canal de notificação por e-mail (Cloud Monitoring) com `budget_alert_email` | Evita Pub/Sub; o Design valida via Context7 | n |
| `disable_on_destroy` das APIs | `false` em todos os `google_project_service` | `cloudresourcemanager`/`serviceusage` foram habilitadas fora do Terraform; destruir não deve desligar APIs | n |
| Versão do robô local x VM | Mesmo `Dockerfile` e mesmo Compose, diferenças só em variáveis de ambiente | Reprodutibilidade; paridade dev/prod | y |
| Idioma | Código, logs e commits em inglês; docs em português | PRD | y |

**Open questions:** none - all resolved or logged above. A linha "Entrega da imagem" aguarda confirmação do autor antes do Design.

---

## User Stories

### P1: Coletar categorias e livros ⭐ MVP

**User Story**: Como autor, quero que o robô percorra todas as categorias e páginas do site para ter título, preço, disponibilidade e URL de cada livro.

**Why P1**: É o núcleo funcional do RPA.

**Acceptance Criteria**:

1. WHEN o robô inicia a coleta THEN the system SHALL obter a lista de categorias a partir da página inicial do site, sem lista fixa no código <!-- SCR-01 -->
2. WHEN uma categoria tem mais de uma página de listagem THEN the system SHALL percorrer todas as páginas até não existir link "next" <!-- SCR-02 -->
3. WHEN uma página de listagem é lida THEN the system SHALL extrair, para cada livro, categoria, título completo (atributo `title` do link, não o texto truncado), preço numérico, disponibilidade em texto e URL absoluta <!-- SCR-03 -->
4. WHEN a coleta de uma categoria termina THEN the system SHALL comparar a quantidade coletada com o total "N results" exibido pelo site <!-- SCR-04 -->
5. IF a quantidade coletada de uma categoria diverge do total exibido pelo site THEN the system SHALL falhar a execução com o erro `count mismatch` e o nome da categoria <!-- SCR-05 -->
6. IF uma requisição falha por timeout ou HTTP 5xx THEN the system SHALL repetir até 3 tentativas com espera de 2 s, 4 s e 8 s antes de falhar a execução <!-- SCR-06 -->
7. IF o preço de um livro não pode ser convertido em número THEN the system SHALL falhar a execução com o erro contendo a URL do livro <!-- SCR-07 -->
8. The system SHALL esperar `SCRAPE_DELAY_SECONDS` (padrão 0,5 s) entre requisições de páginas consecutivas <!-- SCR-08 -->
9. The system SHALL usar Chrome headless via Selenium para carregar as páginas <!-- SCR-09 -->

**Independent Test**: Rodar o robô contra o site real e conferir que o número de itens coletados é 1.000 (soma dos "N results" das 50 categorias) e que todos os campos estão preenchidos.

---

### P1: Persistir histórico e log de execuções ⭐ MVP

**User Story**: Como autor, quero que cada execução grave os preços observados e um registro de execução para consultar a evolução dos preços e diagnosticar falhas.

**Why P1**: Sem persistência não há histórico nem como saber se o agendamento funcionou.

**Acceptance Criteria**:

1. WHEN o robô inicia e o schema não existe THEN the system SHALL criar as tabelas `books`, `price_history` e `executions` automaticamente <!-- DB-01 -->
2. WHEN o robô inicia THEN the system SHALL inserir uma linha em `executions` com `started_at` e status `RUNNING` antes de iniciar a coleta <!-- DB-02 -->
3. WHEN a coleta termina sem erro THEN the system SHALL gravar, em uma única transação, o upsert de cada livro em `books` (chave: URL) e uma linha em `price_history` por livro ligada à execução <!-- DB-03 -->
4. WHEN a gravação é concluída THEN the system SHALL atualizar a execução com `finished_at`, status `SUCCESS` e `items_count` igual ao número de linhas de preço gravadas <!-- DB-04 -->
5. IF qualquer erro ocorre durante a execução THEN the system SHALL atualizar a execução com `finished_at`, status `FAILED` e a mensagem de erro truncada em 2.000 caracteres, sem gravar linhas de `price_history` dessa execução <!-- DB-05 -->
6. WHEN o robô inicia THEN the system SHALL marcar como `FAILED` com erro `abandoned` toda execução `RUNNING` com `started_at` anterior a 2 horas <!-- DB-06 -->
7. IF o PostgreSQL está inacessível ao iniciar THEN the system SHALL tentar reconectar por até 60 s e, esgotado o prazo, encerrar com código de saída 1 e mensagem sem credenciais <!-- DB-07 -->
8. WHEN o container `postgres` é recriado ou a VM reinicia THEN the system SHALL preservar todos os dados anteriores no volume persistente <!-- DB-08 -->
9. The system SHALL armazenar o preço como `NUMERIC(10,2)` com a moeda `GBP` <!-- DB-09 -->

**Independent Test**: Executar duas vezes; `executions` mostra 2 linhas `SUCCESS` com `items_count` = 1.000 e `price_history` tem 2.000 linhas; derrubar a rede no meio de uma terceira execução e ver `FAILED` sem novas linhas de preço.

---

### P1: Configuração por ambiente e execução agnóstica de nuvem ⭐ MVP

**User Story**: Como autor, quero configurar o robô só por variáveis de ambiente para rodar igual no local, no GCP e no futuro no Azure.

**Why P1**: É requisito de portabilidade e segurança.

**Acceptance Criteria**:

1. The system SHALL ler toda configuração (`DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `SCRAPE_DELAY_SECONDS`, `SCRAPE_MAX_RETRIES`, `LOG_LEVEL`) de variáveis de ambiente <!-- CFG-01 -->
2. IF uma variável obrigatória (`DB_HOST`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`) está ausente THEN the system SHALL encerrar com código de saída 2 e uma mensagem que cita o nome da variável ausente <!-- CFG-02 -->
3. The system SHALL NOT escrever o valor de `DB_PASSWORD` em logs, mensagens de erro ou na tabela `executions` <!-- CFG-03 -->
4. The system SHALL NOT importar SDKs de provedor de nuvem no código Python <!-- CFG-04 -->
5. WHEN a execução termina THEN the system SHALL encerrar com código de saída 0 se `SUCCESS` e 1 se `FAILED` <!-- CFG-05 -->
6. The system SHALL emitir logs em formato JSON, uma linha por evento, na saída padrão <!-- CFG-06 -->
7. The system SHALL declarar dependências Python com versões pinadas em `requirements.txt` (e `requirements-dev.txt` para ferramentas de teste) <!-- CFG-07 -->

**Independent Test**: Rodar com `DB_PASSWORD` removida e ver exit code 2 citando a variável; fazer `grep` do valor da senha nos logs de uma execução completa e não encontrar nada.

---

### P1: Ambiente local com Docker Compose ⭐ MVP

**User Story**: Como autor, quero rodar a stack local com Docker Compose para desenvolver e validar antes de ir para produção.

**Why P1**: Primeiro degrau do caminho "local → produção".

**Acceptance Criteria**:

1. WHEN o autor executa `docker compose run --rm robo` THEN the system SHALL subir o serviço `postgres`, aguardar seu healthcheck e então executar o robô <!-- LOC-01 -->
2. The system SHALL construir a imagem do `robo` a partir de Python 3.13 com Chromium e driver compatíveis e executar o processo como usuário não-root <!-- LOC-02 -->
3. The system SHALL persistir os dados do `postgres` em um volume nomeado <!-- LOC-03 -->
4. The system SHALL definir `mem_limit` para os serviços `robo` e `postgres` no Compose, com valores que somados cabem na RAM de uma e2-micro (≈ 1 GB) <!-- LOC-04 -->
5. The system SHALL ler as variáveis de um arquivo `.env` não versionado e fornecer `.env.example` versionado sem segredos <!-- LOC-05 -->
6. The system SHALL iniciar o Chrome com flags de baixo consumo (headless, `--disable-dev-shm-usage`, `--disable-gpu`, sem carregar imagens) <!-- LOC-06 -->

**Independent Test**: `docker compose run --rm robo` em máquina limpa, só com `.env` copiado do exemplo, termina com exit code 0 e popula as tabelas.

---

### P1: Bootstrap do remote state ⭐ MVP

**User Story**: Como autor, quero uma stack de bootstrap que cria o bucket do remote state para que o state de produção não fique só na minha máquina.

**Why P1**: Pré-requisito de `envs/prod`; evita o problema ovo-e-galinha.

**Acceptance Criteria**:

1. WHEN o autor executa `terraform apply` na stack de bootstrap THEN the system SHALL habilitar a API `storage.googleapis.com` e criar um bucket GCS em `us-central1` <!-- TFB-01 -->
2. The system SHALL criar o bucket com versionamento ligado, acesso uniforme e prevenção de acesso público <!-- TFB-02 -->
3. The system SHALL receber `project_id` e `billing_account_id` (quando aplicável) e o nome do bucket por variáveis, sem valores reais versionados <!-- TFB-03 -->
4. WHEN o bootstrap termina THEN the system SHALL exibir em `outputs` o nome do bucket para uso no backend de `envs/prod` <!-- TFB-04 -->
5. IF o `project_id` não é informado THEN the system SHALL falhar na validação de variáveis antes de qualquer chamada à API <!-- TFB-05 -->

**Independent Test**: `terraform apply` no bootstrap; `gcloud storage buckets describe` mostra região `US-CENTRAL1` e versioning habilitado.

---

### P1: Infraestrutura de produção no GCP ⭐ MVP

**User Story**: Como autor, quero um único `apply` em `envs/prod` que crie rede, firewall, service account, VM e budget alert, tudo dentro do Free Tier.

**Why P1**: É o objetivo principal do estudo.

**Acceptance Criteria**:

1. WHEN o autor executa `terraform apply` em `envs/prod` THEN the system SHALL habilitar via `google_project_service` as APIs `compute.googleapis.com`, `billingbudgets.googleapis.com` e as demais necessárias, antes de criar os recursos que dependem delas <!-- TFP-01 -->
2. The system SHALL usar o bucket de bootstrap como backend remoto do state, com o nome informado na configuração do backend <!-- TFP-02 -->
3. The system SHALL criar uma VPC customizada e uma subnet em `us-central1` <!-- TFP-03 -->
4. The system SHALL criar regras de firewall que permitem ingress somente TCP 22 a partir de `allowed_ssh_cidr` <!-- TFP-04 -->
5. IF `allowed_ssh_cidr` é `0.0.0.0/0` THEN the system SHALL falhar a validação da variável <!-- TFP-05 -->
6. The system SHALL criar uma service account dedicada para a VM com apenas `roles/logging.writer` e sem chave JSON <!-- TFP-06 -->
7. The system SHALL criar exatamente uma VM `e2-micro` não-preemptível em `us-central1-a`, com disco de boot `pd-standard` de no máximo 30 GB <!-- TFP-07 -->
8. The system SHALL NOT criar Cloud NAT, load balancer, IP estático reservado, snapshot, Cloud SQL, Pub/Sub, Artifact Registry nem Secret Manager <!-- TFP-08 -->
9. The system SHALL criar um budget alert de R$ 5 (moeda da conta) com notificação por e-mail em 50%, 90% e 100%, sem Pub/Sub <!-- TFP-09 -->
10. The system SHALL receber `project_id`, `billing_account_id`, `allowed_ssh_cidr`, `budget_alert_email` e a senha do banco por variáveis, com `sensitive = true` na senha, e fornecer `terraform.tfvars.example` sem valores reais <!-- TFP-10 -->
11. WHEN o `apply` termina THEN the system SHALL expor em `outputs` o nome da VM, a zona e o comando `gcloud compute ssh` pronto <!-- TFP-11 -->
12. The system SHALL organizar o código em `modules/` reutilizáveis (rede, compute, iam, budget, apis) e `envs/prod` que apenas os compõe <!-- TFP-12 -->
13. The system SHALL definir `disable_on_destroy = false` nos `google_project_service` <!-- TFP-13 -->

**Independent Test**: `terraform plan` em `envs/prod` lista somente os recursos esperados; `terraform apply` termina sem erro; `gcloud compute instances list` mostra uma e2-micro.

---

### P1: Runtime da VM e agendamento ⭐ MVP

**User Story**: Como autor, quero que a VM suba sozinha a stack e execute o robô 1x/dia sem intervenção.

**Why P1**: Fecha o caminho até produção e entrega o valor diário.

**Acceptance Criteria**:

1. WHEN a VM é criada THEN the system SHALL executar o startup script que instala Docker e o plugin Compose, cria o swap file, obtém o código, escreve o `.env` (permissão 600) a partir da metadata e sobe o `postgres` <!-- VM-01 -->
2. The system SHALL configurar um swap file de 1 GB e `vm.swappiness` documentado antes de qualquer build ou execução do robô <!-- VM-02 -->
3. The system SHALL registrar uma entrada de cron diária (`cron_schedule`, padrão `0 6 * * *` UTC) que executa `docker compose run --rm robo` <!-- VM-03 -->
4. IF a execução anterior do cron ainda está rodando THEN the system SHALL pular a nova execução sem iniciar um segundo robô (uso de `flock`) <!-- VM-04 -->
5. WHEN o startup script executa novamente (reboot ou redeploy) THEN the system SHALL manter uma única entrada de cron e preservar o volume do banco e o `.env` existente <!-- VM-05 -->
6. WHEN a VM reinicia THEN the system SHALL religar o container `postgres` automaticamente (`restart: unless-stopped`) <!-- VM-06 -->
7. The system SHALL gravar a saída de cada execução em arquivo de log na VM, com rotação diária de 7 arquivos <!-- VM-07 -->
8. WHILE o robô está em execução na e2-micro THE system SHALL concluir a coleta completa sem ser encerrado por falta de memória (nenhuma ocorrência de OOM kill no log do kernel) <!-- VM-08 -->

**Independent Test**: Após o `apply`, `gcloud compute ssh` na VM e `docker compose run --rm robo` manual termina com `SUCCESS`; no dia seguinte `executions` tem uma linha criada pelo cron.

---

### P2: Operação, custo e destruição

**User Story**: Como autor, quero documentação e verificações para operar a stack com segurança e remover tudo sem deixar cobrança.

**Why P2**: Necessário para não pagar por engano, mas não bloqueia o funcionamento.

**Acceptance Criteria**:

1. The system SHALL documentar em README, passo a passo, o `terraform destroy` de `envs/prod` e do bootstrap (incluindo o esvaziamento do bucket versionado) <!-- OPS-01 -->
2. The system SHALL documentar como verificar o Billing Report para confirmar a cobrança (ou não) do IPv4 externo <!-- OPS-02 -->
3. The system SHALL documentar que o budget alert apenas notifica e não limita gastos <!-- OPS-03 -->
4. The system SHALL documentar o pré-requisito de ADC (`gcloud auth application-default login`) e o uso de `billing_project` com `user_project_override` quando exigido <!-- OPS-04 -->
5. The system SHALL versionar apenas `*.tfvars.example`, `.env.example` e nenhuma chave de service account <!-- OPS-05 -->

**Independent Test**: Seguir o README do zero em outro projeto de teste sem consultar nada externo.

---

### P3: Reaproveitamento para Azure

**User Story**: Como autor, quero que a estrutura de módulos seja documentada para replicar em Azure depois.

**Why P3**: Útil no futuro; sem impacto na produção GCP.

**Acceptance Criteria**:

1. The system SHALL documentar a correspondência entre os módulos GCP e os recursos equivalentes no Azure (rede, compute, identidade, orçamento, state) <!-- AZR-01 -->

---

## Edge Cases

- IF o site retorna uma categoria vazia (0 results) THEN the system SHALL registrá-la com 0 itens e seguir sem falhar <!-- EDG-01 -->
- IF a mesma URL de livro aparece duas vezes na mesma execução THEN the system SHALL falhar a execução com o erro `duplicate url` e a URL <!-- EDG-02 -->
- WHEN o título contém aspas, acentos ou caracteres não-ASCII THEN the system SHALL gravá-lo íntegro em UTF-8 <!-- EDG-03 -->
- WHEN o robô roda duas vezes no mesmo dia THEN the system SHALL criar duas execuções independentes, cada uma com seu conjunto de linhas de preço <!-- EDG-04 -->
- IF o disco da VM atinge 90% de uso THEN the system SHALL ser alertável por inspeção manual documentada, sem automação adicional <!-- EDG-05 -->

### Varredura das dimensões implícitas

| Dimensão | Resolução |
| --- | --- |
| Validação de entrada e limites | CFG-02, TFP-05, TFB-05, DB-05 (truncar erro em 2.000 caracteres), SCR-07 |
| Falha / falha parcial | DB-05, DB-06, SCR-05, SCR-07, EDG-02 |
| Idempotência / retry / duplicata | SCR-06, DB-03 (upsert por URL), VM-04, VM-05, EDG-02, EDG-04 |
| Auth e rate limit | TFP-04..06 (SSH restrito, SA mínima); rate limit de saída: SCR-08 |
| Concorrência / ordenação | VM-04 (`flock`), DB-03 (transação única) |
| Ciclo de vida / expiração dos dados | N/A porque a retenção indefinida cabe em 30 GB (premissa logada); VM-07 cobre rotação de logs |
| Observabilidade | CFG-06, DB-02/04/05, VM-07, OPS-02 |
| Falha de dependência externa | SCR-06 (site), DB-07 (Postgres) |
| Integridade de transição de estado | DB-02 → DB-04/DB-05 (`RUNNING` → `SUCCESS`/`FAILED`), DB-06 |

---

## Requirement Traceability

| Requirement ID | Story | Phase | Status |
| --- | --- | --- | --- |
| SCR-01 | P1: Coletar categorias e livros | Design | Pending |
| SCR-02 | P1: Coletar categorias e livros | Design | Pending |
| SCR-03 | P1: Coletar categorias e livros | Design | Pending |
| SCR-04 | P1: Coletar categorias e livros | Design | Pending |
| SCR-05 | P1: Coletar categorias e livros | Design | Pending |
| SCR-06 | P1: Coletar categorias e livros | Design | Pending |
| SCR-07 | P1: Coletar categorias e livros | Design | Pending |
| SCR-08 | P1: Coletar categorias e livros | Design | Pending |
| SCR-09 | P1: Coletar categorias e livros | Design | Pending |
| DB-01 | P1: Persistir histórico | Design | Pending |
| DB-02 | P1: Persistir histórico | Design | Pending |
| DB-03 | P1: Persistir histórico | Design | Pending |
| DB-04 | P1: Persistir histórico | Design | Pending |
| DB-05 | P1: Persistir histórico | Design | Pending |
| DB-06 | P1: Persistir histórico | Design | Pending |
| DB-07 | P1: Persistir histórico | Design | Pending |
| DB-08 | P1: Persistir histórico | Design | Pending |
| DB-09 | P1: Persistir histórico | Design | Pending |
| CFG-01 | P1: Configuração e agnóstico de nuvem | Design | Pending |
| CFG-02 | P1: Configuração e agnóstico de nuvem | Design | Pending |
| CFG-03 | P1: Configuração e agnóstico de nuvem | Design | Pending |
| CFG-04 | P1: Configuração e agnóstico de nuvem | Design | Pending |
| CFG-05 | P1: Configuração e agnóstico de nuvem | Design | Pending |
| CFG-06 | P1: Configuração e agnóstico de nuvem | Design | Pending |
| CFG-07 | P1: Configuração e agnóstico de nuvem | Design | Pending |
| LOC-01 | P1: Ambiente local Docker Compose | Design | Pending |
| LOC-02 | P1: Ambiente local Docker Compose | Design | Pending |
| LOC-03 | P1: Ambiente local Docker Compose | Design | Pending |
| LOC-04 | P1: Ambiente local Docker Compose | Design | Pending |
| LOC-05 | P1: Ambiente local Docker Compose | Design | Pending |
| LOC-06 | P1: Ambiente local Docker Compose | Design | Pending |
| TFB-01 | P1: Bootstrap do remote state | Design | Pending |
| TFB-02 | P1: Bootstrap do remote state | Design | Pending |
| TFB-03 | P1: Bootstrap do remote state | Design | Pending |
| TFB-04 | P1: Bootstrap do remote state | Design | Pending |
| TFB-05 | P1: Bootstrap do remote state | Design | Pending |
| TFP-01 | P1: Infraestrutura de produção | Design | Pending |
| TFP-02 | P1: Infraestrutura de produção | Design | Pending |
| TFP-03 | P1: Infraestrutura de produção | Design | Pending |
| TFP-04 | P1: Infraestrutura de produção | Design | Pending |
| TFP-05 | P1: Infraestrutura de produção | Design | Pending |
| TFP-06 | P1: Infraestrutura de produção | Design | Pending |
| TFP-07 | P1: Infraestrutura de produção | Design | Pending |
| TFP-08 | P1: Infraestrutura de produção | Design | Pending |
| TFP-09 | P1: Infraestrutura de produção | Design | Pending |
| TFP-10 | P1: Infraestrutura de produção | Design | Pending |
| TFP-11 | P1: Infraestrutura de produção | Design | Pending |
| TFP-12 | P1: Infraestrutura de produção | Design | Pending |
| TFP-13 | P1: Infraestrutura de produção | Design | Pending |
| VM-01 | P1: Runtime da VM | Design | Pending |
| VM-02 | P1: Runtime da VM | Design | Pending |
| VM-03 | P1: Runtime da VM | Design | Pending |
| VM-04 | P1: Runtime da VM | Design | Pending |
| VM-05 | P1: Runtime da VM | Design | Pending |
| VM-06 | P1: Runtime da VM | Design | Pending |
| VM-07 | P1: Runtime da VM | Design | Pending |
| VM-08 | P1: Runtime da VM | Design | Pending |
| OPS-01 | P2: Operação, custo e destruição | Design | Pending |
| OPS-02 | P2: Operação, custo e destruição | Design | Pending |
| OPS-03 | P2: Operação, custo e destruição | Design | Pending |
| OPS-04 | P2: Operação, custo e destruição | Design | Pending |
| OPS-05 | P2: Operação, custo e destruição | Design | Pending |
| AZR-01 | P3: Reaproveitamento para Azure | - | Pending |
| EDG-01 | Edge Cases | Design | Pending |
| EDG-02 | Edge Cases | Design | Pending |
| EDG-03 | Edge Cases | Design | Pending |
| EDG-04 | Edge Cases | Design | Pending |
| EDG-05 | Edge Cases | Design | Pending |

**Coverage:** 68 total, 0 mapped to tasks, 68 unmapped ⚠️ (esperado: tasks ainda não existem)

---

## Success Criteria

- [ ] `docker compose run --rm robo` local termina com exit code 0 e 1.000 itens na tabela `price_history`.
- [ ] 1 `apply` de bootstrap + 1 `apply` em `envs/prod` criam toda a infra, sem passo manual além de `terraform.tfvars` e ADC.
- [ ] O cron da VM cria uma linha `SUCCESS` em `executions` por dia, sem OOM kill.
- [ ] O Billing Report do primeiro mês mostra R$ 0 em recursos faturáveis (ou apenas o IPv4 externo).
- [ ] `terraform destroy` em `envs/prod` e no bootstrap remove tudo que gera custo.
- [ ] Nenhum segredo, `.tfvars` real ou chave JSON aparece em `git ls-files`.
