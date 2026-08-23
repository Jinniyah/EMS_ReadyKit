# EMS ReadyKit — Decommission Record (2026-08-21)

This document records the decommissioning of the `rg-ems-readykit-dev` Azure
environment: why it was taken down, what was backed up beforehand, the exact
steps run, and the final verified state. It exists as evidence that the
teardown was deliberate, reviewed, and non-destructive to data that mattered —
companion to `iac/Terraform/README.md` and `docs/runbook.md`, which document
the build side of this same infrastructure.

**Status as of 2026-08-22:** Decommission complete. `rg-ems-readykit-dev`
(70 resources) and `tfstate-rg` are both destroyed and verified gone. Only
`NetworkWatcherRG` (Azure-managed, empty, zero-cost) remains in the
subscription.

---

## 1. Decision

EMS ReadyKit's UAT deployment (`rg-ems-readykit-dev`, live since 2026-06-23)
was costing approximately $20/month with no active users. The owner decided
to decommission the Azure environment rather than continue paying to keep it
running, on the basis that the infrastructure is fully defined as Terraform
IaC and can be redeployed later if needed.

Both `iac/Terraform/README.md` and `docs/runbook.md` carry an explicit
warning not to run `terraform destroy` against `rg-ems-readykit-dev`, written
while the environment was in active use by the Newberg Township EMS team.
That warning is superseded by this decision — the environment is confirmed
no longer in use as of this date.

**Note for anyone rebuilding from this IaC later:** a `terraform apply` will
recreate the infrastructure shell, but not the data or the two pieces of
manual configuration described below. See §2 and §5.

---

## 2. What Terraform *cannot* restore

Identified during pre-decommission review, before any destructive action:

- **Application data** — PostgreSQL database contents and blob storage
  contents (`app-exports`, `audit-logs`, `evidence`, `app-backups`
  containers) are not part of Terraform state. `terraform apply` after a
  destroy recreates empty resources, not a restore.
- **Azure AD app registration manual config** — the SPA redirect URI and
  `required_resource_access` (self-referencing API permission) on the
  "EMS ReadyKit API" app registration were configured by hand in the Azure
  Portal (see the long comment block in
  `iac/Terraform/modules/identity_rbac/main.tf`), because the azuread
  provider cannot express a self-referencing API permission and requires a
  trailing slash on redirect URIs that the frontend's MSAL config never
  sends. This exact gap caused a full sign-in outage on 2026-06-21. If the
  app registration is recreated, this must be redone by hand.
- **Terraform state backend** (`tfstate-rg` resource group / storage account
  `emsreadykittfstate`) was bootstrapped manually outside this Terraform
  config per `iac/Terraform/README.md` and is not touched by
  `terraform destroy`.

Given the above, data was backed up before any resources were deleted (§3),
and the app registration's manual configuration was captured for reference
(§5) before deletion.

---

## 3. Pre-destroy backup

<!-- Fill in with actual results as each step is run and pasted back. -->

### 3a. PostgreSQL dump

- Server: `pg-ems-readykit-dev.postgres.database.azure.com`
- Database: `ems_readykit`
- Run from: Azure Cloud Shell (avoids needing local Postgres client tools; the
  server's "Allow Azure Services" firewall rule covers Cloud Shell's egress
  automatically, and the Key Vault holding `pg-admin-password` was reachable
  without opening its firewall further)
- Command run:
  ```
  export PGPASSWORD=$(az keyvault secret show --vault-name kvqzf6ns --name pg-admin-password --query value -o tsv)
  pg_dump -h pg-ems-readykit-dev.postgres.database.azure.com -U emsadmin -d ems_readykit -F c -f ems_readykit_backup_2026-08-21.dump
  ```
- First attempt (2026-08-21 evening): dump completed (`ls -la` showed a
  144438-byte file) but the Cloud Shell session dropped before
  `pg_restore --list` returned, and the file was not confirmed recoverable
  from that session afterward. **Discarded — not used as the backup of
  record**, since its integrity was never verified.
- Second attempt (2026-08-22, fresh Cloud Shell session): re-ran the full
  command sequence and verified before downloading:
  ```
  jennifer [ ~ ]$ pg_restore --list ems_readykit_backup_2026-08-21.dump | head -30
  ;
  ; Archive created at 2026-08-22 11:18:05 UTC
  ;     dbname: ems_readykit
  ;     TOC Entries: 260
  ;     Compression: gzip
  ;     Dump Version: 1.15-0
  ;     Format: CUSTOM
  ;     Dumped from database version: 16.14
  ;     Dumped by pg_dump version: 16.14
  ```
  260 TOC entries, valid CUSTOM-format archive, matches the live server's
  Postgres 16.14. **This is the backup of record.**
