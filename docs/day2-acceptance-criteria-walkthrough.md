# Day 2 acceptance criteria walkthrough

Source list: [w02-02-acceptance-criteria.md](assignment-w2-02/assignment-week2-day2/w02-02-acceptance-criteria.md). Contract: [w02-02-contracts.md](assignment-w2-02/assignment-week2-day2/w02-02-contracts.md) (C2) and [callRecordContract.md](callRecordContract.md) (C1).

For each criterion: **where** it is met (file links) and **how** it is implemented (with snippets).

---

## 1. `CompletionRequest`, `CompletionResult`, and `ModelAdapter` exist in `adapters/base.py` with the specified fields, names, and types

**Where:** [src/promptlab/adapters/base.py](../src/promptlab/adapters/base.py)

**How:** The three C2 types live in this file with the contracted names and types. `CompletionRequest` is a Pydantic model; `CompletionResult` holds one `CallRecord` per attempt; `ModelAdapter` is a `Protocol`.

```8:34:src/promptlab/adapters/base.py
class CompletionRequest(BaseModel):
    task: Literal["triage", "summarization", "extraction"]
    case_id: str
    prompt_id: str
    prompt_version: str
    system: str
    user_content: str
    temperature: float
    max_output_tokens: int


class CompletionResult(BaseModel):
    succeeded: bool
    text: str | None
    error_type: str | None
    records: list[CallRecord]


class ModelAdapter(Protocol):
    provider: str
    model_id: str

    def complete(
        self,
        request: CompletionRequest,
        run_id: str,
    ) -> CompletionResult: ...
```

---

## 2. `OllamaAdapter` satisfies `ModelAdapter` and can run either configured model without changing adapter code

**Where:**

- [src/promptlab/adapters/ollama.py](../src/promptlab/adapters/ollama.py)
- [src/promptlab/day2.py](../src/promptlab/day2.py)
- [tests/test_adapter_contract.py](../tests/test_adapter_contract.py) (`test_same_ollama_adapter_class_can_target_both_models`)

**How:** There is one adapter class. `provider` is a class attribute. `model_id` is an `__init__` argument, not a subclass. Day 2 instantiates that same class once per configured model.

```38:44:src/promptlab/adapters/ollama.py
class OllamaAdapter:
    provider = "ollama"

    def __init__(self, model_id: str) -> None:
        settings = Settings.from_env()
        self.model_id = model_id
        self._base_url = settings.ollama_base_url
```

```64:65:src/promptlab/day2.py
    for model in settings.models.values():
        adapter = OllamaAdapter(model_id=model.model_id)
```

```96:103:tests/test_adapter_contract.py
def test_same_ollama_adapter_class_can_target_both_models() -> None:
    mistral = OllamaAdapter(model_id=_model_id("mistral"))
    qwen = OllamaAdapter(model_id=_model_id("qwen"))

    assert type(mistral) is type(qwen)
    assert mistral.provider == "ollama"
    assert qwen.provider == "ollama"
    assert mistral.model_id != qwen.model_id
```

---

## 3. `tests/test_adapter_contract.py` passes unmodified and without a live Ollama connection

**Where:** [tests/test_adapter_contract.py](../tests/test_adapter_contract.py) (untouched), [src/promptlab/adapters/ollama.py](../src/promptlab/adapters/ollama.py)

**How:** The tests patch `httpx.post` (and `time.sleep` on the retry test) with `FakeResponse`. The adapter calls `httpx.post` and reads `status_code` plus `.json()`; it does not call `raise_for_status()`, which the fake object does not implement. No live Ollama is required.

```147:150:tests/test_adapter_contract.py
    monkeypatch.setattr(httpx, "post", fake_post)

    adapter = OllamaAdapter(model_id=_model_id("mistral"))
    result = adapter.complete(_request(), "success-run")
```

```157:172:src/promptlab/adapters/ollama.py
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
```

---

## 4. `TransientProviderError`, `PermanentProviderError`, `TruncatedResponseError`, and `UnknownModelError` exist in `errors.py`

**Where:** [src/promptlab/errors.py](../src/promptlab/errors.py)

**How:** `UnknownModelError` is the Day 1 `ValueError` subclass (not duplicated). The three Day 2 types were added beside it.

```4:17:src/promptlab/errors.py
class UnknownModelError(ValueError):
    """Raised when a model identifier is not present in the configured model table."""


class TransientProviderError(Exception):
    """Raised on timeout, connection failure, or temporary Ollama/server failure."""


class PermanentProviderError(Exception):
    """Raised on malformed request, unavailable model, or other non-retryable failure."""


class TruncatedResponseError(Exception):
    """Raised when Ollama reports that the output token ceiling was reached."""
```

---

