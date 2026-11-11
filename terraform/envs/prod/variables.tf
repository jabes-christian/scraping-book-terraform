variable "project_id" {
  type        = string
  description = "ID do projeto GCP onde a infraestrutura de producao sera criada (informado via terraform.tfvars local)."

  validation {
    condition     = length(trimspace(var.project_id)) > 0
    error_message = "project_id é obrigatório e não pode ser vazio."
  }

  # Regra do GCP: 6 a 30 caracteres, letras minúsculas, dígitos e hífens;
  # começa com letra e não termina com hífen.
  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{4,28}[a-z0-9]$", var.project_id))
    error_message = "project_id inválido: use 6 a 30 caracteres (minúsculas, dígitos e hífens), começando por letra e sem terminar em hífen."
  }
}

variable "billing_account_id" {
  type        = string
  description = "ID da conta de faturamento (formato XXXXXX-XXXXXX-XXXXXX, sem o prefixo billingAccounts/). Usado pelo orçamento."

  validation {
    condition     = can(regex("^[A-Z0-9]{6}-[A-Z0-9]{6}-[A-Z0-9]{6}$", var.billing_account_id))
    error_message = "billing_account_id inválido: use o formato XXXXXX-XXXXXX-XXXXXX (letras maiúsculas e dígitos), sem o prefixo billingAccounts/."
  }
}

variable "region" {
  type        = string
  description = "Região da sub-rede. Só as regiões us-central1, us-east1 e us-west1 têm e2-micro no Free Tier."
  default     = "us-central1"

  validation {
    condition     = contains(["us-central1", "us-east1", "us-west1"], var.region)
    error_message = "region deve ser us-central1, us-east1 ou us-west1: fora delas a e2-micro não é gratuita."
  }
}

variable "zone" {
  type        = string
  description = "Zona da VM; deve pertencer à região informada."
  default     = "us-central1-a"

  validation {
    condition     = startswith(var.zone, "${var.region}-")
    error_message = "zone deve pertencer à região informada em region (ex.: us-central1-a para us-central1)."
  }
}

variable "repo_url" {
  type        = string
  description = "URL HTTPS do repositório público que a VM clona (AD-001)."

  validation {
    condition     = startswith(var.repo_url, "https://")
    error_message = "repo_url deve ser uma URL HTTPS (a VM clona o repositório público sem credenciais)."
  }
}

variable "repo_ref" {
  type        = string
  description = "Branch ou tag do repositório que a VM implanta a cada boot. Prefira uma tag para estabilidade (hash de commit não funciona: o clone usa --branch)."
  default     = "main"
}

variable "db_name" {
  type        = string
  description = "Nome do banco PostgreSQL gravado no .env da VM."
  default     = "books"
}

variable "db_user" {
  type        = string
  description = "Usuário do PostgreSQL gravado no .env da VM."
  default     = "books"
}

variable "db_password" {
  type        = string
  description = "Senha do PostgreSQL. Informe por TF_VAR_db_password, nunca no terraform.tfvars (AD-002)."
  sensitive   = true

  # O Compose interpreta $, #, aspas, espaço e \ ao ler o .env, o que faria o
  # banco subir com senha diferente da do Terraform.
  validation {
    condition     = can(regex("^[A-Za-z0-9_.-]*$", var.db_password))
    error_message = "db_password só pode conter letras, números, _, . e - (outros caracteres, como $ e #, são alterados pelo Compose ao ler o .env)."
  }

  validation {
    condition     = length(var.db_password) >= 16
    error_message = "db_password deve ter no mínimo 16 caracteres."
  }
}

variable "cron_schedule" {
  type        = string
  description = "Expressão cron (5 campos) da execução diária do robô."
  default     = "0 6 * * *"
}

variable "swap_size_mb" {
  type        = number
  description = "Tamanho do swap file em MB, criado antes do build."
  default     = 1024
}

variable "boot_disk_size_gb" {
  type        = number
  description = "Tamanho do disco de boot (pd-standard) em GB. O Free Tier cobre até 30 GB."
  default     = 30

  validation {
    condition     = var.boot_disk_size_gb <= 30
    error_message = "boot_disk_size_gb deve ser no máximo 30: acima disso o disco deixa de caber no Free Tier."
  }
}
