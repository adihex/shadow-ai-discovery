# Architecture & Design Document: Shadow AI Discovery Engine

This document details the engineering decisions, trade-offs, and scaling patterns for the **Shadow AI Discovery Engine** proof-of-concept.

---

## 🎯 Design Decisions & Rationale

### 1. Backend: Python + FastAPI
* **Why Python**: Google Cloud Client SDKs (`google-cloud-run`, `google-cloud-functions`, etc.) are natively supported and highly mature in Python.
* **Why FastAPI**: It offers asynchronous processing (essential for running multiple slow API scans in the background), type safety via Pydantic, and automatic Swagger documentation.

### 2. Database: SQLite + SQLModel
* **Why SQLite**: Self-contained and requires zero local configuration or external container management, matching the "lightweight POC" requirement perfectly.
* **Why SQLModel**: It unifies SQLAlchemy ORM and Pydantic validation into a single model, reducing schema duplication.

### 3. Frontend: Vite + React + Vanilla CSS
* **Why Vite**: High-performance dev server and instant hot-reloading.
* **Why Vanilla CSS**: To build a premium design system tailored around specific HSL colors, grid structures, glassmorphic glows, and transition animations without relying on boilerplate utility classes.
* **Why SVG Charts**: Custom inline SVG charts provide a high-performance visual dashboard with zero third-party package dependencies.

### 4. Double Scanning Mode (Real GCP vs. Mock Demo)
* The scanner dynamically checks if Google Application Default Credentials or Service Account variables are configured.
* If credentials exist, it queries the live GCP API; if not, it automatically runs in **Mock Demo Mode** with realistic simulated environments, making the application immediately runnable and reviewable in any environment.

---

## ⚖️ Trade-offs Made
* **In-Memory / Async Background Tasks**: We used FastAPI's built-in `BackgroundTasks` instead of Celery/Redis. This keeps the stack lightweight and simple but lacks progress state persistence across backend restarts.
* **Kubernetes Workload Scanning**: Listing GKE clusters is implemented via the SDK, but scanning actual container manifests requires in-cluster GKE workload discovery or direct Kubernetes API integration (using Workload Identity). This was omitted for simplicity in favor of a robust mock payload.

---

## 🚀 Scaling to Production & Thousands of GCP Projects
If this service were to scale to support an enterprise with thousands of Google Cloud projects, we would transition to the following architecture:

### 1. Event-Driven Inventory (Google Cloud Asset Inventory)
Instead of polling APIs in each project (which hits GCP API rate limits and is extremely slow), we would subscribe to **Google Cloud Asset Inventory (CAI)**.
* Configure a feed or export CAI data to a centralized **Pub/Sub** topic.
* Central backend receives real-time creation/update events for Cloud Run, Cloud Functions, and GKE.

### 2. Distributed Celery Workers
* Replace FastAPI background tasks with **Celery** or **GCP Cloud Tasks**.
* Use Redis or RabbitMQ as a message broker to queue scan tasks per project.

### 3. BigQuery or PostgreSQL Persistence
* Swap SQLite for **Cloud SQL (PostgreSQL)** for transactional metadata (inventory status, alert history).
* Export raw metadata and historical scan results to **BigQuery** to perform high-scale analytics.

### 4. IAM & Cross-Project Access
* Use a centralized **Service Account** with **Asset Viewer** (or custom security auditor roles) granted at the GCP **Organization** or **Folder** level, rather than managing service account keys for individual projects.
