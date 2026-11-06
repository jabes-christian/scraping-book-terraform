output "services" {
  description = "APIs habilitadas pelo módulo. Dependa deste output (ou do módulo) para ordenar recursos que exigem as APIs."
  value       = [for s in google_project_service.this : s.service]
}
