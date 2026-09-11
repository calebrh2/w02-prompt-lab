Acceptance criteria
1. CallRecord has exactly the twenty fields above with the specified names and types. (Contract found in @callRecordContract.md.)
2. tests/test_usage_contract.py passes unmodified and without network access.
3. The Day 1 script makes real local Ollama calls to the configured Mistral model.
4. Model identifiers are read from configuration rather than duplicated at the call site.
5. Every successful record captures Ollama's reported input and output token counts.
6. Every timestamp is timezone-aware and in UTC.
7. Records are appended to JSONL rather than overwriting the run file.
8. An unknown model identifier raises UnknownModelError.
9. The deliberate low-output call is detected as truncation when Ollama reports the output ceiling was reached.
10. No cloud credentials are required and no populated .env file is committed.
11. pytest, ruff, and mypy are clean for the Day 1 work.
12. docs/day1-observations.md contains the requested comparison in no more than three sentences.