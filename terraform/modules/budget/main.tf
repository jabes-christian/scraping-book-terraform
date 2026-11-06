# O orçamento filtra por número do projeto ("projects/<número>"), não pelo ID.
data "google_project" "this" {
  project_id = var.project_id
}

# Alerta de gasto da conta de faturamento, restrito a este projeto.
# Sem all_updates_rule: vale o padrão do GCP, que avisa por e-mail quem tem os
# papéis Billing Account Administrator/User. Nada de Pub/Sub nem Monitoring.
resource "google_billing_budget" "this" {
  billing_account = var.billing_account_id
  display_name    = "book-price-monitor-${var.project_id}"

  budget_filter {
    projects = ["projects/${data.google_project.this.number}"]
  }

  amount {
    specified_amount {
      currency_code = var.currency_code
      units         = tostring(var.amount_units)
    }
  }

  dynamic "threshold_rules" {
    for_each = var.thresholds

    content {
      threshold_percent = threshold_rules.value
    }
  }
}
