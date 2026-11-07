# Testes do módulo compute_vm (TFP-07, TFP-10, TFP-12).
# mock_provider: nenhuma chamada de API e nenhuma credencial necessária.

mock_provider "google" {}

variables {
  subnetwork            = "projects/p/regions/us-central1/subnetworks/s"
  network_tag           = "book-monitor"
  service_account_email = "vm@p.iam.gserviceaccount.com"
  repo_url              = "https://github.com/example/repo.git"
  db_password           = "Senha-De-Teste_1234"
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

run "db_password_with_forbidden_character_fails" {
  command = plan

  variables {
    db_password = "Senha$De-Teste_1234"
  }

  expect_failures = [var.db_password]
}

run "db_password_too_short_fails" {
  command = plan

  variables {
    db_password = "Curta-123"
  }

  expect_failures = [var.db_password]
}

run "db_password_valid_is_accepted" {
  command = plan

  variables {
    db_password = "abcDEF0123456789_.-"
  }

  assert {
    condition     = length(var.db_password) >= 16
    error_message = "Uma senha de 19 caracteres com [A-Za-z0-9_.-] deve ser aceita."
  }
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

# --- Startup script, parte 2 (VM-01, VM-05, VM-09, VM-10) ---

run "startup_script_clones_and_updates_with_repo_url_and_ref" {
  command = plan

  variables {
    repo_url = "https://github.com/example/book-price-monitor.git"
    repo_ref = "v1.2.3"
  }

  assert {
    condition     = strcontains(local.startup_script, "git clone --depth 1 --branch \"v1.2.3\" \"https://github.com/example/book-price-monitor.git\" \"$APP_DIR\"")
    error_message = "O clone deve usar repo_ref e repo_url."
  }

  assert {
    condition     = strcontains(local.startup_script, "git -C \"$APP_DIR\" fetch --depth 1 origin \"v1.2.3\"")
    error_message = "A atualização deve buscar repo_ref."
  }
}

run "startup_script_env_only_if_absent_with_metadata_password" {
  command = plan

  variables {
    db_name = "booksdb"
    db_user = "booksuser"
  }

  assert {
    condition     = strcontains(local.startup_script, "if [ ! -f \"$ENV_FILE\" ]; then")
    error_message = "O .env só pode ser criado se ausente."
  }

  assert {
    condition     = strcontains(local.startup_script, "-H \"Metadata-Flavor: Google\" \"$METADATA_URL\"")
    error_message = "A senha deve ser lida da metadata com o cabeçalho Metadata-Flavor: Google."
  }

  assert {
    condition     = strcontains(local.startup_script, "echo \"DB_NAME=booksdb\"") && strcontains(local.startup_script, "echo \"DB_USER=booksuser\"")
    error_message = "DB_NAME e DB_USER devem vir das variáveis do módulo."
  }

  assert {
    condition     = strcontains(local.startup_script, "chmod 600 \"$ENV_FILE\"")
    error_message = "O .env deve ter permissão 600."
  }
}

run "startup_script_build_before_postgres_up" {
  command = plan

  assert {
    condition = (
      length(split("docker compose build", local.startup_script)[0]) < length(split("docker image prune -f", local.startup_script)[0])
      && length(split("docker image prune -f", local.startup_script)[0]) < length(split("docker compose up -d --wait", local.startup_script)[0])
    )
    error_message = "A ordem deve ser build, prune, up -d --wait postgres."
  }
}

# --- Startup script, parte 3 (VM-03, VM-04, VM-05, VM-07) ---

run "startup_script_cron_line_uses_default_schedule_and_flock" {
  command = plan

  assert {
    condition     = var.cron_schedule == "0 6 * * *"
    error_message = "O padrão de cron_schedule deve ser 0 6 * * *."
  }

  assert {
    condition     = strcontains(local.startup_script, "\n0 6 * * * root flock -n /var/lock/book-monitor.lock docker compose -f /opt/book-monitor/docker-compose.yml run --rm -T robo >> /var/log/book-monitor/run.log 2>&1\n")
    error_message = "A linha de cron deve usar o agendamento padrão, flock -n e redirecionar para run.log."
  }
}

run "startup_script_cron_file_is_overwritten_not_appended" {
  command = plan

  variables {
    cron_schedule = "15 4 * * *"
  }

  assert {
    condition     = strcontains(local.startup_script, "cat > /etc/cron.d/book-monitor <<'CRON'\n15 4 * * * root flock -n")
    error_message = "O arquivo de cron deve ser sobrescrito (>) com a linha de cron_schedule logo no início."
  }

  assert {
    condition     = !strcontains(local.startup_script, ">> /etc/cron.d/")
    error_message = "Nada pode acrescentar (>>) ao /etc/cron.d."
  }
}

run "startup_script_logrotate_policy" {
  command = plan

  assert {
    condition     = strcontains(local.startup_script, "/var/log/book-monitor/*.log {\n    daily\n    rotate 7\n    compress\n    copytruncate\n    missingok\n}")
    error_message = "O logrotate deve ter daily, rotate 7, compress, copytruncate e missingok."
  }
}

# --- Recurso da VM (TFP-07, TFP-08, TFP-12) ---

run "instance_is_e2_micro_non_preemptible_with_shielded_vm" {
  command = plan

  assert {
    condition     = google_compute_instance.this.machine_type == "e2-micro"
    error_message = "A VM deve ser e2-micro."
  }

  assert {
    condition     = one(google_compute_instance.this.scheduling).preemptible == false
    error_message = "A VM não pode ser preemptível."
  }

  assert {
    condition     = one(google_compute_instance.this.scheduling).provisioning_model == "STANDARD"
    error_message = "A VM deve usar o modelo de provisionamento STANDARD (não Spot)."
  }

  assert {
    condition = (
      one(google_compute_instance.this.shielded_instance_config).enable_secure_boot == true
      && one(google_compute_instance.this.shielded_instance_config).enable_vtpm == true
      && one(google_compute_instance.this.shielded_instance_config).enable_integrity_monitoring == true
    )
    error_message = "A VM deve habilitar secure boot, vTPM e monitoramento de integridade."
  }

  assert {
    condition     = google_compute_instance.this.deletion_protection == false
    error_message = "deletion_protection deve ser false (o destroy da T56 precisa funcionar)."
  }
}

run "boot_disk_is_pd_standard_debian_12_within_free_tier" {
  command = plan

  assert {
    condition     = one(one(google_compute_instance.this.boot_disk).initialize_params).type == "pd-standard"
    error_message = "O disco de boot deve ser pd-standard."
  }

  assert {
    condition     = one(one(google_compute_instance.this.boot_disk).initialize_params).image == "debian-cloud/debian-12"
    error_message = "A imagem deve ser debian-cloud/debian-12."
  }

  assert {
    condition     = one(one(google_compute_instance.this.boot_disk).initialize_params).size == 30
    error_message = "O disco de boot padrão deve ter 30 GB (limite do Free Tier)."
  }

  assert {
    condition     = length(google_compute_instance.this.scratch_disk) == 0 && length(google_compute_instance.this.attached_disk) == 0
    error_message = "A VM não pode ter disco extra (scratch ou anexado)."
  }
}

run "boot_disk_size_follows_variable" {
  command = plan

  variables {
    boot_disk_size_gb = 20
  }

  assert {
    condition     = one(one(google_compute_instance.this.boot_disk).initialize_params).size == 20
    error_message = "O tamanho do disco deve seguir boot_disk_size_gb."
  }
}

run "network_has_only_an_ephemeral_external_ip_and_the_firewall_tag" {
  command = plan

  assert {
    condition     = length(one(google_compute_instance.this.network_interface).access_config) == 1
    error_message = "Deve haver exatamente um access_config (IP externo efêmero)."
  }

  assert {
    condition     = one(google_compute_instance.this.network_interface).subnetwork == var.subnetwork
    error_message = "A VM deve usar a sub-rede informada."
  }

  assert {
    condition     = contains(google_compute_instance.this.tags, "book-monitor")
    error_message = "A VM deve ter a tag de rede da regra de firewall SSH."
  }
}

run "instance_identity_zone_and_service_account" {
  command = plan

  assert {
    condition     = google_compute_instance.this.name == "book-monitor" && google_compute_instance.this.zone == "us-central1-a"
    error_message = "A VM deve se chamar book-monitor e ficar em us-central1-a por padrão."
  }

  assert {
    condition     = one(google_compute_instance.this.service_account).email == var.service_account_email
    error_message = "A VM deve usar a service account informada."
  }
}

run "metadata_carries_startup_script_and_password" {
  command = plan

  assert {
    condition     = google_compute_instance.this.metadata["startup-script"] == local.startup_script
    error_message = "A metadata startup-script deve ser o script renderizado."
  }

  assert {
    condition     = google_compute_instance.this.metadata["book-db-password"] == var.db_password
    error_message = "A metadata book-db-password deve ser a senha informada."
  }

  assert {
    condition     = length(google_compute_instance.this.metadata) == 2
    error_message = "A metadata deve ter somente startup-script e book-db-password."
  }
}
