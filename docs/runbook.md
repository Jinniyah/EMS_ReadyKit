# EMS ReadyKit -- Deployment & Validation Runbook

This runbook documents how to deploy, validate, and safely destroy the EMS
ReadyKit environment using Terraform.

It is written for:
- Reviewers evaluating operational maturity
- Engineers validating observability and security controls
- Portfolio demonstration purposes

This runbook assumes non-production usage only.

---

## Purpose

The purpose of this runbook is to demonstrate:
- Safe infrastructure deployment
- Basic operational validation
- Evidence-driven verification of logging and security controls
- Clean teardown of all resources

The goal is confidence and correctness, not uptime or scale.

---

## Prerequisites

Before running Terraform:

- Azure subscription with sufficient privileges
- Azure CLI installed and authenticated
- Terraform installed locally
- Contributor or Owner permission on the target subscription
- Azure AD permissions to create groups and role assignments

---

## Repository Location

Terraform code lives at:

```text
iac/Terraform/
```

All commands below are run from that directory.

**Important:** Always delete the resource lock before running `terraform apply`:

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
- Remote backend initializes (if configured)
- No secrets are prompted or stored in state

---

## Step 2: Review Planned Changes

```bash
terraform plan -var-file="terraform.tfvars"
```

Verify that the plan includes:
- Virtual network and subnets
- Network Security Groups
- Log Analytics workspace
- RBAC role assignments via groups
- Application hosting resources
- No public IP addresses (unless explicitly justified)

Do not proceed if unexpected resources appear.

---

## Step 3: Deploy Infrastructure

```bash
terraform apply -var-file="terraform.tfvars"
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
- Confirm required tags are enforced
- Confirm public IP creation is denied

### Validate RBAC

- Confirm Azure AD groups exist
- Confirm role assignments are group-based
- Verify no user-level role assignments exist

---

## Step 5: Validate Networking Baseline

Confirm:
- Application resources are deployed into the correct subnets
- NSGs enforce restrictive defaults
- Traffic diagnostics or flow logs are enabled

Evidence may include:
- Azure portal screenshots
- Flow log entries in storage

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

See ADR-006 (`docs/adr/ADR-006-Azure-AD-Token-Lifetime.md`) for the rationale.

---

## Step 9: Cost Validation

Confirm:
- Azure budget alerts are configured
- Log retention is set to 30 days or less (short retention reduces cost)
- B1 App Service is the active SKU (not accidentally scaled up)

Document estimated monthly cost range if needed.

---

## Step 10: Environment Teardown

When validation is complete:

```bash
# Re-delete the lock first if it was re-created by policy
az lock delete --name delete-lock --resource-group rg-ems-readykit-dev

terraform destroy -var-file="terraform.tfvars"
```

Confirm destroy when prompted.

Expected results:
- All resources are removed
- No orphaned infrastructure remains
- No manual cleanup required

---

## Failure Handling

If deployment fails:
- Review Terraform error output
- Correct configuration issues
- Re-run `terraform apply -var-file="terraform.tfvars"`

Avoid manual changes in the Azure portal -- they will be overwritten or
create drift on the next apply.

---

## Important Notes

- This environment is disposable by design
- Data persistence is not guaranteed across teardown/redeploy cycles
- Do not leave resources running unnecessarily
- Do not reuse this environment for live EMS operations without a
  production-hardening review

---

## Disclaimer

This runbook supports a technical demonstration only.
It does not constitute production guidance or regulatory compliance documentation.

---

**End of Runbook**