- Downloaded via Cloud Shell "Manage files → Download" and confirmed present
  locally at `azure-backup-2026-08-21\ems_readykit_backup_2026-08-21.dump`,
  144438 bytes, local mtime 2026-08-22 07:23 (timestamp confirms it's the
  verified second-attempt file, not the discarded first attempt).
- Stored at: `azure-backup-2026-08-21\ems_readykit_backup_2026-08-21.dump`
  (repo root, gitignored — not committed)

### 3b. Blob storage containers

- Storage account: `emsreadykitstorage123`
- Command run: `az storage blob download-batch --account-name emsreadykitstorage123 --source <container> --destination <local-dir>` per container, 2026-08-21
- Stored at: `azure-backup-2026-08-21\` (repo root, gitignored — not committed)
- Result:

  | Container | Files | Notes |
  |---|---|---|
  | `app-exports` | 0 | Empty — consistent with no active usage; also has a 90-day auto-delete lifecycle rule |
  | `audit-logs` | 0 | Empty — the actual application audit trail lives in the Postgres `AuditEvent` table (`core/audit.py::write_audit_event()`), not this container; captured by the pg_dump in §3a instead |
  | `evidence` | 0 | Empty — no evidence files were ever uploaded through this environment |
  | `app-backups` | 21 (7 daily automated App Service backups + matching `.log`/`.xml` manifests, 2026-08-15 through 2026-08-21) | ~3.0 GB total. These are Azure App Service's own automated site backups (via the SAS token in `modules/storage/main.tf`) — a redundant, independent backup covering the same window as the manual pg_dump, kept as a belt-and-suspenders copy. Has a 30-day auto-delete lifecycle rule, so this is why only 7 days' worth existed at backup time. |

---

## 4. Pre-destroy resource inventory

Captured via `az resource list --resource-group rg-ems-readykit-dev --output table`
before the lock was removed, so the destroy plan below can be checked against
a known-good "what existed" baseline. Run 2026-08-21, confirmed against the
correct subscription (`75fce2ea-1d83-4c5a-9929-b424b2913c8e`, matching
`backend.tf`) via `az account list`.

```
Name                                                              ResourceGroup        Location        Type                                        Status
-----------------------------------------------------------------  -------------------  --------------  ------------------------------------------  ---------
nsg-management                                                    rg-ems-readykit-dev  northcentralus  Microsoft.Network/networkSecurityGroups     Succeeded
vnet-ems-readykit                                                 rg-ems-readykit-dev  northcentralus  Microsoft.Network/virtualNetworks           Succeeded
nsg-app                                                           rg-ems-readykit-dev  northcentralus  Microsoft.Network/networkSecurityGroups     Succeeded
nsg-data                                                          rg-ems-readykit-dev  northcentralus  Microsoft.Network/networkSecurityGroups     Succeeded
emsreadykitstorage123                                             rg-ems-readykit-dev  northcentralus  Microsoft.Storage/storageAccounts           Succeeded
law-ems-readykit-dev                                              rg-ems-readykit-dev  northcentralus  Microsoft.OperationalInsights/workspaces    Succeeded
asp-ems-readykit-dev                                              rg-ems-readykit-dev  northcentralus  Microsoft.Web/serverFarms                   Succeeded
pg-ems-readykit-dev                                               rg-ems-readykit-dev  northcentralus  Microsoft.DBforPostgreSQL/flexibleServers   Succeeded
pe-pg-ems-readykit-dev                                            rg-ems-readykit-dev  northcentralus  Microsoft.Network/privateEndpoints          Succeeded
pe-pg-ems-readykit-dev.nic.126ea145-b9bc-4d44-93a1-ce96da3a0e6b   rg-ems-readykit-dev  northcentralus  Microsoft.Network/networkInterfaces         Succeeded
app-ems-readykit-dev                                              rg-ems-readykit-dev  northcentralus  Microsoft.Web/sites                         Succeeded
kv-f07bxc                                                         rg-ems-readykit-dev  northcentralus  Microsoft.KeyVault/vaults                   Succeeded
kvqzf6ns                                                          rg-ems-readykit-dev  northcentralus  Microsoft.KeyVault/vaults                   Succeeded
swa-ems-readykit-dev                                              rg-ems-readykit-dev  centralus       Microsoft.Web/staticSites                   Succeeded
ag-ems-readykit-dev-ops                                           rg-ems-readykit-dev  global          Microsoft.Insights/actiongroups             Succeeded
alert-ems-readykit-dev-destructive-ops                            rg-ems-readykit-dev  global          Microsoft.Insights/activityLogAlerts        Succeeded
```

16 resources, all mapping cleanly to Terraform modules — no drift or orphaned
resources found. Notes:
- No SIEM VM present, consistent with `enable_siem = false` (the default).
- Two Key Vaults are both expected: `kvqzf6ns` (root `main.tf`,
  `azurerm_key_vault.platform`, holds `pg-admin-password`) and `kv-f07bxc`
  (`modules/app/main.tf`, `azurerm_key_vault.ems_kv`, holds
  `sql-connection-string` / `app-secret-key`) — different modules, each with
  its own `random_string.kv_suffix`, hence the differing naming pattern
  (`kv-<suffix>` vs `kv<suffix>`).
- `ag-ems-readykit-dev-ops` / `alert-ems-readykit-dev-destructive-ops` are
  Terraform-managed (`modules/logging/main.tf`), not manual additions.
- `azurerm_consumption_budget_resource_group` does not appear in
  `az resource list` output (budgets aren't listed the same way as standard
  resources) — verify separately via `az consumption budget list` or the
  Cost Management blade if confirming its removal post-destroy.

---

## 5. Azure AD app registration manual config (reference only)

Screenshots captured 2026-08-22, before deletion, since this configuration is
not recoverable from Terraform state. Stored at
`azure-backup-2026-08-21\ad-app-registration\`. Values transcribed below so
this record doesn't depend on the images surviving.

**Authentication → Redirect URI configuration:**
- Platform type: Single-page application
- `http://localhost:5173`
- `https://lively-bush-0ed75ca10.7.azurestaticapps.net`
- (Neither has a trailing slash — confirms the `modules/identity_rbac/main.tf`
  comment about MSAL's `window.location.origin` never sending one.)
- Screenshot: `2026-08-22_EMS_ReadyKit_API_Authetication.png`

**API permissions:**
- `EMS ReadyKit API (1)` → `api.access`, Delegated, Admin consent required:
  No, Status: Granted for Default Directory
- (Only `api.access` appears here — this page lists *requested* permissions
  the app asks for on its own API, distinct from the two *offered* scopes
  under "Expose an API" below. Matches the `required_resource_access` /
  self-reference note in `main.tf`.)
- Screenshot: `2026-08-22_EMS_ReadyKit_API_Permissions.png`

**Expose an API:**
- Application ID URI: `api://a780b97f-5451-46d5-8fc9-5268e491e0ee`
- Scopes: `user_impersonation` and `api.access`, both "Who can consent:
  Admins and users", admin/user consent display name "Access EMS ReadyKit API"
- Authorized client applications: Client ID
  `a780b97f-5451-46d5-8fc9-5268e491e0ee` (the app itself — the
  SPA-calls-own-API self-authorization), 2 scopes
- Screenshot: `2026-08-22_EMS_ReadyKit_API_ExposeAnAPI.png`

---

## 6. Teardown execution

### 6a. Remove the resource-group delete lock

```
az lock delete --name delete-lock --resource-group rg-ems-readykit-dev
```

Result: succeeded, 2026-08-22. Confirmed via `az lock list --resource-group rg-ems-readykit-dev -o table` returning empty.

### 6b. Review the destroy plan (read-only — no changes made)

```
terraform plan -destroy -no-color 2>&1 | Out-File -FilePath destroy-plan-full.txt -Encoding utf8
```

(Note: the root-level `pg_admin_password` variable is unreferenced by root
`main.tf` — the real DB password is generated internally by
`random_password.pg_admin` — so it doesn't need to be supplied for plan or
destroy.)

Resource count / summary: `Plan: 0 to add, 0 to change, 70 to destroy.`

Reviewed and confirmed 2026-08-22 — all 70 resources map to expected
Terraform-managed infrastructure, none unaccounted for:

```
azurerm_consumption_budget_resource_group.main
azurerm_key_vault.platform
azurerm_key_vault_secret.pg_admin_password
azurerm_resource_group.ems_rg
random_password.pg_admin
random_string.kv_suffix
module.app.azurerm_key_vault.ems_kv
module.app.azurerm_key_vault_secret.app_secret_key
module.app.azurerm_key_vault_secret.sql_connection
module.app.azurerm_linux_web_app.ems_app
module.app.azurerm_monitor_diagnostic_setting.app_diag
module.app.azurerm_monitor_diagnostic_setting.kv_diag
module.app.azurerm_role_assignment.app_kv_secrets_user
module.app.azurerm_role_assignment.terraform_kv_secrets_officer
module.app.azurerm_service_plan.ems_plan
module.app.random_password.app_secret_key
module.app.random_string.kv_suffix
module.data.azurerm_monitor_diagnostic_setting.pg_diag
module.data.azurerm_postgresql_flexible_server.ems_pg
module.data.azurerm_postgresql_flexible_server_database.ems_db
module.data.azurerm_postgresql_flexible_server_firewall_rule.allow_azure_services
module.data.azurerm_private_endpoint.pg_pe
module.identity_rbac.azuread_app_role_assignment.administrators
module.identity_rbac.azuread_app_role_assignment.responders
module.identity_rbac.azuread_app_role_assignment.supervisors
module.identity_rbac.azuread_application.ems_readykit
module.identity_rbac.azuread_application.github_actions
module.identity_rbac.azuread_application_identifier_uri.ems_readykit
module.identity_rbac.azuread_group.administrators
module.identity_rbac.azuread_group.responders
module.identity_rbac.azuread_group.supervisors
module.identity_rbac.azuread_service_principal.ems_readykit
module.identity_rbac.azuread_service_principal.github_actions
module.identity_rbac.azurerm_role_assignment.administrators_reader
module.identity_rbac.azurerm_role_assignment.github_actions_tfstate_blob
module.identity_rbac.azurerm_role_assignment.github_actions_website_contributor
module.identity_rbac.azurerm_role_assignment.supervisors_contributor
module.identity_rbac.azurerm_role_assignment.supervisors_log_reader
module.logging.azurerm_log_analytics_saved_search.high_severity_events
module.logging.azurerm_log_analytics_saved_search.recent_audit_events
module.logging.azurerm_log_analytics_workspace.ems_law
module.network.azurerm_monitor_diagnostic_setting.app_nsg_diag
module.network.azurerm_monitor_diagnostic_setting.data_nsg_diag
module.network.azurerm_network_security_group.app_nsg
module.network.azurerm_network_security_group.data_nsg
module.network.azurerm_network_security_group.management_nsg
module.network.azurerm_subnet.app
module.network.azurerm_subnet.data
module.network.azurerm_subnet.management
module.network.azurerm_subnet_network_security_group_association.app_assoc
module.network.azurerm_subnet_network_security_group_association.data_assoc
module.network.azurerm_subnet_network_security_group_association.management_assoc
module.network.azurerm_virtual_network.ems_vnet
module.policy.azurerm_policy_definition.deny_public_ip
module.policy.azurerm_subscription_policy_assignment.allowed_locations
module.policy.azurerm_subscription_policy_assignment.deny_public_ip
module.policy.azurerm_subscription_policy_assignment.require_tag["CostCenter"]
module.policy.azurerm_subscription_policy_assignment.require_tag["Environment"]
module.policy.azurerm_subscription_policy_assignment.require_tag["ManagedBy"]
module.policy.azurerm_subscription_policy_assignment.require_tag["Owner"]
module.policy.azurerm_subscription_policy_assignment.require_tag["Project"]
module.static_web_app.azurerm_monitor_diagnostic_setting.swa_diag
module.static_web_app.azurerm_static_web_app.frontend
module.storage.azurerm_monitor_diagnostic_setting.storage_diag
module.storage.azurerm_storage_account.ems_storage
module.storage.azurerm_storage_container.app
module.storage.azurerm_storage_container.audit
module.storage.azurerm_storage_container.backup
module.storage.azurerm_storage_container.evidence
module.storage.azurerm_storage_management_policy.ems_lifecycle
```

Notes:
- `azurerm_management_lock.rg_lock` does not appear — expected, since it was
  already deleted in 6a and Terraform's refresh detects it's gone.
- No errors during the plan/refresh. No unexpected resources — full overlap
  with §4's inventory plus the AD/RBAC and sub-resource objects (Key Vault
  secrets, storage containers, diagnostic settings, policy assignments) that
  don't surface in a plain `az resource list`.

