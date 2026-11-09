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
