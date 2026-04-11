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

    subgraph Azure["Azure Tenant"]
        subgraph Subscription["Azure Subscription"]

            subgraph VNet["Virtual Network"]
                AppSubnet[App Subnet]
                DataSubnet[Data Subnet]
                MonSubnet[Monitoring Subnet]
            end

            subgraph StationRG["Station Resource Group"]
                App[Web / API Application]
                DB[(Primary Database)]
                KV[Key Vault]
                Store[Blob Storage]
            end

            Logs[Log Analytics Workspace]
            SIEM[Security Onion VM<br/>(Optional)]
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