## 5. A transient failure is retryable, a permanent failure is not, truncation is not retried, and no request produces more than three attempts

**Where:** [src/promptlab/adapters/ollama.py](../src/promptlab/adapters/ollama.py) (`complete`, `_one_attempt`, `_call_model`, `_sleep_before_retry`); tests in [tests/test_adapter_contract.py](../tests/test_adapter_contract.py)

**How:**

- Loop is `range(1, MAX_ATTEMPTS + 1)` with `MAX_ATTEMPTS = 3`.
- `_one_attempt` returns `(record, retryable)`. Transient → `True`; permanent, unknown model, truncation, and success → `False`.
- `complete` retries only when `retryable` is true **and** `attempt < 3`, then sleeps with exponential backoff plus jitter.
- HTTP timeouts / connection errors / 5xx / 408 / 429 → transient; other 4xx and bad JSON → permanent; mapped `stop_reason == "length"` → `TruncatedResponseError`, not retried.

```24:24:src/promptlab/adapters/ollama.py
MAX_ATTEMPTS = 3
```

```51:70:src/promptlab/adapters/ollama.py
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
```

```88:146:src/promptlab/adapters/ollama.py
        except TransientProviderError:
            ...
            return record, True
        except PermanentProviderError:
            ...
            return record, False
        ...
        if mapped.stop_reason == "length":
            record = self._record(
                request,
                run_id,
                attempt,
                mapped,
                error_type=TruncatedResponseError.__name__,
            )
            return record, False
```

```171:177:src/promptlab/adapters/ollama.py
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            raise TransientProviderError(str(exc)) from exc

        latency_ms = _elapsed_ms(started)
        if response.status_code >= 500 or response.status_code in _TRANSIENT_HTTP_STATUSES:
            raise TransientProviderError(f"HTTP {response.status_code}")
        if response.status_code >= 400:
            raise PermanentProviderError(f"HTTP {response.status_code}")
```

```231:233:src/promptlab/adapters/ollama.py
def _sleep_before_retry(failed_attempt: int) -> None:
    delay = (2 ** (failed_attempt - 1)) + random.random()
    time.sleep(delay)
```

Covered by `test_transient_failure_retries_and_records_each_attempt`, `test_permanent_failure_is_not_retried`, and `test_truncation_is_recorded_and_not_retried`.

---

## 6. Every actual attempt produces a `CallRecord` with `attempt` incrementing from 1

**Where:** [src/promptlab/adapters/ollama.py](../src/promptlab/adapters/ollama.py) (`complete`, `_one_attempt`, `_record`)

**How:** Each loop iteration calls `_one_attempt`, which always builds a `CallRecord` (success, transport failure, 4xx, or truncation). The loop variable starts at 1 and is written onto the record. `CompletionResult.records` is that list in order.

```51:53:src/promptlab/adapters/ollama.py
        for attempt in range(1, MAX_ATTEMPTS + 1):
            record, retryable = self._one_attempt(request, run_id, attempt)
            records.append(record)
```

```203:213:src/promptlab/adapters/ollama.py
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
```

The flaky-connect test expects attempts `[1, 2, 3]`:

```175:186:tests/test_adapter_contract.py
    def flaky_post(*args, **kwargs) -> FakeResponse:
        nonlocal calls
        calls += 1
        if calls < 3:
            raise httpx.ConnectError("temporary connection failure")
        return FakeResponse(text="eventual success")

    monkeypatch.setattr(httpx, "post", flaky_post)
    monkeypatch.setattr("time.sleep", lambda _: None)

    adapter = OllamaAdapter(model_id=_model_id("mistral"))
    result = adapter.complete(_request(), "retry-run")
```

---

## 7. `usage.py` is unchanged from Day 1

**Where:** [src/promptlab/usage.py](../src/promptlab/usage.py)

**How:** Day 2 consumes C1 (`CallRecord`, `compute_cost`, `append_record`) and does not edit that file. Git status shows `usage.py` unmodified. Day 2 imports those helpers rather than reimplementing them:

```13:16:src/promptlab/day2.py
from promptlab.adapters.base import CompletionRequest
from promptlab.adapters.ollama import OllamaAdapter
from promptlab.config import PROJECT_ROOT, Settings
from promptlab.usage import append_record
```

```18:42:src/promptlab/usage.py
class CallRecord(BaseModel):
    """One model-call attempt with the Day 1 twenty-field contract."""

    model_config = ConfigDict(extra="forbid")

    record_id: str
    run_id: str
    timestamp: datetime
    provider: Literal["ollama"]
    model_id: str
    task: Literal["triage", "summarization", "extraction"]
    case_id: str
    prompt_id: str
    prompt_version: str
    attempt: int
    temperature: float
    max_output_tokens: int
    input_tokens: int
    output_tokens: int
    cached_input_tokens: int | None = None
    latency_ms: int
    cost_usd: float
    stop_reason: str | None = None
    error_type: str | None = None
    response_text: str | None = None
```

