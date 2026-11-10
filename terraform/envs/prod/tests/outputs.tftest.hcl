# Testes dos outputs de envs/prod (TFP-11).
# mock_provider: nenhuma chamada de API e nenhuma credencial necessaria.

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

# O project da instancia e herdado do provider (atributo computado); o override
# simula o valor real. override_during = plan: por padrao o override so vale no apply.
override_resource {
  target          = module.compute_vm.google_compute_instance.this
  override_during = plan
  values = {
    project = "projeto-teste-123"
  }
}

run "outputs_expose_name_zone_and_ssh_command" {
  command = plan

  assert {
    condition     = output.instance_name == "book-monitor"
    error_message = "instance_name deve expor o nome da VM."
  }

  assert {
    condition     = output.zone == "us-central1-a"
    error_message = "zone deve expor a zona da VM."
  }

  assert {
    condition     = output.ssh_command == "gcloud compute ssh book-monitor --zone us-central1-a --project projeto-teste-123 --tunnel-through-iap"
    error_message = "ssh_command deve ser exatamente: gcloud compute ssh <vm> --zone <zone> --project <id> --tunnel-through-iap."
  }
}

run "ssh_command_follows_the_zone_variable" {
  command = plan

  variables {
    region = "us-east1"
    zone   = "us-east1-b"
  }

  assert {
    condition     = output.ssh_command == "gcloud compute ssh book-monitor --zone us-east1-b --project projeto-teste-123 --tunnel-through-iap"
    error_message = "ssh_command deve usar a zona informada."
  }
}
