# Mapa GCP → Azure

Correspondência entre os módulos Terraform deste projeto (GCP) e os recursos equivalentes no Azure (provider `azurerm`), com as diferenças que importam para uma futura migração. É um guia de planejamento: **nada aqui foi aplicado nem testado no Azure**.

Os nomes dos recursos e argumentos do `azurerm` foram conferidos na documentação do provider (Context7, `hashicorp/terraform-provider-azurerm`). O que **não** foi confirmado em documentação está marcado como **[não verificado]**.

## 1. Visão geral

| Módulo GCP | Recursos GCP | Equivalente no Azure | Diferença principal |
| ---------- | ------------ | -------------------- | ------------------- |
| `apis` | `google_project_service` (4 APIs, `disable_on_destroy = false`) | Registro de *resource providers* da assinatura: propriedade `resource_providers_to_register` do provider | No Azure não se "liga uma API por projeto"; registram-se provedores de recursos na assinatura, e o próprio provider pode fazê-lo |
| `network` | `google_compute_network`, `google_compute_subnetwork`, `google_compute_firewall` | `azurerm_virtual_network`, `azurerm_subnet`, `azurerm_network_security_group`, `azurerm_subnet_network_security_group_association` | Tudo vive dentro de um *resource group*; o firewall é um NSG associado à sub-rede, com prioridades numéricas; **não há equivalente direto confirmado do SSH por IAP** (ver 2.5) |
| `identity` | `google_service_account` (sem roles) | `identity` da própria VM (`SystemAssigned`) ou `azurerm_user_assigned_identity` | A identidade pode ser criada junto com a VM; sem papéis atribuídos, equivale à SA sem roles |
| `compute_vm` | `google_compute_instance` (e2-micro, `pd-standard`, IP efêmero, startup script em metadata) | `azurerm_linux_virtual_machine`, `azurerm_network_interface`, `azurerm_public_ip` | Mais recursos separados; o script vai em `custom_data`, que **recria a VM** ao mudar (ver 2.4) |
| `budget` | `google_billing_budget` (R$ 5; 50/90/100%) | `azurerm_consumption_budget_subscription` (ou `..._resource_group`) | O escopo é a assinatura ou o resource group, não a conta de faturamento; o alerta também só notifica |
| `bootstrap` (state) | `google_storage_bucket` versionado + backend `gcs` | `azurerm_storage_account` (com `blob_properties`) + `azurerm_storage_container` + backend `azurerm` | Exige um resource group e uma *storage account* antes do container |

## 2. Detalhes por módulo

### 2.0 Resource Group: o primeiro recurso a criar

Todo recurso do Azure vive dentro de um `azurerm_resource_group` (com `name` e `location`), e quase todos os recursos citados abaixo exigem `resource_group_name` e `location`. O projeto GCP **não tem equivalente direto**: lá o contêiner é o próprio projeto, que já existe antes do Terraform (`project_id`).

Por isso, no Azure o resource group é o **primeiro recurso a criar**, antes da rede, da VM e da storage account do state. Há duas consequências:

- O bootstrap do state precisa de um resource group próprio (ou do mesmo) para a storage account, e `envs/prod` precisa do seu.
- O `destroy` de um resource group remove tudo o que há dentro dele, o que muda o desenho do runbook `docs/destroy.md` (ordem e riscos).

### 2.1 `apis` → registro de resource providers

No GCP, o módulo habilita `compute`, `iam`, `billingbudgets` e `iap` com `disable_on_destroy = false`, para que o `destroy` não desligue APIs do projeto.

No Azure, o equivalente é o registro dos *resource providers* na assinatura (por exemplo, Compute, Network, Storage e Consumption). O provider `azurerm` registra um conjunto configurável por `resource_provider_registrations` (`core`, `extended`, `all`, `legacy`, `none`) e aceita uma lista explícita em `resource_providers_to_register`. A documentação recomenda registrar apenas o que o projeto usa. O comportamento do registro no `destroy` (equivalente ao `disable_on_destroy = false`) **não foi verificado**: confirme antes de depender dele.

### 2.2 `network` → VNet, sub-rede e NSG

