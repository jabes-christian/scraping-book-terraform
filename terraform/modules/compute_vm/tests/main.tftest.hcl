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

# --- Startup script, parte 1 (VM-02): conteúdo de local.startup_script ---

run "startup_script_swap_uses_swap_size_mb" {
  command = plan

  variables {
    swap_size_mb = 2048
  }

  assert {
    condition     = strcontains(local.startup_script, "fallocate -l 2048M \"$SWAP_FILE\"")
    error_message = "O swap deve ser criado com swap_size_mb (fallocate -l 2048M)."
  }
}

run "startup_script_swap_only_when_not_active" {
  command = plan

  assert {
    condition     = strcontains(local.startup_script, "if ! swapon --show=NAME --noheadings | grep -qx \"$SWAP_FILE\"; then")
    error_message = "O swap só pode ser criado se /swapfile não estiver ativo."
  }

  assert {
    condition     = strcontains(local.startup_script, "if ! grep -q '^/swapfile ' /etc/fstab; then")
    error_message = "A linha do fstab só pode ser adicionada se ausente."
  }
}

run "startup_script_swap_and_sysctl_before_docker" {
  command = plan

  assert {
    condition = (
      length(split("swapon \"$SWAP_FILE\"", local.startup_script)[0]) < length(split("sysctl -p", local.startup_script)[0])
      && length(split("sysctl -p", local.startup_script)[0]) < length(split("apt-get install -y docker-ce", local.startup_script)[0])
    )
    error_message = "swap e sysctl devem aparecer antes da instalação do Docker."
  }
}

run "startup_script_has_no_secret_and_no_unrendered_placeholder" {
  command = plan

  assert {
    condition     = !strcontains(local.startup_script, var.db_password)
    error_message = "A senha do banco não pode aparecer no startup script."
  }

  assert {
    condition     = !strcontains(local.startup_script, "$${") && !strcontains(local.startup_script, "%%{")
    error_message = "Não pode sobrar placeholder do Terraform no script renderizado."
  }
}
