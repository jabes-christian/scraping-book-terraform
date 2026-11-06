variable "billing_account_id" {
  type        = string
  description = "ID da conta de faturamento (formato XXXXXX-XXXXXX-XXXXXX, sem o prefixo billingAccounts/)."
}

variable "project_id" {
  type        = string
  description = "ID do projeto GCP cujo gasto o orçamento acompanha."
}

variable "amount_units" {
  type        = number
  description = "Valor do orçamento em unidades inteiras da moeda (padrão: 5)."
  default     = 5
}

variable "currency_code" {
  type        = string
  description = "Código ISO 4217 da moeda; deve ser a moeda da conta de faturamento (padrão: BRL)."
  default     = "BRL"
}

variable "thresholds" {
  type        = list(number)
  description = "Fração do orçamento que dispara o alerta por e-mail (0.5 = 50%)."
  default     = [0.5, 0.9, 1.0]
}
