Error types
Extend src/promptlab/errors.py with these error types:

Error	Raised when	Retried
TransientProviderError	timeout, connection failure, or temporary Ollama/server failure	Yes
PermanentProviderError	malformed request, unavailable model, unsupported parameter, or other non-retryable request failure	No
TruncatedResponseError	Ollama reports that the output token ceiling was reached	No
UnknownModelError	model identifier is not present in the configured model table	No
UnknownModelError already exists from Day 1. Do not create a second version of it.

Retry policy
A request may make at most three attempts.

Use exponential backoff with jitter between retries.

Retry only failures classified as TransientProviderError.

Do not retry:

PermanentProviderError
TruncatedResponseError
UnknownModelError
Every actual model-call attempt must produce a CallRecord, including a failed attempt.

The attempt field starts at 1 and increments for each retry of that request.

Ollama isolation
Implement one reusable OllamaAdapter.

Do not create separate MistralAdapter and QwenAdapter classes just because the models are different.

The intended design is:

                    ModelAdapter
                         |
                   OllamaAdapter
                    /          \
             Mistral config   Qwen config
The same adapter code should work for either model when instantiated with a different configured model_id.

Nothing outside src/promptlab/adapters/ should depend on Ollama-specific response field names such as:

prompt_eval_count
eval_count
done_reason
The adapter translates those fields into the existing CallRecord contract.

Local cost policy
There is no dollar spend-cap exercise in this local version.

Both models run locally through Ollama, so their provider/API charge is 0.0.

Do not invent token prices for Mistral or Qwen.

Operational safety in this assignment comes from:

a fixed maximum output-token value
a maximum of three attempts per request
retrying only transient failures
Deliverable
A merge request containing:

src/promptlab/adapters/base.py
src/promptlab/adapters/ollama.py
src/promptlab/errors.py
src/promptlab/day2.py
docs/day2-run.jsonl
docs/day2-comparison.md
src/promptlab/usage.py must remain unchanged from Day 1.