"""Day 1 local Ollama instrumentation script."""

from __future__ import annotations

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


def call_mistral(
    settings: Settings,
    prompt: str,
    *,
    temperature: float = TEMPERATURE,
    num_predict: int = DEFAULT_NUM_PREDICT,
) -> dict[str, Any]:
    model = settings.models["mistral"]
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
    response.raise_for_status()
    payload: object = response.json()
    if not isinstance(payload, dict):
        raise TypeError(f"Expected JSON object from Ollama, got {type(payload).__name__}")
    return payload


def main() -> None:
    settings = Settings.from_env()
    template = load_baseline_prompt()
    selected = select_day1_cases(load_extraction_cases())
    for case in selected:
        prompt = render_prompt(template, case.source)
        payload = call_mistral(settings, prompt, temperature=TEMPERATURE)
        print(f"=== {case.id} ===")
        print(payload.get("response"))
        print()


if __name__ == "__main__":
    main()
