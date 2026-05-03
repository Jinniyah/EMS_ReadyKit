# Module: policy

Defines and assigns **Azure Policy guardrails** to enforce governance baselines at the subscription scope.

## Policies Applied

| Policy | Type | Effect |
|---|---|---|
| Allowed locations | Built-in | Deny |
| Require tag: Project | Built-in | Deny |
| Require tag: Environment | Built-in | Deny |
| Require tag: Owner | Built-in | Deny |
| Require tag: CostCenter | Built-in | Deny |
| Require tag: ManagedBy | Built-in | Deny |
| Deny public IP creation | Custom | Deny |

## Inputs

| Name | Description | Default |
|---|---|---|
| `subscription_id` | Azure subscription ID | required |
| `resource_group_name` | Resource group name | required |
| `allowed_location` | Permitted Azure region | `eastus` |
| `required_tags` | Tag keys to enforce | see variables.tf |

## Outputs

| Name | Description |
|---|---|
| `allowed_locations_assignment_id` | Policy assignment resource ID |
| `deny_public_ip_assignment_id` | Policy assignment resource ID |

## Notes

- All policies are assigned at subscription scope for maximum coverage.
- The public IP deny policy uses a custom definition — effect is `Deny` (not audit-only).
- Tag policies use `for_each` over the `required_tags` list for DRY structure.
