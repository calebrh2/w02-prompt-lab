# Day 2 comparison — Mistral vs Qwen

Evidence: `docs/day2-run.jsonl` (24 records, one `run_id`, 12 summarization cases × 2 models, `max_output_tokens=1024`, temperature 0.0, baseline v0). Every attempt succeeded (`error_type` null, `stop_reason=stop`). Local provider charge is 0.0 for both models; this comparison does not use dollar cost.

## Success counts

| Model | Successful cases | Failed cases | Attempts recorded |
| --- | ---: | ---: | ---: |
| Mistral (`mistral:7b`) | 12 / 12 | 0 | 12 |
| Qwen (`qwen3:8b`) | 12 / 12 | 0 | 12 |

## Token totals

| Model | Input tokens | Output tokens | Combined tokens |
| --- | ---: | ---: | ---: |
| Mistral | 2,787 | 1,142 | 3,929 |
| Qwen | 2,427 | 5,015 | 7,442 |

## Latency (ms)

| Model | Median | Max | Min |
| --- | ---: | ---: | ---: |
| Mistral | 3,915.5 | 8,886 | 3,000 |
| Qwen | 19,312 | 33,408 | 17,108 |

## Observation

The same requests completed on both models, but they did not spend the budget the same way. Qwen emitted about 4.4× as many output tokens as Mistral (5,015 vs 1,142) and its median latency was about 5× higher (19,312 ms vs 3,915.5 ms). That matches Qwen3 using thinking tokens inside the shared 1,024-token ceiling: input size was actually slightly lower for Qwen (2,427 vs 2,787), so the extra time and tokens are generation-side, not prompt-side. A 256-token ceiling would have been a poor comparison here; at 1,024 both models stopped on their own rather than at the cap.
