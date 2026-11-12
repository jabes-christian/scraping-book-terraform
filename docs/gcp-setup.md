# Preparação do GCP e do Terraform

Runbook para preparar a máquina e o projeto GCP, criar o bucket do state (bootstrap) e deixar `envs/prod` pronto para `plan`/`apply`. Todos os comandos são PowerShell e partem da **raiz do projeto**. Nenhum valor real é versionado: use os seus no lugar de `<...>`.

Quem executa `terraform` e `gcloud` é você; o repositório só traz os arquivos e esta documentação.

> O comando marcado com **[a validar]** (`terraform force-unlock`) foi escrito a partir da documentação do Terraform, mas ainda não foi executado neste projeto. Confirme a saída na primeira vez e corrija o runbook se divergir.

## 1. Pré-requisitos

| Item | Observação |
| ---- | ---------- |
| Projeto GCP existente | Com a conta de faturamento vinculada. Anote o `project_id` e o `billing_account_id` (formato `XXXXXX-XXXXXX-XXXXXX`). |
| APIs `cloudresourcemanager.googleapis.com` e `serviceusage.googleapis.com` | Habilitadas manualmente, antes do Terraform (passo 6 do setup abaixo). Elas **não** são gerenciadas pelo Terraform deste projeto. |
| Terraform `>= 1.9` | Provider `google ~> 7.0` (os `.terraform.lock.hcl` versionados fixam a versão). |
| `gcloud` CLI | Para autenticação, verificações e o acesso SSH por IAP. |
| Python 3.13 e `.venv\` | Usados para gerar a senha do banco e rodar `pytest`/`ruff`. Sempre via `.venv\Scripts\python.exe`. |

Compute Engine, IAP, IAM e Billing Budgets ficam desabilitadas de propósito: o Terraform de `envs/prod` as habilita.

### Setup inicial do `gcloud` (uma vez por máquina/projeto)

Execute nesta ordem (os comandos foram usados e validados no setup inicial do projeto):

1. Login e escolha do projeto (interativo):

   ```powershell
   gcloud init
   ```

2. Região e zona padrão. Se algum comando pedir para habilitar a API Compute Engine, responda **N**: o Terraform a habilita.

   ```powershell
   gcloud config set compute/region us-central1
   gcloud config set compute/zone us-central1-a
   ```

3. Credencial ADC (a que o Terraform usa) e seu *quota project* (ver a seção 2):

   ```powershell
   gcloud auth application-default login
   gcloud auth application-default set-quota-project <project_id>
   ```

4. APIs que o Terraform precisa já ativas para conseguir habilitar as demais:

   ```powershell
   gcloud services enable cloudresourcemanager.googleapis.com serviceusage.googleapis.com
   ```

5. Confirme que o faturamento está ativo no projeto:

   ```powershell
   gcloud billing projects describe <project_id>
   ```

   Esperado na saída: `billingEnabled: true`.

## 2. Autenticação: ADC e `billing_project`

O Terraform autentica pelo **Application Default Credentials (ADC)** com a sua conta de usuário. Não há chave JSON de service account: nenhuma chave deve existir no disco do projeto nem no repositório.

O `gcloud auth application-default login` (passo 3 do setup) abre o navegador e grava a credencial local do ADC. Refaça-o se o Terraform acusar credencial expirada.

Os providers de `bootstrap` e `envs/prod` já trazem:

```hcl
user_project_override = true
billing_project       = var.project_id
```

Com ADC de usuário, as chamadas de API precisam de um *quota project*. `user_project_override` faz o provider enviar o cabeçalho `X-Goog-User-Project`, e `billing_project` define qual projeto recebe a cota. Isso é obrigatório para o `google_billing_budget` (sem ele a API responde 403) e inofensivo nos demais recursos. Você não precisa configurar nada além do `project_id` nas variáveis.

O `set-quota-project` do passo 3 define o mesmo projeto como *quota project* da credencial ADC no lado do `gcloud`; ele e as duas linhas acima se complementam.

## 3. O que vai e o que não vai para o Git

Só os arquivos de exemplo são versionados. Os arquivos reais ficam locais e já estão no `.gitignore`.

| Versionado | Local (gitignored) |
| ---------- | ------------------ |
| (o bootstrap não tem `.example`: o `terraform.tfvars` tem uma só variável, ver passo 5.1) | `terraform/bootstrap/terraform.tfvars` |
| `terraform/envs/prod/terraform.tfvars.example` | `terraform/envs/prod/terraform.tfvars` |
| `terraform/envs/prod/backend.hcl.example` | `terraform/envs/prod/backend.hcl` |
| `.env.example` | `.env` |
| `.terraform.lock.hcl` (de cada stack e módulo) | `.terraform/`, `*.tfstate`, `*.tfplan`, `.rendered-startup.json` |

Regras:

- Nunca versione `*.tfvars`, `backend.hcl`, `*.tfstate`, `*.tfplan`, `.env` nem chaves de service account.
- Para conferir antes de qualquer commit: `git status` não pode listar nenhum desses arquivos. O teste `tests/unit/test_repo_hygiene.py` também falha se algum for rastreado.

## 4. Lições práticas do PowerShell 5.1

Valem para todos os comandos abaixo.

1. **Argumentos `-opcao=valor` com ponto no valor vão entre aspas.** Sem aspas, o PowerShell 5.1 quebra o argumento no ponto:

   ```powershell
   terraform -chdir=terraform/envs/prod plan "-out=prod.tfplan"
   terraform -chdir=terraform/envs/prod init -reconfigure "-backend-config=backend.hcl"
   ```

2. **Arquivos lidos pelo Terraform: grave em ASCII.** `Set-Content -Encoding utf8` grava BOM, e `>` grava UTF-16; ambos quebram o parser. Use `Set-Content -Encoding ascii` ou crie o arquivo pelo editor.
3. **`.tfvars` e `backend.hcl`: crie pelo editor** (ou copie o `.example` com `Copy-Item` e edite). Evite redirecionar texto para eles.
4. **`-chdir` muda o diretório de trabalho do Terraform.** O caminho do plano salvo (`prod.tfplan`) é relativo a `terraform/envs/prod/`, não à raiz.

## 5. Fluxo completo

```
tfvars do bootstrap → bootstrap (bucket do state) → backend.hcl → tfvars e senha de envs/prod → init → plan
```

### 5.1 Bootstrap: bucket do remote state

O bootstrap cria o bucket GCS (versionado, acesso público bloqueado) que guarda o state de `envs/prod`. O state do **próprio bootstrap é local**.

1. Crie `terraform/bootstrap/terraform.tfvars` pelo editor, com:

   ```hcl
   project_id = "<project_id>"
   ```

   Opcionais: `region` (`us-central1`, `us-east1` ou `us-west1`), `bucket_name` (padrão `<project_id>-tfstate`) e `force_destroy` (mantenha `false`; só vira `true` no destroy, ver `docs/destroy.md`).

2. Inicialize, gere o plano e leia-o. O esperado é `Plan: 2 to add, 0 to change, 0 to destroy` (API `storage.googleapis.com` e o bucket):

   ```powershell
   terraform -chdir=terraform/bootstrap init
   terraform -chdir=terraform/bootstrap plan "-out=bootstrap.tfplan"
   ```

3. Aplique o plano salvo. Um `apply` com plano salvo **não pede confirmação**: executa direto, porque a revisão do `plan` do passo anterior é a confirmação. Só rode depois de ler o plano:

   ```powershell
   terraform -chdir=terraform/bootstrap apply "bootstrap.tfplan"
   ```

   Esperado: `Apply complete! Resources: 2 added, 0 changed, 0 destroyed.`

4. Confira o resultado:

   ```powershell
   terraform -chdir=terraform/bootstrap output -raw bucket_name
   gcloud storage buckets describe gs://<bucket_name>
   ```

   No `describe`: `location: US-CENTRAL1`, `versioning_enabled: true`, `uniform_bucket_level_access: true` e `public_access_prevention: enforced`.

5. Apague o plano salvo: `Remove-Item terraform\bootstrap\bootstrap.tfplan`.

#### Backup do `terraform.tfstate` do bootstrap

O state do bootstrap fica em `terraform/bootstrap/terraform.tfstate` (gitignored). **Não apague esse arquivo**: o `terraform destroy` do bootstrap depende dele. Sem ele, o Terraform não sabe que o bucket é seu e tentaria recriá-lo. Guarde uma cópia fora do repositório (e fora de pastas sincronizadas publicamente), e refaça a cópia após qualquer novo `apply` do bootstrap:

```powershell
Copy-Item terraform\bootstrap\terraform.tfstate "<pasta-segura>\bootstrap.tfstate.bak"
```

### 5.2 `backend.hcl`

O `backend.tf` de `envs/prod` é uma configuração **parcial**: só traz `prefix = "envs/prod"`. O nome do bucket vem do `backend.hcl` local.

Opção A (recomendada): copie o exemplo e edite o `bucket` pelo editor.

```powershell
Copy-Item terraform\envs\prod\backend.hcl.example terraform\envs\prod\backend.hcl
```

O conteúdo final fica assim (com o nome do bucket do passo 5.1):

```hcl
bucket = "<project_id>-tfstate"
prefix = "envs/prod"
```

Opção B: gravar direto o snippet que o bootstrap devolve, em ASCII (usado neste projeto).

```powershell
terraform -chdir=terraform/bootstrap output -raw backend_hcl_snippet | Set-Content -Path terraform/envs/prod/backend.hcl -Encoding ascii
```

### 5.3 `envs/prod`: variáveis

1. Copie o exemplo e preencha pelo editor:

   ```powershell
   Copy-Item terraform\envs\prod\terraform.tfvars.example terraform\envs\prod\terraform.tfvars
   ```

   Obrigatórios: `project_id`, `billing_account_id`, `repo_url` (HTTPS de um repositório **público**: a VM clona sem credenciais) e `repo_ref` (padrão `main`; branch ou tag; prefira uma tag para estabilidade, hash de commit não funciona). Os demais têm padrão: `region`, `zone`, `db_name`, `db_user`, `cron_schedule`, `swap_size_mb` e `boot_disk_size_gb` (máximo 30, limite do Free Tier).

2. **A senha do banco não vai no `terraform.tfvars`.** Ela entra só por variável de ambiente, na janela do PowerShell em que você roda o Terraform.

#### Senha do banco (`db_password`)

Regras (validadas em `variables.tf`): somente `[A-Za-z0-9_.-]` e no mínimo 16 caracteres. Outros caracteres, como `$` e `#`, seriam reinterpretados pelo Compose ao ler o `.env` e o banco subiria com senha diferente da do Terraform.