---

## 8. Every Day 2 record validates against the Day 1 `CallRecord` contract

**Where:** [src/promptlab/adapters/ollama.py](../src/promptlab/adapters/ollama.py) (`_record`); evidence [docs/day2-run.jsonl](day2-run.jsonl); schema [src/promptlab/usage.py](../src/promptlab/usage.py) and [docs/callRecordContract.md](callRecordContract.md)

**How:** `_record` constructs a `CallRecord` with the twenty C1 fields. Pydantic `extra="forbid"` rejects extra keys. All 24 lines in `docs/day2-run.jsonl` validate as `CallRecord`.

```191:224:src/promptlab/adapters/ollama.py
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
            ...
            cost_usd=cost_usd,
            stop_reason=mapped.stop_reason,
            error_type=error_type,
            response_text=mapped.response_text,
        )
```

Day 2 appends every returned record, then copies the run file to the evidence path:

```77:87:src/promptlab/day2.py
            result = adapter.complete(request, run_id)
            for record in result.records:
                append_record(record, run_id)
                record_count += 1
            ...
    run_path = Path("runs") / f"{run_id}.jsonl"
    shutil.copyfile(run_path, EVIDENCE_PATH)
```

---

## 9. All twelve summarization cases are run against both Mistral and Qwen

**Where:** [src/promptlab/day2.py](../src/promptlab/day2.py); [cases/summarization.jsonl](../cases/summarization.jsonl); [docs/day2-run.jsonl](day2-run.jsonl)

**How:** `load_summarization_cases()` reads the twelve cases and aborts if the count is not 12. Nested loops run every configured model × every case under one `run_id`. Evidence: 24 records, case ids S01–S12, both configured models.

```36:42:src/promptlab/day2.py
def load_summarization_cases(path: Path = SUMMARIZATION_CASES_PATH) -> list[SummarizationCase]:
    cases: list[SummarizationCase] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        cases.append(SummarizationCase.model_validate_json(line))
    return cases
```

```58:77:src/promptlab/day2.py
    if len(cases) != 12:
        raise RuntimeError(f"Expected 12 summarization cases, found {len(cases)}")

    run_id = str(uuid4())
    record_count = 0

    for model in settings.models.values():
        adapter = OllamaAdapter(model_id=model.model_id)
        for case in cases:
            request = CompletionRequest(
                task=case.task,
                case_id=case.id,
                ...
            )
            result = adapter.complete(request, run_id)
```

---

## 10. For a given case, `task`, `case_id`, `prompt_id`, `prompt_version`, `temperature`, and `max_output_tokens` are identical across the two model runs

**Where:** [src/promptlab/day2.py](../src/promptlab/day2.py) request construction; confirmed in [docs/day2-run.jsonl](day2-run.jsonl)

**How:** Those fields come from the case, shared constants, and `Settings` — not from which model is selected. Only `model_id` on the adapter (and thus on the record) changes.

```20:22:src/promptlab/day2.py
PROMPT_ID = "baseline"
PROMPT_VERSION = "v0"
MAX_OUTPUT_TOKENS = 1024
```

```67:76:src/promptlab/day2.py
            request = CompletionRequest(
                task=case.task,
                case_id=case.id,
                prompt_id=PROMPT_ID,
                prompt_version=PROMPT_VERSION,
                system="",
                user_content=render_prompt(template, case.source),
                temperature=settings.temperature,
                max_output_tokens=MAX_OUTPUT_TOKENS,
            )
```

Shared values in the live run: `task=summarization`, `prompt_id=baseline`, `prompt_version=v0`, `temperature=0.0`, `max_output_tokens=1024`.

---

## 11. Both models record `provider="ollama"` and are distinguished by their configured `model_id`

**Where:** [src/promptlab/adapters/ollama.py](../src/promptlab/adapters/ollama.py) (`_record`); [src/promptlab/config.py](../src/promptlab/config.py)

**How:** Every record hardcodes `provider="ollama"` (this lab’s runtime). `model_id` is `self.model_id`, loaded from `Settings.models` (`MODEL_A` / `MODEL_B`).

```203:208:src/promptlab/adapters/ollama.py
        return CallRecord(
            record_id=str(uuid4()),
            run_id=run_id,
            timestamp=datetime.now(UTC),
            provider="ollama",
            model_id=self.model_id,
```

```49:58:src/promptlab/config.py
        model_a = os.getenv("MODEL_A", "mistral:7b")
        model_b = os.getenv("MODEL_B", "qwen3:8b")
        return cls(
            ...
            models={
                "mistral": ModelConfig(logical_name="mistral", model_id=model_a),
                "qwen": ModelConfig(logical_name="qwen", model_id=model_b),
            },
```

