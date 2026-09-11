Acceptance criteria
CompletionRequest, CompletionResult, and ModelAdapter exist in adapters/base.py with the specified fields, names, and types.

OllamaAdapter satisfies the ModelAdapter protocol and can run either configured model without changing adapter code.

tests/test_adapter_contract.py passes unmodified and without a live Ollama connection.

TransientProviderError, PermanentProviderError, TruncatedResponseError, and UnknownModelError exist in errors.py.

A transient failure is retryable, a permanent failure is not, truncation is not retried, and no request produces more than three attempts.

Every actual attempt produces a CallRecord with attempt incrementing from 1.

usage.py is unchanged from Day 1.

Every Day 2 record validates against the Day 1 CallRecord contract.

All twelve summarization cases are run against both Mistral and Qwen.

For a given case, task, case_id, prompt_id, prompt_version, temperature, and max_output_tokens are identical across the two model runs.

Both models record provider="ollama" and are distinguished by their configured model_id.

No model identifier literal appears in day2.py or the adapter implementation. Model identifiers come from configuration.

Ollama-specific response field names do not appear outside src/promptlab/adapters/.

docs/day2-comparison.md reports counts and token/latency measurements for both models and does not invent a dollar-cost comparison.

No cloud credential, key, or populated .env file appears in the diff.

pytest, ruff, and mypy report no findings on the changed files.