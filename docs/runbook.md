# EMS ReadyKit -- Deployment & Validation Runbook

This runbook documents how to deploy and validate the EMS ReadyKit Azure
environment using Terraform, and — for anyone standing up their own copy to
evaluate the infrastructure — how to tear it back down safely.

**The `rg-ems-readykit-dev` resource group described throughout this runbook
is the real infrastructure behind EMS ReadyKit's UAT (user acceptance
testing) rollout**, in use by the real Newberg Township EMS team since
2026-06-23. It is not yet in production, and it is not a disposable demo
environment either. The steps below (init/plan/apply, validation) apply to
it directly. The teardown section at the end applies only to a *separate*
copy of this stack you stand up yourself for review purposes — never to this
resource group.

It is written for:
- Reviewers evaluating operational maturity
- Engineers validating observability and security controls
- Anyone standing up their own instance of this stack to explore it

---

## Purpose

The purpose of this runbook is to demonstrate:
- Safe, repeatable infrastructure deployment via Terraform
- Operational validation of governance, networking, and RBAC controls
- Evidence-driven verification of logging, auditing, and cost controls
- A clean teardown path for anyone evaluating their own copy of the stack

---

## Prerequisites

Before running Terraform:

- Azure subscription with sufficient privileges
- Azure CLI installed and authenticated
- Terraform installed locally
- Contributor or Owner permission on the target subscription
- Azure AD permissions to create app registrations, groups, and role assignments

---

## Repository Location

Terraform code lives at:

```text
iac/Terraform/
```

All commands below are run from that directory.

**Important:** Always delete the resource lock before running `terraform apply` —
the resource group is protected by a `CanNotDelete` management lock:

```bash
az lock delete --name delete-lock --resource-group rg-ems-readykit-dev
```

---

## Step 1: Initialize Terraform

```bash
terraform init
```

Expected results:
- Providers download successfully
- Remote backend initializes
- No secrets are prompted or stored in state

---

## Step 2: Review Planned Changes

```bash
terraform plan -var="pg_admin_password=<your_password>"
```

Verify that the plan includes:
- Virtual network, 3 subnets (app/data/management), and Network Security Groups
- Log Analytics workspace
- Azure AD app registration, 3 app roles, 3 matching security groups, and RBAC role assignments
- PostgreSQL Flexible Server, Key Vault, and App Service
- A resource-group budget with 80%/100% alert thresholds
- No public IP addresses (denied by policy)

Do not proceed if unexpected resources appear.

---

## Step 3: Deploy Infrastructure

```bash
terraform apply -var="pg_admin_password=<your_password>"
```

Confirm the apply when prompted.

Expected results:
- All resources deploy successfully
- No policy violations block deployment
- Deployment completes without manual intervention

---

## Step 4: Validate Governance and Security

### Validate Policies

- Navigate to Azure Policy compliance view
- Confirm required tags are enforced (Owner, CostCenter, Project, Environment, ManagedBy)
- Confirm public IP creation is denied

### Validate RBAC

- Confirm the three Azure AD security groups exist: `ems-readykit-administrators`,
  `ems-readykit-supervisors`, `ems-readykit-responders`
