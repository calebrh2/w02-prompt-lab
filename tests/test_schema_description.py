from __future__ import annotations

import json

from promptlab.schemas import (
    PolicyExtraction,
    SummarizationOutput,
    schema_description,
)


def test_schema_description_uses_shipped_summarization_fields() -> None:
    text = schema_description(SummarizationOutput)
    payload = json.loads(text)

    assert set(payload) == set(SummarizationOutput.model_fields)
    assert "ProcedureSummary" not in text
    assert "$defs" not in payload
    assert "properties" not in payload


def test_schema_description_uses_citation_not_section() -> None:
    summarization = schema_description(SummarizationOutput)
    extraction = schema_description(PolicyExtraction)

    assert '"citation"' in summarization
    assert '"citation"' in extraction
    title = json.loads(summarization)["title"]
    assert isinstance(title, dict)
    assert "citation" in title
    assert "section" not in title


def test_schema_description_uses_shipped_extraction_fields() -> None:
    payload = json.loads(schema_description(PolicyExtraction))
    assert set(payload) == set(PolicyExtraction.model_fields)
