# Atualização do código na VM

Como o código novo do robô chega à VM, como forçar a atualização na hora e como trocar a versão implantada (`repo_ref`). Comandos de `terraform` e `gcloud` em PowerShell, a partir da **raiz do projeto**; os comandos de dentro da VM são `bash`.

> Os comandos marcados com **[a validar]** foram derivados do startup script (`terraform/modules/compute_vm/startup.sh.tftpl`), mas ainda não foram executados na VM. Eles serão validados na Fase 10 (T54); corrija este guia onde a prática divergir.

## 1. Como a VM obtém o código (AD-001)

O código **não** vem de uma imagem pronta: a VM faz `git clone`/`git fetch` HTTPS do repositório **público** (`repo_url`, na versão `repo_ref`) e constrói a imagem do robô na própria VM com `docker compose build`.

O startup script roda como root **a cada boot** (e é idempotente). Em cada boot, o trecho de código faz:

1. Primeiro boot: `git clone --depth 1 --branch <repo_ref> <repo_url> /opt/book-monitor`.
2. Boots seguintes: `git fetch --depth 1 origin <repo_ref>` seguido de `git reset --hard FETCH_HEAD`. Se o `fetch` falhar (sem rede, por exemplo), registra um aviso e **mantém o checkout existente**.
3. `docker compose build`, `docker image prune -f` e `docker compose up -d --wait postgres`.

Esse trecho usa o mesmo `flock` do cron (`/var/lock/book-monitor.lock`): se um robô estiver rodando, a atualização espera (até 15 minutos) em vez de trocar o código por baixo dele.

Consequências:

- **Reiniciar a VM atualiza o código** para o que estiver no `repo_ref` naquele momento.
- **Edições manuais em arquivos versionados da VM são perdidas** no próximo boot (`reset --hard`). O `.env` (não versionado) e o volume do banco são preservados.
- O script **não cria o `.env` de novo** se ele já existe: mudar `db_password` no Terraform depois do primeiro boot não altera o `.env` nem o banco (ver a seção 5).

## 2. Escolher o `repo_ref`

`repo_ref` aceita uma **branch ou uma tag**. O clone usa `--branch`, então um hash de commit solto não funciona.

| `repo_ref` | Efeito | Quando usar |
| ---------- | ------ | ----------- |
| `main` (padrão) | Todo commit que chegar na `main` é implantado **no próximo boot**, sem revisão adicional | Estudo e testes |
| Tag (ex.: `v1.0.0`) | Versão congelada até você trocar a tag | Estabilidade: recomendado para uso contínuo |

Cuidados com `main`:

- Qualquer push na `main` entra em produção no próximo boot (inclusive após uma manutenção do host, que reinicia a VM).
- O repositório precisa ser público e **não pode conter segredos** (AD-001): a VM clona sem credenciais.
- Um commit com erro pode quebrar o build e deixar a VM sem a imagem nova (o `fetch` é refeito a cada boot, então corrigir o código e reiniciar resolve).

## 3. Atualização manual (sem esperar o boot)

Abra a sessão SSH pelo túnel IAP (único caminho de acesso, AD-007):

```powershell
terraform -chdir=terraform/envs/prod output -raw ssh_command
```

Execute a saída (algo como `gcloud compute ssh book-monitor --zone us-central1-a --project <project_id> --tunnel-through-iap`). Dentro da VM **[a validar]**:

```bash
cd /opt/book-monitor
sudo flock -w 900 /var/lock/book-monitor.lock git fetch --depth 1 origin main
sudo git reset --hard FETCH_HEAD
sudo docker compose build
sudo docker image prune -f
sudo docker compose up -d --wait --wait-timeout 180 postgres
```

Troque `main` pelo seu `repo_ref`. O `flock` espera um robô em execução terminar antes de mexer no código, como o startup script faz. O `build` é lento na e2-micro (0,25 vCPU compartilhada): leva vários minutos e usa bastante memória; evite fazê-lo perto do horário do cron (padrão 06:00 UTC).

### Verificar **[a validar]**

```bash
git -C /opt/book-monitor log -1 --oneline
sudo docker compose -f /opt/book-monitor/docker-compose.yml ps
sudo tail -n 50 /var/log/book-monitor/run.log
```

- O `log -1` deve mostrar o commit esperado (compare com `git log -1 --oneline` na sua máquina).
- O `ps` deve mostrar o serviço `postgres` como `healthy`.
- O `run.log` traz a saída das execuções do cron; o log do startup script fica em `/var/log/book-monitor-startup.log`.

