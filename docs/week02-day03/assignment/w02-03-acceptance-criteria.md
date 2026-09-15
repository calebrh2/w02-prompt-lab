
## Acceptance Criteria

1. The existing `SummarizationOutput` is used for summarization; no `ProcedureSummary` is added.
2. The existing `EvidenceField` contract is used; evidence references use `citation`, not `section`.
3. `schema_description(...)` derives the output description from the supplied Pydantic model.
4. `src/prompts/extract.v1.md` contains the required five sections.
5. `src/prompts/extract.v2.md` adds examples without using scored cases.
6. All source documents are explicitly delimited and treated as data, not instruction.
7. `complete_structured(...)` makes at most one semantic repair attempt.
8. The repair request includes the validation error.
9. Adapters and `usage.py` are not modified for semantic repair.
10. All 12 summarization and 12 extraction cases run under one `run_id`.
11. Summarization outputs validate against `SummarizationOutput`.
12. Extraction outputs validate against `PolicyExtraction`.
13. Citation-existence checking reads `EvidenceField.citation`.
14. `docs/day3-notes.md` contains both repair rates, leakage count, and citation failure count.
15. `pytest`, `ruff check`, and `mypy` pass.
