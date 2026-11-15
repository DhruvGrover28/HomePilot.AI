import asyncio
import time
from uuid import uuid4

from fastapi.testclient import TestClient
import pytest

from app.config import get_settings
from app.db import initialize_database
from app.main import app
from app.schemas_agents import InvestigationContext, InvestigationIssueContext
from app.services import agent_graph
from app.services.agent_graph import GroqDecisionModel, _recommendations, execute_agent
from app.services.provider_models import (
    FailoverDecisionModel,
    HttpDecisionModel,
    OpenRouterDecisionModel,
    ProviderCallError,
    ProviderExhaustedError,
    StaggeredDecisionModel,
    decision_prompt,
)


@pytest.fixture
def mock_mode(monkeypatch):
    monkeypatch.setenv("LLM_MODE", "mock")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _auth_client() -> TestClient:
    client = TestClient(app)
    client.post(
        "/api/auth/register",
        json={
            "full_name": "Agent Tester",
            "email": f"{uuid4()}@example.com",
            "password": "correct horse battery",
            "confirm_password": "correct horse battery",
        },
    )
    return client


def test_agent_run_routes_domains_and_persists_result(mock_mode):
    initialize_database()
    with _auth_client() as client:
        response = client.post(
            "/api/agents/runs",
            json={"goal": "Review energy and supplies.", "domains": ["energy", "inventory"]},
        )
        assert response.status_code == 200
        result = response.json()
        assert result["status"] == "completed"
        assert result["domains"] == ["energy", "inventory"]
        assert result["trace"][0]["kind"] == "decision"
        assert result["findings"]
        assert any(step["kind"] == "tool_call" for step in result["trace"])
        finding_ids = {finding["id"] for finding in result["findings"]}
        assert all(set(item["finding_ids"]) <= finding_ids for item in result["recommendations"])

        persisted = client.get(f"/api/agents/runs/{result['id']}")
        assert persisted.status_code == 200
        assert persisted.json()["id"] == result["id"]


def test_agent_run_rejects_unknown_domain_and_missing_run(mock_mode):
    initialize_database()
    with _auth_client() as client:
        response = client.post(
            "/api/agents/runs",
            json={"goal": "Review household.", "domains": ["unknown"]},
        )
        assert response.status_code == 422
        assert client.get("/api/agents/runs/not-a-real-run").status_code == 404


def test_investigation_context_is_traced_and_persisted(mock_mode):
    initialize_database()
    context = InvestigationContext(
        primary_issue_id="primary-issue",
        issues=[
            InvestigationIssueContext(
                issue_id="primary-issue",
                fingerprint="energy:anomaly",
                issue_type="consumption_anomaly",
                domain="energy",
                title="Unusual energy consumption",
                relationship="primary",
                evidence={"latest_evidence_reading_id": 42},
            ),
            InvestigationIssueContext(
                issue_id="maintenance-issue",
                fingerprint="appliance:7:maintenance_overdue",
                issue_type="maintenance_due",
                domain="maintenance",
                title="Maintenance due",
                relationship="plausible",
                relationship_reason="The issues affect compatible household concerns.",
            ),
        ],
    )
    result = execute_agent(
        "Investigate the energy issue and related household evidence.",
        ["energy", "maintenance"],
        investigation_context=context,
    )
    decision = next(item for item in result["trace"] if item["kind"] == "decision")
    assert decision["context_issue_ids"] == ["primary-issue", "maintenance-issue"]
    assert result["investigation_context"] == context

    with _auth_client() as client:
        response = client.post(
            "/api/agents/runs",
            json={
                "goal": "Review energy.",
                "domains": ["energy"],
                "investigation_context": context.model_dump(mode="json"),
            },
        )
    assert response.status_code == 200
    assert response.json()["investigation_context"]["primary_issue_id"] == "primary-issue"


