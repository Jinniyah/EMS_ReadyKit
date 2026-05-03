// modules/network/main.tf
// VNet, subnets, NSGs with restrictive rules, route table,
// and NSG diagnostic settings routing flow logs to Log Analytics.

resource "azurerm_virtual_network" "ems_vnet" {
  name                = "vnet-ems-readykit"
  location            = var.location
  resource_group_name = var.resource_group_name
  address_space       = ["10.10.0.0/16"]
  tags                = var.tags
}

# ── Subnets ───────────────────────────────────────────────────────────────────

resource "azurerm_subnet" "app" {
  name                 = "snet-app"
  resource_group_name  = var.resource_group_name
  virtual_network_name = azurerm_virtual_network.ems_vnet.name
  address_prefixes     = ["10.10.1.0/24"]

  delegation {
    name = "appservice-delegation"
    service_delegation {
      name    = "Microsoft.Web/serverFarms"
      actions = ["Microsoft.Network/virtualNetworks/subnets/action"]
    }
  }
}

resource "azurerm_subnet" "data" {
  name                 = "snet-data"
  resource_group_name  = var.resource_group_name
  virtual_network_name = azurerm_virtual_network.ems_vnet.name
  address_prefixes     = ["10.10.2.0/24"]
}

resource "azurerm_subnet" "management" {
  name                 = "snet-management"
  resource_group_name  = var.resource_group_name
  virtual_network_name = azurerm_virtual_network.ems_vnet.name
  address_prefixes     = ["10.10.3.0/24"]
}

# ── NSGs ──────────────────────────────────────────────────────────────────────

resource "azurerm_network_security_group" "app_nsg" {
  name                = "nsg-app"
  location            = var.location
  resource_group_name = var.resource_group_name
  tags                = var.tags

  # Allow inbound HTTPS from the internet (App Service public endpoint)
  security_rule {
    name                       = "Allow-HTTPS-Inbound"
    priority                   = 100
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "443"
    source_address_prefix      = "Internet"
    destination_address_prefix = "*"
  }

  # Allow App Service infrastructure tags
  security_rule {
    name                       = "Allow-AppServiceManagement"
    priority                   = 110
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "454-455"
    source_address_prefix      = "AppServiceManagement"
    destination_address_prefix = "*"
  }

  # Deny all other inbound
  security_rule {
    name                       = "Deny-All-Inbound"
    priority                   = 4096
    direction                  = "Inbound"
    access                     = "Deny"
    protocol                   = "*"
    source_port_range          = "*"
    destination_port_range     = "*"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }
}

resource "azurerm_network_security_group" "data_nsg" {
  name                = "nsg-data"
  location            = var.location
  resource_group_name = var.resource_group_name
  tags                = var.tags

  # Allow SQL from app subnet only
  security_rule {
    name                       = "Allow-SQL-From-App"
    priority                   = 100
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "1433"
    source_address_prefix      = "10.10.1.0/24"
    destination_address_prefix = "*"
  }

  # Deny all other inbound
  security_rule {
    name                       = "Deny-All-Inbound"
    priority                   = 4096
    direction                  = "Inbound"
    access                     = "Deny"
    protocol                   = "*"
    source_port_range          = "*"
    destination_port_range     = "*"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }
}

resource "azurerm_network_security_group" "management_nsg" {
  name                = "nsg-management"
  location            = var.location
  resource_group_name = var.resource_group_name
  tags                = var.tags

  # Allow SSH from RFC1918 only (no public SSH)
  security_rule {
    name                       = "Allow-SSH-Internal"
    priority                   = 100
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "22"
    source_address_prefixes    = ["10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"]
    destination_address_prefix = "*"
  }

  # Deny all other inbound
  security_rule {
    name                       = "Deny-All-Inbound"
    priority                   = 4096
    direction                  = "Inbound"
    access                     = "Deny"
    protocol                   = "*"
    source_port_range          = "*"
    destination_port_range     = "*"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }
}

# ── NSG → Subnet associations ─────────────────────────────────────────────────

resource "azurerm_subnet_network_security_group_association" "app_assoc" {
  subnet_id                 = azurerm_subnet.app.id
  network_security_group_id = azurerm_network_security_group.app_nsg.id
}

resource "azurerm_subnet_network_security_group_association" "data_assoc" {
  subnet_id                 = azurerm_subnet.data.id
  network_security_group_id = azurerm_network_security_group.data_nsg.id
}

resource "azurerm_subnet_network_security_group_association" "management_assoc" {
  subnet_id                 = azurerm_subnet.management.id
  network_security_group_id = azurerm_network_security_group.management_nsg.id
}

# ── Route table ───────────────────────────────────────────────────────────────

resource "azurerm_route_table" "ems_rt" {
  name                = "rt-ems-readykit"
  location            = var.location
  resource_group_name = var.resource_group_name
  tags                = var.tags
}

resource "azurerm_subnet_route_table_association" "app_rt_assoc" {
  subnet_id      = azurerm_subnet.app.id
  route_table_id = azurerm_route_table.ems_rt.id
}

resource "azurerm_subnet_route_table_association" "data_rt_assoc" {
  subnet_id      = azurerm_subnet.data.id
  route_table_id = azurerm_route_table.ems_rt.id
}

resource "azurerm_subnet_route_table_association" "management_rt_assoc" {
  subnet_id      = azurerm_subnet.management.id
  route_table_id = azurerm_route_table.ems_rt.id
}

# ── NSG Diagnostic Settings → Log Analytics ───────────────────────────────────

resource "azurerm_monitor_diagnostic_setting" "app_nsg_diag" {
  name                       = "diag-nsg-app"
  target_resource_id         = azurerm_network_security_group.app_nsg.id
  log_analytics_workspace_id = var.log_analytics_workspace_id

  enabled_log {
    category = "NetworkSecurityGroupEvent"
  }

  enabled_log {
    category = "NetworkSecurityGroupRuleCounter"
  }
}

resource "azurerm_monitor_diagnostic_setting" "data_nsg_diag" {
  name                       = "diag-nsg-data"
  target_resource_id         = azurerm_network_security_group.data_nsg.id
  log_analytics_workspace_id = var.log_analytics_workspace_id

  enabled_log {
    category = "NetworkSecurityGroupEvent"
  }

  enabled_log {
    category = "NetworkSecurityGroupRuleCounter"
  }
}
