locals {
  # Nenhum segredo entra no template: a senha trafega pela metadata (AD-002).
  startup_script = templatefile("${path.module}/startup.sh.tftpl", {
    swap_size_mb  = var.swap_size_mb
    repo_url      = var.repo_url
    repo_ref      = var.repo_ref
    db_name       = var.db_name
    db_user       = var.db_user
    cron_schedule = var.cron_schedule
  })
}
