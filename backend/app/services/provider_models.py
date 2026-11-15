from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
import json
import time
from typing import Any, Protocol

import httpx
from google.api_core.exceptions import DeadlineExceeded, GoogleAPIError, ResourceExhausted, ServiceUnavailable
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import ValidationError

from app.config import get_settings
from app.schemas_agents import SupervisorDecision


PROVIDER_NAMES = ("gemini", "groq", "openrouter")


class ProviderCallError(RuntimeError):
    def __init__(
        self,
        provider: str,
        model: str,
        category: str,
        *,
        http_status: int | None = None,
    ) -> None:
        self.provider = provider
        self.model = model
        self.category = category
        self.http_status = http_status
        super().__init__(f"{provider} provider call failed: {category}.")


class ProviderExhaustedError(RuntimeError):
    def __init__(self, attempts: list[dict[str, Any]]) -> None:
        self.attempts = attempts
        super().__init__("All configured LLM providers failed.")


class ProviderOutcome:
    def __init__(
        self,
        *,
        decision: SupervisorDecision | None = None,
        error: Exception | None = None,
        cancelled: bool = False,
    ) -> None:
        self.decision = decision
        self.error = error
        self.cancelled = cancelled


class ProviderDecisionModel(Protocol):
    provider: str
    model: str
    last_metadata: dict[str, Any]

    def decide(self, state: dict[str, Any]) -> SupervisorDecision:
        ...


def decision_prompt(state: dict[str, Any]) -> str:
    context = state.get("investigation_context")
    context_payload = context.model_dump(mode="json") if context is not None else None
    return (
        "You are a bounded household investigation supervisor. "
        "Return one JSON object matching the requested decision schema. "
        "Choose investigate only when evidence or the goal justifies it. "
        "You may stop, choose one available specialist, or choose another after findings. "
        "Never perform tools or modify data. "
        f"Goal: {state['goal']}\n"
        f"Available specialists: {state['remaining_domains']}\n"
        f"Investigation context: {json.dumps(context_payload)}\n"
        f"Previous decisions: {json.dumps(state['decisions'])}\n"
        f"Findings from tools: {json.dumps(state['findings'])}\n"
        f"Supervisor calls remaining: {state['supervisor_budget'] - state['supervisor_calls']}\n"
    )


def decision_schema() -> dict[str, Any]:
    schema = SupervisorDecision.model_json_schema()
    schema["required"] = list(schema["properties"])
    schema["additionalProperties"] = False
    return schema


def _http_failure(provider: str, model: str, response: httpx.Response) -> ProviderCallError:
    if response.status_code == 429:
        category = "rate_limit"
    elif response.status_code >= 500:
        category = "provider_unavailable"
    elif response.status_code in {401, 403}:
        category = "authentication"
    else:
        category = "provider_error"
    return ProviderCallError(provider, model, category, http_status=response.status_code)


def _invoke_provider(
    provider: ProviderDecisionModel,
    state: dict[str, Any],
    entry: dict[str, Any] | None = None,
) -> ProviderOutcome:
    try:
        outcome = ProviderOutcome(decision=provider.decide(state))
    except ProviderCallError as exc:
        outcome = ProviderOutcome(error=exc)
    except Exception as exc:
        outcome = ProviderOutcome(error=exc)
    if entry is not None and outcome.decision is not None:
        entry["success"] = True
    return outcome


