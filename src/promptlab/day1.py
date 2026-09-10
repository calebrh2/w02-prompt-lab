"""Day 1 local Ollama instrumentation script."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict

from promptlab.config import PROJECT_ROOT

DAY1_CASE_IDS = ("E12", "E07", "E11")
EXTRACTION_CASES_PATH = PROJECT_ROOT / "cases" / "extraction.jsonl"


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


def main() -> None:
    selected = select_day1_cases(load_extraction_cases())
    for case in selected:
        print(f"{case.id}\t{len(case.source)}")


if __name__ == "__main__":
    main()
