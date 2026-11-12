# Desenvolvimento local

Como rodar o robô, o banco e os testes na sua máquina. Comandos em PowerShell, a partir da **raiz do projeto**. O Python é sempre o do ambiente virtual do projeto (`.venv\Scripts\python.exe`); nunca instale pacotes no Python global.

> Os comandos abaixo foram usados e validados no projeto (tasks T13 a T21 e a consulta às tabelas).

## 1. Pré-requisitos

| Item | Observação |
| ---- | ---------- |
| Python 3.13 | Com o ambiente virtual em `.venv\` |
| Docker Desktop | **Ligado** antes dos testes de integração, de Docker e e2e, e antes de qualquer `docker compose` |
| `git` | Para clonar o repositório |

Instale as dependências no ambiente virtual:

```powershell
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

(`requirements-dev.txt` inclui o `requirements.txt` e acrescenta `pytest` e `ruff`.)

## 2. Configuração: `.env`

O `.env` guarda as credenciais do banco e os parâmetros do robô. Ele é **ignorado pelo Git**; só o `.env.example` é versionado.

```powershell
Copy-Item .env.example .env
```

Edite o `.env` pelo editor e troque a senha:

| Variável | Padrão no exemplo | Para que serve |
| -------- | ----------------- | -------------- |
| `DB_NAME` | `books` | Nome do banco |
| `DB_USER` | `books` | Usuário do Postgres |
| `DB_PASSWORD` | `change-me` | Senha do Postgres: **troque** |
| `SCRAPE_DELAY_SECONDS` | `0.5` | Pausa entre requisições ao site |
| `SCRAPE_MAX_RETRIES` | `3` | Tentativas por página |
| `LOG_LEVEL` | `INFO` | Nível dos logs |

Variáveis opcionais (não estão no exemplo): `BASE_URL` (padrão `https://books.toscrape.com/`) e `DB_PORT` (padrão `5432`).

Atenção: o Postgres fixa a senha na **primeira inicialização do volume** `pgdata`. Se você mudar `DB_PASSWORD` depois, o robô passa a falhar na autenticação; para recomeçar com outra senha, apague o volume (`docker compose down -v`, que também **apaga os dados**).

## 3. Subir o banco e rodar o robô

O Compose tem dois serviços: `postgres` (permanente, volume `pgdata`) e `robo` (efêmero, roda uma coleta e termina).

Suba o banco e espere o healthcheck:

```powershell
docker compose up -d --wait postgres
```

Construa a imagem do robô (a primeira vez demora, por causa do Chromium) e rode uma coleta completa:

```powershell
docker compose build robo
docker compose run --rm -T robo
```

Uma coleta completa percorre as 50 categorias (1.000 livros) e leva entre 80 e 95 segundos no Docker Desktop (82 s na validação do guia, com 1.000 itens). O `-T` desliga o pseudo-terminal, como faz o cron na VM.

O código de saída do robô (`$LASTEXITCODE` logo depois do comando):

| Código | Significado |
| ------ | ----------- |
| `0` | Coleta concluída com sucesso |
| `1` | Falha na execução (banco inacessível, erro durante a coleta) |
| `2` | Configuração inválida (variável ausente ou fora do formato); o banco não é tocado |

### Rede com inspeção TLS (Netskope)

Em rede corporativa que intercepta o TLS, o Chromium do container não confia na CA da empresa e a coleta falha com `unexpected page structure` já na home (e `CERTIFICATE_VERIFY_FAILED` nos logs). Não é defeito do robô. Para validar localmente, use o site por HTTP:

```powershell
docker compose run --rm -T -e BASE_URL=http://books.toscrape.com/ robo
```

A validação por HTTPS é feita na VM, que não tem inspeção TLS.

## 4. Consultar as tabelas

O schema tem três tabelas: `executions` (uma linha por execução, com `status` `RUNNING`/`SUCCESS`/`FAILED`, `items_count` e `error`), `books` (um livro por `url`) e `price_history` (um preço por livro e por execução).

**O banco de desenvolvimento começa vazio.** O schema é criado pelo próprio robô na primeira coleta, então antes dela o Postgres não tem tabelas nenhuma.

