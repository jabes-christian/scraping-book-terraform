# Configuracao PARCIAL do backend: o nome do bucket (um valor do ambiente do
# autor) nao fica no codigo versionado. Ele vem do backend.hcl local (gitignored):
#   terraform init "-backend-config=backend.hcl"
# Variaveis nao sao permitidas em blocos backend, por isso o bucket e passado so no init.
terraform {
  backend "gcs" {
    prefix = "envs/prod"
  }
}
