# Habilita as APIs informadas, uma instância por serviço (for_each).
# disable_on_destroy = false: o destroy não desliga a API para o projeto
# inteiro (AD-003 / TFP-13). disable_dependent_services = false: nunca desliga
# serviços dependentes em cascata.
resource "google_project_service" "this" {
  for_each = toset(var.services)

  project = var.project_id
  service = each.key

  disable_on_destroy         = false
  disable_dependent_services = false
}
