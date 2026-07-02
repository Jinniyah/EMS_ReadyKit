# EMS ReadyKit — Evidence Directory

This directory holds the artifacts (diagrams, screenshots, exports, and UAT
records) collected as proof of EMS ReadyKit's architecture, deployment, and
correctness — used both for portfolio presentation and as a record of the
UAT (user acceptance testing) rollout.

EMS ReadyKit has been deployed to Azure and in **UAT with the real Newberg
Township EMS team since 2026-06-23** — it is not yet in production. Unlike a
throwaway demo environment, most of the evidence below documents a real
deployed system being exercised by real users, not a one-time validation
exercise.

The canonical, up-to-date list of what to capture, how to capture it, and
whether it's done lives in **[Portfolio_Evidence_Checklist.csv](Portfolio_Evidence_Checklist.csv)**
in this directory. That file is the source of truth for evidence status —
this README just explains how the directory is organized and what the
current architecture actually looks like, so captured evidence matches
reality.

---

## Directory Structure

```
evidence/
├── Portfolio_Evidence_Checklist.csv   — master checklist: what to capture, why, and current status
├── arch_and_design/                   — architecture diagrams, ERD, API surface, migration history
├── live_deployment/                   — screenshots of the deployed app + Azure Portal resource blades
├── uat/                                — completed UAT test case spreadsheets (Admin/Supervisor/Responder)
├── screenshots/                       — CI/CD, code quality, testing, and security evidence screenshots
└── logs/                              — exported test output, coverage reports, and audit log samples
```

`arch_and_design/` and `live_deployment/` are already populated (see the
checklist's ARCH-01–05 and LIVE-01–09 rows, both marked Complete).
`screenshots/` and `logs/` are intentionally still empty — they correspond to
the CI/CD, code quality, testing, and security checklist rows, which remain
open.

---

## Current Architecture (what evidence should reflect)

EMS ReadyKit runs as a single-region application on Azure:

- **Azure Static Web Apps** — React 18 PWA frontend, free tier
- **Azure App Service (B1)** — FastAPI backend, always-on, VNet-integrated (outbound)
- **Azure Database for PostgreSQL Flexible Server** — primary datastore
- **Azure Key Vault** — database credentials and secrets, accessed via managed identity
- **Log Analytics Workspace** — structured application logs, audit events, and NSG flow logs
- **Azure AD (Entra ID)** — identity provider issuing RS256 JWTs. The global role (Administrator / Supervisor / Responder) comes from real Azure AD app-role assignments via three matching security groups (`ems-readykit-administrators`/`-supervisors`/`-responders`); *which station* a person belongs to is a separate, purely application-layer concern (the `StationMember` table) with no Azure AD equivalent

The VNet, 3 subnets, and NSGs (deny-all-inbound baseline) are real, deployed
infrastructure — not placeholders. App Service VNet integration is active on
the current B1 SKU. What's *not* yet active is full private database
connectivity: a private endpoint for PostgreSQL exists in the data subnet,
but the server still permits public access via its "Allow Azure Services"
firewall rule, since no private DNS zone override has been added yet. So NSG
and RBAC-group screenshots (SEC-01, ARCH-04) are legitimate evidence to
capture — it's specifically the *private-endpoint-only* database connection
that's still pending, tracked alongside the related Azure Firewall work in
the backlog (I-1). See `iac/Terraform/README.md`'s Networking section for
the exact remaining steps.

See `docs/architecture.md` for the full diagram and `docs/adr/` for the
decision records behind these choices.

---

## How to Capture

### Screenshots (`screenshots/` and `live_deployment/`)

Use the Azure Portal's built-in screenshot tool or your OS's. Crop to the
relevant pane. Match filenames to the Evidence ID in
`Portfolio_Evidence_Checklist.csv` (e.g. `LIVE-06_app_service_overview.png`)
so it's obvious which checklist row each file satisfies.

### Test / coverage / audit output (`logs/`)

Run the relevant command locally (`pytest`, `npm test`, `pip-audit`, coverage
export) and save the console output or exported file here, again named after
the corresponding Evidence ID.

### After capture

Update the **Status** column for the corresponding row in
`Portfolio_Evidence_Checklist.csv` rather than tracking completion anywhere
else — that file is the single source of truth for what's done.
