terraform {
  required_version = ">= 1.5"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# --- APIs ---------------------------------------------------------------

resource "google_project_service" "run" {
  project            = var.project_id
  service            = "run.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "iam" {
  project            = var.project_id
  service            = "iam.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "artifact_registry" {
  project            = var.project_id
  service            = "artifactregistry.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "resource_manager" {
  project            = var.project_id
  service            = "cloudresourcemanager.googleapis.com"
  disable_on_destroy = false
}

# --- Scanner service account ---------------------------------------------
# Read-only identity the Shadow AI Discovery Engine backend authenticates as.
# Scoped to viewer-only roles so a compromised scanner credential cannot
# modify or delete any cloud resource.

resource "google_service_account" "scanner" {
  project      = var.project_id
  account_id   = "shadow-ai-scanner"
  display_name = "Shadow AI Discovery Scanner (read-only)"
  depends_on   = [google_project_service.iam]
}

resource "google_project_iam_member" "scanner_run_viewer" {
  project = var.project_id
  role    = "roles/run.viewer"
  member  = "serviceAccount:${google_service_account.scanner.email}"
}

resource "google_project_iam_member" "scanner_iam_security_reviewer" {
  project = var.project_id
  role    = "roles/iam.securityReviewer"
  member  = "serviceAccount:${google_service_account.scanner.email}"
}

resource "google_project_iam_member" "scanner_browser" {
  project = var.project_id
  role    = "roles/browser"
  member  = "serviceAccount:${google_service_account.scanner.email}"
}

# --- Demo workloads --------------------------------------------------------
# Both use Google's public Cloud Run quickstart "hello" image (no build/push
# needed, no cost beyond the always-free tier). The only difference the
# scanner should key off of is naming + env vars + IAM policy, mirroring
# how a real "shadow" AI workload would look next to an ordinary service.

resource "google_cloud_run_v2_service" "ai_agent_demo" {
  name                = "langgraph-agent-demo"
  project             = var.project_id
  location            = var.region
  deletion_protection = false
  ingress             = "INGRESS_TRAFFIC_ALL"

  template {
    scaling {
      min_instance_count = 0
      max_instance_count = 1
    }
    containers {
      image = "us-docker.pkg.dev/cloudrun/container/hello"
      env {
        name  = "OPENAI_API_KEY"
        value = "sk-demo-0000000000000000000000000000"
      }
      env {
        name  = "LANGCHAIN_TRACING_V2"
        value = "true"
      }
      env {
        name  = "LLM_MODEL"
        value = "gpt-4o"
      }
      resources {
        limits = {
          cpu    = "1"
          memory = "512Mi"
        }
      }
    }
  }

  depends_on = [google_project_service.run]
}

# Public invoker binding so the scanner's IAM-policy read demonstrates a
# real allUsers finding (feeds the "public endpoint" risk-score rule).
resource "google_cloud_run_v2_service_iam_member" "ai_agent_demo_public" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.ai_agent_demo.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

resource "google_cloud_run_v2_service" "control_service" {
  name                = "internal-api-service"
  project             = var.project_id
  location            = var.region
  deletion_protection = false
  ingress             = "INGRESS_TRAFFIC_ALL"

  template {
    scaling {
      min_instance_count = 0
      max_instance_count = 1
    }
    containers {
      image = "us-docker.pkg.dev/cloudrun/container/hello"
      env {
        name  = "SERVICE_TIER"
        value = "internal"
      }
      resources {
        limits = {
          cpu    = "1"
          memory = "512Mi"
        }
      }
    }
  }

  depends_on = [google_project_service.run]
}
# control_service is intentionally left private (no allUsers binding).
