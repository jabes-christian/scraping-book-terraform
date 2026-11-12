# Custo, billing e disco

O projeto foi desenhado para ficar no **Free Tier** do GCP. A conta de faturamento, porém, é **paga, em BRL e sem créditos**: qualquer recurso fora do Free Tier gera cobrança real no cartão. Este guia mostra como conferir o que está sendo cobrado, o que o orçamento faz (e não faz) e como vigiar o disco da VM. Comandos em PowerShell, a partir da **raiz do projeto**.

> Comandos marcados com **[a validar]** não foram executados neste projeto. Confirme a saída na primeira vez e corrija o guia se divergir.

## 1. O que cabe no Free Tier (e o que o projeto cria)

| Recurso | Limite gratuito | O que o projeto usa |
| ------- | --------------- | ------------------- |
| Compute Engine | 1 VM `e2-micro` não-preemptível por mês, em `us-central1`, `us-east1` ou `us-west1` | 1 VM `e2-micro` em `us-central1-a` (as guardas de `variables.tf` rejeitam outras regiões) |
| Disco | 30 GB-mês de `pd-standard` | 1 disco `pd-standard` de 30 GB (`boot_disk_size_gb` no máximo 30) |
| Egress de rede | 1 GB/mês (América do Norte) | Baixo: o robô só faz ingress; o egress relevante é o SSH |
| Cloud Storage | 5 GB-mês regional, só nas 3 regiões acima | Bucket do state, poucos KB, com limpeza das versões antigas |

O que **não** existe no projeto, de propósito, porque não é gratuito: Cloud NAT, balanceador de carga, IP estático reservado, snapshots, Cloud SQL, Pub/Sub, Artifact Registry e Secret Manager. Se qualquer um aparecer num `plan`, pare e revise (ver `docs/gcp-setup.md`, seção 5.4). Mais de uma `e2-micro` consumiria as horas gratuitas: o máximo é uma VM.

## 2. Conferir o IPv4 externo no Billing Report

A VM usa um **IP externo efêmero** (necessário para clonar o repositório e baixar pacotes, já que não há NAT). A documentação do GCP sobre a cobrança desse IPv4 em VM do Free Tier é conflitante: há fontes dizendo que não é cobrado e outras que citam algo em torno de US$ 0,005 por hora (cerca de US$ 3,65 por mês, ou R$ 20). **Isso não está confirmado**: a decisão do projeto é aceitar o IP e verificar na prática.

Como verificar (console do Cloud Billing, no navegador):

1. Abra o Cloud Billing da conta de faturamento do projeto e vá em **Faturamento → Gerenciamento de custo → Relatórios** (no console em inglês: Billing → Cost management → Reports).
2. Filtre pelo **projeto** (`<project_id>`) e agrupe por **SKU**.
3. Procure, no Compute Engine, itens relativos a **endereço IP externo / IPv4**. Se houver custo, o item aparece com o valor acumulado; se não houver, o IP está coberto pelo Free Tier.
4. Confira também que os demais itens do Compute Engine e do Storage estão em **R$ 0**.

Faça a primeira conferência depois de alguns dias de VM no ar e repita ao fechar o mês. Critério de sucesso do projeto: o Billing Report do primeiro mês mostra R$ 0 em recursos faturáveis, ou apenas o IPv4 externo.

**Atraso dos dados:** o Billing Report e os alertas do orçamento usam dados de billing que chegam com **atraso de horas a dias**. Uma conferência no dia seguinte ao `apply` pode ainda não mostrar nada; não conclua "R$ 0" sem esperar.

Se o IPv4 for cobrado e você não quiser pagar, a saída é destruir a VM (`docs/destroy.md`); não há como abrir mão do IP externo sem NAT, que também é pago.

## 3. O orçamento apenas notifica: não limita o gasto

O Terraform cria um orçamento (`google_billing_budget`) de **R$ 5**, filtrado pelo projeto, com alertas por e-mail em **50%, 90% e 100%** (R$ 2,50, R$ 4,50 e R$ 5,00). Sem Pub/Sub e sem automação: o e-mail vai para quem tem os papéis de administrador ou usuário da conta de faturamento (padrão do GCP).

O que isso **não** faz:

- **Não bloqueia nem desliga nada.** Passar de 100% só envia um aviso; o gasto continua.
- **Não é em tempo real.** Por causa do atraso dos dados de billing (seção 2), o aviso pode chegar horas ou dias depois do gasto.
- **Não garante que o e-mail chegue.** O destinatário padrão não foi verificado em produção; confira a caixa de entrada (e o spam) quando o primeiro alerta disparar.

O **corte real de custo é o `terraform destroy`** (`docs/destroy.md`). Se receber um alerta inesperado, abra o Billing Report, identifique o SKU e, se for o caso, destrua.

No console, o orçamento fica em **Faturamento → Cost control → Budgets & caps**.

Para inspecioná-lo pela linha de comando **[a validar]**:

```powershell
gcloud billing budgets list --billing-account=<billing_account_id>
```

## 4. Disco da VM: inspeção manual aos 90%

O disco de boot tem 30 GB e guarda tudo: sistema, imagens do Docker, o volume do Postgres e os logs em `/var/log/book-monitor/`. O logrotate roda diariamente (7 rotações, comprimidas), e o startup script limpa imagens antigas, mas **não há alerta automático de disco**. A vigilância é manual.

Abra uma sessão SSH pelo túnel IAP (único caminho de acesso, AD-007) com o comando que o Terraform entrega:

```powershell
terraform -chdir=terraform/envs/prod output -raw ssh_command
```

Execute a saída (algo como `gcloud compute ssh book-monitor --zone us-central1-a --project <project_id> --tunnel-through-iap`) e, dentro da VM:

```bash
df -h /
```

Leia a coluna `Use%` da linha de `/`.

- **Abaixo de 90%:** nada a fazer.
- **90% ou mais:** investigue o que cresce. Os suspeitos são as imagens e camadas do Docker, o volume do Postgres e os logs. Comandos de diagnóstico **[a validar]**: `docker system df` (uso do Docker) e `sudo du -xh --max-depth=1 /var | sort -h` (maiores diretórios em `/var`).
- Se o crescimento vier do Docker, remova imagens sem uso com `sudo docker image prune -f` **[a validar]**. Não apague o volume do Postgres: é o histórico de preços.
- Se o problema for o volume de dados em si, a opção é aumentar `boot_disk_size_gb`, mas o limite do Free Tier é **30 GB**: acima disso o disco deixa de ser gratuito (a variável rejeita valores maiores). Nesse caso, decida entre pagar pelo disco maior ou limpar dados antigos.

Sugestão de rotina: rodar o `df -h /` ao fim da primeira semana e uma vez por mês.

## 5. Referências

- `docs/gcp-setup.md`: preparação e fluxo do Terraform.
- `docs/destroy.md`: o `terraform destroy` como corte de custo.
- `docs/update-code.md`: atualização do código na VM (rebuild consome disco).
