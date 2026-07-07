from typing import Dict, List, Tuple, Optional
from app.models import Asset

# Detection indicators and their confidence weights
INDICATORS = {
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
    
    # GCP APIs
    "vertex-ai": {"score": 25, "reason": "Vertex AI SDK or service usage indicator"},
    "google-cloud-aiplatform": {"score": 20, "reason": "Vertex AI client library detected"},
}

def analyze_asset(
    name: str, 
    resource_type: str, 
    env_vars: Dict[str, str], 
    labels: Dict[str, str], 
    runtime: Optional[str], 
    service_account: Optional[str]
) -> Tuple[bool, int, List[str], int, List[str]]:
    
    confidence_reasons = []
    confidence_score = 0
    
    # Convert text pieces to lowercase for keyword scanning
    name_lower = name.lower()
    runtime_lower = (runtime or "").lower()
    
    # 1. Environment Variable Check
    for env_key, val in env_vars.items():
        # Exact match env variables
        if env_key in INDICATORS:
            confidence_score += INDICATORS[env_key]["score"]
            confidence_reasons.append(INDICATORS[env_key]["reason"])
        
        # Substring search in env keys/values
        env_key_lower = env_key.lower()
        val_lower = str(val).lower()
        
        for keyword in ["langchain", "langgraph", "llamaindex", "crewai", "autogen", "openai", "anthropic", "vertex"]:
            if (keyword in env_key_lower or keyword in val_lower) and not any(keyword in r.lower() for r in confidence_reasons):
                # Avoid duplicate reasons
                score = INDICATORS.get(keyword, {"score": 20})["score"]
                reason = INDICATORS.get(keyword, {"reason": f"AI keyword '{keyword}' found in env var"})["reason"]
                confidence_score += score
                confidence_reasons.append(reason)
                
    # 2. Resource Name Keywords
    for keyword in ["agent", "chatbot", "rag-service", "langchain", "llamaindex"]:
        if keyword in name_lower and not any(keyword in r.lower() for r in confidence_reasons):
            score = INDICATORS.get(keyword, {"score": 15})["score"]
            reason = INDICATORS.get(keyword, {"reason": f"AI keyword '{keyword}' found in resource name"})["reason"]
            confidence_score += score
            confidence_reasons.append(reason)
            
    # 3. Vertex AI Native Resources
    if resource_type.lower() == "vertex ai" or "vertex" in name_lower:
        if not any("vertex" in r.lower() for r in confidence_reasons):
            confidence_score += 40
            confidence_reasons.append("Native GCP Vertex AI service")
            
    # Cap confidence score at 100
    confidence_score = min(confidence_score, 100)
    is_ai_agent = confidence_score >= 30 # Threshold
    
    # 4. Risk Score Calculation (Bonus 3)
    risk_score = 0
    risk_reasons = []
    
    # Rule 1: Public endpoint (Cloud Run/Functions without authorization check, or public labels)
    is_public = False
    if "public" in name_lower or labels.get("allow-unauthenticated") == "true" or labels.get("visibility") == "public" or labels.get("allUsers") == "roles/run.invoker":
        is_public = True
    if is_public:
        risk_score += 20
        risk_reasons.append("Public endpoint exposed (+20)")
        
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
    if is_ai_agent and is_public:
        risk_score += 20
        risk_reasons.append("Unauthenticated AI agent exposed to public (+20)")
        
    risk_score = min(risk_score, 100)
    
    return is_ai_agent, confidence_score, confidence_reasons, risk_score, risk_reasons
