# Module: siem (Optional)

Deploys an **Ubuntu 22.04 VM** in the monitoring subnet for use as a Security Onion SIEM node.

> **Disabled by default.** Enable by setting `enable_siem = true` in root variables.

## Purpose

Security Onion is used to:
- Validate detection capability
- Demonstrate log correlation and alerting
- Simulate attack scenarios (e.g., via TryHackMe) against the platform

It is a **demonstration and validation tool**, not a production SOC replacement. See [ADR-003](../../../docs/adr/ADR-003-Logging-and-Audit.md).

## Resources

| Resource | Purpose |
|---|---|
| `azurerm_network_interface` | Private NIC in monitoring subnet |
| `azurerm_linux_virtual_machine` | Security Onion VM (Ubuntu 22.04 LTS) |
| `azurerm_virtual_machine_extension` | OMS Agent → Log Analytics |
| `azurerm_monitor_diagnostic_setting` | VM metrics → Log Analytics |

## Inputs

| Name | Description | Default |
|---|---|---|
| `resource_group_name` | Resource group | required |
| `location` | Azure region | required |
| `name_prefix` | Naming prefix | required |
| `subnet_monitoring_id` | Monitoring subnet ID | required |
| `admin_username` | VM admin username | `siemadmin` |
| `admin_password` | VM admin password (sensitive) | required |
| `vm_size` | VM size | `Standard_D4s_v3` |
| `log_analytics_workspace_id` | LAW resource ID | required |
| `tags` | Tag map | `{}` |

## Outputs

| Name | Description |
|---|---|
| `siem_vm_id` | VM resource ID |
| `siem_private_ip` | Private IP address |
| `siem_vm_name` | VM name |

## Post-Deployment

After the VM is provisioned, install Security Onion manually:

```bash
# SSH to the VM via private IP (requires VPN or bastion)
ssh siemadmin@<private_ip>

# Follow Security Onion installation guide:
# https://docs.securityonion.net/en/2.4/
```

## Notes

- No public IP is assigned — SSH access requires VPN or Azure Bastion.
- VM size `Standard_D4s_v3` (4 vCPU, 16 GB) meets Security Onion minimum requirements.
- OMS Agent extension forwards VM auth and syslog events to Log Analytics.
