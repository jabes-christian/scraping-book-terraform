# Composicao do ambiente de producao: habilita as APIs e, depois delas, cria
# rede, identidade, VM e orcamento. Todos os recursos vivem nos modulos; este
# arquivo so liga as entradas e as saidas (TFP-01, TFP-03 a TFP-09, TFP-12, TFP-13).

# cloudresourcemanager e serviceusage ja estao ativas fora do Terraform e nao
# sao gerenciadas aqui. disable_on_destroy = false esta no modulo apis.
module "apis" {
  source = "../../modules/apis"

  project_id = var.project_id
  services = [
    "compute.googleapis.com",
    "iam.googleapis.com",
    "billingbudgets.googleapis.com",
  ]
}

# depends_on nas APIs: uma API recem-habilitada pode responder 403 por alguns
# segundos (consistencia eventual); o depends_on ordena a criacao, e reexecutar
# o apply resolve o resto.
module "network" {
  source = "../../modules/network"

  region           = var.region
  allowed_ssh_cidr = var.allowed_ssh_cidr

  depends_on = [module.apis]
}

module "identity" {
  source = "../../modules/identity"

  depends_on = [module.apis]
}

module "compute_vm" {
  source = "../../modules/compute_vm"

  zone                  = var.zone
  boot_disk_size_gb     = var.boot_disk_size_gb
  subnetwork            = module.network.subnetwork
  network_tag           = module.network.network_tag
  service_account_email = module.identity.email
  repo_url              = var.repo_url
  repo_ref              = var.repo_ref
  db_name               = var.db_name
  db_user               = var.db_user
  db_password           = var.db_password
  cron_schedule         = var.cron_schedule
  swap_size_mb          = var.swap_size_mb

  depends_on = [module.apis]
}

module "budget" {
  source = "../../modules/budget"

  project_id         = var.project_id
  billing_account_id = var.billing_account_id

  depends_on = [module.apis]
}