| GCP | Azure |
| --- | ----- |
| `google_compute_network` (`auto_create_subnetworks = false`) | `azurerm_virtual_network` (precisa de `address_space`) |
| `google_compute_subnetwork` (`10.10.0.0/24`) | `azurerm_subnet` (`address_prefixes`) |
| `google_compute_firewall` ingress `tcp:22` com `source_ranges` e `target_tags` | `azurerm_network_security_group` com `security_rule` (`direction`, `access`, `priority`, `protocol`, `source_address_prefix` etc.) + `azurerm_subnet_network_security_group_association` |

Diferenças:

- No GCP o firewall é aplicado às VMs por **tag** (`book-monitor`). No Azure o NSG é associado à **sub-rede** (ou à interface de rede) e as regras têm `priority` obrigatória entre 100 e 4096.
- Não misture regras `security_rule` embutidas no NSG com recursos `azurerm_network_security_rule` separados no mesmo NSG: a documentação avisa que um sobrescreve o outro.
- O Azure exige um `azurerm_resource_group` e uma `location` em quase todo recurso. O GCP usa só `project` e `region`.

### 2.3 `identity` → identidade gerenciada

A SA dedicada e sem papéis do GCP (a VM não chama APIs do GCP) corresponde, no Azure, a uma identidade gerenciada:

- `identity { type = "SystemAssigned" }` na própria `azurerm_linux_virtual_machine`, ou
- `azurerm_user_assigned_identity` separada, referenciada na VM.

Sem atribuições de papel (RBAC), a identidade não tem permissão nenhuma, o mesmo efeito da SA sem roles. Como a VM deste projeto não chama APIs da nuvem, uma identidade nem é obrigatória no Azure: avalie se vale mantê-la só por paridade.

### 2.4 `compute_vm` → máquina virtual Linux

| GCP (`google_compute_instance`) | Azure |
| ------------------------------- | ----- |
| `machine_type = "e2-micro"` | `size` da `azurerm_linux_virtual_machine` (por exemplo, a série B; o tamanho gratuito depende do plano, ver 3) |
| `boot_disk` `pd-standard`, `size` 30 | `os_disk` com `storage_account_type` (`Standard_LRS`, `StandardSSD_LRS`, `Premium_LRS`...) e `disk_size_gb` |
| `network_interface` com `access_config {}` (IP efêmero) | `azurerm_network_interface` + `azurerm_public_ip` (os SKUs atuais exigem `allocation_method = "Static"`: **não há IP público efêmero**; o `Basic`/`Dynamic` foi descontinuado para novos recursos) |
| `metadata.startup-script` | `custom_data` (base64, **sensível**) |
| `metadata.book-db-password` | Sem atributo de metadata equivalente confirmado na documentação do recurso: avalie `custom_data` (cuidado, ver abaixo) ou, como evolução, Azure Key Vault lido com a identidade da VM |
| `service_account` | `identity` (ver 2.3) |
| `shielded_instance_config` | Argumentos de segurança da VM (consulte a documentação do recurso) |
| `scheduling` (`preemptible = false`) | `priority = "Regular"` (padrão) |
| Autenticação SSH por IAP / chaves do `gcloud` | `admin_ssh_key` (chave pública) ou `admin_password` (um dos dois é obrigatório) |

Diferenças que podem causar prejuízo:

1. **Mudar `custom_data` recria a VM.** No schema do provider, `custom_data` é `ForceNew`. No GCP, trocar o `startup-script` ou o `repo_ref` é uma alteração in-place. No Azure, trocar o script (ou qualquer valor que entre nele, como o `repo_ref`) **destrói e recria a VM**, apagando o disco e o volume do banco. O fluxo de `docs/update-code.md` (trocar `repo_ref` por `apply`) não pode ser copiado como está.
2. **O `custom_data` não roda a cada boot.** No GCP, o startup script roda em todo boot e é a base do ciclo de atualização (AD-001). No Azure, o `custom_data` é entregue ao cloud-init, que o executa por padrão apenas no primeiro boot da instância **[não verificado na documentação do provider]**. Para repetir a atualização a cada boot, será preciso outro mecanismo e o fluxo de atualização do código precisa ser repensado (ver 2.4.1).
3. **Senha no `custom_data`.** O valor fica marcado como sensível, mas está no state do Terraform e é entregue à VM **[onde fica gravado na VM: não verificado]**. Valem o mesmo cuidado e a mesma dívida técnica do AD-002.

