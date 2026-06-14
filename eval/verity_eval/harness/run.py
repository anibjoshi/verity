"""Runner: execute the corpus against a model and emit the three-valued outcome.

The live run (E1) needs a local vLLM server — see the `local-serving-setup`
notes. Results (JSONL + a per-class summary) are written under `eval/results/`
(git-ignored). This is the baseline path; the verifier is OFF.

    python -m verity_eval.harness.run --model Qwen/Qwen2.5-3B-Instruct
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from verity_eval.corpus_check import corpus_dir

from .loop import run_episode
from .oracle import score
from .scenario import load_scenarios
from .serving import VLLMClient


def results_dir() -> Path:
    return corpus_dir().parent / "results"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run the Verity corpus against a model (baseline; verifier OFF)."
    )
    parser.add_argument("--model", default="Qwen/Qwen2.5-3B-Instruct")
    parser.add_argument("--base-url", default="http://localhost:8000/v1")
    parser.add_argument("--max-steps", type=int, default=6)
    parser.add_argument(
        "--out", default=None, help="output JSONL path (default: eval/results/<model>.jsonl)"
    )
    args = parser.parse_args(argv)

    scenarios = load_scenarios()
    client = VLLMClient(model=args.model, base_url=args.base_url)

    default_name = f"{args.model.replace('/', '__')}.jsonl"
    out_path = Path(args.out) if args.out else results_dir() / default_name
    out_path.parent.mkdir(parents=True, exist_ok=True)

    counts: Counter[str] = Counter()
    with out_path.open("w", encoding="utf-8") as fh:
        for sc in scenarios:
            # Per-scenario resilience: one bad call/response must not lose the run.
            try:
                traj = run_episode(sc, client, max_steps=args.max_steps)
                result = score(
                    sc.oracle, traj.calls, traj.engaged,
                    world_before=traj.world_before, world_after=traj.world_after,
                )
                row = {
                    "id": sc.id,
                    "floor_class": sc.floor_class,
                    "outcome_kind": sc.outcome_kind,
                    "expected_disposition": sc.expected_disposition,
                    "outcome": result.outcome.value,
                    "executed_success": result.executed_success,
                    "steps": traj.steps,
                    "calls": [{"tool": c.tool, "args": c.args} for c in traj.calls],
                    "model": args.model,
                    "corpus_version": sc.corpus_version,
                }
                tag = result.outcome.value
            except Exception as exc:  # noqa: BLE001 — record and continue the sweep
                row = {
                    "id": sc.id,
                    "floor_class": sc.floor_class,
                    "outcome_kind": sc.outcome_kind,
                    "expected_disposition": sc.expected_disposition,
                    "outcome": "error",
                    "executed_success": False,
                    "error": repr(exc),
                    "model": args.model,
                    "corpus_version": sc.corpus_version,
                }
                tag = "error"
            counts[f"{sc.outcome_kind}/{tag}"] += 1
            fh.write(json.dumps(row) + "\n")
            print(f"{sc.id:46s} {sc.outcome_kind:8s} -> {tag}")

    print(f"\nwrote {out_path}")
    for key in sorted(counts):
        print(f"  {key}: {counts[key]}")
    # exit 0 even if outcomes vary; this is measurement, not a pass/fail gate
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
