# Day 3 notes

Run `98516079-9cf0-4fa7-aad7-b9d2e16dab72` used the configured Mistral model at temperature `0.0`. All 12 summarization cases (`summarize.v1`) and all 12 extraction cases (`extract.v2`) produced objects that validated against `SummarizationOutput` and `PolicyExtraction`.

## Rates

- Summarization repair rate: **0 / 12**
- Extraction repair rate: **4 / 12**
- Example leakage count: **0**
- Citation-existence failure count: **64** (64 on summarization, 0 on extraction)

Leakage was measured by searching extraction outputs for distinctive strings that appear only in the two `extract.v2.md` example documents (`Northglass`, `Norwyn`, `Bellwater`, `Redhaven`, `East Kestrel`). Citation-existence checking reads `EvidenceField.citation` for every field with `status: "present"` and requires that string to match a real section heading in the case source.

## What failed, and what changed

The most common validation error was the model echoing JSON Schema metadata (`$defs`, `properties`, `type`, `title`) and wrapping `document_status` as an `EvidenceField` object instead of a bare enum string. Generating an instance-shaped `schema_description(...)` from the Pydantic model fields, instead of dumping `model_json_schema()`, stopped those schema-echo failures; extraction still used one repair on four cases, usually to add the required `value: null` on absent fields.

Summarization citations often used a section number only (`"1"`) rather than the full heading (`"1. Document Control"`), which is why the citation-existence count is high even though every output validated.
