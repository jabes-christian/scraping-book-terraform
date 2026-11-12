# Infraestrutura (Terraform)

Infraestrutura do projeto na GCP, dentro do Free Tier: um bucket para o state remoto (bootstrap) e um ambiente de produção (`envs/prod`) com uma VM `e2-micro`, rede, identidade e orçamento. Os comandos são PowerShell, a partir da **raiz do projeto**, e são executados por você (`terraform` e `gcloud` nunca rodam no automático, AD-006).

## 1. Estrutura

```
terraform/
├── bootstrap/        # stack do bucket do remote state (state local)
├── modules/          # módulos reutilizáveis, uma responsabilidade cada
│   ├── apis/         # habilita as APIs do projeto
│   ├── network/      # VPC, sub-rede e firewall (SSH só pelo IAP)
│   ├── identity/     # service account da VM
│   ├── compute_vm/   # a VM e o startup script
│   └── budget/       # orçamento com alerta por e-mail
└── envs/
    └── prod/         # compõe os módulos; state no bucket do bootstrap
```

Cada stack e módulo tem seus `.tf`, o `.terraform.lock.hcl` (versionado, fixa a versão do provider) e uma pasta `tests/` com `*.tftest.hcl`. O provider é `hashicorp/google ~> 7.0` e o Terraform é `>= 1.9`.

## 2. Ordem de aplicação

1. **Bootstrap** (`terraform/bootstrap`): cria o bucket GCS versionado do state. O state do próprio bootstrap é **local** (`terraform/bootstrap/terraform.tfstate`, não versionado; faça backup).
2. **`backend.hcl`** em `terraform/envs/prod/`: aponta `envs/prod` para o bucket (não versionado; há um `backend.hcl.example`).
3. **`envs/prod`**: `init -reconfigure "-backend-config=backend.hcl"`, `plan "-out=prod.tfplan"` e `apply "prod.tfplan"`. A senha do banco entra só por `$env:TF_VAR_db_password`.

O passo a passo completo, com comandos e armadilhas do PowerShell 5.1, está em [docs/gcp-setup.md](../docs/gcp-setup.md). A destruição, em ordem inversa, está em [docs/destroy.md](../docs/destroy.md).

## 3. Módulos

### `bootstrap` (stack)

Cria `google_project_service.storage` e `google_storage_bucket.tfstate` (versionamento, acesso público bloqueado, `uniform_bucket_level_access`, regra de ciclo de vida que mantém as 5 versões mais novas).

| Entradas | Saídas |
| -------- | ------ |
| `project_id` (obrigatória), `region` (`us-central1`, `us-east1` ou `us-west1`), `bucket_name` (padrão `<project_id>-tfstate`), `force_destroy` (padrão `false`) | `bucket_name`, `backend_hcl_snippet` (conteúdo pronto para o `backend.hcl`) |

### `modules/apis`

Habilita um `google_project_service` por API, com `disable_on_destroy = false` e `disable_dependent_services = false`.

| Entradas | Saídas |
| -------- | ------ |
| `project_id`, `services` (lista de APIs) | `services` (para ordenar recursos com `depends_on`) |

### `modules/network`

VPC customizada (`book-monitor-vpc`), sub-rede `10.10.0.0/24` e a regra de firewall `book-monitor-allow-iap-ssh`: `tcp:22` somente da faixa do IAP `35.235.240.0/20`, para a tag `book-monitor` (AD-007). Não há mais `allowed_ssh_cidr`.

| Entradas | Saídas |
| -------- | ------ |
| `region` (padrão `us-central1`) | `network`, `subnetwork`, `network_tag` |

### `modules/identity`

Service account dedicada da VM, **sem nenhuma role** de projeto: a VM não chama APIs do GCP.

| Entradas | Saídas |
| -------- | ------ |
| `account_id` (padrão `book-monitor-vm`) | `email` |

### `modules/compute_vm`

A única VM (`e2-micro`, Debian 12, disco `pd-standard`, IP externo efêmero, shielded VM) e o startup script (`startup.sh.tftpl`), que roda a cada boot: swap, Docker, `git clone`/`fetch` do repositório, `.env`, build, cron diário com `flock` e logrotate. O script e a senha vão na metadata da instância.

| Entradas | Saídas |
| -------- | ------ |
| `subnetwork`, `network_tag`, `service_account_email`, `repo_url`, `db_password` (sensível, obrigatórias); `zone`, `machine_type`, `boot_disk_size_gb`, `repo_ref`, `db_name`, `db_user`, `cron_schedule`, `swap_size_mb` (com padrão) | `instance_name`, `zone`, `ssh_command` (com `--tunnel-through-iap`) |

### `modules/budget`

`google_billing_budget` filtrado pelo projeto (R$ 5, alertas em 50%, 90% e 100%, por e-mail aos papéis da conta de faturamento). **Apenas notifica; não limita o gasto.** Detalhes em [docs/cost-and-billing.md](../docs/cost-and-billing.md).

| Entradas | Saídas |
| -------- | ------ |
| `billing_account_id`, `project_id`; `amount_units` (5), `currency_code` (`BRL`), `thresholds` (`[0.5, 0.9, 1.0]`) | `budget_name` |