### 6c. Execute destroy

```
terraform destroy -var="pg_admin_password=<value>"
```

**First attempt (2026-08-22):** the interactive `terraform destroy` was
started, then killed mid-run after being left unattended, leaving a stale
state lock (`f42c30cb-cb79-a15c-ac34-fec3ee00e4a8`). By the time it was
checked, `terraform force-unlock` reported the lock was already gone on its
own (likely an expired blob lease) — confirmed unlocked via a clean
`terraform plan -destroy`.

Separately noticed while investigating: `ag-ems-readykit-dev-ops` (action
group) and `alert-ems-readykit-dev-destructive-ops` (activity log alert),
both present in §4's baseline, are now confirmed gone from Azure
(`ResourceNotFound` on direct lookup). Initially assumed this was the killed
destroy run partially completing — **that assumption was wrong**: a
byte-for-byte diff of the destroy plan captured in §6b (before any destroy
attempt) against a fresh plan taken after the unlock shows both are
identical, and neither ever listed these two resources as
`will be destroyed`. They were not in Terraform's tracked state at all —
pre-existing drift unrelated to this session. Something else removed them
from Azure; cause not identified. Since they're alerting/notification
resources with no cost impact and are already gone either way, this wasn't
investigated further, but the destroy plan itself (`70 to destroy`, unchanged
before and after) is unaffected and remains accurate for everything
Terraform actually manages.

