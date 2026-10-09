# Evaluation

`cases.json` holds 11 CV/job pairs with the expected recommendation(s) and the
criteria RAG should retrieve per job. `run_eval.py` runs every case several
times against the real model (nothing is written to the audit log) and writes a
Markdown + JSON report to `results/`. A hard `--budget-usd` stops the run early.

```bash
.venv/bin/python evals/run_eval.py --rag-only                                  # free
.venv/bin/python evals/run_eval.py --model claude-sonnet-5 --repeats 3 --budget-usd 1
```

## Summary (2026-10-09, claude-sonnet-5, 3 runs per case)

| Metric | Prompt v2 | Prompt v3 |
|---|---|---|
| Runs passing expectation | 27/33 (82%) | **31/33 (94%)** |
| Cases with identical recommendation across runs | 11/11 | 10/11 |
| Mean score spread within a case | 1.6 points | 1.5 points |
| Prompt injection CV (expected score ≤ 30) | 0.3, passed | 0.3, passed |
| Invalid outputs after retry | 0 | 0 |
| Mean latency | 7.8 s | 7.7 s |
| Cost of the run | $0.36 | $0.35 |

**What changed:** v2 was too strict on partial matches. A strong backend
engineer applying for the AI role and a no-code career changer both got
`reject_suggested`. v3 defines `review` explicitly as "partial match or
transferable experience a human should weigh". The backend engineer now gets
`review` in every run.

**Known limitations**
- The career changer is still borderline (2× `reject_suggested`, 1× `review`).
  Its score is pulled down because RAG also retrieves `api_design` and
  `devops_cloud` for the AI role.
- RAG recall: 100% / 80% / 75% for the three jobs (misses `automated_testing`
  and `languages`). A larger embedding model or per-job criteria overrides would
  fix this.
- 11 cases is a small set. The prompt change was made once and then stopped,
  to avoid tuning the prompt to these exact cases.

Full reports: `results/2026-10-09_claude-sonnet-5_v2.md`, `results/2026-10-09_claude-sonnet-5_v3.md`, `results/2026-10-09_rag.md`.
