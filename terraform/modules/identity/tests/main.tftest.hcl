# Testes do módulo identity (TFP-06, TFP-12).
# mock_provider: nenhuma chamada de API e nenhuma credencial necessária.
# A ausência de recursos IAM e de chave é verificada estaticamente por
# tests/infra/test_identity_resources.py (terraform test não enumera recursos).

mock_provider "google" {}

run "default_service_account" {
  command = plan

  assert {
    condition     = google_service_account.this.account_id == "book-monitor-vm"
    error_message = "account_id padrão deve ser book-monitor-vm."
  }

  assert {
    condition     = google_service_account.this.display_name == "Book Price Monitor VM"
    error_message = "A service account deve ter display_name descritivo."
  }
}

run "custom_account_id" {
  command = plan

  variables {
    account_id = "outro-robo-vm"
  }

  assert {
    condition     = google_service_account.this.account_id == "outro-robo-vm"
    error_message = "account_id deve acompanhar a variável."
  }
}

run "email_output" {
  command = plan

  # O e-mail é calculado pela API; o override simula o valor real.
  # override_during = plan: por padrão o override só vale no apply, e este
  # run usa command = plan.
  override_resource {
    target          = google_service_account.this
    override_during = plan
    values = {
      email = "book-monitor-vm@projeto-teste-123.iam.gserviceaccount.com"
    }
  }

  assert {
    condition     = output.email == "book-monitor-vm@projeto-teste-123.iam.gserviceaccount.com"
    error_message = "O output email deve expor o e-mail da service account."
  }
}
