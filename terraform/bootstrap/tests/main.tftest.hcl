# Testes do main.tf do bootstrap (TFB-01, TFB-02, TFP-13).
# mock_provider: nenhuma chamada de API e nenhuma credencial necessária.

mock_provider "google" {}

variables {
  project_id = "projeto-teste-123"
}

run "bucket_secure_defaults" {
  command = plan

  assert {
    condition     = google_storage_bucket.tfstate.location == "US-CENTRAL1"
    error_message = "O bucket deve ficar em US-CENTRAL1."
  }

  assert {
    condition     = google_storage_bucket.tfstate.storage_class == "STANDARD"
    error_message = "storage_class deve ser STANDARD."
  }

  assert {
    condition     = google_storage_bucket.tfstate.versioning[0].enabled == true
    error_message = "O versionamento deve estar ligado."
  }

  assert {
    condition     = google_storage_bucket.tfstate.uniform_bucket_level_access == true
    error_message = "uniform_bucket_level_access deve ser true."
  }

  assert {
    condition     = google_storage_bucket.tfstate.public_access_prevention == "enforced"
    error_message = "public_access_prevention deve ser enforced."
  }

  assert {
    condition     = google_storage_bucket.tfstate.force_destroy == false
    error_message = "force_destroy deve ser false por padrão."
  }
}

run "bucket_name_derived_from_project_id" {
  command = plan

  assert {
    condition     = google_storage_bucket.tfstate.name == "projeto-teste-123-tfstate"
    error_message = "O nome do bucket deve ser <project_id>-tfstate."
  }
}

run "bucket_name_override" {
  command = plan

  variables {
    bucket_name = "meu-bucket-tfstate"
  }

  assert {
    condition     = google_storage_bucket.tfstate.name == "meu-bucket-tfstate"
    error_message = "bucket_name informado deve ter precedência sobre o nome derivado."
  }
}

run "force_destroy_follows_variable" {
  command = plan

  variables {
    force_destroy = true
  }

  assert {
    condition     = google_storage_bucket.tfstate.force_destroy == true
    error_message = "force_destroy deve seguir a variável."
  }
}

run "lifecycle_keeps_five_noncurrent_versions" {
  command = plan

  assert {
    condition     = length(google_storage_bucket.tfstate.lifecycle_rule) == 1
    error_message = "Deve haver exatamente uma regra de ciclo de vida."
  }

  assert {
    condition     = one(one(google_storage_bucket.tfstate.lifecycle_rule).action).type == "Delete"
    error_message = "A regra deve apagar objetos."
  }

  assert {
    condition = (
      one(one(google_storage_bucket.tfstate.lifecycle_rule).condition).with_state == "ARCHIVED"
      && one(one(google_storage_bucket.tfstate.lifecycle_rule).condition).num_newer_versions == 5
    )
    error_message = "A regra deve atingir só versões não correntes com 5 ou mais versões mais novas."
  }
}

run "storage_api_is_not_disabled_on_destroy" {
  command = plan

  assert {
    condition     = google_project_service.storage.service == "storage.googleapis.com"
    error_message = "A API habilitada deve ser storage.googleapis.com."
  }

  assert {
    condition     = google_project_service.storage.disable_on_destroy == false
    error_message = "disable_on_destroy deve ser false."
  }
}