class GeminiDecisionModel:
    provider = "gemini"
    _default_timeout_seconds = 60

    def __init__(self) -> None:
        self._settings = get_settings()
        self.model = self._settings.gemini_model
        self.last_metadata: dict[str, Any] = {}
        self._structured = None
        self._timeout_seconds = self._default_timeout_seconds

    def set_timeout(self, timeout_seconds: float) -> None:
        self._timeout_seconds = min(self._default_timeout_seconds, max(0.001, timeout_seconds))

    def decide(self, state: dict[str, Any]) -> SupervisorDecision:
        if not self._settings.gemini_api_key:
            raise ProviderCallError(self.provider, self.model, "configuration")
        if self._structured is None:
            model = ChatGoogleGenerativeAI(
                model=self.model,
                google_api_key=self._settings.gemini_api_key,
                temperature=0,
                timeout=self._timeout_seconds,
                max_retries=0,
            )
            self._structured = model.with_structured_output(SupervisorDecision)
        try:
            decision = self._structured.invoke(decision_prompt(state))
            return SupervisorDecision.model_validate(decision)
        except DeadlineExceeded as exc:
            raise ProviderCallError(self.provider, self.model, "timeout") from exc
        except ResourceExhausted as exc:
            raise ProviderCallError(self.provider, self.model, "rate_limit") from exc
        except ServiceUnavailable as exc:
            raise ProviderCallError(self.provider, self.model, "provider_unavailable") from exc
        except GoogleAPIError as exc:
            status = getattr(getattr(exc, "response", None), "status_code", None)
            category = "provider_error"
            if status == 429:
                category = "rate_limit"
            elif status is not None and status >= 500:
                category = "provider_unavailable"
            raise ProviderCallError(self.provider, self.model, category, http_status=status) from exc
        except (TimeoutError, httpx.TimeoutException) as exc:
            raise ProviderCallError(self.provider, self.model, "timeout") from exc
        except (ConnectionError, OSError) as exc:
            raise ProviderCallError(self.provider, self.model, "connection") from exc
        except ValidationError as exc:
            raise ProviderCallError(self.provider, self.model, "schema_validation") from exc


class HttpDecisionModel:
    endpoint: str
    _default_timeout_seconds = 30

    def __init__(self, provider: str, api_key: str, model: str, endpoint: str) -> None:
        self.provider = provider
        self._api_key = api_key
        self.model = model
        self.endpoint = endpoint
        self.last_metadata: dict[str, Any] = {}
        self._timeout_seconds = self._default_timeout_seconds

    def set_timeout(self, timeout_seconds: float) -> None:
        self._timeout_seconds = min(self._default_timeout_seconds, max(0.001, timeout_seconds))

    def decide(self, state: dict[str, Any]) -> SupervisorDecision:
        if not self._api_key:
            raise ProviderCallError(self.provider, self.model, "configuration")
        try:
            payload = {
                "model": self.model,
                "messages": [{"role": "user", "content": decision_prompt(state)}],
                "temperature": 0,
                "max_completion_tokens": 1024,
                "response_format": {
                    "type": "json_schema",
                    "json_schema": {
                        "name": "supervisor_decision",
                        "strict": True,
                        "schema": decision_schema(),
                    },
                },
            }
            payload.update(self._provider_payload())
            response = httpx.post(
                self.endpoint,
                headers={"Authorization": f"Bearer {self._api_key}"},
                json=payload,
                timeout=self._timeout_seconds,
            )
            if not response.is_success:
                raise _http_failure(self.provider, self.model, response)
            body = response.json()
            self.last_metadata = {
                "model": body.get("model", self.model),
                "provider": body.get("provider"),
            }
            content = body["choices"][0]["message"].get("content") or ""
            if not content:
                raise ProviderCallError(self.provider, self.model, "empty_response")
            return SupervisorDecision.model_validate_json(content)
        except ProviderCallError:
            raise
        except httpx.HTTPStatusError as exc:
            raise _http_failure(self.provider, self.model, exc.response) from exc
        except httpx.TimeoutException as exc:
            raise ProviderCallError(self.provider, self.model, "timeout") from exc
        except httpx.ConnectError as exc:
            raise ProviderCallError(self.provider, self.model, "connection") from exc
        except httpx.RequestError as exc:
            raise ProviderCallError(self.provider, self.model, "connection") from exc
        except ValidationError as exc:
            raise ProviderCallError(self.provider, self.model, "schema_validation") from exc
        except (json.JSONDecodeError, KeyError, IndexError, TypeError) as exc:
            raise ProviderCallError(self.provider, self.model, "malformed_response") from exc

    def _provider_payload(self) -> dict[str, Any]:
        return {}


class GroqDecisionModel(HttpDecisionModel):
    def __init__(self) -> None:
        settings = get_settings()
        super().__init__("groq", settings.groq_api_key, settings.groq_model, "https://api.groq.com/openai/v1/chat/completions")

    def _provider_payload(self) -> dict[str, Any]:
        return {"reasoning_effort": "low", "include_reasoning": False}