Consulta dentro do container do Postgres, sem expor porta no host. Os comandos usam os valores do `.env.example` (`-U books -d books`); se você mudou `DB_USER` ou `DB_NAME` no `.env`, troque-os:

```powershell
docker compose exec postgres psql -U books -d books -c "\dt"
```

Antes da primeira coleta, a saída é `Did not find any relations.`. Depois dela, lista as 3 tabelas (`books`, `executions` e `price_history`). Para consultar o conteúdo:

```powershell
docker compose exec postgres psql -U books -d books -c "SELECT id, status, items_count, started_at FROM executions ORDER BY id DESC LIMIT 5;"
docker compose exec postgres psql -U books -d books -c "SELECT count(*) FROM books;"
docker compose exec postgres psql -U books -d books -c "SELECT count(*) FROM price_history;"
``` Depois de duas coletas completas, o esperado é: 2 linhas `SUCCESS` em `executions` com `items_count = 1000`, 1.000 linhas em `books` e 2.000 em `price_history`.

### Acesso pelo host (opcional)

Por padrão o Postgres **não publica porta**. Para acessá-lo do host (por um cliente SQL, por exemplo), copie o override, que publica só em `127.0.0.1:5432`:

```powershell
Copy-Item docker-compose.override.yml.example docker-compose.override.yml
docker compose up -d --wait postgres
```

O `docker-compose.override.yml` é ignorado pelo Git e carregado automaticamente pelo Compose. Ele existe só em desenvolvimento: na VM o Postgres fica na rede interna. Os testes de integração **não dependem** dele.

## 5. Testes e qualidade

Os testes são separados por *markers* do pytest (declarados no `pyproject.toml`; com `--strict-markers`, um marker desconhecido falha):

| Marker | O que exige | Onde |
| ------ | ----------- | ---- |
| (nenhum) | Nada: testes unitários | `tests/unit/` |
| `integration` | Docker Desktop ligado (PostgreSQL do Compose) | `tests/integration/` |
| `docker` | Docker Desktop ligado e build da imagem | `tests/docker/` |
| `infra` | Testes de renderização do startup script e de Terraform | `tests/infra/` |
| `e2e` | Docker, `.env` e o site real (minutos) | `tests/e2e/` |

Comandos:

```powershell
# Quick: unitários + lint (o que roda a cada mudança)
.venv\Scripts\python.exe -m pytest -m "not integration and not docker and not infra and not e2e"
.venv\Scripts\python.exe -m ruff check .

# Integração (exige Docker Desktop ligado)
.venv\Scripts\python.exe -m pytest -m integration

# Build da imagem e smoke do Compose
docker compose build
.venv\Scripts\python.exe -m pytest -m docker

# Estáticos de infraestrutura
.venv\Scripts\python.exe -m pytest -m infra

# Ponta a ponta contra o site real (~3-4 minutos)
.venv\Scripts\python.exe -m pytest -m e2e -s
```

Em rede com inspeção TLS, o e2e precisa do site por HTTP:

```powershell
$env:E2E_BASE_URL = "http://books.toscrape.com/"
.venv\Scripts\python.exe -m pytest -m e2e -s
```

Pontos importantes:

- Os testes de integração **não usam** o seu `.env`, o `docker-compose.override.yml` nem o volume de desenvolvimento: o `conftest.py` sobe e remove sozinho um projeto Compose isolado (`bookmonitor_it`, porta livre em `127.0.0.1`, credenciais de teste). Não é preciso rodar `docker compose up` antes.
- O e2e usa o projeto isolado `bookmonitor_e2e` com volume próprio (apagado no fim), mas lê as credenciais do seu `.env`.
- Os testes `infra` que dependem do startup script exigem o JSON renderizado pelo Terraform (ver `terraform/README.md`); sem ele, o teste é **ignorado (`skip`) e o gate de infraestrutura não está cumprido**.

## 6. Parar e limpar

```powershell
docker compose stop      # para o banco, mantém os dados
docker compose down      # remove os containers, mantém o volume pgdata
docker compose down -v   # remove também o volume: APAGA os dados locais
```

## 7. Referências

- `README.md`: visão geral do projeto.
- `docs/gcp-setup.md`: preparação do GCP e do Terraform (produção).
- `docs/update-code.md`: como o código chega à VM.
