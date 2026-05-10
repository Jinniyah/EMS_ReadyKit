// data outputs.tf

output "pg_server_id" {
  description = "Resource ID of the PostgreSQL Flexible Server"
  value       = azurerm_postgresql_flexible_server.ems_pg.id
}

output "pg_server_fqdn" {
  description = "Fully qualified domain name of the PostgreSQL Flexible Server"
  value       = azurerm_postgresql_flexible_server.ems_pg.fqdn
}

output "pg_database_name" {
  description = "Name of the PostgreSQL database"
  value       = azurerm_postgresql_flexible_server_database.ems_db.name
}

output "sql_connection_string" {
  description = "SQLAlchemy connection string for the EMS database (sensitive)"
  value       = "postgresql+psycopg2://${var.pg_admin_login}:${var.pg_admin_password}@${azurerm_postgresql_flexible_server.ems_pg.fqdn}:5432/${azurerm_postgresql_flexible_server_database.ems_db.name}?sslmode=require&sslrootcert=/etc/ssl/certs/ca-certificates.crt"
  sensitive   = true
}

output "private_endpoint_ip" {
  description = "Private IP address of the PostgreSQL private endpoint"
  value       = azurerm_private_endpoint.pg_pe.private_service_connection[0].private_ip_address
}