def test_live_prompt_serializes_investigation_context():
    context = InvestigationContext(
        primary_issue_id="primary-issue",
        issues=[
            InvestigationIssueContext(
                issue_id="primary-issue",
                fingerprint="energy:anomaly",
                issue_type="consumption_anomaly",
                domain="energy",
                title="Unusual energy consumption",
                relationship="primary",
            )
        ],
    )
    prompt = decision_prompt(
        {
            "goal": "Investigate the issue.",
            "remaining_domains": ["energy"],
            "investigation_context": context,
            "decisions": [],
            "findings": [],
            "supervisor_budget": 8,
            "supervisor_calls": 0,
        }
    )
    assert '"primary_issue_id": "primary-issue"' in prompt


def test_electricity_spike_can_trigger_maintenance_follow_up(mock_mode, monkeypatch):
    monkeypatch.setitem(
        agent_graph.TOOLSETS,
        "energy",
        (lambda: {
            "type": "energy_readings",
            "count": 6,
            "rates": [10, 10, 10, 10, 10, 25],
            "statistics": {"mean": 12.5, "standard_deviation": 5.59, "count": 6},
            "anomaly": {"flagged": True, "insufficient_data": False, "z_score": 2.2},
        },),
    )
    monkeypatch.setitem(
        agent_graph.TOOLSETS,
        "maintenance",
        (lambda: {"type": "maintenance_statuses", "today": "2026-11-14", "items": []},),
    )
    result = execute_agent("Investigate an electricity spike.", ["energy", "maintenance"])
    assert [decision["specialist"] for decision in result["decisions"][:2]] == ["energy", "maintenance"]
    decisions = [entry for entry in result["trace"] if entry["kind"] == "decision"]
    assert decisions[0]["findings_seen"] == 0
    assert decisions[1]["findings_seen"] == 1
    assert result["recommendations"][0]["finding_ids"] == [result["findings"][0]["id"]]


def test_normal_energy_evidence_does_not_select_maintenance(mock_mode, monkeypatch):
    monkeypatch.setitem(
        agent_graph.TOOLSETS,
        "energy",
        (lambda: {
            "type": "energy_readings",
            "count": 6,
            "rates": [10, 10, 10, 10, 10, 10],
            "statistics": {"mean": 10, "standard_deviation": 0, "count": 6},
            "anomaly": {"flagged": False, "insufficient_data": False},
        },),
    )
    result = execute_agent("Investigate an electricity issue.", ["energy", "maintenance"])
    assert [decision["specialist"] for decision in result["decisions"] if decision["action"] == "investigate"] == ["energy"]
    assert result["decisions"][-1]["action"] == "stop"


def test_water_only_concern_does_not_invoke_unrelated_specialists(mock_mode, monkeypatch):
    calls = []

    def water_tool():
        calls.append("water")
        return {"type": "water_readings", "count": 6, "rates": [1, 1, 1, 1, 1, 1], "statistics": {}, "anomaly": {"flagged": False}}

    monkeypatch.setitem(agent_graph.TOOLSETS, "water", (water_tool,))
    monkeypatch.setitem(agent_graph.TOOLSETS, "energy", (lambda: calls.append("energy"),))
    result = execute_agent("Investigate water usage.", ["energy", "water", "maintenance"])
    assert calls == ["water"]
    assert [decision["specialist"] for decision in result["decisions"] if decision["action"] == "investigate"] == ["water"]


def test_inventory_and_insufficient_history_are_evidence_bounded(mock_mode, monkeypatch):
    monkeypatch.setitem(
        agent_graph.TOOLSETS,
        "inventory",
        (lambda: {"type": "inventory_levels", "items": [{"item": "Milk", "quantity": 0, "unit": "unit", "reorder_threshold": 1, "low": True}]},),
    )
    inventory = execute_agent("Check low inventory.", ["inventory", "energy"])
    assert [decision["specialist"] for decision in inventory["decisions"] if decision["action"] == "investigate"] == ["inventory"]
    monkeypatch.setitem(
        agent_graph.TOOLSETS,
        "energy",
        (lambda: {"type": "energy_readings", "count": 2, "rates": [5, 6], "statistics": {}, "anomaly": {"insufficient_data": True}},),
    )
    insufficient = execute_agent("Investigate an electricity spike.", ["energy"])
    assert insufficient["findings"][0]["severity"] == "info"
    assert "Collect at least five" in insufficient["findings"][0]["suggested_action"]


