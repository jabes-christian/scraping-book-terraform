output "network" {
  description = "Self link da VPC."
  value       = google_compute_network.this.self_link
}

output "subnetwork" {
  description = "Self link da sub-rede onde a VM será criada."
  value       = google_compute_subnetwork.this.self_link
}

output "network_tag" {
  description = "Tag de rede que a VM deve ter para receber a regra de SSH."
  value       = local.network_tag
}
