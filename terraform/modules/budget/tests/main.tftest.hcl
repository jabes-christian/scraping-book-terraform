# Testes do módulo budget (TFP-09, TFP-12).
# mock_provider: nenhuma chamada de API e nenhuma credencial necessária.
# A ausência de recursos Pub/Sub/Monitoring e de all_updates_rule também é
# verificada estaticamente por tests/infra/test_budget_resources.py.

mock_provider "google" {}

variables {
  billing_account_id = "AAAAAA-BBBBBB-CCCCCC"
  project_id         = "projeto-teste-123"
}

# O número do projeto vem da API; o override o fixa já no plano.
override_data {
  target          = data.google_project.this
  override_during = plan
  values = {
    number = "123456789"
  }
}

run "amount_and_currency" {
  command = plan

  assert {
    condition     = one(one(google_billing_budget.this.amount).specified_amount).currency_code == "BRL"
    error_message = "A moeda do orçamento deve ser BRL."
  }

  assert {
    condition     = one(one(google_billing_budget.this.amount).specified_amount).units == "5"
    error_message = "O valor do orçamento deve ser 5 unidades."
  }
}

run "three_thresholds" {
  command = plan

  assert {
    condition     = length(google_billing_budget.this.threshold_rules) == 3
    error_message = "Devem existir exatamente 3 threshold_rules."
  }

  assert {
    condition     = toset([for r in google_billing_budget.this.threshold_rules : r.threshold_percent]) == toset([0.5, 0.9, 1.0])
    error_message = "Os limites devem ser 0.5, 0.9 e 1.0."
  }
}

run "filtered_by_project_number" {
  command = plan

  assert {
    condition     = one(google_billing_budget.this.budget_filter).projects == toset(["projects/123456789"])
    error_message = "O filtro deve ser exatamente projects/<número do projeto>."
  }

  assert {
    condition     = google_billing_budget.this.billing_account == "AAAAAA-BBBBBB-CCCCCC"
    error_message = "O orçamento deve usar a conta de faturamento informada."
  }
}

run "no_all_updates_rule" {
  command = plan

  assert {
    condition     = length(google_billing_budget.this.all_updates_rule) == 0
    error_message = "all_updates_rule deve ficar omitido (alerta por e-mail padrão)."
  }
}

run "budget_name_output" {
  command = plan

  # O nome é gerado pela API; o override simula o valor real.
  override_resource {
    target          = google_billing_budget.this
    override_during = plan
    values = {
      name = "billingAccounts/AAAAAA-BBBBBB-CCCCCC/budgets/abc123"
    }
  }

  assert {
    condition     = output.budget_name == "billingAccounts/AAAAAA-BBBBBB-CCCCCC/budgets/abc123"
    error_message = "O output budget_name deve expor o nome do orçamento."
  }
}

run "custom_amount_and_thresholds" {
  command = plan

  variables {
    amount_units = 10
    thresholds   = [0.8]
  }

  assert {
    condition     = one(one(google_billing_budget.this.amount).specified_amount).units == "10"
    error_message = "amount_units deve ser repassado como string em units."
  }

  assert {
    condition     = length(google_billing_budget.this.threshold_rules) == 1
    error_message = "thresholds deve controlar a quantidade de threshold_rules."
  }
}
