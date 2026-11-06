variable "project_id" {
  description = "ID do projeto GCP onde as APIs serão habilitadas."
  type        = string
}

variable "services" {
  description = "APIs a habilitar (ex.: compute.googleapis.com). Uma instância de google_project_service por item."
  type        = list(string)
}
