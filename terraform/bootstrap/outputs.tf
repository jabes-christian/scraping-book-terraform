output "bucket_name" {
  description = "Nome do bucket do remote state, para o backend GCS de envs/prod."
  value       = google_storage_bucket.tfstate.name
}

output "backend_hcl_snippet" {
  description = "Conteúdo pronto para salvar como terraform/envs/prod/backend.hcl (gitignored)."
  value       = <<-EOT
    bucket = "${google_storage_bucket.tfstate.name}"
    prefix = "envs/prod"
  EOT
}