class OpenRouterDecisionModel(HttpDecisionModel):
    def __init__(self) -> None:
        settings = get_settings()
        super().__init__(
            "openrouter",
            settings.openrouter_api_key,
            settings.openrouter_model,
            "https://openrouter.ai/api/v1/chat/completions",
        )


def _provider_model(name: str) -> ProviderDecisionModel:
    models = {
        "gemini": GeminiDecisionModel,
        "groq": GroqDecisionModel,
        "openrouter": OpenRouterDecisionModel,
    }
    try:
        return models[name]()
    except KeyError as exc:
        raise RuntimeError(f"Unsupported LLM provider: {name}") from exc


class StaggeredDecisionModel:
    def __init__(
        self,
        providers: list[str],
        *,
        deadline_seconds: float = 50,
        stagger_seconds: float = 10,
        sleep: Any = asyncio.sleep,
        clock: Any = time.monotonic,
    ) -> None:
        self._providers = providers
        self._deadline_seconds = deadline_seconds
        self._stagger_seconds = stagger_seconds
        self._sleep = sleep
        self._clock = clock
        self.last_attempts: list[dict[str, Any]] = []

    def decide(self, state: dict[str, Any]) -> SupervisorDecision:
        return asyncio.run(self.decide_async(state))

    async def decide_async(self, state: dict[str, Any]) -> SupervisorDecision:
        self.last_attempts = []
        race_started = self._clock()
        entries = [
            {
                "provider": name,
                "model": None,
                "attempt": index,
                "scheduled_at_ms": round(index * self._stagger_seconds * 1000, 2),
                "started_at_ms": None,
                "elapsed_ms": None,
                "outcome": "scheduled",
                "success": False,
                "failure_category": None,
                "http_status": None,
                "cancelled": False,
                "winner": False,
                "fallback_triggered": False,
                "deadline_exhausted": False,
            }
            for index, name in enumerate(self._providers)
        ]
        executor = ThreadPoolExecutor(max_workers=len(self._providers), thread_name_prefix="homepilot-provider")
        tasks = {
            asyncio.create_task(
                self._run_after_delay(
                    index,
                    name,
                    state,
                    entry=entries[index],
                    entries=entries,
                    race_started=race_started,
                    executor=executor,
                )
            ): index
            for index, name in enumerate(self._providers)
        }
        deadline = race_started + self._deadline_seconds
        winner: tuple[int, SupervisorDecision] | None = None
        try:
            while tasks and self._clock() < deadline:
                timeout = max(0, deadline - self._clock())
                done, _ = await asyncio.wait(
                    tasks,
                    timeout=timeout,
                    return_when=asyncio.FIRST_COMPLETED,
                )
                if not done:
                    break
                unexpected_error: Exception | None = None
                for task in sorted(done, key=lambda item: tasks[item]):
                    index = tasks.pop(task)
                    outcome = task.result()
                    if outcome.error is not None and not isinstance(outcome.error, ProviderCallError):
                        unexpected_error = outcome.error
                    if outcome.decision is not None and winner is None:
                        winner = (index, outcome.decision)
                        entries[index]["winner"] = True
                        entries[index]["success"] = True
                        entries[index]["outcome"] = "success"
                    elif outcome.decision is not None:
                        entries[index]["success"] = True
                        entries[index]["outcome"] = "lost_race"
                if winner is not None:
                    break
                if unexpected_error is not None:
                    raise unexpected_error
            if winner is not None:
                for task, index in list(tasks.items()):
                    entries[index]["cancelled"] = True
                    entries[index]["outcome"] = "cancelled"
                    entries[index]["fallback_triggered"] = False
                    task.cancel()
                    task.add_done_callback(_consume_task)
                for entry in entries:
                    if entry["outcome"] == "success" and not entry["winner"]:
                        entry["outcome"] = "lost_race"
                return winner[1]
            for task, index in list(tasks.items()):
                entries[index]["deadline_exhausted"] = True
                entries[index]["cancelled"] = True
                entries[index]["outcome"] = "cancelled"
                task.cancel()
                task.add_done_callback(_consume_task)
            raise ProviderExhaustedError(_finalize_attempts(entries))
        finally:
            self.last_attempts = _finalize_attempts(entries)
            executor.shutdown(wait=False, cancel_futures=True)

    async def _run_after_delay(
        self,
        index: int,
        provider_name: str,
        state: dict[str, Any],
        entry: dict[str, Any],
        entries: list[dict[str, Any]],
        race_started: float,
        executor: ThreadPoolExecutor,
    ) -> ProviderOutcome:
        try:
            await self._sleep(index * self._stagger_seconds)
            if index:
                await asyncio.sleep(self._stagger_seconds)
            if any(previous["success"] for previous in entries[:index]):
                entry["cancelled"] = True
                entry["outcome"] = "cancelled"
                return ProviderOutcome(cancelled=True)
            provider = _provider_model(provider_name)
            entry["model"] = provider.model
            entry["started_at_ms"] = round((self._clock() - race_started) * 1000, 2)
            entry["outcome"] = "running"
            started = self._clock()
            remaining_seconds = race_started + self._deadline_seconds - self._clock()
            if isinstance(provider, (GeminiDecisionModel, HttpDecisionModel)):
                provider.set_timeout(remaining_seconds)
            future = asyncio.get_running_loop().run_in_executor(
                executor,
                _invoke_provider,
                provider,
                state,
                entry,
            )
            outcome = await future
            if outcome.error is not None:
                if isinstance(outcome.error, ProviderCallError):
                    entry["model"] = outcome.error.model
                    entry["failure_category"] = outcome.error.category
                    entry["http_status"] = outcome.error.http_status
                    entry["elapsed_ms"] = round((self._clock() - started) * 1000, 2)
                    entry["outcome"] = "failed"
                else:
                    entry["elapsed_ms"] = round((self._clock() - started) * 1000, 2)
                    entry["outcome"] = "error"
                return outcome
            decision = outcome.decision
            entry["model"] = provider.last_metadata.get("model", provider.model)
            entry["elapsed_ms"] = round((self._clock() - started) * 1000, 2)
            entry["success"] = True
            return ProviderOutcome(decision=decision)
        except asyncio.CancelledError:
            entry["cancelled"] = True
            entry["outcome"] = "cancelled"
            return ProviderOutcome(cancelled=True)


