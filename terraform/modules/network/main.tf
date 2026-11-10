locals {
  # Tag de rede da VM: a regra de firewall só vale para instâncias com ela.
  network_tag = "book-monitor"

  # Faixa de origem do Identity-Aware Proxy (IAP) para encaminhamento TCP: todo
  # SSH chega à VM por `gcloud compute ssh --tunnel-through-iap` (AD-007).
  iap_source_range = "35.235.240.0/20"
}

# VPC customizada: sem sub-redes automáticas em todas as regiões.
resource "google_compute_network" "this" {
  name                    = "book-monitor-vpc"
  auto_create_subnetworks = false
}

resource "google_compute_subnetwork" "this" {
  name          = "book-monitor-subnet"
  region        = var.region
  network       = google_compute_network.this.id
  ip_cidr_range = "10.10.0.0/24"
}

# Único acesso de entrada: SSH (tcp:22) a partir da faixa do IAP, só para
# instâncias com a tag book-monitor. Todo o resto de entrada é negado pela
# regra implícita da VPC.
resource "google_compute_firewall" "ssh" {
  name        = "book-monitor-allow-iap-ssh"
  network     = google_compute_network.this.id
  direction   = "INGRESS"
  description = "SSH somente pelo tunel IAP"

  source_ranges = [local.iap_source_range]
  target_tags   = [local.network_tag]

  allow {
    protocol = "tcp"
    ports    = ["22"]
  }
}