### `envs/prod`

Compõe os módulos: `apis` (compute, iam, billingbudgets e iap) e, com `depends_on = [module.apis]`, `network`, `identity`, `compute_vm` e `budget`. Backend `gcs` parcial (`prefix = "envs/prod"`).

| Entradas | Saídas |
| -------- | ------ |
| `project_id`, `billing_account_id`, `repo_url`, `db_password` (obrigatórias); `region`, `zone`, `repo_ref`, `db_name`, `db_user`, `cron_schedule`, `swap_size_mb`, `boot_disk_size_gb` (com padrão) | `instance_name`, `zone`, `ssh_command` |

Valores reais ficam em `terraform.tfvars` (não versionado, a partir do `terraform.tfvars.example`). Como atualizar o código da VM: [docs/update-code.md](../docs/update-code.md).

## 4. Guardas de Free Tier

Variáveis com `validation` fazem o `plan` falhar antes de gerar custo:

| Guarda | Onde |
| ------ | ---- |
| Região em `us-central1`, `us-east1` ou `us-west1` (as únicas com `e2-micro` e Cloud Storage gratuitos) | `bootstrap`, `envs/prod` |
| Zona pertencente a uma dessas regiões | `modules/compute_vm`, `envs/prod` |
| `machine_type == "e2-micro"` | `modules/compute_vm` |
| `boot_disk_size_gb <= 30` | `modules/compute_vm`, `envs/prod` |
| `db_password` com `[A-Za-z0-9_.-]` e mínimo de 16 caracteres | `modules/compute_vm`, `envs/prod` |
| `project_id`, `billing_account_id`, `repo_url` (HTTPS) e `bucket_name` no formato correto | `bootstrap`, `envs/prod` |

Também não existem, de propósito, recursos pagos: NAT, balanceador, IP estático, snapshot, Cloud SQL, Pub/Sub, Artifact Registry e Secret Manager. Um teste estático (`pytest -m infra`) garante essa lista.

## 5. Decisões de arquitetura

Registradas em `.specs/STATE.md`; as que moldam a infraestrutura:

- **AD-001:** o código chega à VM por `git clone`/`git pull` HTTPS do repositório público, com `docker compose build` na própria VM. Sem Artifact Registry ou Docker Hub; o repositório não pode ter segredos.
- **AD-002:** a senha do Postgres vai por metadata da instância e é gravada em `.env` (chmod 600) pelo startup script. Aparece no state; Secret Manager fica como evolução.
- **AD-003:** estrutura `bootstrap` / `modules` / `envs/prod`, backend GCS por configuração parcial, `disable_on_destroy = false` em toda API e guardas de Free Tier em `validation`.
- **AD-007:** SSH somente por túnel IAP (`gcloud compute ssh ... --tunnel-through-iap`); a rede corporativa (Netskope) torna um IP fixo no firewall pouco confiável.

## 6. Testes

Rodam sem credenciais: usam `mock_provider "google"`. Substitua `<dir>` por `terraform/bootstrap`, `terraform/modules/<módulo>` ou `terraform/envs/prod`:

```powershell
terraform fmt -check -recursive terraform
terraform -chdir=<dir> init -backend=false
terraform -chdir=<dir> validate
terraform -chdir=<dir> test
```

Depois do `init -backend=false` em `envs/prod`, rode `init -reconfigure "-backend-config=backend.hcl"` antes de qualquer `plan`/`apply`.

O startup script tem um teste de renderização à parte. Gere o JSON e rode os testes estáticos:

```powershell
terraform -chdir=terraform/modules/compute_vm/tests/render init        # só na primeira vez
terraform -chdir=terraform/modules/compute_vm/tests/render apply -auto-approve
terraform -chdir=terraform/modules/compute_vm/tests/render output -json | Set-Content -Path .rendered-startup.json -Encoding ascii
.venv\Scripts\python.exe -m pytest -m infra
```

O `-auto-approve` só é aceito nessa configuração de renderização (sem provider e sem recursos). O `.rendered-startup.json` não é versionado.

**Quando renderizar de novo:** só uma mudança real no `startup.sh.tftpl` exige repetir o `apply` e o `output`. O teste compara o `template_sha256` do JSON com o SHA-256 do template atual (checagem por hash, não por data), então trocar de branch ou tocar no arquivo sem mudar o conteúdo não invalida o JSON. Se o `pytest -m infra` mostrar `skip` por JSON ausente, o gate de infraestrutura **não** foi cumprido.

## 7. Reaproveitar no Azure

A estrutura (`bootstrap` / `modules` / `envs`), o backend parcial e os testes se repetem; os recursos mudam. O [mapa GCP → Azure](../docs/azure-mapping.md) lista o equivalente de cada módulo e as diferenças que importam (Resource Group, `custom_data` que recria a VM, custo e SSH).

## 8. Runbooks

- [Preparação do GCP e do Terraform](../docs/gcp-setup.md)
- [Destruição](../docs/destroy.md)
- [Custo, billing e disco](../docs/cost-and-billing.md)
- [Atualização do código na VM](../docs/update-code.md)
- [Mapa GCP → Azure](../docs/azure-mapping.md)
- [Desenvolvimento local](../docs/local-development.md)