Em máquina corporativa com **Constrained Language Mode**, a geração por .NET (`[System.Security...]`) é bloqueada. Use o Python do projeto. O comando gera a senha (24 caracteres) e já a atribui à variável da sessão, sem exibi-la:

```powershell
$env:TF_VAR_db_password = .venv\Scripts\python.exe -c "import secrets, string; print(''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(24)))"
```

Como a senha não é exibida, **copie-a para um gerenciador de senhas agora** (ela é fixada no primeiro boot do volume, ver abaixo). Exiba, copie e limpe a tela em seguida:

```powershell
$env:TF_VAR_db_password
Clear-Host
```

Para usar uma senha já existente (por exemplo, em outra janela), atribua o valor guardado: `$env:TF_VAR_db_password = "<senha-guardada>"`.

Pontos importantes:

- A variável vale **só naquela janela do PowerShell**. Abriu outra janela (ou reiniciou), defina de novo, com a mesma senha.
- A senha do Postgres é **fixada na primeira inicialização do volume** de dados da VM. Trocar `db_password` depois não troca a senha do banco já criado, e o robô passa a falhar na autenticação. Por isso a senha do primeiro `apply` precisa ser guardada.
- A senha fica em texto no state (AD-002) e na metadata da instância; o bucket do state tem acesso público bloqueado, e o acesso ao projeto deve ser restrito a você.

