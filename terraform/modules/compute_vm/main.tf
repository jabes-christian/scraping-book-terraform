locals {
  instance_name = "book-monitor"
}

# Única VM do projeto: e2-micro, disco pd-standard e IP externo efêmero, tudo
# dentro do Free Tier (TFP-07, TFP-08). Sem disco extra, IP estático, snapshot ou NAT.
resource "google_compute_instance" "this" {
  name         = local.instance_name
  machine_type = var.machine_type
  zone         = var.zone
  tags         = [var.network_tag]

  deletion_protection = false

  boot_disk {
    initialize_params {
      image = "debian-cloud/debian-12"
      size  = var.boot_disk_size_gb
      type  = "pd-standard"
    }
  }

  network_interface {
    subnetwork = var.subnetwork

    # Bloco vazio = IP externo efêmero (sem nat_ip e sem google_compute_address).
    access_config {}
  }

  scheduling {
    preemptible         = false
    automatic_restart   = true
    on_host_maintenance = "MIGRATE"
    provisioning_model  = "STANDARD"
  }

  shielded_instance_config {
    enable_secure_boot          = true
    enable_vtpm                 = true
    enable_integrity_monitoring = true
  }

  # A SA não recebe nenhuma role de projeto; o escopo amplo é limitado pelo IAM.
  service_account {
    email  = var.service_account_email
    scopes = ["cloud-platform"]
  }

  metadata = {
    startup-script   = local.startup_script
    book-db-password = var.db_password
  }
}
