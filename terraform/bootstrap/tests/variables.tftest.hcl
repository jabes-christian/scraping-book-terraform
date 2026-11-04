# Testes das variáveis do bootstrap (TFB-03, TFB-05).
# mock_provider evita qualquer chamada de API/ADC; command = plan basta, pois
# a validação de variáveis roda antes de qualquer recurso.

mock_provider "google" {}

variables {
  project_id = "projeto-teste-123"
}

run "valid_inputs_and_defaults" {
  command = plan

  assert {
    condition     = var.region == "us-central1"
    error_message = "region deve ser us-central1 por padrão."
  }

  assert {
    condition     = var.bucket_name == null
    error_message = "bucket_name deve ser opcional (null por padrão)."
  }

  assert {
    condition     = var.force_destroy == false
    error_message = "force_destroy deve ser false por padrão."
  }
}

run "valid_custom_bucket_name" {
  command = plan

  variables {
    bucket_name = "meu-bucket-tfstate"
  }
}

run "empty_project_id_fails" {
  command = plan

  variables {
    project_id = ""
  }

  expect_failures = [var.project_id]
}

run "uppercase_project_id_fails" {
  command = plan

  variables {
    project_id = "Projeto-Teste-123"
  }

  expect_failures = [var.project_id]
}

run "short_project_id_fails" {
  command = plan

  variables {
    project_id = "abc"
  }

  expect_failures = [var.project_id]
}

run "trailing_hyphen_project_id_fails" {
  command = plan

  variables {
    project_id = "projeto-teste-"
  }

  expect_failures = [var.project_id]
}

run "region_outside_free_tier_fails" {
  command = plan

  variables {
    region = "europe-west1"
  }

  expect_failures = [var.region]
}

run "invalid_bucket_name_fails" {
  command = plan

  variables {
    bucket_name = "Bucket_Maiusculo"
  }

  expect_failures = [var.bucket_name]
}
