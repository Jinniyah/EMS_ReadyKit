# Module: logging

Creates the **central Log Analytics Workspace** that serves as the system of record for all platform telemetry, application logs, and audit events per [ADR-003](../../../docs/adr/ADR-003-Logging-and-Audit.md).

## Resources

| Resource | Purpose |
|---|---|
| `azurerm_log_analytics_workspace` | Central log store |
| `azurerm_log_analytics_saved_search` (×2) | Pre-built audit and high-severity queries |
| `azurerm_monitor_action_group` | Ops alert routing target |
| `azurerm_monitor_activity_log_alert` | Alert on destructive subscription operations |

## Inputs

| Name | Description | Default |
|---|---|---|
| `resource_group_name` | Resource group | required |
| `location` | Azure region | required |
| `name_prefix` | Naming prefix | required |
| `log_retention_days` | Log retention in days | `30` |
| `tags` | Tag map | `{}` |

## Outputs

| Name | Description |
|---|---|
| `workspace_id` | Resource ID of the workspace |
| `workspace_name` | Workspace name |
| `primary_shared_key` | Shared key (sensitive) |
| `workspace_customer_id` | Customer/workspace GUID |

## Notes

- Retention set to 30 days by default — cost-appropriate for demo scope.
- Increase `log_retention_days` for a longer-running environment.
- Saved searches are pre-loaded for audit events and high-severity correlation.
