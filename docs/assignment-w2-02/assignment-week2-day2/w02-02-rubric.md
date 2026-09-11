Rubric
Scored out of 100.

Adapter contract and model isolation — 35 points
35: The protocol and request/result models match the contract. One reusable OllamaAdapter runs either configured model. Ollama-specific response fields remain inside the adapter package.

25: Both models work, but there is one unnecessary model-specific branch or duplicated implementation.

12: Mistral and Qwen are implemented as separate adapters with duplicated Ollama logic, or Ollama response details leak into day2.py.

0: Only one model works or there is no shared adapter boundary.

Retry and error classification — 20 points
20: Transient failures retry with exponential backoff and jitter, permanent/truncation failures do not, all attempts are recorded, and no request exceeds three attempts.

14: Retry behavior is mostly correct but classification or attempt recording is incomplete.

7: Retries occur indiscriminately or use an unbounded/fixed retry loop.

0: No meaningful retry/error handling exists.

Cross-model run and record integrity — 25 points
25: All twelve cases run against both models under one run_id; shared request fields match; all records validate against C1.

18: Both models and all cases run, but one comparison field differs unnecessarily or failed attempts are not recorded.

8: The run is incomplete or the two models use different prompts/settings.

0: No usable two-model run is produced.

Comparison evidence — 10 points
10: The comparison reports success counts, token totals, median/max latency, and a concise evidence-based observation for both models.

7: Comparison is present but one required metric is missing.

3: Comparison is mostly subjective and not grounded in the run records.

0: Comparison is absent.

Engineering hygiene — 10 points
10: Model IDs live only in configuration, usage.py is untouched, no credentials are committed, and tests/lint/type checks are clean.

7: One minor convention or tooling issue remains.

3: C1 was changed unnecessarily or model/runtime details are duplicated throughout the code.

0: A credential or populated .env is committed.