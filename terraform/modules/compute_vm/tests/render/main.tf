# Configuração de renderização do startup script (T32-T34).
# Sem provider e sem recursos: só calcula um output local a partir do template.
# O autor roda init + apply -auto-approve aqui (e só aqui) e grava o output em
# .rendered-startup.json (terraform output -json, todos os outputs), que o pytest
# (tests/infra/test_startup_script.py) verifica. O output template_sha256 e o
# SHA-256 do template usado na renderizacao: o pytest o compara com o hash do
# startup.sh.tftpl atual e reprova o JSON se o conteudo do template mudou.
# As chaves passadas ao templatefile devem ser iguais às de ../../locals.tf.

terraform {
  required_version = ">= 1.9"
}

output "script" {
  value = templatefile("${path.module}/../../startup.sh.tftpl", {
    swap_size_mb  = 2048
    repo_url      = "https://github.com/example/book-price-monitor.git"
    repo_ref      = "v1.2.3"
    db_name       = "booksdb"
    db_user       = "booksuser"
    cron_schedule = "15 4 * * *"
  })
}

output "template_sha256" {
  value = filesha256("${path.module}/../../startup.sh.tftpl")
}
