from __future__ import annotations

from pydantic import BaseModel

from promptlab.adapters.base import CompletionRequest, CompletionResult
from promptlab.structured import StructuredCompletionError, complete_structured


class TinySchema(BaseModel):
    value: str


class AlwaysInvalidAdapter:
    provider = "ollama"
    model_id = "fixture-model"

    def __init__(self) -> None:
        self.calls = 0

    def complete(self, request: CompletionRequest, run_id: str) -> CompletionResult:
        assert run_id == "fixture-run"
        self.calls += 1
        return CompletionResult(
            succeeded=True,
            text='{"wrong":"shape"}',
            error_type=None,
            records=[],
        )


def _request() -> CompletionRequest:
    return CompletionRequest(
        task="summarization",
        case_id="S00",
        prompt_id="summarize",
        prompt_version="v1",
        system="",
        user_content="Summarize the supplied procedure.",
        temperature=0.0,
        max_output_tokens=128,
    )


def test_complete_structured_does_not_exceed_max_repairs() -> None:
    adapter = AlwaysInvalidAdapter()

    try:
        complete_structured(
            adapter,
            _request(),
            TinySchema,
            "fixture-run",
            max_repairs=1,
        )
    except StructuredCompletionError as exc:
        assert exc.repairs == 1
    else:
        raise AssertionError("expected StructuredCompletionError")

    assert adapter.calls == 2
