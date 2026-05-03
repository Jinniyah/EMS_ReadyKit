# Module: app

Deploys the **App Service (Linux B1)** with managed identity, VNet integration, Key Vault secret storage, and diagnostic logging.

## Resources

| Resource | Purpose |
|---|---|
| `azurerm_service_plan` | Linux App Service Plan (B1) |
| `azurerm_linux_web_app` | EMS ReadyKit web/API application |
| `azurerm_key_vault` | Secret store for connection strings |
| `azurerm_role_assignment` | App identity → Key Vault Secrets User |
| `azurerm_key_vault_secret` | SQL connection string |
| `azurerm_monitor_diagnostic_setting` (×2) | App + KV diagnostics → Log Analytics |

## Inputs

| Name | Description |
|---|---|
| `resource_group_name` | Resource group |
| `location` | Azure region |
| `name_prefix` | Naming prefix |
| `subnet_app_id` | App subnet ID for VNet integration |
| `key_vault_tenant_id` | Tenant ID for Key Vault |
| `sql_connection_string` | Connection string (stored in KV, sensitive) |
| `storage_account_name` | Storage account name passed to app settings |
| `log_analytics_workspace_id` | LAW resource ID |
| `tags` | Tag map |

## Outputs

| Name | Description |
|---|---|
| `app_service_id` | App Service resource ID |
| `app_service_url` | Default HTTPS URL |
| `app_managed_identity_principal_id` | Managed identity principal ID |
| `key_vault_id` | Key Vault resource ID |
| `key_vault_uri` | Key Vault URI |

## Notes

- App uses a System-assigned Managed Identity — no stored credentials.
- Key Vault uses RBAC authorization (`enable_rbac_authorization = true`).
- Key Vault network ACL is set to Deny public access; Azure services bypass is enabled.
- `dotnet_version = "8.0"` is a placeholder — update the `application_stack` block to match your actual runtime.
- `purge_protection_enabled = false` for demo convenience; set to `true` in production.
