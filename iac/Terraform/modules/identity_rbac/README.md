# Module: identity_rbac

Implements the **group-based RBAC model** using Azure AD groups and Azure role assignments per [ADR-002](../../../docs/adr/ADR-002-RBAC.md).

## Resources

| Resource | Purpose |
|---|---|
| `azuread_group` (×3) | AD groups for Administrator, Supervisor, Responder |
| `azurerm_role_assignment` — Administrators | Reader at subscription scope |
| `azurerm_role_assignment` — Supervisors (×2) | Contributor + Log Analytics Reader at RG scope |

## Role Design

| Role | Azure Scope | Application Scope |
|---|---|---|
| Administrator | Subscription Reader | Global read |
| Supervisor | RG Contributor + LAW Reader | Station-scoped |
| Responder | None (authenticated only) | Vehicle-scoped (app-enforced) |

## Inputs

| Name | Description |
|---|---|
| `resource_group_id` | Station resource group ID (Supervisor scope) |
| `subscription_id` | Azure subscription ID (Administrator scope) |
| `tags` | Tag map |

## Outputs

| Name | Description |
|---|---|
| `administrators_group_id` | Object ID of the Administrators group |
| `supervisors_group_id` | Object ID of the Supervisors group |
| `responders_group_id` | Object ID of the Responders group |

## Notes

- No user-level role assignments — group-based only.
- Responders have no Azure RBAC; access is enforced entirely at the application layer.
- Requires `azuread` provider in addition to `azurerm`.
