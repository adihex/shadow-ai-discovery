import base64
import os
import re
import tempfile
from typing import List, Dict, Any, Optional
from app.models import Asset, utc_now
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

# Env var keys that look like credentials get their values masked before
# persistence — the inventory only needs to know the key exists.
SENSITIVE_ENV_KEY = re.compile(
    r"(KEY|SECRET|TOKEN|PASSWORD|PASSWD|CREDENTIAL|AUTH)", re.IGNORECASE
)

# Namespaces whose workloads are GKE system components, not user workloads.
GKE_SYSTEM_NAMESPACES = {
    "kube-system",
    "kube-public",
    "kube-node-lease",
    "gmp-system",
    "gmp-public",
    "config-management-system",
    "gatekeeper-system",
}


def redact_env_vars(env_vars: Dict[str, str]) -> Dict[str, str]:
    """Mask values of credential-looking env vars, keeping a short prefix."""
    redacted = {}
    for key, value in env_vars.items():
        value = "" if value is None else str(value)
        if value and SENSITIVE_ENV_KEY.search(key):
            prefix = value[:4] if len(value) > 12 else ""
            redacted[key] = f"{prefix}{'*' * 20}"
        else:
            redacted[key] = value
    return redacted


class GCPScanner:
    def __init__(self, project_id: str, db_session: Session):
        self.project_id = project_id
        self.db = db_session
        # Per-asset ingress hints gathered from IAM policies during scanning.
        # True/False = verified via IAM; absent = unknown (heuristics fall
        # back to labels/naming).
        self._public_hints: Dict[str, bool] = {}

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
        self._public_hints = {}

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
            # Run heuristics on the raw metadata so value-based indicators
            # still fire, then redact before anything is persisted.
            is_ai_agent, conf_score, conf_reasons, risk_score, risk_reasons = analyze_asset(
                name=raw_asset.name,
                resource_type=raw_asset.resource_type,
                env_vars=raw_asset.env_vars,
                labels=raw_asset.labels,
                runtime=raw_asset.runtime,
                service_account=raw_asset.service_account,
                is_public=self._public_hints.get(raw_asset.id)
            )

            # Update scores
            raw_asset.env_vars = redact_env_vars(raw_asset.env_vars)
            raw_asset.is_ai_agent = is_ai_agent
            raw_asset.confidence_score = conf_score
            raw_asset.confidence_reasons = conf_reasons
            raw_asset.risk_score = risk_score
            raw_asset.risk_reasons = risk_reasons
            raw_asset.last_seen = utc_now()

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
        """Scan Cloud Run services using run_v2.ServicesClient."""
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

                labels = dict(service.labels or {})
                asset_id = f"run-{service.name.split('/')[-1]}"

                # Check the service's IAM policy for an allUsers invoker
                # binding — labels cannot carry IAM state, so this is the
                # only reliable public-ingress signal.
                try:
                    policy = client.get_iam_policy(request={"resource": service.name})
                    self._public_hints[asset_id] = any(
                        binding.role == "roles/run.invoker"
                        and any(m in ("allUsers", "allAuthenticatedUsers") for m in binding.members)
                        for binding in policy.bindings
                    )
                except Exception as e:
                    print(f"Could not read IAM policy for {service.name}: {e}")

                # Convert run_v2 Service to Asset
                assets.append(Asset(
                    id=asset_id,
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
        """Scan Cloud Functions using functions_v2.FunctionServiceClient."""
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
        """
        Scan GKE workloads: list clusters via the Container API, then query
        each cluster's Kubernetes API server for Deployments.
        """
        assets = []
        try:
            client = container_v1.ClusterManagerClient()
            parent = f"projects/{self.project_id}/locations/-"
            response = client.list_clusters(parent=parent)
        except Exception as e:
            print(f"Error listing GKE clusters: {e}")
            return assets

        for cluster in response.clusters:
            workloads = self._scan_gke_cluster_workloads(cluster)
            if workloads:
                assets.extend(workloads)
            else:
                # Workload listing can fail (private endpoint, RBAC); still
                # record the cluster itself in the inventory.
                assets.append(Asset(
                    id=f"gke-{cluster.name}",
                    name=cluster.name,
                    resource_type="GKE",
                    region=cluster.location,
                    runtime=f"Kubernetes {cluster.current_master_version}",
                    service_account=cluster.node_config.service_account or "default",
                    env_vars={},
                    labels=dict(cluster.resource_labels or {})
                ))
        return assets

    def _scan_gke_cluster_workloads(self, cluster) -> List[Asset]:
        """
        Connect to one GKE cluster's API server (endpoint + CA from the
        Container API, bearer token from ADC) and inventory its Deployments.
        """
        ca_path = None
        try:
            import google.auth
            import google.auth.transport.requests
            from kubernetes import client as k8s_client

            creds, _ = google.auth.default(
                scopes=["https://www.googleapis.com/auth/cloud-platform"]
            )
            creds.refresh(google.auth.transport.requests.Request())

            configuration = k8s_client.Configuration()
            configuration.host = f"https://{cluster.endpoint}"
            with tempfile.NamedTemporaryFile(delete=False, suffix=".crt") as ca_file:
                ca_file.write(base64.b64decode(cluster.master_auth.cluster_ca_certificate))
                ca_path = ca_file.name
            configuration.ssl_ca_cert = ca_path
            configuration.api_key = {"authorization": f"Bearer {creds.token}"}

            api_client = k8s_client.ApiClient(configuration)
            apps_api = k8s_client.AppsV1Api(api_client)
            core_api = k8s_client.CoreV1Api(api_client)
            deployments = apps_api.list_deployment_for_all_namespaces(timeout_seconds=30)
        except Exception as e:
            print(f"Error connecting to GKE cluster {cluster.name}: {e}")
            if ca_path:
                os.unlink(ca_path)
            return []

        assets = []
        # Cache Workload Identity lookups per (namespace, ksa).
        wi_cache: Dict[tuple, Optional[str]] = {}
        try:
            for deploy in deployments.items:
                namespace = deploy.metadata.namespace
                if namespace in GKE_SYSTEM_NAMESPACES or namespace.startswith("gke-"):
                    continue

                pod_spec = deploy.spec.template.spec
                env_vars: Dict[str, str] = {}
                images: List[str] = []
                for container in pod_spec.containers or []:
                    if container.image:
                        images.append(container.image)
                    for env in container.env or []:
                        if env.value is not None:
                            env_vars[env.name] = env.value
                        else:
                            # secretKeyRef / configMapKeyRef / fieldRef —
                            # record that the key exists, never the value.
                            env_vars[env.name] = "<valueFrom reference>"

                ksa = pod_spec.service_account_name or "default"
                service_account = ksa
                # Resolve the Workload Identity GSA annotation if present.
                cache_key = (namespace, ksa)
                if cache_key not in wi_cache:
                    try:
                        sa_obj = core_api.read_namespaced_service_account(ksa, namespace)
                        annotations = sa_obj.metadata.annotations or {}
                        wi_cache[cache_key] = annotations.get("iam.gke.io/gcp-service-account")
                    except Exception:
                        wi_cache[cache_key] = None
                if wi_cache[cache_key]:
                    service_account = f"{ksa} -> {wi_cache[cache_key]}"

                assets.append(Asset(
                    id=f"gke-{cluster.name}-{namespace}-{deploy.metadata.name}",
                    name=deploy.metadata.name,
                    resource_type="GKE",
                    region=cluster.location,
                    runtime=", ".join(images) or f"Kubernetes {cluster.current_master_version}",
                    service_account=service_account,
                    env_vars=env_vars,
                    labels=dict(deploy.metadata.labels or {})
                ))
        finally:
            if ca_path:
                os.unlink(ca_path)
        return assets

    def _scan_vertex_ai(self) -> List[Asset]:
        """Scan Vertex AI endpoints."""
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
                    "LLAMAINDEX_CACHE_DIR": "/data/cache"
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
