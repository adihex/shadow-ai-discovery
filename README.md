# 🛡️ Shadow AI Discovery Engine

A lightweight governance platform designed to scan, inventory, and assess AI-enabled workloads (Shadow AI Agents) running inside Google Cloud Platform (GCP) projects.

---

## ✨ Features
* **Multi-Resource Scanning**: Detects workloads across Cloud Run, Cloud Functions, GKE, and Vertex AI.
* **Heuristics Scoring Engine**: Evaluates environment variables, resource naming patterns, and IAM permissions to assign a **Confidence Score (0-100%)** of whether a workload is an autonomous AI agent.
* **Risk Profiling (Bonus 3)**: Computes a compound **Risk Score (0-100%)** assessing security vulnerability (public ingress, default/admin identity permissions, external API communication).
* **Architecture Flow Diagram (Bonus 2)**: Renders a reactive relationship visualization showing the workload's flow (`Resource -> IAM Service Account -> AI Service`).
* **Zero-Setup Demo Mode**: Automatically detects if live GCP credentials are not set and falls back to a highly realistic mock discovery catalog, making the dashboard fully functional out-of-the-box.

---

## 🛠️ Tech Stack
* **Backend**: Python, FastAPI, SQLModel (SQLAlchemy + Pydantic), SQLite.
* **Frontend**: React, TypeScript, Vite, Vanilla CSS (custom glassmorphic theme).
* **API Specs**: Automatic Swagger docs (`http://localhost:8000/docs`).

---

## 📁 Project Structure
```
shadow-ai-discovery/
├── backend/
│   ├── app/
│   │   ├── config.py            # Settings and prefixes
│   │   ├── database.py          # SQLite engine & sessions
│   │   ├── main.py              # FastAPI app
│   │   ├── models.py            # SQLModel schemas
│   │   ├── routes/              # Endpoints (assets, agents, scans)
│   │   └── services/            # Core logic (scanner, heuristics)
│   ├── requirements.txt
│   └── database.db              # Local SQLite database
├── frontend/
│   ├── src/
│   │   ├── services/api.ts      # REST API client
│   │   ├── styles/index.css     # Design system & CSS properties
│   │   ├── App.tsx              # Dashboard interface
│   │   └── main.tsx
│   ├── package.json
│   └── vite.config.ts
├── ARCHITECTURE.md              # Engineering decisions & scaling docs
└── README.md                    # Setup & user guide
```

---

## 🚀 Setup & Installation

### Prerequisite
* Python 3.10+
* Node.js 18+

### Step 1: Clone the Repository & Start the Backend
1. Open a terminal and navigate to the backend directory:
   ```bash
   cd backend
   ```
2. Create and sync the Python virtual environment:
   ```bash
   uv sync
   ```
3. Start the FastAPI development server:
   ```bash
   uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```
The backend API is now running at `http://localhost:8000`. You can explore the interactive API docs at `http://localhost:8000/docs`.

### Step 2: Start the Frontend Dashboard
1. Open a separate terminal and navigate to the frontend directory:
   ```bash
   cd frontend
   ```
2. Install npm packages:
   ```bash
   npm install
   ```
3. Run the Vite development server:
   ```bash
   npm run dev
   ```
The dashboard interface will be available at `http://localhost:5173`. Open it in your web browser.

---

## 📡 REST API Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| **GET** | `/api/assets` | Retrieve all scanned GCP workloads |
| **GET** | `/api/agents` | Retrieve only workloads classified as AI Agents |
| **GET** | `/api/agents/{id}` | Retrieve details of a specific AI Agent workload |
| **POST** | `/api/scan` | Trigger a new asynchronous project discovery scan |
| **GET** | `/api/scan/history` | Retrieve history and stats of all scans |

---

## 🔑 GCP Service Account Integration (Optional)
To query live resources instead of using Demo Mode:
1. Provide a Service Account with **Viewer** and **Cloud Run Viewer** roles on the target GCP project.
2. Export the path to the Service Account JSON key:
   ```bash
   export GOOGLE_APPLICATION_CREDENTIALS="/path/to/key.json"
   ```
3. Set your project ID environment variable:
   ```bash
   export SHADOW_AI_GCP_PROJECT_ID="your-project-id"
   ```
4. Re-run the backend server and trigger a scan.