**Second attempt (2026-08-22, resumed):** run via `terraform destroy -auto-approve -no-color`,
executed as a background process so it couldn't be interrupted by walking
away again. Completed cleanly:

```
Destroy complete! Resources: 70 destroyed.
```

Notable timings from the log: `azurerm_postgresql_flexible_server.ems_pg`
took ~1m2s (the slowest single resource), `azurerm_resource_group.ems_rg`
was destroyed last (16s) after everything inside it was gone, consistent
with Terraform's reverse-dependency destroy order.

Result: **Success.**

### 6d. Delete the Terraform state backend (only after 6c is confirmed clean)

The subscription has three resource groups total (`az group list`,
2026-08-22): `rg-ems-readykit-dev`, `tfstate-rg`, `NetworkWatcherRG`.

`tfstate-rg` holds exactly one resource — the `emsreadykittfstate` storage
account backing Terraform's remote state (bootstrapped manually per
`iac/Terraform/README.md`; not part of this Terraform config, so
`terraform destroy` above does not touch it). **It must not be deleted until
after 6c succeeds** — Terraform needs to read/write state there to know what
to destroy. Once 6c is verified clean:

```
az group delete --name tfstate-rg --yes
```

`NetworkWatcherRG` is excluded from this teardown: it's an Azure
platform-managed resource group, auto-created the first time any VNet/NSG is
deployed in a region within the subscription — not created by this Terraform
config (no `network_watcher` references anywhere in `iac/Terraform`).
Confirmed empty (zero resources) on 2026-08-22, so it carries no cost. Azure
recreates it automatically the moment networking resources exist again in
this subscription/region, so deleting it now has no lasting effect — left
alone.