def test_no_relevant_issue_and_budget_exhaustion_are_recorded(mock_mode):
    no_issue = execute_agent("Tell me something unrelated.", ["energy", "water"])
    assert no_issue["decisions"][0]["action"] == "stop"
    assert not [entry for entry in no_issue["trace"] if entry["kind"] == "tool_call"]
    exhausted = execute_agent("Investigate energy.", ["energy"], supervisor_budget=0)
    assert exhausted["stop_reason"] == "supervisor_budget_exhausted"
    assert exhausted["trace"][0]["kind"] == "budget_exhausted"


def test_specialist_budget_and_duplicate_suppression_are_enforced(mock_mode, monkeypatch):
    monkeypatch.setitem(
        agent_graph.TOOLSETS,
        "energy",
        (lambda: {"type": "energy_readings", "count": 6, "rates": [1, 1, 1, 1, 1, 4], "statistics": {}, "anomaly": {"flagged": True}},),
    )
    exhausted = execute_agent("Investigate energy.", ["energy"], specialist_budget=0)
    assert exhausted["status"] == "stopped"
    assert exhausted["stop_reason"] == "specialist_budget_exhausted"
    assert any(entry["kind"] == "budget_exhausted" for entry in exhausted["trace"])
    findings = [
        {
            "id": "a",
            "category": "energy",
            "subject": "electricity",
            "summary": "Spike",
            "evidence": [{"type": "energy_readings"}],
            "severity": "high",
            "confidence": 0.9,
            "possible_explanations": ["usage"],
            "suggested_action": "Review usage.",
        },
        {
            "id": "b",
            "category": "energy",
            "subject": "electricity",
            "summary": "Same spike",
            "evidence": [{"type": "energy_readings"}],
            "severity": "high",
            "confidence": 0.9,
            "possible_explanations": ["usage"],
            "suggested_action": "Review usage.",
        },
    ]
    recommendations, trace = _recommendations(findings)
    assert len(recommendations) == 2
    assert recommendations[1]["suppressed"] is True
    assert trace[0]["kind"] == "recommendation_suppressed"


def test_groq_decision_model_validates_structured_response(monkeypatch):
    captured = {}

    class FakeResponse:
        is_success = True

        def raise_for_status(self):
            return None

        def json(self):
            return {
                "choices": [
                    {
                        "message": {
                            "content": '{"action":"investigate","specialist":"energy","rationale":"The goal identifies energy use.","next_investigation":null}'
                        }
                    }
                ]
            }

    def fake_post(url, **kwargs):
        captured["url"] = url
        captured["kwargs"] = kwargs
        return FakeResponse()

    monkeypatch.setattr(agent_graph.httpx, "post", fake_post)
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.setenv("GROQ_MODEL", "openai/gpt-oss-20b")
    get_settings.cache_clear()
    try:
        decision = GroqDecisionModel().decide(
            {
                "goal": "Investigate electricity.",
                "remaining_domains": ["energy"],
                "decisions": [],
                "findings": [],
                "supervisor_budget": 8,
                "supervisor_calls": 0,
            }
        )
    finally:
        get_settings.cache_clear()

    assert decision.specialist == "energy"
    assert decision.action == "investigate"
    assert captured["kwargs"]["json"]["reasoning_effort"] == "low"
    assert captured["kwargs"]["json"]["include_reasoning"] is False
    assert captured["kwargs"]["json"]["max_completion_tokens"] == 1024
    schema = captured["kwargs"]["json"]["response_format"]["json_schema"]["schema"]
    assert set(schema["required"]) == set(schema["properties"])
    assert schema["additionalProperties"] is False


