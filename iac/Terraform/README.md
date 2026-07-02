# EMS ReadyKit — Terraform Infrastructure

This directory contains the complete Infrastructure-as-Code for EMS ReadyKit,
deployed to Azure via Terraform. EMS ReadyKit has been deployed and in **UAT
with the real Newberg Township EMS team since 2026-06-23** — it is not yet in
production, but this is not demo or throwaway infrastructure either.

See [ADR-001](../../docs/adr/ADR-001-Architecture.md) for the overall
architecture rationale, [ADR-002](../../docs/adr/ADR-002-RBAC.md) for the
identity/RBAC design, and [ADR-004](../../docs/adr/ADR-004-Terraform-Module-Structure.md)
for the rationale behind this module structure.

---

## Prerequisites

- Terraform ~> 1.6
- Azure CLI authenticated (`az login`)
- Contributor access to the target subscription
- Azure AD permissions to create app registrations, groups, and role assignments
- Remote state backend pre-created (see below)

---

## Module Overview

```
modules/
├── logging/        — Log Analytics workspace, diagnostic settings
├── network/        — VNet, 3 subnets (app/data/management), NSGs with deny-all-inbound baseline
├── identity_rbac/  — Azure AD app registration + 3 app roles, matching AD security groups,
│                      Azure RBAC role assignments, CI/CD service principal (ADR-002)
├── policy/         — Allowed locations, required tags, deny public IP
├── storage/        — Blob storage (exports, audit logs, evidence, App Service backups)
├── data/           — Azure PostgreSQL Flexible Server + database, private endpoint, auditing
├── app/            — App Service (Linux), Key Vault, managed identity
└── siem/           — Security Onion VM (optional, disabled by default)
```

---

## Remote State Backend

State is stored in Azure Blob Storage. The backend storage account must be created **before** running `terraform init`.

```bash
# One-time setup (run manually or via bootstrap script)
az group create --name tfstate-rg --location southcentralus
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

# Always delete the resource-group lock first — it protects the resource
# group from accidental deletion and blocks every apply until removed
az lock delete --name delete-lock --resource-group rg-ems-readykit-dev

# Initialize (pulls providers, configures backend)
terraform init

# Review execution plan
terraform plan -var="pg_admin_password=<your_password>"

# Apply
terraform apply -var="pg_admin_password=<your_password>"

# Enable optional SIEM
terraform apply \
  -var="pg_admin_password=<password>" \
  -var="enable_siem=true" \
  -var="siem_admin_password=<siem_password>"
```

> **Tip:** Use a `.tfvars` file (gitignored) or environment variables for sensitive values rather than passing them on the command line.

> **This is the real infrastructure behind an active UAT deployment**, not a
> disposable sandbox. `terraform destroy` is documented in `docs/runbook.md`
> for anyone standing up their *own* separate copy of this stack to evaluate
> it — it should never be run against `rg-ems-readykit-dev`.

---

## Key Variables

| Variable | Description | Default |
|---|---|---|
| `environment` | Deployment environment (`dev`, `staging`, `prod`) | `dev` |
| `location` | Azure region | `northcentralus` |
| `owner_tag` | Owner tag value | `EMS-ReadyKit-Team` |
| `cost_center_tag` | CostCenter tag value | `EMS-Demo` |
| `storage_account_name` | Globally unique storage name (3-24 lowercase alphanumeric) | `emsreadykitstorage123` |
| `pg_admin_login` | PostgreSQL Flexible Server admin login | `emsadmin` |
| `pg_admin_password` | PostgreSQL Flexible Server admin password | *(sensitive, required)* |
| `app_service_sku` | App Service SKU. B1+ enables VNet integration and always-on; F1 (free) does not | `B1` |
| `static_web_app_sku` | `Free` or `Standard` | `Free` |
| `enable_siem` | Deploy Security Onion VM | `false` |
| `allowed_admin_ips` | CIDR list allowed to reach the Key Vaults during terraform apply | `[]` |
| `office_ip_cidr` | Admin IP (CIDR) for SCM/Kudu access restriction | `""` |
| `monthly_budget_usd` | Monthly spend threshold in USD for cost alerts | `50` |
| `budget_start_date` | Budget period start date (RFC3339) | `2026-05-01T00:00:00Z` |
| `budget_alert_emails` | Email addresses notified at 80% and 100% of budget | *(required)* |

---

## Build Order

Modules are deployed in dependency order by Terraform automatically. The logical order is:

1. `logging` — workspace must exist before diagnostic settings
2. `network` — VNet before private endpoints and VNet integration
3. `static_web_app` — deployed early since `identity_rbac` needs its URL for the app registration's redirect URI
4. `identity_rbac` — app registration and groups before application configuration
5. `policy` — guardrails applied subscription-wide
6. `storage` — storage account before app settings reference it
7. `data` — PostgreSQL before app reads the connection string
8. `app` — app deploys last, referencing all upstream outputs
9. `siem` — optional, independent of the app layer

---

## Networking

The default SKU (and the one used for the current UAT deployment) is **B1**,
which enables App Service VNet integration (outbound-only — inbound HTTPS
still terminates on Azure's managed frontend, never on the app subnet).
Three subnets exist: `snet-app`, `snet-data`, and `snet-management`, each
with an NSG enforcing a deny-all-inbound baseline (plus narrow allow rules
where needed — SQL/Postgres from the app subnet only, SSH from RFC1918
ranges only). NSG flow events are forwarded to Log Analytics.

A private endpoint for PostgreSQL is provisioned in the data subnet, but the
server still has `public_network_access_enabled = true` with an
"Allow Azure Services" firewall rule as the active path — there's no private
DNS zone override yet forcing resolution to the private endpoint's IP, so
traffic to Postgres currently still resolves via its public endpoint (over
Azure's backbone, not the open internet). Completing the fully private
connection requires adding a `privatelink.postgres.database.azure.com`
private DNS zone linked to the VNet and removing the public firewall rule —
tracked in the backlog as a hardening item (I-1 covers the related Azure
Firewall work), and worth finishing before any production cutover.

---

## Identity and RBAC

`identity_rbac` creates a real Azure AD app registration with three app
roles (Administrator, Supervisor, Responder) and three matching Azure AD
security groups (`ems-readykit-administrators`, `-supervisors`, `-responders`).
Each group is both:

- assigned the corresponding **app role**, so its members get that role in
  the JWT issued at sign-in (this is what `core/auth.py` reads), and
- granted **Azure infrastructure RBAC** at the appropriate scope — Reader at
  subscription scope for administrators, Contributor + Log Analytics Reader
  at resource-group scope for supervisors.

Station-level membership (which station a person belongs to) is a separate,
purely application-layer concern handled by the `StationMember` table — it
has no Azure AD equivalent by design (see ADR-002).

A separate CI/CD service principal (`sp-ems-readykit-github-actions`) is
scoped to Website Contributor on the resource group plus Storage Blob Data
Contributor on the Terraform state account — enough to deploy the app and
manage state, nothing more.

---

## Cost Controls

A resource-group-scoped budget (`monthly_budget_usd`, default $50) with 80%
and 100% threshold notifications is created automatically on every apply —
this isn't optional or aspirational, it's live. Update `budget_alert_emails`
to whoever should be notified.

---

## Acceptance Criteria

- [x] `terraform fmt` passes with no changes
- [x] `terraform validate` passes cleanly
- [x] `terraform plan` produces expected resource count with no errors
- [x] Remote state is configured and working
- [x] No secrets committed to the repository
- [x] All modules expose documented inputs and outputs
- [x] Tags are applied to all resources
