# EMS ReadyKit — Evidence Directory

This directory holds deployment evidence captured after `terraform apply` and
application validation, as required by the acceptance criteria in
[Requirements.md](../Requirements.md) and the [runbook](../runbook.md).

Evidence is **not committed until the environment has been deployed**.
The directory structure is pre-created so the intent is clear to reviewers.

---

## Directory Structure

```
evidence/
├── screenshots/    — Azure portal and Log Analytics screenshots
└── logs/           — Exported KQL query results and audit log samples
```

---

## What to Capture

### screenshots/

| Filename | What to show |
|---|---|
| `01_resource_group_overview.png` | All resources deployed in the resource group |
| `02_policy_compliance.png` | Azure Policy compliance view showing enforced guardrails |
| `03_rbac_groups.png` | Azure AD groups (ems-readykit-administrators, supervisors, responders) |
| `04_rbac_assignments.png` | Role assignments at subscription and resource group scope |
| `05_nsg_rules_app.png` | App subnet NSG with Deny-All-Inbound rule |
| `06_nsg_rules_data.png` | Data subnet NSG with SQL allow rule |
| `07_log_analytics_workspace.png` | Log Analytics workspace overview |
| `08_log_query_activity.png` | AzureActivity query returning results |
| `09_log_query_audit.png` | AppEvents or custom audit event query |
| `10_budget_alert.png` | Budget alert configuration showing 80% and 100% thresholds |
| `11_app_service_health.png` | App Service health check returning 200 OK |
| `12_key_vault_secrets.png` | Key Vault secrets list (values hidden) |

### logs/

| Filename | Contents |
|---|---|
| `activity_log_sample.json` | Output of `AzureActivity \| take 10` exported as JSON |
| `audit_events_sample.json` | Output of the EMS-RecentAuditEvents saved query |
| `high_severity_sample.json` | Output of the EMS-HighSeverityEvents saved query (if triggered) |

---

## How to Capture

### KQL Query Export (Log Analytics)

1. Navigate to Log Analytics workspace → Logs
2. Run the desired query
3. Click **Export** → **Export to CSV** or copy results
4. Save to `evidence/logs/`

### Screenshots

Use the Azure portal's built-in screenshot or your OS screenshot tool.
Crop to show the relevant pane — full-desktop screenshots are acceptable but
should be clearly labelled by filename.

### After Capture

Update the acceptance criteria checkboxes in the [Terraform README](../../iac/Terraform/README.md)
as each item is verified.

---

> This directory is intentionally empty until the environment is deployed.
> See the [runbook](../runbook.md) for step-by-step deployment and validation instructions.