- Confirm each group holds both its app role assignment (visible on the
  app registration's Enterprise Application → Users and groups page) and its
  Azure RBAC role assignment (Reader at subscription scope for administrators;
  Contributor + Log Analytics Reader at resource-group scope for supervisors)
- Verify no user has been assigned an app role individually, outside of group membership

---

## Step 5: Validate Networking

Confirm:
- `snet-app`, `snet-data`, and `snet-management` subnets exist in `vnet-ems-readykit`
- Each subnet's NSG shows a `Deny-All-Inbound` rule at priority 4096, plus its
  narrow allow rule where applicable (Postgres from the app subnet only on
  `nsg-data`; SSH from RFC1918 ranges only on `nsg-management`)
- NSG flow events are visible in Log Analytics (`AzureDiagnostics` where
  `Category == "NetworkSecurityGroupEvent"`)
- The App Service's Networking blade shows VNet integration into `snet-app`
  (active on B1+; not available on F1)

Note: the PostgreSQL private endpoint exists in `snet-data`, but the server
still permits public access via its "Allow Azure Services" firewall rule —
there's no private DNS zone override yet, so this is the current, expected
state rather than a misconfiguration. This is one of the items worth closing
out before any production cutover. See `iac/Terraform/README.md`'s
Networking section for the remaining steps to full private connectivity.

Evidence may include:
- Azure Portal screenshots of the NSG rule lists and App Service networking blade
- A Log Analytics query result showing NSG flow events

---

## Step 6: Validate Centralized Logging

Navigate to the Log Analytics workspace and run a basic query:

```kusto
AzureActivity
| take 10
```

Expected results:
- Logs are visible
- Timestamps are current
- Data includes resource identifiers

Capture one screenshot or query result for evidence.

---

## Step 7: Validate Application Audit Events

- Perform a sample inventory update
- Complete a daily vehicle readiness check

Verify:
- Audit events appear in the application audit log (`GET /api/v1/audit`)
- Events include actor identity, station_id, entity_type, and timestamp
- Events are immutable (no edit or delete endpoint)

---

## Step 8: Azure AD Token Lifetime Validation

Confirm the following in the Azure AD app registration:

- Access token lifetime is configured (default 60-90 minutes is acceptable)
- Continuous Access Evaluation (CAE) is enabled -- provides near-real-time
  token revocation without code changes if an account is compromised
- The app registration has the three app roles configured:
  Administrator, Supervisor, Responder
- `sign_in_audience` is `AzureADandPersonalMicrosoftAccount` — required so
  administrators with personal Microsoft accounts (e.g. @outlook.com) can
  sign in; reverting this will lock them out

See ADR-006 (`docs/adr/ADR-006-Azure-AD-Token-Lifetime.md`) for the rationale.

---

## Step 9: Cost Validation

Confirm:
- The resource-group budget (`budget-ems-readykit-dev`) exists with 80% and
  100% notification thresholds configured
- `budget_alert_emails` points to a monitored address
- Log retention is set to 30 days or less on the Log Analytics workspace
- B1 App Service is the active SKU (not accidentally scaled up)

Document estimated monthly cost range if needed (Burstable B1ms PostgreSQL is
roughly $12-15/month; App Service B1 and the rest of the stack add to that).

---

## Step 10: Teardown (evaluation copies only — NOT the UAT environment)

If you stood up your **own separate copy** of this stack (a different
resource group, under your own subscription) to evaluate it, tear it down
when finished:

```bash
# Re-delete the lock first if it was re-created by policy
az lock delete --name delete-lock --resource-group <your-resource-group>

terraform destroy -var="pg_admin_password=<your_password>"
```

Confirm destroy when prompted.

**Do not run `terraform destroy` against `rg-ems-readykit-dev`.** That
resource group backs an active UAT deployment in use by a real EMS team; the
`CanNotDelete` lock exists specifically to make this mistake harder, not to
be routinely removed and re-added.

---

## Failure Handling

If deployment fails:
- Review Terraform error output
- Correct configuration issues
- Re-run `terraform apply -var="pg_admin_password=<your_password>"`

Avoid manual changes in the Azure portal where possible — they create drift
and may be overwritten on the next apply. Where a manual change is genuinely
necessary (as happened during the 2026-06-21/22 incident response — see
`docs/backlog_completed.md`, Sessions AL/AM), reconcile it back into Terraform
as soon as practical via a reviewed `terraform plan`, rather than leaving the
drift in place indefinitely.

---

## Disclaimer

This runbook documents the actual infrastructure behind an application
currently in UAT with a real EMS team — not a production deployment, and not
a throwaway demo either. It is not a substitute for a full
regulatory-compliance review; EMS ReadyKit does not currently store PHI, and
no HIPAA-specific controls are implemented or claimed.

---

**End of Runbook**