### 5.4 `envs/prod`: `init` e `plan`

```powershell
terraform -chdir=terraform/envs/prod init -reconfigure "-backend-config=backend.hcl"
terraform -chdir=terraform/envs/prod plan "-out=prod.tfplan"
```

- `-reconfigure` é uma precaução: refaz a configuração do backend a partir do `backend.hcl`, ignorando qualquer configuração salva anteriormente em `.terraform/`, e **não migra state**. (O `init -backend=false` dos testes só pula o backend; não o desconfigura.)
- Esperado no primeiro plano: `Plan: 10 to add, 0 to change, 0 to destroy.` São 4 APIs (compute, iam, billingbudgets, iap), a rede, a sub-rede, a regra de firewall, a service account, a instância e o orçamento. As 4 APIs aparecem como criação porque nenhuma estava gerenciada.
- O `data.google_project` do orçamento é lido "during apply": efeito esperado do `depends_on` nas APIs.
- Nenhum NAT, balanceador, IP estático, snapshot, Cloud SQL, Pub/Sub, Artifact Registry ou Secret Manager pode aparecer: se aparecer, pare e revise.

**O plano salvo contém a senha em texto puro.** Apague-o assim que terminar de usá-lo:

```powershell
Remove-Item terraform\envs\prod\prod.tfplan
```