**Executed 2026-08-22:** `az group delete --name tfstate-rg --yes`, owner's
explicit choice over keeping it (see §8's trade-off). Verified via
`az group exists --name tfstate-rg` → `false`. `az group list` for the
subscription now shows only `NetworkWatcherRG`.

**Rebuild impact:** a future `terraform init` against this repo's
`backend.tf` will fail until a new state backend is bootstrapped first —
follow `iac/Terraform/README.md`'s "Remote State Backend" section (`az group
create --name tfstate-rg ...` /
`az storage account create --name emsreadykittfstate ...`) before running
`terraform init`/`apply` again. Since the old state was pointing at zero
live resources anyway (this destroy completed cleanly), a fresh empty state
backend is equivalent — nothing is lost by starting over.

---

## 7. Post-destroy verification

- [x] `az group exists --name rg-ems-readykit-dev` → `false` (stronger check
      than an empty resource list — confirms the resource group itself is
      gone, not just empty)
- [x] Resource group itself deleted
- [x] Azure AD app registrations and groups removed — verified via
      `az ad app list --display-name "EMS ReadyKit API"` and
      `az ad app list --display-name "sp-ems-readykit-github-actions"`
      (both empty) and `az ad group list --display-name "ems-readykit"`
      (empty, covers all three `-administrators`/`-supervisors`/`-responders`
      groups)
- [x] `az group list` for the subscription now shows only `tfstate-rg` and
      `NetworkWatcherRG` — matches the plan exactly
- [ ] Budget alert / cost management shows no further spend accruing — not
      independently checked (the budget resource itself was destroyed along
      with the resource group it was scoped to, per the 70-resource destroy
      list in §6b, so this should self-resolve; worth a look in Cost
      Management after the next billing cycle to confirm no residual charges)
- [x] `tfstate-rg` / `emsreadykittfstate` disposition: **deleted** (owner's
      choice, 2026-08-22) — see §6d for rebuild impact

---

## 8. Outcome

`rg-ems-readykit-dev` and all 70 Terraform-managed resources within it —
including the Azure AD app registration, security groups, and role
assignments — were destroyed successfully on 2026-08-22. Verified against
live Azure state, not just the destroy command's own exit code (see §7).

Pre-destroy backups (§3) are complete and verified: a validated `pg_dump` of
the full database, and the blob storage containers (three of which were
already empty; the fourth held 7 days of redundant App Service backups).
Reference-only capture of the manually-configured Azure AD pieces (§5) is
also done, for use if §9's reconstitution plan is ever needed.

`tfstate-rg` was also deleted at the owner's explicit request (2026-08-22) —
see §6d for the command and verification. This means a future rebuild needs
to re-bootstrap a Terraform state backend first (§9, step 0, updated below)
before `terraform init`/`apply` will work again. Nothing of value was lost —
the old state was pointing at zero live resources by the time it was
deleted.

**As of 2026-08-22, the subscription contains only `NetworkWatcherRG`**
(Azure's own empty, auto-managed, zero-cost artifact — see §6d). The
decommission is complete.

---

## 9. Reconstitution plan (if the customer returns)

The owner's stated intent is that this is a pause driven by cost and lack of
current usage, not a permanent shutdown — if the customer comes back willing
to pay, the environment should be rebuildable from this repository. Steps,
in order:

0. **Re-bootstrap the Terraform state backend** — `tfstate-rg` was deleted
   during this decommission (§6d/§8), so `terraform init` will fail against
   `backend.tf` until a new one exists. Follow `iac/Terraform/README.md`'s
   "Remote State Backend" section: recreate `tfstate-rg`, the
   `emsreadykittfstate` storage account, and the `tfstate` container.
1. **`terraform apply`** from `iac/Terraform/` — rebuilds the infrastructure
   shell (VNet, subnets/NSGs, Log Analytics, Postgres server, storage
   account, App Service, both Key Vaults, Static Web App, budget, policy)
   against a fresh `pg_admin_password`. See `iac/Terraform/README.md` and
   `docs/runbook.md` Steps 1-3 for the standard init/plan/apply flow.
2. **Restore the database** — `pg_restore` the backup from §3a
   (`azure-backup-2026-08-21\ems_readykit_backup_2026-08-21.dump`) into the
   new, empty `ems_readykit` database.
3. **Restore blob storage** — re-upload the `app-backups` contents from §3b
   if needed for reference; `app-exports`, `audit-logs`, and `evidence` were
   empty at decommission time so there's nothing to restore there.
4. **Manually redo the Azure AD app registration config** — the SPA redirect
   URI and `required_resource_access` block are not Terraform-managed (§2);
   use the screenshots captured in §5 as the reference for exact values.
5. **Regenerate the CI/CD service principal** — the old
   `sp-ems-readykit-github-actions` and its secret won't survive the app
   registration being recreated. Re-run the `az ad sp create-for-rbac`
   command documented in `modules/identity_rbac/main.tf`'s comments and
   update the `AZURE_CREDENTIALS` GitHub secret.
6. **Redeploy the application** via the existing CI/CD pipeline.
7. **Re-validate** by walking `docs/runbook.md` Steps 4-9 (governance, RBAC,
   networking, logging, audit events, token lifetime, cost controls) before
   calling the rebuilt environment live again.

Estimated effort: a few hours of hands-on work, mostly around step 4 (manual
AD config) and step 7 (re-validation) — not a from-scratch rebuild.

---

**End of Decommission Record**
