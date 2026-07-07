output "scanner_service_account_email" {
  description = "Service account the Shadow AI Discovery backend should authenticate as."
  value       = google_service_account.scanner.email
}

output "ai_agent_demo_url" {
  description = "URL of the demo workload flagged as a likely AI agent."
  value       = google_cloud_run_v2_service.ai_agent_demo.uri
}

output "control_service_url" {
  description = "URL of the demo workload with no AI indicators (control)."
  value       = google_cloud_run_v2_service.control_service.uri
}
