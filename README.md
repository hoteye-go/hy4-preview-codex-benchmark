# Hy4-preview Codex Benchmark

A small, reproducible end-to-end comparison of Tencent MaaS `hy4-preview` and `gpt-5.6-sol` through the official Codex CLI.

## Result

Six task categories were repeated three times (36 calls total):

| Model | Passed | Weighted score | Mean latency |
|---|---:|---:|---:|
| GPT-5.6-sol | 18/18 | 100/100 | 15.22 s |
| Hy4-preview | 17/18 | 95/100 | 17.74 s |

The only Hy4 failure was one strict JSON response with incorrect field values. Both models passed math, logic, code execution, strict formatting, and long-context retrieval in all three rounds. No `429`, `finish_reason=length`, or empty final answer occurred in this Codex-mediated run.

## Files

- [Full report](data/reports/2026-08-30-codex-ab.md)
- [X post draft](data/reports/2026-08-30-codex-ab-x.md)
- [All raw results](data/reports/2026-08-30-codex-ab-all.json)
- [Benchmark runner](scripts/codex_ab_benchmark.py)

## Reproduction

The runner expects `TENCENT_MAAS_API_KEY` and optionally `TENCENT_MAAS_BASE_URL` in a local, untracked `configs/secrets.env.local` file. It uses a temporary `CODEX_HOME` for the Tencent run and the normal local Codex configuration for the GPT control run.

```bash
python scripts/codex_ab_benchmark.py
```

## Limitations

This is a six-category engineering smoke benchmark, not an independent leaderboard. The models use different providers, and the sample is too small for broad claims about general capability. Larger task sets, repeated trials, token cost, provider errors, and confidence intervals are needed for stronger conclusions.
