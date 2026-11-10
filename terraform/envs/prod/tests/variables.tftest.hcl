# Testes das variaveis de envs/prod (TFP-10).
# mock_provider evita qualquer chamada de API/ADC; command = plan basta, pois
# a validacao de variaveis roda antes de qualquer recurso.

mock_provider "google" {}

variables {
  project_id         = "projeto-teste-123"
  billing_account_id = "012345-6789AB-CDEF01"
  repo_url           = "https://github.com/exemplo/repositorio.git"
  db_password        = "senha-de-teste-1234"
}

run "valid_inputs_and_defaults" {
  command = plan

  assert {
    condition     = var.repo_ref == "main"
    error_message = "repo_ref deve ser main por padrão."
  }

  assert {
    condition     = var.region == "us-central1" && var.zone == "us-central1-a"
    error_message = "region e zone devem ser us-central1 e us-central1-a por padrão."
  }

  assert {
    condition     = var.boot_disk_size_gb == 30
    error_message = "boot_disk_size_gb deve ser 30 por padrão."
  }
}

run "db_password_is_sensitive" {
  command = plan

  assert {
    condition     = issensitive(var.db_password)
    error_message = "db_password deve ser sensitive."
  }
}

run "invalid_billing_account_id_fails" {
  command = plan

  variables {
    billing_account_id = "billingAccounts/012345-6789AB-CDEF01"
  }

  expect_failures = [var.billing_account_id]
}

run "db_password_with_special_char_fails" {
  command = plan

  variables {
    db_password = "senha-com-cifrao-$1234"
  }

  expect_failures = [var.db_password]
}

run "short_db_password_fails" {
  command = plan

  variables {
    db_password = "curta-123"
  }

  expect_failures = [var.db_password]
}

run "region_outside_free_tier_fails" {
  command = plan

  variables {
    region = "europe-west1"
    zone   = "europe-west1-b"
  }

  expect_failures = [var.region]
}

run "zone_outside_region_fails" {
  command = plan

  variables {
    zone = "us-east1-b"
  }

  expect_failures = [var.zone]
}

run "http_repo_url_fails" {
  command = plan

  variables {
    repo_url = "http://github.com/exemplo/repositorio.git"
  }

  expect_failures = [var.repo_url]
}

run "boot_disk_above_free_tier_fails" {
  command = plan

  variables {
    boot_disk_size_gb = 31
  }

  expect_failures = [var.boot_disk_size_gb]
}
