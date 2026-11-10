# Testes do módulo network (TFP-03, TFP-04, TFP-05, TFP-12).
# mock_provider: nenhuma chamada de API e nenhuma credencial necessária.

mock_provider "google" {}

run "vpc_and_subnet" {
  command = plan

  assert {
    condition     = google_compute_network.this.auto_create_subnetworks == false
    error_message = "A VPC deve ser customizada (auto_create_subnetworks = false)."
  }

  assert {
    condition     = google_compute_subnetwork.this.region == "us-central1"
    error_message = "A sub-rede deve ficar em us-central1 por padrão."
  }

  assert {
    condition     = google_compute_subnetwork.this.ip_cidr_range == "10.10.0.0/24"
    error_message = "A sub-rede deve usar 10.10.0.0/24."
  }
}

run "ssh_firewall_only_tcp_22_from_iap_range" {
  command = plan

  assert {
    condition     = google_compute_firewall.ssh.name == "book-monitor-allow-iap-ssh"
    error_message = "A regra deve se chamar book-monitor-allow-iap-ssh."
  }

  assert {
    condition     = google_compute_firewall.ssh.direction == "INGRESS"
    error_message = "A regra deve ser de entrada (INGRESS)."
  }

  assert {
    condition     = one(google_compute_firewall.ssh.allow).protocol == "tcp"
    error_message = "A regra deve permitir apenas o protocolo tcp."
  }

  assert {
    condition     = one(google_compute_firewall.ssh.allow).ports == tolist(["22"])
    error_message = "A regra deve permitir apenas a porta 22."
  }

  assert {
    condition     = google_compute_firewall.ssh.source_ranges == toset(["35.235.240.0/20"])
    error_message = "source_ranges deve ser exatamente a faixa do IAP [35.235.240.0/20]."
  }

  assert {
    condition     = google_compute_firewall.ssh.target_tags == toset(["book-monitor"])
    error_message = "target_tags deve ser exatamente [book-monitor]."
  }
}

run "output_network_tag" {
  command = plan

  assert {
    condition     = output.network_tag == "book-monitor"
    error_message = "O output network_tag deve ser book-monitor."
  }
}
