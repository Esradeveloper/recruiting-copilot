"""Offline evaluation of retrieval (RAG) and scoring.

Nothing is written to the audit log; CV texts never leave this process except
to the Claude API. Usage:
    .venv/bin/python evals/run_eval.py --rag-only                 # free
    .venv/bin/python evals/run_eval.py --repeats 3 --budget-usd 1.5
"""

import argparse
import json
import os
import statistics
import sys
import time
from collections import Counter
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env")

from app import db  # noqa: E402
from app.pdf_text import extract_text  # noqa: E402
from app.rag import MIN_SIMILARITY, TOP_K, retrieve_criteria  # noqa: E402
from app.scoring import DEFAULT_MODEL, PROMPT_VERSION, score_cv  # noqa: E402

# USD per million tokens (input, output)
PRICES = {
    "claude-sonnet-5": (2.0, 10.0),
    "claude-opus-5": (5.0, 25.0),
    "claude-haiku-4-5": (1.0, 5.0),
}

EVAL_DIR = Path(__file__).resolve().parent
CV_DIR = ROOT / "data" / "cvs"


def cost_usd(model: str, input_tokens: int, output_tokens: int) -> float:
    price_in, price_out = PRICES[model]
    return (input_tokens * price_in + output_tokens * price_out) / 1_000_000


def eval_rag(conn, expected: dict[str, list[str]]) -> list[dict]:
    rows = []
    for slug, gold in expected.items():
        job_id, _ = db.get_job(conn, slug)
        got = [c.name for c in retrieve_criteria(conn, job_id)]
        hits = set(got) & set(gold)
        rows.append({
            "job": slug,
            "recall": len(hits) / len(gold),
            "precision": len(hits) / len(got) if got else 0.0,
            "missed": sorted(set(gold) - set(got)),
            "extra": sorted(set(got) - set(gold)),
        })
    return rows


def eval_scoring(conn, cases: list[dict], model: str, repeats: int, budget: float) -> tuple[list[dict], float, bool]:
    spent, stopped = 0.0, False
    results = []
    for case in cases:
        job_id, title = db.get_job(conn, case["job"])
        criteria = retrieve_criteria(conn, job_id)
        cv_text = extract_text((CV_DIR / case["cv"]).read_bytes())
        runs = []
        for _ in range(repeats):
            if spent >= budget:
                stopped = True
                break
            start = time.monotonic()
            r = score_cv(title, criteria, cv_text, model=model)
            spent += cost_usd(model, r.input_tokens, r.output_tokens)
            runs.append({
                "status": r.status.value,
                "attempts": r.attempts,
                "score": r.evaluation.score if r.evaluation else None,
                "recommendation": r.evaluation.recommendation.value if r.evaluation else None,
                "seconds": round(time.monotonic() - start, 1),
                "input_tokens": r.input_tokens,
                "output_tokens": r.output_tokens,
            })
            print(f"  {case['id']:<22} {runs[-1]['recommendation']} {runs[-1]['score']}  (${spent:.3f})", flush=True)
        results.append(summarise(case, runs))
        if stopped:
            break
    return results, spent, stopped


def summarise(case: dict, runs: list[dict]) -> dict:
    scores = [r["score"] for r in runs if r["score"] is not None]
    recs = [r["recommendation"] for r in runs]

    def run_passes(r: dict) -> bool:
        return (
            r["status"] == "ok"
            and r["recommendation"] in case["expected"]
            and r["score"] <= case.get("max_score", 100)
        )

    return {
        **case,
        "runs": runs,
        "recommendations": dict(Counter(recs)),
        "score_mean": round(statistics.mean(scores), 1) if scores else None,
        "score_range": [min(scores), max(scores)] if scores else None,
        "stable": len(set(recs)) == 1,
        "passed_runs": sum(run_passes(r) for r in runs),
        "passed": bool(runs) and all(run_passes(r) for r in runs),
    }