def test_live_groq_requires_credentials(monkeypatch):
    monkeypatch.setenv("LLM_MODE", "live")
    monkeypatch.setenv("LLM_PROVIDER", "groq")
    monkeypatch.setenv("GROQ_API_KEY", "")
    get_settings.cache_clear()
    try:
        with pytest.raises(RuntimeError, match="GROQ_API_KEY"):
            agent_graph._decision_model()
    finally:
        get_settings.cache_clear()


def _decision():
    return {
        "action": "investigate",
        "specialist": "energy",
        "rationale": "Energy is relevant.",
        "next_investigation": None,
    }


def test_failover_stops_after_first_success(monkeypatch):
    calls = []

    class FakeProvider:
        def __init__(self, name):
            self.provider = name
            self.model = name + "-model"
            self.last_metadata = {}

        def decide(self, state):
            calls.append(self.provider)
            return agent_graph.SupervisorDecision.model_validate(_decision())

    monkeypatch.setattr("app.services.provider_models._provider_model", lambda name: FakeProvider(name))
    model = StaggeredDecisionModel(["gemini", "groq", "openrouter"], deadline_seconds=0.2, stagger_seconds=0.01)
    asyncio.run(model.decide_async({"goal": "energy", "remaining_domains": ["energy"], "findings": [], "decisions": [], "supervisor_budget": 8, "supervisor_calls": 0}))
    assert calls == ["gemini"]
    assert model.last_attempts[0]["success"] is True


def test_failover_prefers_groq_when_gemini_fails(monkeypatch):
    calls = []

    class FakeProvider:
        def __init__(self, name):
            self.provider = name
            self.model = name + "-model"
            self.last_metadata = {}

        def decide(self, state):
            calls.append(self.provider)
            if self.provider == "gemini":
                raise ProviderCallError(self.provider, self.model, "timeout")
            return agent_graph.SupervisorDecision.model_validate(_decision())

    monkeypatch.setattr("app.services.provider_models._provider_model", lambda name: FakeProvider(name))
    model = StaggeredDecisionModel(["gemini", "groq", "openrouter"], deadline_seconds=0.2, stagger_seconds=0.01)
    asyncio.run(model.decide_async({"goal": "energy", "remaining_domains": ["energy"], "findings": [], "decisions": [], "supervisor_budget": 8, "supervisor_calls": 0}))
    assert calls[:2] == ["gemini", "groq"]
    assert model.last_attempts[0]["fallback_triggered"] is True
    assert next(item for item in model.last_attempts if item["provider"] == "groq")["winner"] is True
    assert not any(item["winner"] for item in model.last_attempts if item["provider"] == "openrouter")


def test_failover_reaches_openrouter_and_records_exhaustion(monkeypatch):
    calls = []

    class FakeProvider:
        def __init__(self, name):
            self.provider = name
            self.model = name + "-model"
            self.last_metadata = {}

        def decide(self, state):
            calls.append(self.provider)
            if self.provider != "openrouter":
                raise ProviderCallError(self.provider, self.model, "provider_unavailable", http_status=503)
            return agent_graph.SupervisorDecision.model_validate(_decision())

    monkeypatch.setattr("app.services.provider_models._provider_model", lambda name: FakeProvider(name))
    model = StaggeredDecisionModel(["gemini", "groq", "openrouter"], deadline_seconds=0.2, stagger_seconds=0.01)
    asyncio.run(model.decide_async({"goal": "energy", "remaining_domains": ["energy"], "findings": [], "decisions": [], "supervisor_budget": 8, "supervisor_calls": 0}))
    assert calls == ["gemini", "groq", "openrouter"]
    assert model.last_attempts[-1]["success"] is True


