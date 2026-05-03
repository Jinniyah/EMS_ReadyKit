// modules/siem/main.tf
// Optional Security Onion VM deployed in the monitoring subnet.
// Disabled by default (count = 0). Enable via var.enable_siem = true.
//
// Security Onion is used solely to validate detection capability
// and demonstrate SIEM integration per ADR-003.
// It is NOT a production SOC replacement.

# ── NIC for Security Onion VM ─────────────────────────────────────────────────

resource "azurerm_network_interface" "siem_nic" {
  name                = "nic-siem-${var.name_prefix}"
  location            = var.location
  resource_group_name = var.resource_group_name
  tags                = var.tags

  ip_configuration {
    name                          = "siem-ipconfig"
    subnet_id                     = var.subnet_monitoring_id
    private_ip_address_allocation = "Dynamic"
    # No public IP — management via private/VPN only
  }
}

# ── Security Onion VM ─────────────────────────────────────────────────────────

resource "azurerm_linux_virtual_machine" "security_onion" {
  name                = "vm-siem-${var.name_prefix}"
  resource_group_name = var.resource_group_name
  location            = var.location
  size                = var.vm_size

  admin_username                  = var.admin_username
  admin_password                  = var.admin_password
  disable_password_authentication = false

  network_interface_ids = [azurerm_network_interface.siem_nic.id]

  os_disk {
    name                 = "osdisk-siem-${var.name_prefix}"
    caching              = "ReadWrite"
    storage_account_type = "Standard_LRS"
    disk_size_gb         = 100
  }

  # Ubuntu 22.04 LTS — Security Onion installs on top of Ubuntu
  source_image_reference {
    publisher = "Canonical"
    offer     = "0001-com-ubuntu-server-jammy"
    sku       = "22_04-lts-gen2"
    version   = "latest"
  }

  # Boot diagnostics — stored managed (no storage account needed)
  boot_diagnostics {}

  tags = var.tags
}

# ── Log Analytics Agent Extension ─────────────────────────────────────────────
# Forwards selected VM logs to Log Analytics alongside Security Onion data

resource "azurerm_virtual_machine_extension" "oms_agent" {
  name                 = "OmsAgentForLinux"
  virtual_machine_id   = azurerm_linux_virtual_machine.security_onion.id
  publisher            = "Microsoft.EnterpriseCloud.Monitoring"
  type                 = "OmsAgentForLinux"
  type_handler_version = "1.14"

  settings = jsonencode({
    workspaceId = var.log_analytics_workspace_id
  })

  tags = var.tags
}

# ── VM Diagnostic Settings ─────────────────────────────────────────────────────

resource "azurerm_monitor_diagnostic_setting" "siem_vm_diag" {
  name                       = "diag-vm-siem"
  target_resource_id         = azurerm_linux_virtual_machine.security_onion.id
  log_analytics_workspace_id = var.log_analytics_workspace_id

  metric {
    category = "AllMetrics"
    enabled  = true
  }
}
