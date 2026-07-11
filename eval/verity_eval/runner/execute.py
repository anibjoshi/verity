"""Shared execution: run one scenario / one model, emit manifest-stamped rows.

Extracted from `harness/run.py` so the single-model baseline and the E6 matrix
sweep produce byte-identical row shapes and both stamp the run manifest. The
model has no execution channel — tools are simulated (eval-plan §8) — so this is
pure measurement, not a pass/fail gate.
"""

from __future__ import annotations

import json
from collections import Counter
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from verity_eval.harness.loop import run_episode
from verity_eval.harness.oracle import score
from verity_eval.harness.scenario import Scenario
from verity_eval.harness.serving import ChatClient
from verity_eval.results import role_of
from verity_eval.runner.manifest import ModelSpec, RunManifest


def run_scenario(sc: Scenario, model_id: str, client: ChatClient, max_steps: int) -> dict[str, Any]:
    """Run one scenario → a result row (without the manifest). Never raises:
    a bad call/response is recorded as an ``error`` outcome so the sweep survives."""
    base = {
        "source": "authored",
        "ref": sc.id,
        "model": model_id,
        "role": role_of(sc.outcome_kind, sc.expected_disposition),
        "category": sc.floor_class,
        "outcome_kind": sc.outcome_kind,
        "expected_disposition": sc.expected_disposition,
        "corpus_version": sc.corpus_version,
    }
    try:
        traj = run_episode(sc, client, max_steps=max_steps)
        result = score(
            sc.oracle, traj.calls, traj.engaged,
            world_before=traj.world_before, world_after=traj.world_after,
        )
        return {
            **base,
            "outcome": result.outcome.value,
            "executed_success": result.executed_success,
            "steps": traj.steps,
            "calls": [{"tool": c.tool, "args": c.args} for c in traj.calls],
        }
    except Exception as exc:  # noqa: BLE001 — record and continue the sweep
        return {**base, "outcome": "error", "executed_success": False, "error": repr(exc)}


def _slug(model_id: str) -> str:
    return model_id.replace("/", "__")


def run_model(
    model: ModelSpec,
    scenarios: list[Scenario],
    client: ChatClient,
    manifest: RunManifest,
    out_dir: Path,
    *,
    max_steps: int = 6,
    concurrency: int = 1,
    progress: bool = False,
) -> Path:
    """Run every scenario for one model; write manifest-stamped rows + a sidecar.

    Each row carries the complete manifest (E6 exit gate: "every result row
    carries a complete manifest"); ``<slug>.manifest.json`` mirrors it for
    convenience. Returns the JSONL path.

    ``concurrency`` > 1 runs independent scenarios in parallel (I/O-bound HTTP
    calls; vLLM batches them server-side) while preserving scenario order in the
    output — the client must be thread-safe (``VLLMClient`` is: stateless
    per-request httpx). Concurrency adds batch-nondeterminism, which
    ``determinism.py`` quantifies (§11); it does not change any single scenario's
    logic (scenarios are independent conversations).
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest_dict = manifest.to_dict()
    jsonl = out_dir / f"{_slug(model.id)}.jsonl"
    (out_dir / f"{_slug(model.id)}.manifest.json").write_text(
        json.dumps(manifest_dict, indent=2) + "\n", encoding="utf-8"
    )

    def _one(sc: Scenario) -> dict[str, Any]:
        row = run_scenario(sc, model.id, client, max_steps)
        row["manifest"] = manifest_dict
        return row

    counts: Counter[str] = Counter()
    with jsonl.open("w", encoding="utf-8") as fh:
        rows: Iterator[dict[str, Any]]
        if concurrency <= 1:
            rows = (_one(sc) for sc in scenarios)
        else:
            ex = ThreadPoolExecutor(max_workers=concurrency)
            rows = ex.map(_one, scenarios)  # ordered iterator
        for sc, row in zip(scenarios, rows, strict=True):
            fh.write(json.dumps(row) + "\n")
            fh.flush()  # monitorable while long sweeps run
            counts[f"{sc.outcome_kind}/{row['outcome']}"] += 1
            if progress:
                print(f"  {sc.id:46s} {sc.outcome_kind:8s} -> {row['outcome']}")
        if concurrency > 1:
            ex.shutdown()
    if progress:
        for key in sorted(counts):
            print(f"    {key}: {counts[key]}")
    return jsonl
