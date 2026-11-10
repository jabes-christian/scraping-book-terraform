# Testes da composicao de envs/prod (TFP-01, TFP-03, TFP-07, TFP-08, TFP-09, TFP-12).
# mock_provider: nenhuma chamada de API e nenhuma credencial necessaria.
# O terraform test nao enumera os recursos do plano: a lista fechada de tipos de
# recurso e o disable_on_destroy sao verificados por tests/infra/test_prod_composition.py.

mock_provider "google" {}

variables {
  project_id         = "projeto-teste-123"
  billing_account_id = "012345-6789AB-CDEF01"
  repo_url           = "https://github.com/exemplo/repositorio.git"
  db_password        = "senha-de-teste-1234"
}

# O numero do projeto vem da API; o override o fixa ja no plano.
override_data {
  target          = module.budget.data.google_project.this
  override_during = plan
  values = {
    number = "123456789"
  }
}

run "enables_exactly_the_four_apis" {
  command = plan

  assert {
    condition     = toset(module.apis.services) == toset(["compute.googleapis.com", "iam.googleapis.com", "billingbudgets.googleapis.com", "iap.googleapis.com"])
    error_message = "As APIs habilitadas devem ser exatamente compute, iam, billingbudgets e iap."
  }

  assert {
    condition     = length(module.apis.services) == 4
    error_message = "Devem existir exatamente 4 APIs."
  }
}

run "vm_is_named_and_placed_by_the_inputs" {
  command = plan

  assert {
    condition     = module.compute_vm.instance_name == "book-monitor"
    error_message = "A instância deve se chamar book-monitor."
  }

  assert {
    condition     = module.compute_vm.zone == "us-central1-a"
    error_message = "A zona padrão da VM deve ser us-central1-a."
  }
}

run "network_tag_links_firewall_and_vm" {
  command = plan

  assert {
    condition     = module.network.network_tag == "book-monitor"
    error_message = "A tag de rede deve ser book-monitor."
  }
}

run "custom_zone_reaches_the_vm" {
  command = plan

  variables {
    region = "us-east1"
    zone   = "us-east1-b"
  }

  assert {
    condition     = module.compute_vm.zone == "us-east1-b"
    error_message = "A zona informada em zone deve chegar à VM."
  }
}
