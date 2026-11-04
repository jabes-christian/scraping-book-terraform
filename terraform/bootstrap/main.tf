locals {
  # Nome do bucket: o informado em bucket_name ou "<project_id>-tfstate".
  bucket_name = coalesce(var.bucket_name, "${var.project_id}-tfstate")
}

# Habilita a API do Cloud Storage. disable_on_destroy = false evita que o
# destroy desligue a API para o projeto inteiro (AD-003 / TFP-13).
resource "google_project_service" "storage" {
  service            = "storage.googleapis.com"
  disable_on_destroy = false
}

# Bucket do remote state do envs/prod.
resource "google_storage_bucket" "tfstate" {
  name          = local.bucket_name
  location      = upper(var.region)
  storage_class = "STANDARD"
  force_destroy = var.force_destroy

  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"

  versioning {
    enabled = true
  }

  # Mantém o bucket pequeno (Free Tier: 5 GB): apaga versões não correntes
  # que já têm 5 versões mais novas.
  lifecycle_rule {
    action {
      type = "Delete"
    }
    condition {
      with_state         = "ARCHIVED"
      num_newer_versions = 5
    }
  }

  # A API precisa estar habilitada antes de criar o bucket.
  depends_on = [google_project_service.storage]
}