def test_failover_all_failures_raise_controlled_error(monkeypatch):
    class FakeProvider:
        def __init__(self, name):
            self.provider = name
            self.model = name + "-model"
            self.last_metadata = {}

        def decide(self, state):
            raise ProviderCallError(self.provider, self.model, "schema_validation")

    monkeypatch.setattr("app.services.provider_models._provider_model", lambda name: FakeProvider(name))
    model = StaggeredDecisionModel(["gemini", "groq", "openrouter"], deadline_seconds=0.2, stagger_seconds=0.01)
    with pytest.raises(ProviderExhaustedError) as error:
        asyncio.run(model.decide_async({"goal": "energy", "remaining_domains": ["energy"], "findings": [], "decisions": [], "supervisor_budget": 8, "supervisor_calls": 0}))
    assert [attempt["provider"] for attempt in error.value.attempts] == ["gemini", "groq", "openrouter"]


def test_failover_does_not_catch_programming_errors(monkeypatch):
    class FakeProvider:
        provider = "gemini"
        model = "gemini-model"
        last_metadata = {}

        def decide(self, state):
            raise ValueError("programming bug")

    monkeypatch.setattr("app.services.provider_models._provider_model", lambda name: FakeProvider())
    model = StaggeredDecisionModel(["gemini", "groq", "openrouter"], deadline_seconds=0.2, stagger_seconds=0.01)
    with pytest.raises(ValueError, match="programming bug"):
        asyncio.run(model.decide_async({"goal": "energy", "remaining_domains": ["energy"], "findings": [], "decisions": [], "supervisor_budget": 8, "supervisor_calls": 0}))


def test_explicit_provider_does_not_call_fallbacks(monkeypatch):
    calls = []

    class FakeProvider:
        def __init__(self, name):
            self.provider = name
            self.model = name + "-model"
            self.last_metadata = {}

        def decide(self, state):
            calls.append(self.provider)
            return agent_graph.SupervisorDecision.model_validate(_decision())

    monkeypatch.setattr("app.services.provider_models._provider_model", lambda name: FakeProvider(name))
    monkeypatch.setenv("LLM_PROVIDER", "openrouter")
    monkeypatch.setenv("LLM_PROVIDER_ORDER", "openrouter,groq,gemini")
    get_settings.cache_clear()
    try:
        FailoverDecisionModel().decide({"goal": "energy", "remaining_domains": ["energy"], "findings": [], "decisions": [], "supervisor_budget": 8, "supervisor_calls": 0})
    finally:
        get_settings.cache_clear()
    assert calls == ["openrouter"]


def test_openrouter_request_validates_schema_and_records_routed_metadata(monkeypatch):
    captured = {}

    class FakeResponse:
        is_success = True

        def json(self):
            return {
                "model": "anthropic/claude-sonnet-5.5",
                "provider": "test-host",
                "choices": [
                    {
                        "message": {
                            "content": '{"action":"stop","specialist":null,"rationale":"Evidence is sufficient.","next_investigation":null}'
                        }
                    }
                ],
            }

    def fake_post(url, **kwargs):
        captured["url"] = url
        captured["kwargs"] = kwargs
        return FakeResponse()

    monkeypatch.setattr("app.services.provider_models.httpx.post", fake_post)
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setenv("OPENROUTER_MODEL", "anthropic/claude-sonnet-5.5")
    get_settings.cache_clear()
    try:
        model = OpenRouterDecisionModel()
        decision = model.decide(
            {
                "goal": "Review household.",
                "remaining_domains": ["energy"],
                "decisions": [],
                "findings": [],
                "supervisor_budget": 8,
                "supervisor_calls": 0,
            }
        )
    finally:
        get_settings.cache_clear()

    assert captured["url"] == "https://openrouter.ai/api/v1/chat/completions"
    assert decision.action == "stop"
    assert model.last_metadata == {"model": "anthropic/claude-sonnet-5.5", "provider": "test-host"}
    assert "reasoning_effort" not in captured["kwargs"]["json"]


