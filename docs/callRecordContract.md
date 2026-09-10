**The contract**
Implement CallRecord as a Pydantic v2 model in src/promptlab/usage.py with exactly these twenty fields:

| Field | Type | Notes |
| --- | --- | --- |
| `record_id` | `str` | UUID4 generated per record |
| `run_id` | `str` | identifies one execution |
| `timestamp` | `datetime` | timezone-aware UTC |
| `provider` | `Literal["ollama"]` | this local assignment uses Ollama |
| `model_id` | `str` | read from configuration, never hardcoded at the call site |
| `task` | `Literal["triage", "summarization", "extraction"]` | Day 1 uses extraction |
| `case_id` | `str` | e.g. E12 |
| `prompt_id` | `str` | baseline |
| `prompt_version` | `str` | v0 |
| `attempt` | `int` | 1 for the first attempt |
| `temperature` | `float` | the value actually sent |
| `max_output_tokens` | `int` | maps to Ollama num_predict |
| `input_tokens` | `int` | Ollama prompt_eval_count |
| `output_tokens` | `int` | Ollama eval_count |
| `cached_input_tokens` | `int \| None` | use None for this lab |
| `latency_ms` | `int` | measured around the HTTP call |
| `cost_usd` | `float` | local provider charge; derived from configuration |
| `stop_reason` | `str \| None` | Ollama done_reason when available |
| `error_type` | `str \| None` | None on success |
| `response_text` | `str \| None` | returned model text |
