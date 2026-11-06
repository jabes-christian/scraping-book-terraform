output "budget_name" {
  description = "Nome completo do orçamento (billingAccounts/<conta>/budgets/<id>)."
  value       = google_billing_budget.this.name
}
