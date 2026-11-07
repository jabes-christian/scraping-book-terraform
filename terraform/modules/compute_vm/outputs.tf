output "instance_name" {
  description = "Nome da instância criada."
  value       = google_compute_instance.this.name
}

output "zone" {
  description = "Zona da instância."
  value       = google_compute_instance.this.zone
}

output "ssh_command" {
  description = "Comando para abrir uma sessão SSH na VM (túnel IAP ou IP externo, conforme o gcloud)."
  value       = "gcloud compute ssh ${google_compute_instance.this.name} --zone ${google_compute_instance.this.zone} --project ${google_compute_instance.this.project}"
}
