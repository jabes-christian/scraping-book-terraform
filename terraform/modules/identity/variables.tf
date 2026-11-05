variable "account_id" {
  type        = string
  description = "ID da service account da VM (6 a 30 caracteres: minúsculas, dígitos e hífens). Gera o e-mail <account_id>@<projeto>.iam.gserviceaccount.com."
  default     = "book-monitor-vm"
}