def test_staggered_race_caps_provider_timeout_to_remaining_deadline(monkeypatch):
    captured = {}

    class FakeResponse:
        is_success = True

        def json(self):
            return {
                "model": "test-model",
                "choices": [
                    {
                        "message": {
                            "content": '{"action":"stop","specialist":null,"rationale":"Done.","next_investigation":null}'
                        }
                    }
                ],
            }

    def fake_post(url, **kwargs):
        captured["timeout"] = kwargs["timeout"]
        return FakeResponse()

    provider = HttpDecisionModel("openrouter", "test-key", "test-model", "https://example.test")
    monkeypatch.setattr("app.services.provider_models._provider_model", lambda name: provider)
    monkeypatch.setattr("app.services.provider_models.httpx.post", fake_post)
    model = StaggeredDecisionModel(["openrouter"], deadline_seconds=0.1, stagger_seconds=0)

    asyncio.run(model.decide_async(_race_state()))

    assert 0 < captured["timeout"] <= 0.1


def test_failover_happens_before_tools_and_does_not_repeat_tool_execution(monkeypatch):
    calls = {"gemini": 0, "groq": 0}
    tool_calls = []

    class FakeProvider:
        def __init__(self, name):
            self.provider = name
            self.model = name + "-model"
            self.last_metadata = {}

        def decide(self, state):
            calls[self.provider] += 1
            if self.provider == "gemini":
                raise ProviderCallError(self.provider, self.model, "timeout")
            if calls[self.provider] == 1:
                return agent_graph.SupervisorDecision.model_validate(_decision())
            return agent_graph.SupervisorDecision(action="stop", rationale="Evidence is sufficient.")

    def energy_tool():
        tool_calls.append("energy")
        return {
            "type": "energy_readings",
            "count": 6,
            "rates": [1, 1, 1, 1, 1, 4],
            "statistics": {},
            "anomaly": {"flagged": True},
        }

    monkeypatch.setenv("LLM_MODE", "live")
    monkeypatch.setattr("app.services.provider_models._provider_model", lambda name: FakeProvider(name))
    monkeypatch.setitem(agent_graph.TOOLSETS, "energy", (energy_tool,))
    monkeypatch.setattr(
        agent_graph,
        "_decision_model",
        lambda: StaggeredDecisionModel(["gemini", "groq"], deadline_seconds=0.2, stagger_seconds=0.01),
    )
    result = execute_agent("Investigate energy.", ["energy"])

    attempts = [item for item in result["trace"] if item["kind"] == "provider_attempt"]
    decisions = [item for item in result["trace"] if item["kind"] == "decision"]
    assert tool_calls == ["energy"]
    assert [item["provider"] for item in attempts] == ["gemini", "groq", "gemini", "groq"]
    assert [item["provider"] for item in decisions] == ["groq", "groq"]
    assert [item["findings_seen"] for item in decisions] == [0, 1]


def _race_state():
    return {
        "goal": "Investigate energy.",
        "remaining_domains": ["energy"],
        "findings": [],
        "decisions": [],
        "supervisor_budget": 8,
        "supervisor_calls": 0,
    }


def test_staggered_race_starts_providers_at_configured_offsets(monkeypatch):
    starts = {}

    class TimedProvider:
        def __init__(self, name):
            self.provider = name
            self.model = name
            self.last_metadata = {}

        def decide(self, state):
            starts[self.provider] = time.monotonic()
            time.sleep(0.3)
            raise ProviderCallError(self.provider, self.model, "timeout")

    monkeypatch.setattr("app.services.provider_models._provider_model", lambda name: TimedProvider(name))
    model = StaggeredDecisionModel(["openrouter", "groq", "gemini"], deadline_seconds=0.16, stagger_seconds=0.04)
    with pytest.raises(ProviderExhaustedError):
        asyncio.run(model.decide_async(_race_state()))
    assert starts["groq"] - starts["openrouter"] >= 0.025
    assert starts["gemini"] - starts["openrouter"] >= 0.06


