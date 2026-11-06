# Testes do módulo network (TFP-03, TFP-04, TFP-05, TFP-12).
# mock_provider: nenhuma chamada de API e nenhuma credencial necessária.

mock_provider "google" {}

variables {
  allowed_ssh_cidr = "203.0.113.10/32"
}

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

run "ssh_firewall_only_tcp_22_from_allowed_cidr" {
  command = plan

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
    condition     = google_compute_firewall.ssh.source_ranges == toset(["203.0.113.10/32"])
    error_message = "source_ranges deve ser exatamente [allowed_ssh_cidr]."
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

run "source_range_follows_input" {
  command = plan

  variables {
    allowed_ssh_cidr = "198.51.100.0/24"
  }

  assert {
    condition     = google_compute_firewall.ssh.source_ranges == toset(["198.51.100.0/24"])
    error_message = "source_ranges deve acompanhar allowed_ssh_cidr."
  }
}

run "accepts_single_host_slash_32" {
  command = plan

  variables {
    allowed_ssh_cidr = "203.0.113.10/32"
  }

  assert {
    condition     = google_compute_firewall.ssh.source_ranges == toset(["203.0.113.10/32"])
    error_message = "Um CIDR /32 deve ser aceito e usado em source_ranges."
  }
}

run "rejects_prefix_wider_than_slash_24" {
  command = plan

  variables {
    allowed_ssh_cidr = "10.0.0.0/8"
  }

  expect_failures = [var.allowed_ssh_cidr]
}

run "rejects_open_to_the_world" {
  command = plan

  variables {
    allowed_ssh_cidr = "0.0.0.0/0"
  }

  expect_failures = [var.allowed_ssh_cidr]
}

run "rejects_malformed_cidr" {
  command = plan

  variables {
    allowed_ssh_cidr = "abc"
  }

  expect_failures = [var.allowed_ssh_cidr]
}

run "rejects_out_of_range_prefix" {
  command = plan

  variables {
    allowed_ssh_cidr = "10.0.0.0/33"
  }

  expect_failures = [var.allowed_ssh_cidr]
}
