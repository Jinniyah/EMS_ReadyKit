# EMS ReadyKit – Deployment & Validation Runbook

This runbook documents how to **deploy, validate, and safely destroy** the EMS ReadyKit environment using Terraform.

It is written for:
- Reviewers evaluating operational maturity
- Engineers validating observability and security controls
- Portfolio demonstration purposes

This runbook assumes **non-production usage only**.

---

## Purpose

The purpose of this runbook is to demonstrate:
- Safe infrastructure deployment
- Basic operational validation
- Evidence-driven verification of logging and security controls
- Clean teardown of all resources

The goal is **confidence and correctness**, not uptime or scale.

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
iac/terraform/
```

All commands below are run from that directory.

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
terraform plan
```

Verify that the plan includes:
- Virtual network and subnets
- Network Security Groups
- Log Analytics workspace
- RBAC role assignments via groups
- Application hosting resources
- No public IP addresses (unless explicitly justified)

Do **not** proceed if unexpected resources appear.

---

## Step 3: Deploy Infrastructure

```bash
terraform apply
```

Confirm the apply when prompted.

Expected results:
- All resources deploy successfully
- No policy violations block deployment
- Deployment completes without manual intervention

---

## Step 4: Validate Governance & Security

### Validate Policies

- Navigate to Azure Policy compliance view
- Confirm required tags are enforced
- Confirm public IP creation is denied

---

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
SecurityEvent
| take 10
```

Or:

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

Once application logic is implemented:
- Perform a sample inventory update
- Complete a daily vehicle readiness check

Verify:
- Audit events appear in Log Analytics
- Events include `station_id` and `vehicle_id`
- Actor identity is recorded

---

## Step 8: Validate High-Severity Event Flow (Optional)

If the SIEM module is enabled:

- Trigger a controlled substance discrepancy (test data only)
- Confirm high-severity audit event is generated
- Verify selected logs appear in Security Onion

This step is for **demonstration only**.

---

## Step 9: Cost Validation

Confirm:
- Azure budget alerts are configured
- Log retention is short by default
- Optional SIEM VM is stopped when not in use

Document estimated monthly cost range if needed.

---

## Step 10: Environment Teardown

When validation is complete:

```bash
terraform destroy
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
- Re-run `terraform apply`

Avoid manual changes in the Azure portal.

---

## Important Notes

- This environment is **disposable by design**
- Data persistence is not guaranteed
- Do not leave resources running unnecessarily
- Do not reuse this environment for live EMS operations

---

## Disclaimer

This runbook supports a **technical demonstration only**.
It does not constitute production guidance or regulatory compliance documentation.

---

**End of Runbook**