def write_markdown(rag: list[dict], scoring: list[dict], meta: dict) -> str:
    lines = [f"# Evaluation results ({meta['date']})", ""]
    lines += [
        f"Retrieval: `bge-small-en-v1.5`, top {TOP_K}, min similarity {MIN_SIMILARITY}.",
        "",
        "## Retrieval (RAG)",
        "| Job | Recall | Precision | Missed | Extra |",
        "|---|---|---|---|---|",
    ]
    for r in rag:
        lines.append(f"| {r['job']} | {r['recall']:.0%} | {r['precision']:.0%} | "
                     f"{', '.join(r['missed']) or '–'} | {', '.join(r['extra']) or '–'} |")

    if scoring:
        n_runs = sum(len(c["runs"]) for c in scoring)
        passed_runs = sum(c["passed_runs"] for c in scoring)
        invalid = sum(r["status"] != "ok" for c in scoring for r in c["runs"])
        retries = sum(r["attempts"] > 1 for c in scoring for r in c["runs"])
        spreads = [c["score_range"][1] - c["score_range"][0] for c in scoring if c["score_range"]]
        seconds = [r["seconds"] for c in scoring for r in c["runs"]]
        lines += [
            "",
            f"## Scoring – model `{meta['model']}`, prompt `{meta['prompt_version']}`, {meta['repeats']} runs per case",
            "| Case | Expected | Got | Score (mean, range) | Stable | Pass |",
            "|---|---|---|---|---|---|",
        ]
        for c in scoring:
            got = ", ".join(f"{k} ×{v}" for k, v in c["recommendations"].items())
            rng = f"{c['score_mean']} ({c['score_range'][0]}–{c['score_range'][1]})" if c["score_range"] else "–"
            limit = f" (score ≤ {c['max_score']})" if "max_score" in c else ""
            lines.append(f"| {c['id']} | {' / '.join(c['expected'])}{limit} | {got} | {rng} | "
                         f"{'yes' if c['stable'] else 'no'} | {'✅' if c['passed'] else '❌'} |")
        lines += [
            "",
            "| Metric | Value |",
            "|---|---|",
            f"| Runs passing expectation | {passed_runs}/{n_runs} ({passed_runs / n_runs:.0%}) |",
            f"| Cases passing in every run | {sum(c['passed'] for c in scoring)}/{len(scoring)} |",
            f"| Cases with identical recommendation across runs | {sum(c['stable'] for c in scoring)}/{len(scoring)} |",
            f"| Mean score spread within a case (max − min) | {statistics.mean(spreads):.1f} points |",
            f"| Invalid outputs after retry / runs needing a retry | {invalid} / {retries} |",
            f"| Mean latency per evaluation | {statistics.mean(seconds):.1f} s |",
            f"| Cost of this eval run | ${meta['cost_usd']:.2f} |",
        ]
        if meta["stopped_by_budget"]:
            lines += ["", f"**Stopped early: budget of ${meta['budget_usd']:.2f} reached.**"]
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default=os.environ.get("ANTHROPIC_MODEL", DEFAULT_MODEL))
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--budget-usd", type=float, default=1.50)
    parser.add_argument("--rag-only", action="store_true")
    args = parser.parse_args()
    if not args.rag_only and args.model not in PRICES:
        sys.exit(f"no price known for {args.model}, add it to PRICES")

    spec = json.loads((EVAL_DIR / "cases.json").read_text())
    with db.connect() as conn:
        rag = eval_rag(conn, spec["rag_expected_criteria"])
        for r in rag:
            print(f"RAG {r['job']}: recall {r['recall']:.0%}, precision {r['precision']:.0%}")
        scoring, spent, stopped = ([], 0.0, False)
        if not args.rag_only:
            scoring, spent, stopped = eval_scoring(conn, spec["cases"], args.model, args.repeats, args.budget_usd)

    meta = {
        "date": date.today().isoformat(), "model": args.model, "prompt_version": PROMPT_VERSION,
        "repeats": args.repeats, "cost_usd": spent, "budget_usd": args.budget_usd,
        "stopped_by_budget": stopped,
    }
    out_dir = EVAL_DIR / "results"
    out_dir.mkdir(exist_ok=True)
    name = f"{meta['date']}_{args.model}_{PROMPT_VERSION}" if scoring else f"{meta['date']}_rag"
    (out_dir / f"{name}.json").write_text(json.dumps({"meta": meta, "rag": rag, "scoring": scoring}, indent=2) + "\n")
    (out_dir / f"{name}.md").write_text(write_markdown(rag, scoring, meta))
    print(f"wrote evals/results/{name}.md  (cost ${spent:.2f})")


if __name__ == "__main__":
    main()
