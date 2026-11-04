provider "google" {
  project = var.project_id

  # Com ADC de usuário, as chamadas de API precisam de um "quota project".
  # user_project_override faz o provider enviar o cabeçalho X-Goog-User-Project
  # e billing_project define qual projeto recebe a cota/cobrança dessas chamadas.
  user_project_override = true
  billing_project       = var.project_id
}