def test_valid_openrouter_prevents_later_starts(monkeypatch):
    calls = []

    class FastProvider:
        def __init__(self, name):
            self.provider = name
            self.model = name
            self.last_metadata = {}

        def decide(self, state):
            calls.append(self.provider)
            return agent_graph.SupervisorDecision.model_validate(_decision())

    monkeypatch.setattr("app.services.provider_models._provider_model", lambda name: FastProvider(name))
    model = StaggeredDecisionModel(["openrouter", "groq", "gemini"], deadline_seconds=0.2, stagger_seconds=0.05)
    asyncio.run(model.decide_async(_race_state()))
    assert calls == ["openrouter"]
    assert model.last_attempts[0]["winner"] is True
    assert all(item["cancelled"] for item in model.last_attempts[1:])


def test_groq_wins_while_openrouter_continues(monkeypatch):
    started = []
    completed = []

    class Provider:
        def __init__(self, name):
            self.provider = name
            self.model = name
            self.last_metadata = {}

        def decide(self, state):
            started.append(self.provider)
            if self.provider == "openrouter":
                time.sleep(0.2)
            else:
                time.sleep(0.01)
            completed.append(self.provider)
            if self.provider == "groq":
                return agent_graph.SupervisorDecision.model_validate(_decision())
            raise ProviderCallError(self.provider, self.model, "timeout")

    monkeypatch.setattr("app.services.provider_models._provider_model", lambda name: Provider(name))
    started_at = time.monotonic()
    model = StaggeredDecisionModel(["openrouter", "groq", "gemini"], deadline_seconds=0.4, stagger_seconds=0.03)
    decision = asyncio.run(model.decide_async(_race_state()))
    elapsed = time.monotonic() - started_at
    time.sleep(0.22)
    assert decision.specialist == "energy"
    assert elapsed < 0.15
    assert "openrouter" in started
    assert "openrouter" in completed


def test_invalid_response_allows_gemini_to_win(monkeypatch):
    calls = []

    class Provider:
        def __init__(self, name):
            self.provider = name
            self.model = name
            self.last_metadata = {}

        def decide(self, state):
            calls.append(self.provider)
            if self.provider == "openrouter":
                raise ProviderCallError(self.provider, self.model, "schema_validation")
            return agent_graph.SupervisorDecision.model_validate(_decision())

    monkeypatch.setattr("app.services.provider_models._provider_model", lambda name: Provider(name))
    model = StaggeredDecisionModel(["openrouter", "groq", "gemini"], deadline_seconds=0.2, stagger_seconds=0.01)
    asyncio.run(model.decide_async(_race_state()))
    assert calls[:2] == ["openrouter", "groq"]
    assert model.last_attempts[0]["outcome"] == "failed"
    assert model.last_attempts[1]["winner"] is True


def test_shared_deadline_marks_outstanding_attempts(monkeypatch):
    class SlowProvider:
        def __init__(self, name):
            self.provider = name
            self.model = name
            self.last_metadata = {}

        def decide(self, state):
            time.sleep(0.3)
            raise ProviderCallError(self.provider, self.model, "timeout")

    monkeypatch.setattr("app.services.provider_models._provider_model", lambda name: SlowProvider(name))
    started_at = time.monotonic()
    model = StaggeredDecisionModel(["openrouter", "groq", "gemini"], deadline_seconds=0.08, stagger_seconds=0.01)
    with pytest.raises(ProviderExhaustedError):
        asyncio.run(model.decide_async(_race_state()))
    assert time.monotonic() - started_at < 0.2
    assert all(item["deadline_exhausted"] for item in model.last_attempts)


def test_simultaneous_valid_responses_have_one_winner(monkeypatch):
    class Provider:
        def __init__(self, name):
            self.provider = name
            self.model = name
            self.last_metadata = {}

        def decide(self, state):
            time.sleep(0.03)
            return agent_graph.SupervisorDecision.model_validate(_decision())

    monkeypatch.setattr("app.services.provider_models._provider_model", lambda name: Provider(name))
    model = StaggeredDecisionModel(["openrouter", "groq", "gemini"], deadline_seconds=0.2, stagger_seconds=0)
    asyncio.run(model.decide_async(_race_state()))
    assert sum(item["winner"] for item in model.last_attempts) == 1


