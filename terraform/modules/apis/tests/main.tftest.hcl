# Testes do módulo apis (TFP-01, TFP-12, TFP-13).
# mock_provider: nenhuma chamada de API e nenhuma credencial necessária.

mock_provider "google" {}

variables {
  project_id = "projeto-teste-123"
  services = [
    "compute.googleapis.com",
    "iam.googleapis.com",
    "billingbudgets.googleapis.com",
  ]
}

run "one_instance_per_service" {
  command = plan

  assert {
    condition     = length(google_project_service.this) == 3
    error_message = "Deve haver uma instância de google_project_service por serviço informado."
  }

  assert {
    condition     = toset(keys(google_project_service.this)) == toset(var.services)
    error_message = "As instâncias devem ser indexadas pelo nome do serviço."
  }

  assert {
    condition     = alltrue([for s in google_project_service.this : s.project == "projeto-teste-123"])
    error_message = "Todas as instâncias devem usar o project_id informado."
  }
}

run "never_disables_on_destroy" {
  command = plan

  assert {
    condition     = alltrue([for s in google_project_service.this : s.disable_on_destroy == false])
    error_message = "disable_on_destroy deve ser false em todas as APIs (TFP-13)."
  }

  assert {
    condition     = alltrue([for s in google_project_service.this : s.disable_dependent_services == false])
    error_message = "disable_dependent_services deve ser false em todas as APIs."
  }
}

run "output_lists_services" {
  command = plan

  assert {
    condition     = toset(output.services) == toset(var.services)
    error_message = "O output services deve listar exatamente as APIs informadas."
  }
}

run "single_service_single_instance" {
  command = plan

  variables {
    services = ["compute.googleapis.com"]
  }

  assert {
    condition     = length(google_project_service.this) == 1
    error_message = "Um serviço informado deve gerar uma única instância."
  }
}
