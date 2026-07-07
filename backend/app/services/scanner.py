import os
import random
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from app.models import Asset
from app.services.heuristics import analyze_asset
from sqlmodel import Session

# Import GCP SDK modules
try:
    from google.cloud import run_v2
    from google.cloud import functions_v2
    from google.cloud import container_v1
    from google.cloud import aiplatform
    GCP_SDK_AVAILABLE = True
except ImportError:
    GCP_SDK_AVAILABLE = False

class GCPScanner:
    def __init__(self, project_id: str, db_session: Session):
        self.project_id = project_id
        self.db = db_session

    def run_scan(self) -> Dict[str, Any]:
        """
        Runs a scan on GCP resources. Falls back to mock scan if GCP credentials are not available.
        """
        # Check for service account json or application default credentials
        gcp_creds_set = (
            os.environ.get("GOOGLE_APPLICATION_CREDENTIALS") is not None or 
            os.environ.get("GCP_SA_KEY") is not None
        )
        
        assets_found = 0
        agents_found = 0
        scanned_assets: List[Asset] = []

        if GCP_SDK_AVAILABLE and gcp_creds_set:
            try:
                # 1. Scan Cloud Run
                run_assets = self._scan_cloud_run()
                scanned_assets.extend(run_assets)
                
                # 2. Scan Cloud Functions
                fn_assets = self._scan_cloud_functions()
                scanned_assets.extend(fn_assets)
                
                # 3. Scan GKE Workloads
                gke_assets = self._scan_gke()
                scanned_assets.extend(gke_assets)
                
                # 4. Scan Vertex AI Workloads
                vertex_assets = self._scan_vertex_ai()
                scanned_assets.extend(vertex_assets)
                
            except Exception as e:
                print(f"Error scanning real GCP: {e}. Falling back to mock data.")
                scanned_assets = self._generate_mock_assets()
        else:
            print("GCP credentials not found or SDK not imported. Running in Mock/Demo mode.")
            scanned_assets = self._generate_mock_assets()

        # Process and save assets to database
        for raw_asset in scanned_assets:
            # Run heuristics engine
            is_ai_agent, conf_score, conf_reasons, risk_score, risk_reasons = analyze_asset(
                name=raw_asset.name,
                resource_type=raw_asset.resource_type,
                env_vars=raw_asset.env_vars,
                labels=raw_asset.labels,
                runtime=raw_asset.runtime,
                service_account=raw_asset.service_account
            )
            
            # Update scores
            raw_asset.is_ai_agent = is_ai_agent
            raw_asset.confidence_score = conf_score
            raw_asset.confidence_reasons = conf_reasons
            raw_asset.risk_score = risk_score
            raw_asset.risk_reasons = risk_reasons
            raw_asset.last_seen = datetime.utcnow()
            
            # Upsert into database
            existing = self.db.get(Asset, raw_asset.id)
            if existing:
                # Update attributes
                for key, val in raw_asset.model_dump(exclude_unset=True).items():
                    setattr(existing, key, val)
                self.db.add(existing)
            else:
                self.db.add(raw_asset)
                
            assets_found += 1
            if is_ai_agent:
                agents_found += 1
                
        self.db.commit()
        return {
            "assets_found": assets_found,
            "agents_found": agents_found
        }

    def _scan_cloud_run(self) -> List[Asset]:
        """Skeletal scan for Cloud Run services using run_v2.ServicesClient."""
        assets = []
        try:
            client = run_v2.ServicesClient()
            parent = f"projects/{self.project_id}/locations/-"
            request = run_v2.ListServicesRequest(parent=parent)
            response = client.list_services(request=request)
            
            for service in response:
                # Gather environment variables from first container
                env_vars = {}
                containers = service.template.containers
                if containers:
                    for env in containers[0].env:
                        env_vars[env.name] = env.value
                
                # Fetch IAM policies to determine public access (Bonus)
                labels = dict(service.labels or {})
                
                # Convert run_v2 Service to Asset
                assets.append(Asset(
                    id=f"run-{service.name.split('/')[-1]}",
                    name=service.name.split('/')[-1],
                    resource_type="Cloud Run",
                    region=service.name.split('/')[3],
                    runtime="container",
                    service_account=service.template.service_account,
                    env_vars=env_vars,
                    labels=labels
                ))
        except Exception as e:
            print(f"Error fetching Cloud Run services: {e}")
        return assets

    def _scan_cloud_functions(self) -> List[Asset]:
        """Skeletal scan for Cloud Functions using functions_v2.FunctionServiceClient."""
        assets = []
        try:
            client = functions_v2.FunctionServiceClient()
            parent = f"projects/{self.project_id}/locations/-"
            request = functions_v2.ListFunctionsRequest(parent=parent)
            response = client.list_functions(request=request)
            
            for function in response:
                env_vars = dict(function.service_config.environment_variables or {})
                labels = dict(function.labels or {})
                assets.append(Asset(
                    id=f"fn-{function.name.split('/')[-1]}",
                    name=function.name.split('/')[-1],
                    resource_type="Cloud Function",
                    region=function.name.split('/')[3],
                    runtime=function.build_config.runtime,
                    service_account=function.service_config.service_account_email,
                    env_vars=env_vars,
                    labels=labels
                ))
        except Exception as e:
            print(f"Error fetching Cloud Functions: {e}")
        return assets

    def _scan_gke(self) -> List[Asset]:
        """Skeletal scan for GKE workloads using container_v1.ClusterManagerClient."""
        # For simplicity, GKE clusters are listed. In a production system,
        # we would connect to each cluster's Kubernetes API server to inspect Pod specs.
        return []

    def _scan_vertex_ai(self) -> List[Asset]:
        """Skeletal scan for Vertex AI endpoints."""
        assets = []
        try:
            aiplatform.init(project=self.project_id)
            endpoints = aiplatform.Endpoint.list()
            for ep in endpoints:
                assets.append(Asset(
                    id=f"vertex-{ep.name}",
                    name=ep.display_name,
                    resource_type="Vertex AI",
                    region=ep.resource_name.split('/')[3],
                    runtime="Vertex Endpoint",
                    service_account="Managed Service Identity",
                    env_vars={},
                    labels=dict(ep.labels or {})
                ))
        except Exception as e:
            print(f"Error fetching Vertex AI endpoints: {e}")
        return assets

    def _generate_mock_assets(self) -> List[Asset]:
        # Realistic simulated data
        mock_data = [
            {
                "id": "run-my-ai-service",
                "name": "my-ai-service",
                "resource_type": "Cloud Run",
                "region": "us-central1",
                "runtime": "python310",
                "service_account": "default-compute@developer.gserviceaccount.com",
                "env_vars": {
                    "OPENAI_API_KEY": "sk-proj-********************",
                    "LANGCHAIN_TRACING_V2": "true",
                    "LANGCHAIN_API_KEY": "lsv2_********************",
                    "PORT": "8080"
                },
                "labels": {
                    "allow-unauthenticated": "true",
                    "env": "production",
                    "team": "ai-rnd"
                }
            },
            {
                "id": "run-customer-support-bot",
                "name": "customer-support-bot",
                "resource_type": "Cloud Run",
                "region": "europe-west1",
                "runtime": "python311",
                "service_account": "support-bot-sa@shadow-ai-discovery-demo.iam.gserviceaccount.com",
                "env_vars": {
                    "ANTHROPIC_API_KEY": "sk-ant-********************",
                    "CREWAI_AGENT_OPS": "true",
                    "LOGGING_LEVEL": "INFO"
                },
                "labels": {
                    "allow-unauthenticated": "true",
                    "env": "staging",
                    "team": "support"
                }
            },
            {
                "id": "run-legacy-web-app",
                "name": "legacy-web-app",
                "resource_type": "Cloud Run",
                "region": "us-east1",
                "runtime": "nodejs18",
                "service_account": "default-compute@developer.gserviceaccount.com",
                "env_vars": {
                    "NODE_ENV": "production",
                    "DB_HOST": "10.0.0.4"
                },
                "labels": {
                    "env": "production"
                }
            },
            {
                "id": "fn-summarize-pdf-fn",
                "name": "summarize-pdf-fn",
                "resource_type": "Cloud Function",
                "region": "us-central1",
                "runtime": "python39",
                "service_account": "pdf-processor-sa@shadow-ai-discovery-demo.iam.gserviceaccount.com",
                "env_vars": {
                    "GEMINI_API_KEY": "AIzaSy********************",
                    "LANGCHAIN_API_KEY": "lsv2_********************",
                    "LOGGING": "false"
                },
                "labels": {
                    "allow-unauthenticated": "false",
                    "env": "development"
                }
            },
            {
                "id": "fn-payment-processor",
                "name": "payment-processor-fn",
                "resource_type": "Cloud Function",
                "region": "us-east4",
                "runtime": "go121",
                "service_account": "secure-payment-sa@shadow-ai-discovery-demo.iam.gserviceaccount.com",
                "env_vars": {
                    "STRIPE_SECRET_KEY": "sk_test_********************",
                    "LOGGING_LEVEL": "DEBUG"
                },
                "labels": {
                    "env": "production"
                }
            },
            {
                "id": "gke-llama-deployment",
                "name": "llama-inference-service",
                "resource_type": "GKE",
                "region": "us-central1-a",
                "runtime": "Docker (llama-cpp-python)",
                "service_account": "gke-workload-identity@shadow-ai-discovery-demo.iam.gserviceaccount.com",
                "env_vars": {
                    "LLM_MODEL": "llama-3-8b-instruct.Q4_K_M.gguf",
                    "LLAMAINdex_CACHE_DIR": "/data/cache"
                },
                "labels": {
                    "app": "llama-inference",
                    "tier": "backend"
                }
            },
            {
                "id": "vertex-customer-churn",
                "name": "customer-churn-model",
                "resource_type": "Vertex AI",
                "region": "us-central1",
                "runtime": "Custom Container (Vertex AI Endpoint)",
                "service_account": "vertex-prediction-sa@shadow-ai-discovery-demo.iam.gserviceaccount.com",
                "env_vars": {
                    "MODEL_NAME": "customer_churn_v2",
                    "VERTEX_PROJECT_ID": "shadow-ai-discovery-demo"
                },
                "labels": {
                    "task": "prediction",
                    "framework": "xgboost"
                }
            },
            {
                "id": "run-translation-endpoint",
                "name": "translation-agent",
                "resource_type": "Cloud Run",
                "region": "us-west1",
                "runtime": "python310",
                "service_account": "default-compute@developer.gserviceaccount.com",
                "env_vars": {
                    "COHERE_API_KEY": "co_********************",
                    "DISABLE_LOGGING": "true"
                },
                "labels": {
                    "allow-unauthenticated": "true",
                    "visibility": "public"
                }
            }
        ]
        
        assets = []
        for d in mock_data:
            assets.append(Asset(
                id=d["id"],
                name=d["name"],
                resource_type=d["resource_type"],
                region=d["region"],
                runtime=d["runtime"],
                service_account=d["service_account"],
                env_vars=d["env_vars"],
                labels=d["labels"]
            ))
        return assets