def test_repeatable_energy_to_supervisor_to_maintenance_demo(monkeypatch, mock_mode):
    """Repeatable Demo Scenario 1 (Anomaly):
    Energy spike detected -> finding suggests maintenance -> Supervisor routes to Maintenance specialist."""
    monkeypatch.setattr(
        "app.services.agent_graph.TOOLSETS",
        {
            "energy": [
                lambda household_id=None: {
                    "count": 6,
                    "anomaly": {"flagged": True, "details": "Recent 3.5x consumption spike"},
                    "rates": [10.0, 10.0, 10.0, 10.0, 10.0, 35.0],
                }
            ],
            "maintenance": [
                lambda household_id=None: {
                    "items": [
                        {
                            "name": "HVAC Heat Pump",
                            "warranty": {"status": "expired"},
                            "maintenance": {"status": "overdue"},
                        }
                    ]
                }
            ],
            "water": [],
            "inventory": [],
        },
    )

    result = execute_agent(
        goal="Investigate electricity consumption spike and check appliances.",
        domains=["energy", "maintenance"],
        supervisor_budget=6,
        specialist_budget=4,
        household_id="hh-demo-test",
    )

    assert result["status"] == "completed"
    scopes_contacted = [step.get("scope") for step in result["trace"] if step.get("kind") == "tool_call"]
    assert "energy_specialist" in scopes_contacted
    assert "maintenance_specialist" in scopes_contacted

    # Verify supervisor routing rationale
    supervisor_decisions = [d for d in result["decisions"] if d.get("action") == "investigate"]
    assert len(supervisor_decisions) >= 2
    assert supervisor_decisions[0]["specialist"] == "energy"
    assert supervisor_decisions[1]["specialist"] == "maintenance"
    assert supervisor_decisions[1]["next_investigation"] == "maintenance"

    # Verify findings contain energy spike and maintenance follow-up
    categories = [f["category"] for f in result["findings"]]
    assert "consumption" in categories
    assert "maintenance" in categories
    assert len(result["recommendations"]) > 0


def test_repeatable_energy_normal_scenario_stops(monkeypatch, mock_mode):
    """Repeatable Demo Scenario 2 (Normal Baseline):
    No energy spike -> finding suggests NO maintenance -> Supervisor stops without calling Maintenance."""
    monkeypatch.setattr(
        "app.services.agent_graph.TOOLSETS",
        {
            "energy": [
                lambda household_id=None: {
                    "count": 6,
                    "anomaly": {"flagged": False, "details": "Normal baseline"},
                    "rates": [10.0, 10.2, 9.8, 10.1, 10.0, 10.1],
                }
            ],
            "maintenance": [
                lambda household_id=None: {
                    "items": [
                        {
                            "name": "HVAC Heat Pump",
                            "warranty": {"status": "active"},
                            "maintenance": {"status": "ok"},
                        }
                    ]
                }
            ],
            "water": [],
            "inventory": [],
        },
    )

    result = execute_agent(
        goal="Review electricity consumption.",
        domains=["energy", "maintenance"],
        supervisor_budget=6,
        specialist_budget=4,
        household_id="hh-demo-test",
    )

    assert result["status"] == "completed"
    scopes_contacted = [step.get("scope") for step in result["trace"] if step.get("kind") == "tool_call"]
    assert "energy_specialist" in scopes_contacted
    # Critical requirement: Maintenance specialist was NOT selected or called
    assert "maintenance_specialist" not in scopes_contacted

    # Finding had no suggested next investigation
    energy_findings = [f for f in result["findings"] if f["category"] == "consumption"]
    assert len(energy_findings) == 1
    assert energy_findings[0]["suggested_next_investigation"] is None