Para rodar o robô agora, sem esperar o cron, use o mesmo comando do cron (com `flock`, para não sobrepor outra execução) **[a validar]**:

```bash
sudo flock -n /var/lock/book-monitor.lock docker compose -f /opt/book-monitor/docker-compose.yml run --rm -T robo
```

Se o `flock -n` não imprimir nada e voltar logo, outra execução está rodando.

## 4. Trocar o `repo_ref` pelo Terraform

Para implantar outra branch ou tag, mude `repo_ref` em `terraform/envs/prod/terraform.tfvars` (pelo editor) e aplique. O fluxo é o de `docs/gcp-setup.md` (seção 5.4); lembre que a senha vem de `$env:TF_VAR_db_password`, e que **deve ser a senha guardada**:

```powershell
terraform -chdir=terraform/envs/prod init -reconfigure "-backend-config=backend.hcl"
terraform -chdir=terraform/envs/prod plan "-out=prod.tfplan"
```

Revise o plano. A troca de `repo_ref` deve aparecer como **`update in-place`** na instância (`~ google_compute_instance.this`), porque o script vai em `metadata["startup-script"]` e o provider altera a metadata sem recriar a VM **[a validar]**.

**Se o plano mostrar recriação da VM** (`-/+`, `must be replaced` ou `forces replacement`), **pare e não aplique**: recriar a VM apaga o disco e, com ele, o volume do banco e todo o histórico de preços. Descubra o que forçou a recriação (a linha marcada com `# forces replacement`) antes de continuar.

Se o plano estiver correto (apenas `update in-place`):

```powershell
terraform -chdir=terraform/envs/prod apply "prod.tfplan"
Remove-Item terraform\envs\prod\prod.tfplan
```

O `apply` de plano salvo não pede confirmação (a revisão do plano é a confirmação), e o `.tfplan` contém a senha em texto puro: apague-o.

Mudar a metadata **não executa o script na hora**: o novo `repo_ref` só vale no próximo boot. Para aplicá-lo agora, reinicie a VM **[a validar]**.

**Primeira opção: reboot limpo**, dentro da VM (sessão SSH pelo IAP, seção 3). O sistema encerra os serviços na ordem (inclusive o Docker e o Postgres) antes de reiniciar:

```bash
sudo systemctl reboot
```

**Alternativa, só se a VM não responder** (SSH travado, por exemplo): reset pelo `gcloud`. Ele é **abrupto**: equivale a apertar o botão de reset, sem desligar os serviços, e pode deixar o Postgres para recuperar o log de transações no boot seguinte. Prefira o reboot limpo sempre que possível **[a validar]**:

```powershell
gcloud compute instances reset book-monitor --zone us-central1-a --project <project_id>
```

Se um robô estiver rodando, prefira esperar o fim da execução antes de reiniciar. Ou use o fluxo manual da seção 3 com o novo `repo_ref`, sem reiniciar.

## 5. A senha do Postgres é fixada na primeira inicialização do volume

O Postgres grava a senha ao inicializar o volume de dados pela primeira vez. O `.env` da VM também é criado só uma vez, a partir da metadata. Por isso:

- Trocar `db_password` no Terraform depois do primeiro boot **muda a metadata, mas não o `.env` nem o banco**.
- Reaplicar com uma senha diferente da guardada não quebra o banco existente, mas deixa a metadata e a realidade divergentes, e confunde um futuro `apply`.

**Use sempre a senha guardada** no gerenciador de senhas. Para trocar de verdade a senha, é preciso alterá-la dentro do Postgres e no `.env` da VM, ou recriar o ambiente (`docs/destroy.md`), o que apaga o histórico de preços.

## 6. Resumo

| Quero... | Faça |
| -------- | ---- |
| Pegar o commit novo da `main` | Reiniciar a VM, ou a atualização manual (seção 3) |
| Congelar uma versão | `repo_ref` com uma tag + `apply` (seção 4) e reiniciar |
| Rodar o robô agora | Comando com `flock` da seção 3 |
| Conferir a versão implantada | `git -C /opt/book-monitor log -1 --oneline` na VM |
| Trocar a senha do banco | Seção 5: não é só mudar a variável |

## 7. Referências

- `docs/gcp-setup.md`: preparação, fluxo do Terraform e acesso por IAP.
- `docs/destroy.md`: recriar o ambiente do zero.
- `docs/cost-and-billing.md`: disco e custo (o rebuild consome disco).
