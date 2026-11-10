provider "google" {
  project = var.project_id

  # Com ADC de usuario, as chamadas de API precisam de um "quota project".
  # user_project_override faz o provider enviar o cabecalho X-Goog-User-Project
  # e billing_project define qual projeto recebe a cota/cobranca dessas chamadas
  # (obrigatorio para google_billing_budget; ver Design).
  user_project_override = true
  billing_project       = var.project_id
}
