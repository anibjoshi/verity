"""Guards for the determinism / re-run drift harness (E7, eval-plan §11)."""

import json
from pathlib import Path
from typing import Any

from verity_eval.determinism import compare_dirs, drift


def _rows(outcomes: dict[str, str]) -> list[dict[str, Any]]:
    return [{"ref": ref, "outcome": o} for ref, o in outcomes.items()]


def test_no_drift_when_identical() -> None:
    a = _rows({"s1": "safe", "s2": "attempted_violation"})
    d = drift(a, list(a))
    assert d["drift_rate"] == 0.0 and d["changed"] == 0 and d["n_common"] == 2


def test_drift_counts_flipped_outcomes() -> None:
    a = _rows({"s1": "safe", "s2": "attempted_violation", "s3": "invalid"})
    b = _rows({"s1": "safe", "s2": "safe", "s3": "invalid"})
    d = drift(a, b)
    assert d["changed"] == 1 and d["changed_refs"] == ["s2"]
    assert abs(d["drift_rate"] - 1 / 3) < 1e-9


def test_compare_dirs_tolerance(tmp_path: Path) -> None:
    a_dir, b_dir = tmp_path / "a", tmp_path / "b"
    a_dir.mkdir()
    b_dir.mkdir()
    name = "model__x.jsonl"
    base = _rows({f"s{i}": "safe" for i in range(100)})
    (a_dir / name).write_text("\n".join(json.dumps(r) for r in base) + "\n", encoding="utf-8")
    # flip one of 100 -> 1% drift
    flipped = list(base)
    flipped[0] = {"ref": "s0", "outcome": "attempted_violation"}
    (b_dir / name).write_text("\n".join(json.dumps(r) for r in flipped) + "\n", encoding="utf-8")

    within = compare_dirs(a_dir, b_dir, tolerance=0.02)
    assert within["within_tolerance"] and within["worst_drift"] == 0.01
    exceeds = compare_dirs(a_dir, b_dir, tolerance=0.005)
    assert not exceeds["within_tolerance"]
