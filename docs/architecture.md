flowchart TB
  %% ===== Identity =====
  User[End Users<br/>(Responder / Supervisor / Admin)]
  AAD[Azure AD<br/>Group‑based RBAC]

  User --> AAD

  %% ===== Azure Boundary =====
  subgraph Azure["Azure Tenant"]
    
    %% --- Management & Governance ---
    subgraph MG["Management Group"]
      Policy[Azure Policy<br/>Tags • Region • Deny Public IP]
      Budget[Azure Budget Alert]
    end

    %% --- Subscription ---
    subgraph Sub["Azure Subscription"]

      %% --- Networking ---
      subgraph Net["Virtual Network"]
        AppSubnet[App Subnet]
        DataSubnet[Data Subnet]
        MonSubnet[Monitoring Subnet]
      end

      %% --- Station Scope ---
      subgraph RG["Station Resource Group"]
        App[Web / API Application<br/>(Inventory & Readiness)]
        DB[Database<br/>(Stations, Vehicles, Inventory)]
        KV[Key Vault<br/>(Secrets)]
        Store[Storage Account<br/>(Exports / Artifacts)]
      end

      %% --- Observability ---
      Logs[Log Analytics Workspace]

      %% --- Optional SIEM ---
      SO[Security Onion VM<br/>(Optional SIEM)]

    end
  end

  %% ===== Auth & App Flow =====
  AAD --> App
  App --> DB
  App --> KV
  App --> Store

  %% ===== Logging & Monitoring =====
  App --> Logs
  Logs --> SO

  %% ===== Network Placement =====
  AppSubnet --> App
  DataSubnet --> DB
  MonSubnet --> SO