#### 2.4.1 Reproduzir o comportamento do GCP (script a cada boot, atualização in-place)

O GCP dá, de graça, duas propriedades que o `custom_data` não tem: o script roda a cada boot e mudá-lo não recria a VM. As alternativas para reproduzi-las:

1. **cloud-init instalando um serviço `systemd`.** O `custom_data` (primeiro boot) cria uma unidade `systemd` do tipo `oneshot` que, em todo boot, faz o `git fetch`, o `reset --hard`, o `build` e o `up -d`. O ciclo de atualização por reinício do `docs/update-code.md` passa a funcionar. Limite: o `repo_ref` ainda entraria pelo `custom_data` (que é `ForceNew`), a menos que a unidade o leia de um arquivo atualizado por outro caminho **[não verificado]**.
2. **`azurerm_virtual_machine_extension` (CustomScript).** Recurso separado da VM, com `publisher = "Microsoft.Azure.Extensions"`, `type = "CustomScript"`, `type_handler_version = "2.0"` e o script em `settings` / `protected_settings` (`commandToExecute`). Pela documentação do provider, exige o agente de convidado (Guest Agent) da VM em execução, e o comando precisa terminar com código de saída `0`. Como a extensão é um recurso próprio, alterar o script **não passa pelo `ForceNew` do `custom_data`** da VM, o que aproxima a troca de `repo_ref` do comportamento in-place do GCP. **[não verificado]**: se a extensão reexecuta quando só os `settings` mudam, e se ela roda a cada boot (o padrão é rodar ao ser aplicada ou alterada, não a cada reinício).

Uma combinação possível: serviço `systemd` (via `custom_data`) para rodar a cada boot, e uma extensão (ou outro mecanismo) para entregar o `repo_ref`. Qualquer escolha exige testar o ciclo completo no Azure antes de confiar nele.

### 2.5 Acesso SSH: sem equivalente direto ao IAP

O AD-007 libera o SSH somente pelo túnel IAP, sem abrir a porta 22 para IPs de usuário. No Azure, o equivalente funcional é o **Azure Bastion** (`azurerm_bastion_host`). Os níveis `Basic`, `Standard` e `Premium` são serviços **pagos** (preço não verificado aqui).

O nível **`Developer`** (`sku = "Developer"`, com `virtual_network_id` em vez de `ip_configuration`) é uma alternativa possível, apontada como gratuita. O que o Context7 confirma é só que o `sku` existe no provider. As limitações abaixo estão **[não verificadas]** e precisam ser conferidas na documentação do Azure antes de adotá-lo:

- custo e disponibilidade por região (e se é realmente sem cobrança);
- número de sessões simultâneas e tamanhos de VM suportados;
- o recurso `tunneling_enabled` (túnel nativo para uso com a CLI) é documentado no provider apenas para `Standard` e `Premium`, então o `Developer` provavelmente se limita ao acesso pelo portal, sem um comando equivalente a `gcloud compute ssh --tunnel-through-iap`;
- demais restrições de rede e de região do nível.

Outras opções são o acesso *just-in-time* do Microsoft Defender for Cloud, restringir a regra de NSG a um `source_address_prefix` específico (o problema do IP de saída do proxy corporativo do AD-007 volta) ou usar uma VPN.

Decisão de migração: o AD-007 precisa ser reavaliado no Azure. A combinação "sem custo e sem IP fixo, por linha de comando" não tem um serviço equivalente direto confirmado.

### 2.6 `budget` → orçamento de consumo

`google_billing_budget` corresponde a `azurerm_consumption_budget_subscription` (escopo da assinatura) ou `azurerm_consumption_budget_resource_group` (escopo de um resource group, o mais próximo do filtro por projeto do GCP).

