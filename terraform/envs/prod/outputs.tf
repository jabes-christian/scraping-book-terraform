output "instance_name" {
  description = "Nome da instância criada."
  value       = module.compute_vm.instance_name
}

output "zone" {
  description = "Zona da instância."
  value       = module.compute_vm.zone
}

output "ssh_command" {
  description = "Comando para abrir uma sessão SSH na VM pelo túnel IAP (único caminho liberado no firewall, AD-007)."
  value       = module.compute_vm.ssh_command
}
