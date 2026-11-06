# Testes do módulo compute_vm (TFP-07, TFP-10, TFP-12).
# mock_provider: nenhuma chamada de API e nenhuma credencial necessária.

mock_provider "google" {}

variables {
  subnetwork            = "projects/p/regions/us-central1/subnetworks/s"
  network_tag           = "book-monitor"
  service_account_email = "vm@p.iam.gserviceaccount.com"
  repo_url              = "https://github.com/example/repo.git"
  db_password           = "senha-de-teste"
}

run "defaults_are_valid_and_inside_free_tier" {
  command = plan

  assert {
    condition     = var.machine_type == "e2-micro"
    error_message = "O padrão de machine_type deve ser e2-micro."
  }

  assert {
    condition     = var.boot_disk_size_gb == 30
    error_message = "O padrão de boot_disk_size_gb deve ser 30."
  }

  assert {
    condition     = var.zone == "us-central1-a"
    error_message = "O padrão de zone deve ser us-central1-a."
  }

  assert {
    condition     = var.repo_ref == "main" && var.cron_schedule == "0 6 * * *" && var.swap_size_mb == 1024
    error_message = "Padrões esperados: repo_ref main, cron_schedule 0 6 * * *, swap_size_mb 1024."
  }
}

run "machine_type_other_than_e2_micro_fails" {
  command = plan

  variables {
    machine_type = "e2-small"
  }

  expect_failures = [var.machine_type]
}

run "boot_disk_above_30_gb_fails" {
  command = plan

  variables {
    boot_disk_size_gb = 31
  }

  expect_failures = [var.boot_disk_size_gb]
}

run "zone_outside_free_tier_regions_fails" {
  command = plan

  variables {
    zone = "europe-west1-b"
  }

  expect_failures = [var.zone]
}

run "boundary_values_are_accepted" {
  command = plan

  variables {
    machine_type      = "e2-micro"
    boot_disk_size_gb = 30
    zone              = "us-west1-b"
  }

  assert {
    condition     = var.zone == "us-west1-b" && var.boot_disk_size_gb == 30
    error_message = "30 GB e uma zona de us-west1 devem ser aceitos."
  }
}

run "other_free_tier_regions_are_accepted" {
  command = plan

  variables {
    zone = "us-east1-b"
  }

  assert {
    condition     = var.zone == "us-east1-b"
    error_message = "Zonas de us-east1 devem ser aceitas."
  }
}