| GCP | Azure |
| --- | ----- |
| `amount.specified_amount` (`BRL`, 5) | `amount` e `time_grain` (por exemplo, `Monthly`) |
| `threshold_rules` (0,5 / 0,9 / 1,0) | um bloco `notification` por limite, com `threshold` em **percentual** (50, 90, 100), `operator` e `threshold_type` (`Actual` ou `Forecasted`) |
| e-mail aos papéis da conta de faturamento (padrão) | `contact_emails`, `contact_groups` e/ou `contact_roles` (ao menos um é obrigatório; **não há destinatário padrão**) |
| `budget_filter.projects` | bloco `filter` (por exemplo, dimensão `ResourceGroupName`) |

O orçamento do Azure **também só notifica**: não bloqueia o gasto. Exige `time_period` com `start_date` no primeiro dia do mês.

### 2.7 `bootstrap` e backend → storage account

| GCP | Azure |
| --- | ----- |
| `google_storage_bucket` (`versioning`, `public_access_prevention`, `uniform_bucket_level_access`) | `azurerm_storage_account` com o bloco `blob_properties` (`versioning_enabled = true`, `delete_retention_policy`) + `azurerm_storage_container` |
| Regra de ciclo de vida que apaga versões antigas | Política de gerenciamento do ciclo de vida da storage account (recurso próprio; consulte a documentação) |
| `backend "gcs"` com `bucket` e `prefix` | `backend "azurerm"` com resource group, storage account, container e `key` **[conferir na documentação do backend]** |
| `force_destroy` | Exige esvaziar o container antes do destroy, ou aceitar a remoção da storage account inteira |

A configuração parcial do backend (`backend.hcl` fora do Git) continua valendo no Azure: o nome da storage account é globalmente único e não deve ficar no código versionado.

## 3. O que muda além dos recursos

- **Custo: o principal risco ao portar.** No GCP, a `e2-micro` é gratuita **permanentemente** (dentro do Free Tier), e o projeto inteiro foi desenhado em torno disso. No Azure, a VM gratuita (série B, por exemplo a `B1s`) vale por **12 meses e só em contas novas**; depois disso passa a ser cobrada. O IP público `Standard` (o único disponível para novos recursos, `Static`) também é **cobrado**, e não há IP efêmero gratuito como no GCP. Essas informações vêm do conhecimento do autor e **não foram verificadas** no Context7: confirme limites, tamanhos e preços na página oficial do Azure antes de portar. A consequência prática é que o requisito "custo mensal R$ 0" do projeto pode deixar de valer no Azure, e o orçamento (seção 2.6) passa de rede de segurança a controle de um custo esperado.
- **Guardas de Free Tier.** As `validation` de região, zona, tamanho de disco e tipo de máquina refletem os limites do Free Tier do GCP. O Azure tem regras próprias (por tempo da conta e por tamanho de VM) **[não verificado aqui]**; revise todas as guardas e o orçamento antes de portar.
- **Variáveis.** `project_id` e `billing_account_id` dão lugar a `subscription_id` (e aos dados do resource group). `region`/`zone` viram `location`.
- **Quota/billing project.** `user_project_override` e `billing_project` do provider `google` não têm equivalente no `azurerm`.
- **Provider.** `required_providers` passa a usar `hashicorp/azurerm`; o bloco `features {}` é obrigatório no `provider "azurerm"`.

## 4. O que se reaproveita

- A estrutura `terraform/{bootstrap,modules,envs/prod}` e a divisão em módulos de responsabilidade única.
- O backend remoto parcial com `backend.hcl` local e `*.example` versionado.
- Os testes com `terraform test` e `mock_provider` (trocando o provider para `azurerm`) e os testes estáticos do `pytest -m infra`.
- O runtime da VM: Docker Compose, o robô, o Postgres, o cron com `flock` e o logrotate. A imagem é construída na VM a partir do repositório público (AD-001), independentemente da nuvem. Só o mecanismo que dispara o script (e o ciclo de atualização) muda.
- As lições de operação de `docs/` (senha fixada no primeiro boot do volume, plano salvo com segredo, ordem do destroy).

## 5. Referências

- `terraform/README.md`: estrutura e módulos da infraestrutura atual.
- `docs/update-code.md`: ciclo de atualização que precisa ser repensado no Azure (seção 2.4).
- `docs/destroy.md`: ordem de destruição (vale também para o Azure).
