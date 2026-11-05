# Service account dedicada da VM. Propositalmente SEM binding de IAM e SEM
# chave: a VM não chama APIs do GCP (logs ficam em arquivo) e a SA padrão do
# Compute, que tem o papel Editor, não é usada (TFP-06).
resource "google_service_account" "this" {
  account_id   = var.account_id
  display_name = "Book Price Monitor VM"
  description  = "Identidade da VM do robô. Sem roles de projeto e sem chave."
}
