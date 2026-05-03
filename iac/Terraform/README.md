# EMS ReadyKit — Terraform Infrastructure

This directory contains the complete Infrastructure-as-Code for EMS ReadyKit, deployed to Azure via Terraform.

See [ADR-004](../../docs/adr/ADR-004-Terraform-Module-Structure.md) for the rationale behind this module structure.

---

## Prerequisites

- Terraform >= 1.5.0
- Azure CLI authenticated (`az login`)
- Contributor access to the target subscription
- Remote state backend pre-created (see below)

---

## Module Overview

```
modules/
├── logging/        — Log Analytics workspace, saved queries, alerts
├── network/        — VNet, subnets, NSGs with rules, route table, diagnostics
├── identity_rbac/  — Azure AD groups, RBAC assignments (ADR-002)
├── policy/         — Allowed locations, required tags, deny public IP
├── storage/        — Blob storage, containers, lifecycle, diagnostics
├── data/           — Azure SQL Server + DB, private endpoint, auditing
├── app/            — App Service (Linux B1), Key Vault, managed identity
└── siem/           — Security Onion VM (optional, disabled by default)
```

---

## Remote State Backend

State is stored in Azure Blob Storage. The backend storage account must be created **before** running `terraform init`.

```bash
# One-time setup (run manually or via bootstrap script)
az group create --name tfstate-rg --location eastus
az storage account create \
  --name emsreadykittfstate \
  --resource-group tfstate-rg \
  --sku Standard_LRS \
  --https-only true
az storage container create \
  --name tfstate \
  --account-name emsreadykittfstate
```

No secrets are committed to this repository. Authentication uses the current Azure CLI session or a service principal set via environment variables.

---

## Usage

```bash
cd iac/Terraform

# Initialize (pulls providers, configures backend)
terraform init

# Review execution plan
terraform plan -var="sql_admin_password=<your_password>"

# Apply
terraform apply -var="sql_admin_password=<your_password>"

# Enable optional SIEM
terraform apply \
  -var="sql_admin_password=<password>" \
  -var="enable_siem=true" \
  -var="siem_admin_password=<siem_password>"

# Destroy all resources
terraform destroy -var="sql_admin_password=<your_password>"
```

> **Tip:** Use a `.tfvars` file (gitignored) or environment variables for sensitive values rather than passing them on the command line.

---

## Key Variables

| Variable | Description | Default |
|---|---|---|
| `environment` | Deployment environment | `dev` |
| `location` | Azure region | `eastus` |
| `owner_tag` | Owner tag value | `EMS-ReadyKit-Team` |
| `cost_center_tag` | CostCenter tag value | `EMS-Demo` |
| `storage_account_name` | Globally unique storage name | `emsreadykitstorage123` |
| `sql_admin_login` | SQL Server admin login | `emsadmin` |
| `sql_admin_password` | SQL Server admin password | *(sensitive, required)* |
| `enable_siem` | Deploy Security Onion VM | `false` |

---

## Build Order

Modules are deployed in dependency order by Terraform automatically. The logical order is:

1. `logging` — workspace must exist before diagnostic settings
2. `network` — VNet before private endpoints and VNet integration
3. `identity_rbac` — groups before application configuration
4. `policy` — guardrails applied subscription-wide
5. `storage` — storage account before app settings reference it
6. `data` — SQL before app reads connection string
7. `app` — app deploys last, referencing all upstream outputs
8. `siem` — optional, independent of the app layer

---

## Acceptance Criteria

- [ ] `terraform fmt` passes with no changes
- [ ] `terraform validate` passes cleanly
- [ ] `terraform plan` produces expected resource count with no errors
- [ ] Remote state is configured and working
- [ ] No secrets committed to the repository
- [ ] All modules expose documented inputs and outputs
- [ ] Tags are applied to all resources
