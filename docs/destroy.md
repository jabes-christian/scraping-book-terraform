# Destruição da infraestrutura

Runbook para remover tudo o que gera custo: primeiro `envs/prod` (VM, rede, orçamento), por último o bootstrap (bucket do state). Todos os comandos são PowerShell e partem da **raiz do projeto**. Quem executa `terraform` e `gcloud` é você.

> Os comandos de `destroy` e de verificação abaixo estão marcados **[a validar]**: ainda não foram executados neste projeto. Eles serão validados no teste de destruição (T56), e este runbook será corrigido onde a prática divergir.

## Antes de começar

1. **Os dados do banco serão perdidos.** O volume do Postgres vive no disco de boot da VM; destruir a VM apaga o histórico de preços coletado. Se precisar dele, faça um dump antes (acesso por `gcloud compute ssh ... --tunnel-through-iap`, ver `docs/gcp-setup.md`, seção 6).
2. **Destrua nesta ordem: `envs/prod` primeiro, bootstrap por último.** O state de `envs/prod` está no bucket criado pelo bootstrap. Se o bucket for destruído antes, o Terraform perde o registro dos recursos de produção e eles ficam órfãos (e continuam gerando custo).
3. **Autenticação ativa** (`gcloud auth application-default login`, ver `docs/gcp-setup.md`, seção 2) e `terraform/envs/prod/terraform.tfvars` e `backend.hcl` ainda presentes.
4. **O `terraform.tfstate` local do bootstrap precisa existir** em `terraform/bootstrap/`. Sem ele, o destroy do bootstrap não funciona (ver o backup em `docs/gcp-setup.md`, seção 5.1).
5. Lembre das regras do PowerShell 5.1: argumentos `-opcao=valor` com ponto no valor vão entre aspas (`"-backend-config=backend.hcl"`).

## 1. Destruir `envs/prod`

### 1.1 Preparar a sessão

O `destroy` também valida as variáveis, inclusive `db_password` (`[A-Za-z0-9_.-]`, mínimo de 16 caracteres). Se a janela do PowerShell é nova, defina a variável de novo, **sempre com a senha guardada no gerenciador de senhas**:

```powershell
$env:TF_VAR_db_password = "<senha-guardada>"
```

Use sempre a senha guardada, mesmo que a destruição em si não dependa do valor. Se o `destroy` falhar no meio e você precisar de um `apply` para restaurar o que sobrou, uma senha diferente mudaria a metadata da instância sem mudar a senha do banco (fixada na primeira inicialização do volume), e o robô passaria a falhar na autenticação.

Reconfigure o backend para garantir que o state remoto (bucket GCS) é o usado:

```powershell
terraform -chdir=terraform/envs/prod init -reconfigure "-backend-config=backend.hcl"
```

### 1.2 Conferir o que existe

```powershell
terraform -chdir=terraform/envs/prod state list
```

Esperado: os 10 recursos do plano (4 `google_project_service`, rede, sub-rede, firewall `book-monitor-allow-iap-ssh`, service account `book-monitor-vm`, instância `book-monitor` e o orçamento).

### 1.3 Destruir **[a validar]**

Gere o plano de destruição, revise-o e aplique o plano salvo (mesmo padrão do `plan`/`apply` do projeto):

```powershell
terraform -chdir=terraform/envs/prod plan -destroy "-out=destroy.tfplan"
terraform -chdir=terraform/envs/prod apply "destroy.tfplan"
```

Confira no plano `Plan: 0 to add, 0 to change, 10 to destroy.` O `apply` com plano salvo **não pede confirmação**: a revisão do plano é a confirmação, então só o rode depois de ler. A instância tem `deletion_protection = false`, então a remoção não é bloqueada.

**O plano salvo contém a senha em texto puro.** Apague-o assim que terminar:

```powershell
Remove-Item terraform\envs\prod\destroy.tfplan
```

Se o `apply` falhar no meio (erro transitório de API), gere um novo plano de destruição e aplique de novo: ele retoma do que sobrou.

### 1.4 O que `disable_on_destroy = false` preserva

Todo `google_project_service` do projeto usa `disable_on_destroy = false`. No destroy, as 4 APIs de `envs/prod` (`compute`, `iam`, `billingbudgets` e `iap`) apenas **saem do state**: continuam habilitadas no projeto. As APIs `cloudresourcemanager` e `serviceusage`, habilitadas manualmente, nunca foram gerenciadas pelo Terraform e também permanecem. Isso é intencional: desligar uma API afetaria o projeto inteiro, e APIs habilitadas não geram custo.

