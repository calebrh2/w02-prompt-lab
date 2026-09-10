"""Day 1 local Ollama instrumentation script."""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx
from pydantic import BaseModel, ConfigDict

from promptlab.config import PROJECT_ROOT, Settings

DAY1_CASE_IDS = ("E12", "E07", "E11")
EXTRACTION_CASES_PATH = PROJECT_ROOT / "cases" / "extraction.jsonl"
BASELINE_PROMPT_PATH = PROJECT_ROOT / "src" / "prompts" / "baseline.v0.md"
TEMPERATURE = 0.0
DEFAULT_NUM_PREDICT = 256
GENERATE_TIMEOUT_SECONDS = 180.0


class ExtractionCase(BaseModel):
    """One extraction corpus case."""

    model_config = ConfigDict(extra="forbid")

    id: str
    task: str
    source: str


@dataclass(frozen=True)
class GenerateResult:
    """One Ollama generate call, mapped onto CallRecord field names."""

    payload: dict[str, Any]
    latency_ms: int
    input_tokens: int
    output_tokens: int
    stop_reason: str | None
    response_text: str | None


def load_extraction_cases(path: Path = EXTRACTION_CASES_PATH) -> dict[str, ExtractionCase]:
    cases: dict[str, ExtractionCase] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        case = ExtractionCase.model_validate_json(line)
        cases[case.id] = case
    return cases


def select_day1_cases(
    cases: dict[str, ExtractionCase],
    case_ids: tuple[str, ...] = DAY1_CASE_IDS,
) -> list[ExtractionCase]:
    missing = [case_id for case_id in case_ids if case_id not in cases]
    if missing:
        raise KeyError(f"Missing extraction cases: {', '.join(missing)}")
    return [cases[case_id] for case_id in case_ids]


def load_baseline_prompt(path: Path = BASELINE_PROMPT_PATH) -> str:
    return path.read_text(encoding="utf-8")


def render_prompt(template: str, document_text: str) -> str:
    return template.replace("{document_text}", document_text)


def _require_int(payload: dict[str, Any], key: str) -> int:
    value = payload.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"Ollama field {key!r} must be an int, got {value!r}")
    return value


def map_generate_result(payload: dict[str, Any], latency_ms: int) -> GenerateResult:
    done_reason = payload.get("done_reason")
    response_text = payload.get("response")
    return GenerateResult(
        payload=payload,
        latency_ms=latency_ms,
        input_tokens=_require_int(payload, "prompt_eval_count"),
        output_tokens=_require_int(payload, "eval_count"),
        stop_reason=done_reason if isinstance(done_reason, str) else None,
        response_text=response_text if isinstance(response_text, str) else None,
    )


def call_mistral(
    settings: Settings,
    prompt: str,
    *,
    temperature: float = TEMPERATURE,
    num_predict: int = DEFAULT_NUM_PREDICT,
) -> GenerateResult:
    model = settings.models["mistral"]
    # latency_ms is wall-clock time around the HTTP call, not Ollama's (outlined in call record contract)
    # total_duration / eval_duration fields (those are model-side, in nanoseconds).
    started = time.perf_counter()
    response = httpx.post(
        f"{settings.ollama_base_url}/api/generate",
        json={
            "model": model.model_id,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": num_predict,
            },
        },
        timeout=GENERATE_TIMEOUT_SECONDS,
    )
    latency_ms = max(0, round((time.perf_counter() - started) * 1000))
    response.raise_for_status()
    payload: object = response.json()
    if not isinstance(payload, dict):
        raise TypeError(f"Expected JSON object from Ollama, got {type(payload).__name__}")
    return map_generate_result(payload, latency_ms)


def main() -> None:
    settings = Settings.from_env()
    template = load_baseline_prompt()
    selected = select_day1_cases(load_extraction_cases())
    for case in selected:
        prompt = render_prompt(template, case.source)
        result = call_mistral(settings, prompt, temperature=TEMPERATURE)
        print(f"=== {case.id} ===")
        print(f"input_tokens={result.input_tokens}")
        print(f"output_tokens={result.output_tokens}")
        print(f"stop_reason={result.stop_reason}")
        print(f"latency_ms={result.latency_ms}")
        print(result.response_text)
        print()


if __name__ == "__main__":
    main()
