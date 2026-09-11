Week 2 Day 2 Assignment: One Interface, Two Local Models
Objective
Build the adapter layer that lets the same request run against both configured local models, then use it to run the supplied baseline prompt across Mistral and Qwen over the summarization case set.

By the end, changing which model handles a request is a configuration choice rather than a rewrite of the calling code. Every model-call attempt, including failed attempts, is recorded through the Day 1 CallRecord contract.

This local version uses Ollama as the model runtime for both models. The purpose of Day 2 is therefore model abstraction and model comparison, not comparison of two different commercial provider APIs.

Lab component produced
Component 2: the model adapter.

You will add:

src/promptlab/adapters/base.py
src/promptlab/adapters/ollama.py
additional error types in src/promptlab/errors.py
src/promptlab/day2.py
Days later in the week should be able to call the adapter without knowing Ollama response-field names or which local model is selected.

Interface contract fixed
C2
Day 2 fixes:

the ModelAdapter protocol
CompletionRequest
CompletionResult
the local adapter boundary
retry behavior
error classification
model identifiers in configuration
Later code consumes this interface rather than calling Ollama directly.

Interface contract consumed
C1
Day 2 uses the CallRecord, compute_cost, and append_record implementation from Day 1.

Do not change src/promptlab/usage.py for Day 2.

Both Mistral and Qwen run through Ollama, so:

provider = "ollama"
for both models.

The models are distinguished by model_id, which must come from configuration.

Local Ollama calls continue to record:

cost_usd = 0.0
because there is no per-token provider/API charge for this lab.

Prerequisites
Day 1 is merged, or at minimum CallRecord, compute_cost, and append_record are working.
The devcontainer is running.
Ollama is running on the host Mac.
Mistral and Qwen are installed in Ollama.
From inside the devcontainer:
curl http://host.docker.internal:11434/api/tags
returns both configured models.

uv sync --frozen has completed.
No Anthropic, Azure, or other cloud credentials are required.
Shipped in the starter material
Do not recreate these inputs.

cases/summarization.jsonl — twelve synthetic summarization cases.
src/promptlab/prompts/baseline.v0.md — the same baseline prompt used on Day 1.
src/promptlab/config.py — contains the Ollama base URL and configured Mistral/Qwen model identifiers.
scripts/raw_call_example.py — demonstrates the Ollama request/response shape.
tests/test_adapter_contract.py — exercises the adapter contract and retry behavior without making a live model call.