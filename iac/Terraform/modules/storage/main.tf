// modules/storage/main.tf
// Blob storage for exports, attachments, audit artifacts, and App Service backups.
// HTTPS-only, private containers, lifecycle policy, diagnostic logging.

resource "azurerm_storage_account" "ems_storage" {
  name                     = var.storage_account_name
  resource_group_name      = var.resource_group_name
  location                 = var.location
  account_tier             = "Standard"
  account_replication_type = "LRS"

  https_traffic_only_enabled      = true
  min_tls_version                 = "TLS1_2"
  allow_nested_items_to_be_public = false

  blob_properties {
    delete_retention_policy {
      days = 7
    }
  }

  tags = var.tags
}

# ── Containers ────────────────────────────────────────────────────────────────

resource "azurerm_storage_container" "app" {
  name                  = "app-exports"
  storage_account_name  = azurerm_storage_account.ems_storage.name
  container_access_type = "private"
}

resource "azurerm_storage_container" "audit" {
  name                  = "audit-logs"
  storage_account_name  = azurerm_storage_account.ems_storage.name
  container_access_type = "private"
}

resource "azurerm_storage_container" "evidence" {
  name                  = "evidence"
  storage_account_name  = azurerm_storage_account.ems_storage.name
  container_access_type = "private"
}

# Dedicated container for App Service backup files
resource "azurerm_storage_container" "backup" {
  name                  = "app-backups"
  storage_account_name  = azurerm_storage_account.ems_storage.name
  container_access_type = "private"
}

# ── App Service backup SAS token ──────────────────────────────────────────────
# App Service backup requires a SAS URL with rwdl permissions on the container.
# The token is valid for 10 years (Azure's practical maximum for this use case).

data "azurerm_storage_account_sas" "backup" {
  connection_string = azurerm_storage_account.ems_storage.primary_connection_string
  https_only        = true

  resource_types {
    service   = false
    container = true
    object    = true
  }

  services {
    blob  = true
    queue = false
    table = false
    file  = false
  }

  start  = "2026-01-01T00:00:00Z"
  expiry = "2036-01-01T00:00:00Z"

  permissions {
    read    = true
    write   = true
    delete  = true
    list    = true
    add     = true
    create  = true
    update  = false
    process = false
    tag     = false
    filter  = false
  }
}

# ── Lifecycle Management Policy ────────────────────────────────────────────────

resource "azurerm_storage_management_policy" "ems_lifecycle" {
  storage_account_id = azurerm_storage_account.ems_storage.id

  rule {
    name    = "expire-app-exports"
    enabled = true

    filters {
      prefix_match = ["app-exports/"]
      blob_types   = ["blockBlob"]
    }

    actions {
      base_blob {
        delete_after_days_since_modification_greater_than = 90
      }
    }
  }

  rule {
    name    = "tier-audit-logs"
    enabled = true

    filters {
      prefix_match = ["audit-logs/"]
      blob_types   = ["blockBlob"]
    }

    actions {
      base_blob {
        tier_to_cool_after_days_since_modification_greater_than = 30
        delete_after_days_since_modification_greater_than       = 365
      }
    }
  }

  rule {
    name    = "expire-old-backups"
    enabled = true

    filters {
      prefix_match = ["app-backups/"]
      blob_types   = ["blockBlob"]
    }

    actions {
      base_blob {
        delete_after_days_since_modification_greater_than = 30
      }
    }
  }
}

# ── Diagnostic Settings → Log Analytics ───────────────────────────────────────

resource "azurerm_monitor_diagnostic_setting" "storage_diag" {
  name                       = "diag-storage"
  target_resource_id         = "${azurerm_storage_account.ems_storage.id}/blobServices/default"
  log_analytics_workspace_id = var.log_analytics_workspace_id

  enabled_log {
    category = "StorageRead"
  }

  enabled_log {
    category = "StorageWrite"
  }

  enabled_log {
    category = "StorageDelete"
  }

  metric {
    category = "Transaction"
    enabled  = true
  }
}
