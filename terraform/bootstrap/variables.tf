variable "project_id" {
  type        = string
  description = "ID do projeto GCP onde o bucket do remote state será criado (informado via terraform.tfvars local)."

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

variable "region" {
  type        = string
  description = "Região do bucket. Restrita às regiões do Free Tier do Cloud Storage."
  default     = "us-central1"

  validation {
    condition     = contains(["us-central1", "us-east1", "us-west1"], var.region)
    error_message = "region deve ser us-central1, us-east1 ou us-west1 (regiões do Free Tier do Cloud Storage)."
  }
}

variable "bucket_name" {
  type        = string
  description = "Nome do bucket do state. Se null, usa \"<project_id>-tfstate\"."
  default     = null

  validation {
    condition     = var.bucket_name == null || can(regex("^[a-z0-9][a-z0-9_.-]{1,61}[a-z0-9]$", var.bucket_name))
    error_message = "bucket_name inválido: use 3 a 63 caracteres (minúsculas, dígitos, hífen, underscore ou ponto), começando e terminando com letra ou dígito."
  }
}

variable "force_destroy" {
  type        = bool
  description = "Se true, o destroy apaga o bucket mesmo com objetos (inclusive versões). Mantenha false fora do teste de destruição."
  default     = false
}
