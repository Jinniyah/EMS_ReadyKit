# EMS ReadyKit – Architecture Overview

This document describes the high‑level architecture for **EMS ReadyKit**, a non‑production,
cloud‑native inventory and vehicle readiness platform.

The design emphasizes:
- Simplicity
- Security by default
- Centralized observability
- Cost discipline
- Clear operational boundaries

---

## High‑Level Architecture

```mermaid
flowchart TB
    User[Responders / Supervisors / Administrators]
    AAD[Azure Active Directory<br/>Group‑Based RBAC]

    User --> AAD

    subgraph Azure
        subgraph Subscription

            subgraph VNet
                AppSubnet[App Subnet]
                DataSubnet[Data Subnet]
                MonSubnet[Monitoring Subnet]
            end

            subgraph StationRG
                App[Web / API Application]
                DB[(Primary Database)]
                KV[Key Vault]
                Store[Blob Storage]
            end

            Logs[Log Analytics Workspace]
            SIEM["Security Onion VM (Optional)"]
        end
    end

    AAD --> App
    App --> DB
    App --> KV
    App --> Store
    App --> Logs
    Logs --> SIEM

    AppSubnet --> App
    DataSubnet --> DB
    MonSubnet --> SIEM
```

---

## Networking Notes

The default SKU is **F1 (free tier)**, which does not support VNet integration.
On F1, the App Service reaches Azure SQL over the public internet via an
Azure-services firewall rule. The VNet, subnets, and private endpoint are
provisioned and ready — upgrading to B1+ and enabling VNet integration requires
only a SKU change and adding a Private DNS Zone for `privatelink.database.windows.net`.

See [ADR-001](../adr/ADR-001-Architecture.md) for the full architecture rationale
and [ADR-004](../adr/ADR-004-Terraform-Module-Structure.md) for the IaC structure.