---

## 12. No model identifier literal appears in `day2.py` or the adapter implementation. Model identifiers come from configuration

**Where:** identifiers only in [src/promptlab/config.py](../src/promptlab/config.py); consumers [src/promptlab/day2.py](../src/promptlab/day2.py) and [src/promptlab/adapters/ollama.py](../src/promptlab/adapters/ollama.py)

**How:** Config reads env with `mistral:7b` / `qwen3:8b` defaults. `day2.py` iterates `settings.models.values()` and passes `model.model_id`. The adapter stores whatever string it was given. No model-id literals in Day 2 or adapter source.

```64:65:src/promptlab/day2.py
    for model in settings.models.values():
        adapter = OllamaAdapter(model_id=model.model_id)
```

```41:44:src/promptlab/adapters/ollama.py
    def __init__(self, model_id: str) -> None:
        settings = Settings.from_env()
        self.model_id = model_id
        self._base_url = settings.ollama_base_url
```

---

## 13. Ollama-specific response field names do not appear outside `src/promptlab/adapters/`

**Where:** mapping only in [src/promptlab/adapters/ollama.py](../src/promptlab/adapters/ollama.py) (`_map_payload`); call site [src/promptlab/day2.py](../src/promptlab/day2.py) uses `CallRecord` field names only

**How:** `prompt_eval_count`, `eval_count`, and `done_reason` are translated inside the adapter into `input_tokens`, `output_tokens`, and `stop_reason`. `day2.py` never mentions those Ollama names.

```236:242:src/promptlab/adapters/ollama.py
def _map_payload(payload: dict[str, Any], latency_ms: int) -> _MappedResponse:
    return _MappedResponse(
        latency_ms=latency_ms,
        input_tokens=_require_int(payload, "prompt_eval_count"),
        output_tokens=_require_int(payload, "eval_count"),
        stop_reason=_optional_str(payload.get("done_reason")),
        response_text=_response_text(payload),
    )
```

Day 1’s [src/promptlab/day1.py](../src/promptlab/day1.py) still uses the raw names; that is prior-day code, not Day 2 calling code.

---

## 14. `docs/day2-comparison.md` reports counts and token/latency measurements for both models and does not invent a dollar-cost comparison

**Where:** [docs/day2-comparison.md](day2-comparison.md), numbers from [docs/day2-run.jsonl](day2-run.jsonl)

**How:** Tables for success counts (12/12 each), input/output/combined token totals, and median/max (and min) latency for both models. The observation is tied to those figures. Local charge is stated as 0.0; there is no invented dollar-cost comparison.

```3:24:docs/day2-comparison.md
Evidence: `docs/day2-run.jsonl` (24 records, one `run_id`, 12 summarization cases × 2 models, `max_output_tokens=1024`, temperature 0.0, baseline v0). Every attempt succeeded (`error_type` null, `stop_reason=stop`). Local provider charge is 0.0 for both models; this comparison does not use dollar cost.

## Success counts

| Model | Successful cases | Failed cases | Attempts recorded |
| --- | ---: | ---: | ---: |
| Mistral (`mistral:7b`) | 12 / 12 | 0 | 12 |
| Qwen (`qwen3:8b`) | 12 / 12 | 0 | 12 |

## Token totals
...
## Latency (ms)
```

---

## 15. No cloud credential, key, or populated `.env` file appears in the diff

**Where:** [.gitignore](../.gitignore); [src/promptlab/config.py](../src/promptlab/config.py)

**How:** Day 2 uses local Ollama via `OLLAMA_BASE_URL`. No Anthropic/Azure keys. `.env` is gitignored. The Day 2 diff is adapters, `errors.py`, `day2.py`, and evidence docs — no secrets file.

```1:8:.gitignore
.env
.venv/
__pycache__/
.pytest_cache/
.mypy_cache/
.ruff_cache/
*.py[cod]
runs/
```

---

## 16. `pytest`, `ruff`, and `mypy` report no findings on the changed files

**Where:** changed Python — [src/promptlab/errors.py](../src/promptlab/errors.py), [src/promptlab/adapters/](../src/promptlab/adapters/), [src/promptlab/day2.py](../src/promptlab/day2.py)

**How:** Last check in the lab container, on the Day 2 sources plus the unmodified contract tests:

```text
uv run pytest tests/test_adapter_contract.py tests/test_usage_contract.py
uv run ruff check src/promptlab/errors.py src/promptlab/adapters src/promptlab/day2.py
uv run mypy src/promptlab/errors.py src/promptlab/adapters src/promptlab/day2.py
```

Result: 14 tests passed; ruff and mypy reported no findings.
