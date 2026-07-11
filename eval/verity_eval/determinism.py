"""Determinism harness — quantify re-run drift within a tolerance (E7, §11).

vLLM greedy decoding is *provably not* bit-exact (temp-0 still varies with
batch-size-dependent float-reduction order — Thinking Machines, Sept 2025). So
the E7 gate is **"reproducible up to documented batch-nondeterminism"**, not
byte-equality: run the sweep twice, and check the fraction of scenarios whose
3-valued **outcome** flipped stays within a stated tolerance.

Pure comparison of two result sets — no model — so it is CI-testable (a dry-run
against itself has zero drift).

    python -m verity_eval.determinism --a results_run1 --b results_run2 --tolerance 0.02
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from verity_eval.harness.metrics import load_rows


def drift(rows_a: list[dict[str, Any]], rows_b: list[dict[str, Any]]) -> dict[str, Any]:
    """Outcome drift between two runs of the same model over the same corpus."""
    a = {r["ref"]: r.get("outcome") for r in rows_a}
    b = {r["ref"]: r.get("outcome") for r in rows_b}
    common = sorted(a.keys() & b.keys())
    changed = [ref for ref in common if a[ref] != b[ref]]
    return {
        "n_common": len(common),
        "changed": len(changed),
        "drift_rate": (len(changed) / len(common)) if common else 0.0,
        "changed_refs": changed,
        "only_a": sorted(a.keys() - b.keys()),
        "only_b": sorted(b.keys() - a.keys()),
    }


def compare_dirs(dir_a: Path, dir_b: Path, tolerance: float) -> dict[str, Any]:
    """Drift per model for every result file present in both dirs."""
    files = sorted(p.name for p in dir_a.glob("*.jsonl"))
    per_model: dict[str, Any] = {}
    worst = 0.0
    for name in files:
        pb = dir_b / name
        if not pb.is_file():
            continue
        d = drift(load_rows(dir_a / name), load_rows(pb))
        per_model[name] = d
        worst = max(worst, d["drift_rate"])
    return {"tolerance": tolerance, "worst_drift": worst, "within_tolerance": worst <= tolerance,
            "per_model": per_model}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Quantify re-run drift between two sweeps.")
    parser.add_argument("--a", required=True, help="first results dir")
    parser.add_argument("--b", required=True, help="second results dir")
    parser.add_argument("--tolerance", type=float, default=0.02)
    args = parser.parse_args(argv)

    result = compare_dirs(Path(args.a), Path(args.b), args.tolerance)
    if not result["per_model"]:
        print("[determinism] no overlapping result files to compare")
        return 0
    for name, d in sorted(result["per_model"].items()):
        flag = "OK" if d["drift_rate"] <= args.tolerance else "DRIFT"
        print(f"[{flag}] {name}: {d['changed']}/{d['n_common']} flipped "
              f"({d['drift_rate']:.3f}, tol {args.tolerance})")
        for ref in d["changed_refs"][:10]:
            print(f"        {ref}")
    print(f"[determinism] worst drift {result['worst_drift']:.3f} "
          f"({'within' if result['within_tolerance'] else 'EXCEEDS'} tolerance {args.tolerance})")
    return 0 if result["within_tolerance"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
