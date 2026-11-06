variable "region" {
  type        = string
  description = "Região da sub-rede. A VM deve ficar em uma zona desta região."
  default     = "us-central1"
}

variable "allowed_ssh_cidr" {
  type        = string
  description = "CIDR IPv4 autorizado a acessar a VM por SSH (tcp:22). Use o seu IP público com /32."

  validation {
    condition     = can(cidrnetmask(var.allowed_ssh_cidr))
    error_message = "allowed_ssh_cidr deve ser um CIDR IPv4 válido (ex.: 203.0.113.10/32)."
  }

  validation {
    condition     = var.allowed_ssh_cidr != "0.0.0.0/0"
    error_message = "allowed_ssh_cidr não pode ser 0.0.0.0/0: o SSH ficaria aberto para a internet inteira."
  }

  # Adição ao escopo aprovada pelo autor: prefixo mínimo /24 (no máximo 256
  # endereços). try() evita erro de avaliação quando o valor não tem "/".
  validation {
    condition     = try(tonumber(split("/", var.allowed_ssh_cidr)[1]) >= 24, false)
    error_message = "allowed_ssh_cidr deve ter prefixo /24 ou mais específico (até /32); redes maiores, como /8 e /16, expõem o SSH a faixas amplas demais."
  }
}
