from app.services.heuristics import analyze_asset
from app.services.scanner import redact_env_vars


def analyze(**overrides):
    """Call analyze_asset with a boring baseline workload."""
    params = {
        "name": "billing-api",
        "resource_type": "Cloud Run",
        "env_vars": {},
        "labels": {},
        "runtime": "python311",
        "service_account": "billing-sa@demo.iam.gserviceaccount.com",
    }
    params.update(overrides)
    return analyze_asset(**params)


class TestConfidenceScoring:
    def test_clean_workload_is_not_an_agent(self):
        is_agent, score, reasons, _, _ = analyze()
        assert not is_agent
        assert score == 0
        assert reasons == []

    def test_openai_key_flags_agent(self):
        is_agent, score, reasons, _, _ = analyze(env_vars={"OPENAI_API_KEY": "sk-test"})
        assert is_agent
        assert score == 35
        assert "OpenAI API Key configured" in reasons

    def test_no_duplicate_reason_for_key_and_keyword(self):
        # GEMINI_API_KEY matches both the exact-key indicator and the
        # "gemini" substring keyword; it must only be counted once.
        _, score, reasons, _, _ = analyze(env_vars={"GEMINI_API_KEY": "AIza-test"})
        assert score == 35
        assert reasons == ["Gemini API Key configured"]

    def test_keyword_in_env_value_detected(self):
        is_agent, _, reasons, _, _ = analyze(
            env_vars={"FRAMEWORK": "langgraph orchestration"}
        )
        assert is_agent
        assert "LangGraph orchestrator detected" in reasons

    def test_agent_name_alone_is_below_threshold(self):
        is_agent, score, reasons, _, _ = analyze(name="checkout-agent")
        assert not is_agent
        assert score == 15
        assert "Workload named as 'agent'" in reasons

    def test_runtime_image_keyword_detected(self):
        is_agent, _, reasons, _, _ = analyze(
            resource_type="GKE", runtime="ollama/ollama:0.3.9"
        )
        assert is_agent
        assert "Ollama inference server detected" in reasons

    def test_vertex_ai_native_resource_boost(self):
        is_agent, score, reasons, _, _ = analyze(resource_type="Vertex AI")
        assert is_agent
        assert score == 40
        assert "Native GCP Vertex AI service" in reasons

    def test_vertex_env_var_does_not_suppress_native_boost(self):
        # Regression: the 'vertex' env keyword used to fire first and the
        # dedup guard then swallowed the +40 native-resource boost, leaving
        # Vertex AI's own endpoints below the agent threshold.
        is_agent, score, reasons, _, _ = analyze(
            resource_type="Vertex AI",
            env_vars={"VERTEX_PROJECT_ID": "demo-project"},
        )
        assert is_agent
        assert score == 40
        assert reasons == ["Native GCP Vertex AI service"]

    def test_confidence_capped_at_100(self):
        _, score, _, _, _ = analyze(
            name="rag-service-chatbot-agent",
            env_vars={
                "OPENAI_API_KEY": "sk-1",
                "ANTHROPIC_API_KEY": "sk-2",
                "LANGCHAIN_API_KEY": "ls-3",
            },
        )
        assert score == 100


class TestRiskScoring:
    def test_iam_verified_public_endpoint(self):
        _, _, _, risk, reasons = analyze(is_public=True)
        assert risk == 20
        assert any("allUsers IAM invoker binding" in r for r in reasons)

    def test_iam_hint_overrides_label_fallback(self):
        # IAM says private; a stray label must not mark it public.
        _, _, _, risk, reasons = analyze(
            is_public=False, labels={"allow-unauthenticated": "true"}
        )
        assert risk == 0
        assert reasons == []

    def test_label_fallback_when_iam_unknown(self):
        _, _, _, risk, reasons = analyze(labels={"allow-unauthenticated": "true"})
        assert risk == 20
        assert "Public endpoint exposed (+20)" in reasons

    def test_default_compute_identity_penalty(self):
        _, _, _, risk, reasons = analyze(
            service_account="123-compute@developer.gserviceaccount.com"
        )
        assert risk == 20
        assert any("default/admin identity" in r for r in reasons)

    def test_external_llm_penalty(self):
        _, _, _, risk, reasons = analyze(env_vars={"ANTHROPIC_API_KEY": "sk-ant"})
        assert risk == 30
        assert "Integrates with third-party LLMs (+30)" in reasons

    def test_disabled_logging_penalty(self):
        _, _, _, risk, reasons = analyze(env_vars={"DISABLE_LOGGING": "true"})
        assert risk == 10
        assert "Logging and monitoring disabled (+10)" in reasons

    def test_public_ai_agent_stacks_extra_risk(self):
        _, _, _, risk, reasons = analyze(
            env_vars={"OPENAI_API_KEY": "sk-test"}, is_public=True
        )
        # public(20) + external LLM(30) + public AI agent(20)
        assert risk == 70
        assert any("Unauthenticated AI agent" in r for r in reasons)


class TestEnvVarRedaction:
    def test_credential_keys_are_masked(self):
        redacted = redact_env_vars({"OPENAI_API_KEY": "sk-proj-abc123def456xyz"})
        assert redacted["OPENAI_API_KEY"] == "sk-p" + "*" * 20
        assert "abc123" not in redacted["OPENAI_API_KEY"]

    def test_short_secrets_keep_no_prefix(self):
        redacted = redact_env_vars({"DB_PASSWORD": "hunter2"})
        assert redacted["DB_PASSWORD"] == "*" * 20

    def test_non_sensitive_values_untouched(self):
        env = {"PORT": "8080", "NODE_ENV": "production"}
        assert redact_env_vars(env) == env

    def test_matches_are_case_insensitive(self):
        redacted = redact_env_vars({"stripe_secret": "sk_live_abcdefgh12345"})
        assert redacted["stripe_secret"].endswith("*" * 20)
