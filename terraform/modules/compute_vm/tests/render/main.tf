# Configuração de renderização do startup script (T32-T34).
# Sem provider e sem recursos: só calcula um output local a partir do template.
# O autor roda init + apply -auto-approve aqui (e só aqui) e grava o output em
# .rendered-startup.json, que o pytest (tests/infra/test_startup_script.py) verifica.
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