O `apply` de `envs/prod` e a validação na VM têm runbook próprio (acesso por `gcloud compute ssh ... --tunnel-through-iap`, ver `docs/update-code.md`). Neste documento o fluxo termina no `plan`.

## 6. Acesso SSH à VM (AD-007)

O SSH é **somente por túnel IAP**. O firewall libera `tcp:22` apenas da faixa do IAP (`35.235.240.0/20`) para a tag `book-monitor`, e a variável `allowed_ssh_cidr` não existe mais. O comando pronto é um output do Terraform:

```powershell
terraform -chdir=terraform/envs/prod output -raw ssh_command
```

Ele devolve algo como:

```
gcloud compute ssh book-monitor --zone us-central1-a --project <project_id> --tunnel-through-iap
```

Por que IAP e não o seu IP: a máquina corporativa sai por um proxy (Netskope), cujo IP de saída é compartilhado e pode ser diferente do IP real da conexão na porta 22; um IP residencial, por sua vez, é dinâmico. Um `/32` no firewall não seria confiável.

## 7. Problemas comuns

### Inspeção TLS da rede corporativa (Netskope)

Se `init`, `plan` ou o `gcloud` falharem com `x509: certificate signed by unknown authority`, a rede está interceptando o TLS com uma CA própria que a ferramenta não conhece. Nos testes feitos neste projeto, `init` e `plan` com o backend GCS funcionaram sem erro de certificado; o erro apareceu em outro ponto (o container do robô, ver `docs/local-development.md`). Se ocorrer, não desative a verificação de certificado: peça à TI a CA corporativa e configure a confiança nela.

### State lock preso

O backend GCS bloqueia o state durante `plan`/`apply`. Se um comando for interrompido (Ctrl+C no meio, queda de rede, janela fechada), o próximo pode falhar com `Error acquiring the state lock`, mostrando `Lock Info` com `ID`, `Who`, `Created` e `Operation`.

O que fazer, nesta ordem:

1. **Confirme que não há outro Terraform rodando** (outra janela do PowerShell, outra máquina). Se houver, espere ele terminar.
2. Confira `Who` e `Created` no erro: o lock é seu e antigo?
3. Só então libere, usando exatamente o `ID` mostrado no erro **[a validar]**:

   ```powershell
   terraform -chdir=terraform/envs/prod force-unlock <LOCK_ID>
   ```

**Nunca use `force-unlock` sem conferir o Lock ID e sem ter certeza de que nenhum outro processo usa o state.** Liberar um lock ativo permite duas escritas simultâneas e pode corromper o state.

### Timeout em `registry.terraform.io` durante o `init`

Se o `init` falhar por timeout ao acessar `registry.terraform.io`, o problema é de rede (lentidão ou instabilidade momentânea), **não** de certificado: a mensagem não menciona `x509`. Ocorreu neste projeto na T30, com:

```powershell
terraform -chdir=terraform/modules/budget init -backend=false
```

```
Error: Failed to query available provider packages
Could not retrieve the list of available versions for provider hashicorp/google: could not connect to registry.terraform.io: failed to request discovery document: ... giving up after 4 attempt(s): ... (Client.Timeout exceeded while awaiting headers)
```

Resolução: repetir o mesmo comando alguns minutos depois. Para diagnosticar, teste o acesso ao registry (use `curl.exe`, não o alias `curl` do PowerShell, que é o `Invoke-WebRequest`):

```powershell
curl.exe -I https://registry.terraform.io/.well-known/terraform.json
```

Se responder `200`, a rede está ok e basta repetir o `init`. Só investigue proxy e conectividade se a falha persistir em várias tentativas.

### 403 transitório no primeiro `apply`

O primeiro `apply` habilita as APIs e, na sequência, cria recursos que dependem delas. Por consistência eventual, a API de uma delas pode responder 403 por alguns instantes. Reexecute o `plan` e o `apply`: o Terraform retoma de onde parou.

### Arquivo com BOM ou UTF-16

Erros de parser em `terraform.tfvars` ou `backend.hcl` (caracteres estranhos no início do arquivo) indicam BOM ou UTF-16. Recrie o arquivo pelo editor ou com `Set-Content -Encoding ascii`.

## 8. Referências

- `docs/destroy.md`: destruição de `envs/prod` e do bootstrap.
- `docs/cost-and-billing.md`: custo, Billing Report e disco.
- `docs/update-code.md`: atualização do código na VM.
- `terraform/envs/prod/terraform.tfvars.example` e `terraform/envs/prod/backend.hcl.example`: modelos dos arquivos locais.
