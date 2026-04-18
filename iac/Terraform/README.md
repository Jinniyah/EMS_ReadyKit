# Terraform Infrastructure – EMS ReadyKit

This directory contains the **Infrastructure‑as‑Code (IaC)** for the **EMS ReadyKit** project.

All infrastructure is provisioned using **Terraform** and is designed to be:
- Reproducible
- Reviewable
- Secure by default
- Cost‑controlled
- Easily destroyed

This is a **non‑production demonstration environment** intended for learning, portfolio review, and architectural validation.

---

## What This Terraform Code Provisions

At a high level, this Terraform configuration provisions:

- Azure governance primitives (Policy, RBAC)
- Secure networking baseline (VNet, subnets, NSGs)
- Centralized logging (Log Analytics)
- Application hosting platform
- Datastore and supporting storage
- Optional SIEM environment (Security Onion VM)

All resources are deployed into **a single Azure region** and are scoped to a **single station resource group**.

---

## What This Terraform Code Does *Not* Do

This repository intentionally does **not**:

- Create microservices or distributed infrastructure
- Provision per‑vehicle infrastructure
- Deploy patient, PHI, or clinical systems
- Claim production readiness or regulatory compliance

These exclusions are **intentional architectural decisions** documented in the ADRs.

---

## Repository Structure

```text
iac/terraform/
├── backend.tf          # Remote state configuration (no secrets)
├── providers.tf        # Terraform & Azure providers
├── main.tf             # Root module wiring
├── variables.tf        # Root‑level inputs
├── outputs.tf          # Root‑level outputs
├── README.md           # This file
└── modules/            # Reusable Terraform modules
    ├── network/
    ├── identity_rbac/
    ├── policy/
    ├── logging/
    ├── app/
    ├── data/
    ├── storage/
    └── siem/           # Optional (disabled by default)
```

Each module has its own `README.md` describing its responsibility and inputs.

---

## Architectural Alignment

This Terraform layout aligns directly with the documented architecture and ADRs:

- **ADR‑001** – Overall System Architecture
- **ADR‑002** – Role‑Based Access Control Model
- **ADR‑003** – Logging and Audit Strategy
- **ADR‑004** – Terraform Module Structure

Reviewers are encouraged to read the ADRs before inspecting module implementations.

---

## Deployment Model

- One Terraform root per environment
- All configuration managed via variables
- No secrets committed to source control
- Azure Key Vault used for runtime secrets

Infrastructure is treated as **disposable lab infrastructure**.

---

## Typical Workflow

```bash
terraform init
terraform plan
terraform apply
```

Validation activities are performed after deployment (see runbook).

To tear down the environment:

```bash
terraform destroy
```

---

## Cost & Safety Notes

- Designed to run for **$30–$70/month** depending on usage
- Budget alerts are configured to prevent runaway spend
- Optional SIEM VM is the primary cost driver and should be stopped when idle
- Short log retention is used by default

Destroy resources when not actively validating detections or features.

---

## Security Notes

- Group‑based Azure AD RBAC only (no user‑level assignments)
- No public IPs by default
- Network Security Groups enforce least‑privilege traffic flows
- High‑risk events are explicitly logged and auditable

---

## Disclaimer

This Terraform configuration is:
- A **technical demonstration**
- Not production hardened
- Not certified for regulatory compliance

It exists solely to demonstrate cloud engineering judgment, not to replace operational EMS systems.

---

**See `docs/runbook.md` for deployment validation steps.**
