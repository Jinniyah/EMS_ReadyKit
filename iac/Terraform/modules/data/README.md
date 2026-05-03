# Module: data

Provisions the **Azure SQL Server and Database** with private endpoint, firewall deny-all, auditing, and diagnostic log forwarding.

## Resources

| Resource | Purpose |
|---|---|
| `azurerm_mssql_server` | SQL Server (no public access) |
| `azurerm_mssql_database` | EMS operational database (Basic SKU) |
| `azurerm_mssql_firewall_rule` | Deny-all public firewall rule |
| `azurerm_private_endpoint` | Private network access via data subnet |
| `azurerm_mssql_server_extended_auditing_policy` | SQL audit logging |
| `azurerm_monitor_diagnostic_setting` | Diagnostics → Log Analytics |

## Inputs

| Name | Description |
|---|---|
| `resource_group_name` | Resource group |
| `location` | Azure region |
| `name_prefix` | Naming prefix |
| `subnet_data_id` | Data subnet ID for private endpoint |
| `sql_admin_login` | SQL admin username |
| `sql_admin_password` | SQL admin password (sensitive) |
| `log_analytics_workspace_id` | LAW resource ID |
| `tags` | Tag map |

## Outputs

| Name | Description |
|---|---|
| `sql_server_id` | SQL Server resource ID |
| `sql_server_fqdn` | SQL Server FQDN |
| `sql_database_name` | Database name |
| `sql_connection_string` | ADO.NET connection string (sensitive) |
| `private_endpoint_ip` | Private IP of the SQL endpoint |

## Notes

- `public_network_access_enabled = false` on the server; all access is via private endpoint.
- Basic SKU (2 GB) is right-sized for demo scope. Upgrade to S0+ for any real workload.
- Connection string uses Managed Identity authentication — no embedded passwords.
