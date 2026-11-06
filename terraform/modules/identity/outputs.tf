output "email" {
  description = "E-mail da service account, para anexar à VM."
  value       = google_service_account.this.email
}
