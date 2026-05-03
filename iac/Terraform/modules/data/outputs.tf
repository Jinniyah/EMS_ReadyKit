// data outputs.tf

output "sql_server_id" {
  description = "Resource ID of the SQL Server"
  value       = azurerm_mssql_server.ems_sql.id
}

output "sql_server_fqdn" {
  description = "Fully qualified domain name of the SQL Server"
  value       = azurerm_mssql_server.ems_sql.fully_qualified_domain_name
}

output "sql_database_name" {
  description = "Name of the SQL database"
  value       = azurerm_mssql_database.ems_db.name
}

output "sql_connection_string" {
  description = "ADO.NET connection string for the EMS database (sensitive)"
  value       = "Server=tcp:${azurerm_mssql_server.ems_sql.fully_qualified_domain_name},1433;Database=${azurerm_mssql_database.ems_db.name};Authentication=Active Directory Managed Identity;Encrypt=true;"
  sensitive   = true
}

output "private_endpoint_ip" {
  description = "Private IP address of the SQL private endpoint"
  value       = azurerm_private_endpoint.sql_pe.private_service_connection[0].private_ip_address
}
