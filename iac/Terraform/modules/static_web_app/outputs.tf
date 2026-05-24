// modules/static_web_app/outputs.tf

output "hostname" {
  description = "Default hostname of the Static Web App (e.g. gentle-river-abc123.azurestaticapps.net)"
  value       = azurerm_static_web_app.frontend.default_host_name
}

output "url" {
  description = "Full HTTPS URL of the Static Web App"
  value       = "https://${azurerm_static_web_app.frontend.default_host_name}"
}

output "api_key" {
  description = "Deployment token for GitHub Actions. Store as AZURE_STATIC_WEB_APPS_API_TOKEN GitHub secret. Sensitive — never log."
  value       = azurerm_static_web_app.frontend.api_key
  sensitive   = true
}

output "static_web_app_id" {
  description = "Resource ID of the Static Web App"
  value       = azurerm_static_web_app.frontend.id
}
