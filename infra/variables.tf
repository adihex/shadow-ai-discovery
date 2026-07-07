variable "project_id" {
  description = "GCP project to deploy the Shadow AI Discovery demo resources into."
  type        = string
  default     = "shadow-ai-agent-501704"
}

variable "region" {
  description = "Region for the demo Cloud Run services."
  type        = string
  default     = "us-central1"
}