### 1.5 Verificar **[a validar]**

```powershell
gcloud compute instances list
gcloud compute disks list
gcloud compute addresses list
gcloud compute firewall-rules list
```

Esperado: nenhuma instância, nenhum disco e nenhum endereço; nas regras de firewall, nenhuma `book-monitor-allow-iap-ssh`. Um endereço IP estático nunca é criado por este projeto (a VM usa IP efêmero).

## 2. Destruir o bootstrap

O bucket do state é **versionado**. Com `force_destroy = false` (padrão), o `destroy` falha se houver objetos ou versões antigas no bucket, e o state de `envs/prod` e suas versões ainda estão lá. É preciso primeiro aplicar `force_destroy = true` e só então destruir.

### 2.1 Habilitar `force_destroy`

Edite `terraform/bootstrap/terraform.tfvars` pelo editor e acrescente:

```hcl
force_destroy = true
```

Gere o plano e aplique. A mudança esperada é `1 to change` no bucket (`force_destroy`), sem recriação:

```powershell
terraform -chdir=terraform/bootstrap plan "-out=bootstrap.tfplan"
terraform -chdir=terraform/bootstrap apply "bootstrap.tfplan"
```

O `apply` com plano salvo não pede confirmação: a revisão do `plan` é a confirmação. Apague o plano salvo: `Remove-Item terraform\bootstrap\bootstrap.tfplan`.

### 2.2 Destruir **[a validar]**

```powershell
terraform -chdir=terraform/bootstrap plan -destroy "-out=destroy.tfplan"
terraform -chdir=terraform/bootstrap apply "destroy.tfplan"
```

Confira `Plan: 0 to add, 0 to change, 2 to destroy.` (o bucket e a API `storage.googleapis.com`) antes do `apply`, que executa direto (a revisão do plano é a confirmação). Com `force_destroy = true`, o Terraform apaga o bucket junto com todos os objetos e versões. A API `storage.googleapis.com` continua habilitada (`disable_on_destroy = false`).

Apague o plano salvo: `Remove-Item terraform\bootstrap\destroy.tfplan`.

### 2.3 Limpar os arquivos locais

Depois do destroy do bootstrap, o state local fica vazio e o `backend.hcl` aponta para um bucket que não existe mais. Se não for recriar a infraestrutura, remova-os:

```powershell
Remove-Item terraform\envs\prod\backend.hcl
Remove-Item terraform\bootstrap\terraform.tfstate
Remove-Item terraform\bootstrap\terraform.tfstate.backup
```

Se for reaplicar depois, siga o `docs/gcp-setup.md` desde a seção 5.1, **mas antes** remova a linha `force_destroy = true` de `terraform/bootstrap/terraform.tfvars` (ou volte para `false`), para o novo bucket nascer protegido contra um `destroy` acidental. Uma nova VM cria um novo volume de banco e fixa a senha do Postgres na primeira inicialização, então guarde a nova senha.

## 3. Verificação final **[a validar]**

```powershell
gcloud compute instances list
gcloud storage buckets list
gcloud services list --enabled
```

Esperado:

- `gcloud compute instances list`: `Listed 0 items.`
- `gcloud storage buckets list`: nenhum bucket do projeto (sem `<project_id>-tfstate`).
- `gcloud services list --enabled`: `cloudresourcemanager.googleapis.com` e `serviceusage.googleapis.com` continuam na lista (junto com as APIs do passo 1.4, que também permanecem).

O orçamento (`google_billing_budget`) é destruído junto com `envs/prod`. Para conferir no console: Billing > Budgets & alerts, na conta de faturamento.

## 4. Aviso: a rede `default`

Ao habilitar a API do Compute Engine, o GCP pode criar automaticamente a rede `default`, com regras de firewall abertas (por exemplo, SSH de `0.0.0.0/0`). A VM deste projeto **não** usa essa rede (tem VPC própria, destruída no passo 1), mas a `default` continua existindo, porque não é gerenciada pelo Terraform, e fica exposta a quem criar VMs nela.

Para verificar **[a validar]**:

```powershell
gcloud compute networks list
gcloud compute firewall-rules list
```

Removê-la é manual e está fora do escopo deste projeto. Se decidir removê-la, apague primeiro as regras de firewall dela e confirme que nenhuma VM a usa.

## 5. Referências

- `docs/gcp-setup.md`: autenticação, bootstrap, backup do state local e lock preso.
- `docs/cost-and-billing.md`: o orçamento apenas notifica; `terraform destroy` é o corte real de custo.
