from typing import Dict, List, Tuple, Optional, TypedDict

class IndicatorDict(TypedDict):
    score: int
    reason: str

# Detection indicators and their confidence weights
INDICATORS: Dict[str, IndicatorDict] = {
    # Environment variables indicative of AI/LLM models
    "OPENAI_API_KEY": {"score": 35, "reason": "OpenAI API Key configured"},
    "ANTHROPIC_API_KEY": {"score": 35, "reason": "Anthropic API Key configured"},
    "GEMINI_API_KEY": {"score": 35, "reason": "Gemini API Key configured"},
    "COHERE_API_KEY": {"score": 30, "reason": "Cohere API Key configured"},
    "LLM_MODEL": {"score": 15, "reason": "LLM model environment variable configured"},
    "LANGCHAIN_API_KEY": {"score": 25, "reason": "LangChain API Key configured"},
    "LANGCHAIN_TRACING_V2": {"score": 15, "reason": "LangChain tracing enabled"},

    # Framework indicators in name / image / environment
    "langchain": {"score": 25, "reason": "LangChain library usage detected"},
    "langgraph": {"score": 35, "reason": "LangGraph orchestrator detected"},
    "llamaindex": {"score": 25, "reason": "LlamaIndex framework detected"},
    "crewai": {"score": 35, "reason": "CrewAI agent orchestrator detected"},
    "autogen": {"score": 35, "reason": "AutoGen agent framework detected"},
    "agent": {"score": 15, "reason": "Workload named as 'agent'"},
    "chatbot": {"score": 15, "reason": "Workload named as 'chatbot'"},
    "rag-service": {"score": 20, "reason": "RAG (Retrieval-Augmented Generation) keyword detected"},

    # Model runtimes / inference servers (matched in container images too)
    "gemini": {"score": 30, "reason": "Gemini usage detected"},
    "llama": {"score": 25, "reason": "Llama model runtime detected"},
    "ollama": {"score": 30, "reason": "Ollama inference server detected"},
    "vllm": {"score": 30, "reason": "vLLM inference server detected"},

    # GCP APIs
    "vertex-ai": {"score": 25, "reason": "Vertex AI SDK or service usage indicator"},
    "google-cloud-aiplatform": {"score": 20, "reason": "Vertex AI client library detected"},
}

# Keywords scanned as substrings of env var keys/values.
ENV_KEYWORDS = [
    "langchain", "langgraph", "llamaindex", "crewai", "autogen",
    "openai", "anthropic", "vertex", "gemini",
]

# Keywords scanned as substrings of the resource name.
NAME_KEYWORDS = ["agent", "chatbot", "rag-service", "langchain", "llamaindex"]

# Keywords scanned as substrings of the runtime (for GKE this carries the
# container image references, so framework/inference-server names show here).
RUNTIME_KEYWORDS = [
    "langchain", "langgraph", "llamaindex", "crewai", "autogen",
    "llama", "ollama", "vllm", "gemini",
]


