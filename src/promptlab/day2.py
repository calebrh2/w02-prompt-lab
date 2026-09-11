"""Day 2 two-model adapter run over the summarization case set."""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict

from promptlab.adapters.base import CompletionRequest
from promptlab.adapters.ollama import OllamaAdapter
from promptlab.config import PROJECT_ROOT, Settings
from promptlab.usage import append_record

SUMMARIZATION_CASES_PATH = PROJECT_ROOT / "cases" / "summarization.jsonl"
BASELINE_PROMPT_PATH = PROJECT_ROOT / "src" / "prompts" / "baseline.v0.md"
PROMPT_ID = "baseline"
PROMPT_VERSION = "v0"
MAX_OUTPUT_TOKENS = 1024
EVIDENCE_PATH = PROJECT_ROOT / "docs" / "day2-run.jsonl"


class SummarizationCase(BaseModel):
    """One summarization corpus case."""

    model_config = ConfigDict(extra="forbid")

    id: str
    task: Literal["summarization"]
    source: str


def load_summarization_cases(path: Path = SUMMARIZATION_CASES_PATH) -> list[SummarizationCase]:
    cases: list[SummarizationCase] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        cases.append(SummarizationCase.model_validate_json(line))
    return cases


def load_baseline_prompt(path: Path = BASELINE_PROMPT_PATH) -> str:
    return path.read_text(encoding="utf-8")


def render_prompt(template: str, document_text: str) -> str:
    return template.replace("{document_text}", document_text)


def main() -> None:
    os.chdir(PROJECT_ROOT)
    settings = Settings.from_env()
    template = load_baseline_prompt()
    cases = load_summarization_cases()
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
                prompt_id=PROMPT_ID,
                prompt_version=PROMPT_VERSION,
                system="",
                user_content=render_prompt(template, case.source),
                temperature=settings.temperature,
                max_output_tokens=MAX_OUTPUT_TOKENS,
            )
            result = adapter.complete(request, run_id)
            for record in result.records:
                append_record(record, run_id)
                record_count += 1
            print(
                f"{case.id} model={adapter.model_id} succeeded={result.succeeded} "
                f"attempts={len(result.records)} error_type={result.error_type}"
            )

    run_path = Path("runs") / f"{run_id}.jsonl"
    shutil.copyfile(run_path, EVIDENCE_PATH)
    print(f"appended {record_count} records to {run_path}")
    print(f"copied evidence to {EVIDENCE_PATH}")


if __name__ == "__main__":
    main()
