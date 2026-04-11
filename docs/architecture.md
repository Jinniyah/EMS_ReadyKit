# EMS ReadyKit – Architecture Overview

```mermaid
flowchart TB
    User[Responders / Supervisors / Admins]
    AAD[Azure Active Directory<br/>Group-Based RBAC]

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