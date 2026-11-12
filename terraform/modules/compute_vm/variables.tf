variable "zone" {
  type        = string
  description = "Zona da VM. Só as regiões us-central1, us-east1 e us-west1 têm e2-micro no Free Tier."
  default     = "us-central1-a"

  validation {
    condition     = anytrue([for prefix in ["us-central1-", "us-east1-", "us-west1-"] : startswith(var.zone, prefix)])
    error_message = "zone deve começar com us-central1-, us-east1- ou us-west1-: fora dessas regiões a e2-micro não é gratuita."
  }
}

variable "machine_type" {
  type        = string
  description = "Tipo de máquina. Fixo em e2-micro (Free Tier)."
  default     = "e2-micro"

  validation {
    condition     = var.machine_type == "e2-micro"
    error_message = "machine_type deve ser e2-micro: qualquer outro tipo gera custo fora do Free Tier."
  }
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

variable "subnetwork" {
  type        = string
  description = "Self link (ou id) da sub-rede onde a VM é criada (saída do módulo network)."
}

variable "network_tag" {
  type        = string
  description = "Tag de rede aplicada à VM, usada pela regra de firewall SSH (saída do módulo network)."
}

variable "service_account_email" {
  type        = string
  description = "E-mail da service account anexada à VM (saída do módulo identity)."
}

variable "repo_url" {
  type        = string
  description = "URL HTTPS do repositório público clonado pela VM."
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
  description = "Senha do PostgreSQL. Vai para a metadata book-db-password e é gravada no .env da VM (AD-002)."
  sensitive   = true

  # Adição ao escopo aprovada pelo autor: o Compose interpreta $, #, aspas, espaço
  # e \ ao ler o .env, o que faria o banco subir com senha diferente da do Terraform.
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
