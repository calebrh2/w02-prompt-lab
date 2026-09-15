"""Reusable Ollama adapter for any configured local model."""

from __future__ import annotations

import random
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import httpx

from promptlab.adapters.base import CompletionRequest, CompletionResult
from promptlab.config import Settings
from promptlab.errors import (
    PermanentProviderError,
    TransientProviderError,
    TruncatedResponseError,
    UnknownModelError,
)
from promptlab.usage import CallRecord, compute_cost

MAX_ATTEMPTS = 3
GENERATE_TIMEOUT_SECONDS = 180.0
_TRANSIENT_HTTP_STATUSES = {408, 429}


@dataclass(frozen=True)
class _MappedResponse:
    latency_ms: int
    input_tokens: int
    output_tokens: int
    stop_reason: str | None
    response_text: str | None


class OllamaAdapter:
    provider = "ollama"

    def __init__(self, model_id: str) -> None:
        settings = Settings.from_env()
        self.model_id = model_id
        self._base_url = settings.ollama_base_url

    def complete(self, request: CompletionRequest, run_id: str) -> CompletionResult:
        records: list[CallRecord] = []
        last_error_name: str | None = None
        last_text: str | None = None

        for attempt in range(1, MAX_ATTEMPTS + 1):
            record, retryable = self._one_attempt(request, run_id, attempt)
            records.append(record)
            last_error_name = record.error_type
            last_text = record.response_text
            if record.error_type is None:
                return CompletionResult(
                    succeeded=True,
                    text=record.response_text,
                    error_type=None,
                    records=records,
                )
            if not retryable or attempt == MAX_ATTEMPTS:
                return CompletionResult(
                    succeeded=False,
                    text=last_text,
                    error_type=last_error_name,
                    records=records,
                )
            _sleep_before_retry(attempt)

        return CompletionResult(
            succeeded=False,
            text=last_text,
            error_type=last_error_name,
            records=records,
        )

    def _one_attempt(
        self,
        request: CompletionRequest,
        run_id: str,
        attempt: int,
    ) -> tuple[CallRecord, bool]:
        started = time.perf_counter()
        try:
            mapped = self._call_model(request)
        except TransientProviderError:
            latency_ms = _elapsed_ms(started)
            record = self._record(
                request,
                run_id,
                attempt,
                _MappedResponse(
                    latency_ms=latency_ms,
                    input_tokens=0,
                    output_tokens=0,
                    stop_reason=None,
                    response_text=None,
                ),
                error_type=TransientProviderError.__name__,
            )
            return record, True
        except PermanentProviderError:
            latency_ms = _elapsed_ms(started)
            record = self._record(
                request,
                run_id,
                attempt,
                _MappedResponse(
                    latency_ms=latency_ms,
                    input_tokens=0,
                    output_tokens=0,
                    stop_reason=None,
                    response_text=None,
                ),
                error_type=PermanentProviderError.__name__,
            )
            return record, False
        except UnknownModelError:
            latency_ms = _elapsed_ms(started)
            record = self._record(
                request,
                run_id,
                attempt,
                _MappedResponse(
                    latency_ms=latency_ms,
                    input_tokens=0,
                    output_tokens=0,
                    stop_reason=None,
                    response_text=None,
                ),
                error_type=UnknownModelError.__name__,
                cost_usd=0.0,
            )
            return record, False

        if mapped.stop_reason == "length":
            record = self._record(
                request,
                run_id,
                attempt,
                mapped,
                error_type=TruncatedResponseError.__name__,
            )
            return record, False

        record = self._record(request, run_id, attempt, mapped, error_type=None)
        return record, False

    def _call_model(self, request: CompletionRequest) -> _MappedResponse:
        prompt = request.user_content
        if request.system:
            prompt = f"{request.system}\n\n{request.user_content}"

        started = time.perf_counter()
        try:
            response = httpx.post(
                f"{self._base_url}/api/generate",
                json={
                    "model": self.model_id,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": request.temperature,
                        "num_predict": request.max_output_tokens,
                    },
                },
                timeout=GENERATE_TIMEOUT_SECONDS,
            )
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            raise TransientProviderError(str(exc)) from exc

        latency_ms = _elapsed_ms(started)
        if response.status_code >= 500 or response.status_code in _TRANSIENT_HTTP_STATUSES:
            raise TransientProviderError(f"HTTP {response.status_code}")
        if response.status_code >= 400:
            raise PermanentProviderError(f"HTTP {response.status_code}")

        try:
            payload: object = response.json()
        except ValueError as exc:
            raise PermanentProviderError("malformed JSON response") from exc

        if not isinstance(payload, dict):
            raise PermanentProviderError(
                f"Expected JSON object from provider, got {type(payload).__name__}"
            )
        return _map_payload(payload, latency_ms)

    def _record(
        self,
        request: CompletionRequest,
        run_id: str,
        attempt: int,
        mapped: _MappedResponse,
        *,
        error_type: str | None,
        cost_usd: float | None = None,
    ) -> CallRecord:
        if cost_usd is None:
            cost_usd = compute_cost(self.model_id, mapped.input_tokens, mapped.output_tokens)
        return CallRecord(
            record_id=str(uuid4()),
            run_id=run_id,
            timestamp=datetime.now(UTC),
            provider="ollama",
            model_id=self.model_id,
            task=request.task,
            case_id=request.case_id,
            prompt_id=request.prompt_id,
            prompt_version=request.prompt_version,
            attempt=attempt,
            temperature=request.temperature,
            max_output_tokens=request.max_output_tokens,
            input_tokens=mapped.input_tokens,
            output_tokens=mapped.output_tokens,
            cached_input_tokens=None,
            latency_ms=mapped.latency_ms,
            cost_usd=cost_usd,
            stop_reason=mapped.stop_reason,
            error_type=error_type,
            response_text=mapped.response_text,
        )


def _elapsed_ms(started: float) -> int:
    return max(0, round((time.perf_counter() - started) * 1000))


def _sleep_before_retry(failed_attempt: int) -> None:
    delay = (2 ** (failed_attempt - 1)) + random.random()
    time.sleep(delay)


def _map_payload(payload: dict[str, Any], latency_ms: int) -> _MappedResponse:
    return _MappedResponse(
        latency_ms=latency_ms,
        input_tokens=_require_int(payload, "prompt_eval_count"),
        output_tokens=_require_int(payload, "eval_count"),
        stop_reason=_optional_str(payload.get("done_reason")),
        response_text=_response_text(payload),
    )


def _require_int(payload: dict[str, Any], key: str) -> int:
    value = payload.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        raise PermanentProviderError(f"field {key!r} must be an int, got {value!r}")
    return value


def _optional_str(value: object) -> str | None:
    return value if isinstance(value, str) else None


def _response_text(payload: dict[str, Any]) -> str | None:
    response = payload.get("response")
    if isinstance(response, str):
        return response
    message = payload.get("message")
    if isinstance(message, dict):
        content = message.get("content")
        if isinstance(content, str):
            return content
    return None