def analyze_asset(
    name: str,
    resource_type: str,
    env_vars: Dict[str, str],
    labels: Dict[str, str],
    runtime: Optional[str],
    service_account: Optional[str],
    is_public: Optional[bool] = None,
    has_vertex_logs: bool = False
) -> Tuple[bool, int, List[str], int, List[str]]:
    """
    Score one workload. `is_public` is an IAM-verified ingress hint from the
    scanner (True/False); when None, public exposure falls back to
    label/naming heuristics.
    """

    confidence_reasons = []
    confidence_score = 0

    # Convert text pieces to lowercase for keyword scanning
    name_lower = name.lower()
    runtime_lower = (runtime or "").lower()

    def add_indicator(keyword: str, fallback_reason: str, fallback_score: int = 15) -> None:
        nonlocal confidence_score
        # Skip if an equivalent reason was already recorded
        if any(keyword in r.lower() for r in confidence_reasons):
            return
        indicator = INDICATORS.get(keyword)
        if indicator is not None:
            confidence_score += indicator["score"]
            confidence_reasons.append(indicator["reason"])
        else:
            confidence_score += fallback_score
            confidence_reasons.append(fallback_reason)

    # 1. Vertex AI Native Resources — scored first so the generic 'vertex'
    # keyword below dedups against this stronger signal, not the reverse.
    if resource_type.lower() == "vertex ai" or "vertex" in name_lower:
        confidence_score += 40
        confidence_reasons.append("Native GCP Vertex AI service")

    # 2. Environment Variable Check
    for env_key, val in env_vars.items():
        # Exact match env variables
        if env_key in INDICATORS and INDICATORS[env_key]["reason"] not in confidence_reasons:
            confidence_score += INDICATORS[env_key]["score"]
            confidence_reasons.append(INDICATORS[env_key]["reason"])

        # Substring search in env keys/values
        env_key_lower = env_key.lower()
        val_lower = str(val).lower()

        for keyword in ENV_KEYWORDS:
            if keyword in env_key_lower or keyword in val_lower:
                add_indicator(keyword, f"AI keyword '{keyword}' found in env var", 20)

    # 3. Resource Name Keywords
    for keyword in NAME_KEYWORDS:
        if keyword in name_lower:
            add_indicator(keyword, f"AI keyword '{keyword}' found in resource name")

    # 4. Runtime / Container Image Keywords
    for keyword in RUNTIME_KEYWORDS:
        if keyword in runtime_lower:
            add_indicator(keyword, f"AI keyword '{keyword}' found in runtime")

    # 5. Cloud Logging - API calls to Vertex AI
    if has_vertex_logs:
        confidence_score += 40
        confidence_reasons.append("Verified Vertex AI API calls in Cloud Logging")

    # Cap confidence score at 100
    confidence_score = min(confidence_score, 100)
    is_ai_agent = confidence_score >= 30  # Threshold

    # 5. Risk Score Calculation (Bonus 3)
    risk_score = 0
    risk_reasons = []

    # Rule 1: Public endpoint. Prefer the IAM-verified hint from the scanner;
    # fall back to labels/naming for mock data or when IAM is unreadable.
    if is_public is not None:
        endpoint_public = is_public
        public_reason = "Public endpoint exposed — allUsers IAM invoker binding (+20)"
    else:
        endpoint_public = (
            "public" in name_lower
            or labels.get("allow-unauthenticated") == "true"
            or labels.get("visibility") == "public"
        )
        public_reason = "Public endpoint exposed (+20)"
    if endpoint_public:
        risk_score += 20
        risk_reasons.append(public_reason)

    # Rule 2: Admin Service Account
    # Default compute or empty SA represents general permission
    if not service_account or "compute@developer.gserviceaccount.com" in service_account or "admin" in service_account:
        risk_score += 20
        risk_reasons.append("Runs with highly privileged default/admin identity (+20)")

    # Rule 3: External LLM Integration
    uses_external_llm = any(k in env_vars for k in ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "COHERE_API_KEY"])
    if uses_external_llm:
        risk_score += 30
        risk_reasons.append("Integrates with third-party LLMs (+30)")

    # Rule 4: No logging configured (e.g. LOGGING_ENABLED = false or similar, or default check)
    if env_vars.get("LOGGING_LEVEL") == "NONE" or env_vars.get("DISABLE_LOGGING") == "true" or env_vars.get("LOGGING") == "false":
        risk_score += 10
        risk_reasons.append("Logging and monitoring disabled (+10)")

    # Additional risk if public AI Agent
    if is_ai_agent and endpoint_public:
        risk_score += 20
        risk_reasons.append("Unauthenticated AI agent exposed to public (+20)")

    risk_score = min(risk_score, 100)

    return is_ai_agent, confidence_score, confidence_reasons, risk_score, risk_reasons