def _consume_task(task: asyncio.Task[Any]) -> None:
    try:
        task.result()
    except BaseException:
        return


def _finalize_attempts(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    for index, entry in enumerate(entries):
        if entry["outcome"] == "failed":
            entry["fallback_triggered"] = index < len(entries) - 1
    return [{"kind": "provider_attempt", **entry} for entry in entries]


class FailoverDecisionModel:
    def __init__(self) -> None:
        settings = get_settings()
        self._provider = settings.llm_provider
        self._order = settings.llm_provider_order_list
        self.last_attempts: list[dict[str, Any]] = []

    def decide(self, state: dict[str, Any]) -> SupervisorDecision:
        if self._provider == "auto":
            model = StaggeredDecisionModel(self._order)
            decision = model.decide(state)
            self.last_attempts = model.last_attempts
            return decision
        providers = [self._provider]
        self.last_attempts = []
        provider_name = providers[0]
        provider = _provider_model(provider_name)
        started = time.perf_counter()
        try:
            decision = provider.decide(state)
            self.last_attempts.append(
                {
                    "kind": "provider_attempt",
                    "provider": provider_name,
                    "model": provider.last_metadata.get("model", provider.model),
                    "attempt": 1,
                    "elapsed_ms": round((time.perf_counter() - started) * 1000, 2),
                    "outcome": "success",
                    "failure_category": None,
                    "http_status": None,
                    "cancelled": False,
                    "winner": True,
                    "deadline_exhausted": False,
                }
            )
            return decision
        except ProviderCallError as exc:
            self.last_attempts.append(
                {
                    "kind": "provider_attempt",
                    "provider": exc.provider,
                    "model": exc.model,
                    "attempt": 1,
                    "elapsed_ms": round((time.perf_counter() - started) * 1000, 2),
                    "outcome": "failed",
                    "failure_category": exc.category,
                    "http_status": exc.http_status,
                    "cancelled": False,
                    "winner": False,
                    "deadline_exhausted": False,
                }
            )
            raise ProviderExhaustedError(self.last_attempts) from exc
