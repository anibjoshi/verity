"""Baseline v1 — the Phase-0 proof, read off the manifested sweep results (E7).

Baseline v1 (eval-plan §12) = {corpus v1.0, frozen + hashed} × {pinned model set}
× {recorded config, verifier OFF} → a table: catastrophe rate (`ASR_valid` /
`ASR_all`) and `refusal_rate` **per floor_class per model**, benign
`task_success_rate` / `over_caution_rate`, `invalid_rate` (the capability-noise
floor), and the **small-vs-frontier gap** — the evidence the problem is real and
the fixed reference Phase 2 grades the verifier against.

This module turns `eval/results/*.jsonl` (produced by the out-of-band GPU sweep,
each row carrying its manifest) into `baseline_v1.md` + `baseline_v1.json`. It is
pure aggregation — no model, no GPU — so it is fully testable on synthetic rows.

    python -m verity_eval.report            # over eval/results/
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from verity_eval.corpus_check import corpus_dir
from verity_eval.harness.metrics import load_rows, summarize
from verity_eval.results import role_of_row


def results_dir() -> Path:
    return corpus_dir().parent / "results"


def _rate(num: int, den: int) -> float:
    return num / den if den else 0.0


def _is_frontier(rows: list[dict[str, Any]]) -> bool:
    for r in rows:
        model = r.get("manifest", {}).get("model", {})
        if model:
            return bool(model.get("family") == "frontier" or model.get("served_by") == "api")
    return False


def _benign_task_success(rows: list[dict[str, Any]]) -> float:
    """Fraction of benign scenarios whose legitimate task was performed."""
    benign = [r for r in rows if role_of_row(r) == "benign"]
    done = sum(1 for r in benign if r.get("executed_success"))
    return _rate(done, len(benign))


def _invalid_rate(rows: list[dict[str, Any]]) -> float:
    inv = sum(1 for r in rows if r.get("outcome") in ("invalid", "error"))
    return _rate(inv, len(rows))


def model_report(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Per-class + overall metrics for one model's result rows."""
    classes = sorted({str(r.get("category", "")) for r in rows if r.get("category")})
    per_class = {c: summarize([r for r in rows if r.get("category") == c]) for c in classes}
    overall = summarize(rows)
    task_success = _benign_task_success(rows)
    model_id = rows[0].get("model", "?") if rows else "?"
    return {
        "model": model_id,
        "is_frontier": _is_frontier(rows),
        "n": len(rows),
        "per_class": per_class,
        "asr_valid": overall["asr_valid"],
        "asr_all": overall["asr_all"],
        "refusal_rate": overall["refusal_rate"],
        "invalid_rate": _invalid_rate(rows),
        "over_action_rate": overall["over_action_rate"],
        "task_success_rate": task_success,
        "over_caution_rate": 1.0 - task_success,
        "execution_rate": overall["execution_rate"],
        "over_refusal_rate": overall["over_refusal_rate"],
        "corpus_version": rows[0].get("corpus_version", "?") if rows else "?",
    }


def _mean(xs: list[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def small_vs_frontier_gap(reports: list[dict[str, Any]]) -> dict[str, Any]:
    """Per-class + overall gap = mean small-model ASR_valid − frontier ASR_valid.

    Positive = small models fall to catastrophes the frontier resists — the
    core Phase-0 signal. `null` where no frontier anchor is present.
    """
    small = [r for r in reports if not r["is_frontier"]]
    frontier = next((r for r in reports if r["is_frontier"]), None)
    classes = sorted({c for r in reports for c in r["per_class"]})
    per_class: dict[str, Any] = {}
    for c in classes:
        small_v = _mean([r["per_class"][c]["asr_valid"] for r in small if c in r["per_class"]])
        if frontier and c in frontier["per_class"]:
            per_class[c] = round(small_v - frontier["per_class"][c]["asr_valid"], 4)
        else:
            per_class[c] = None
    overall_small = _mean([r["asr_valid"] for r in small])
    overall = round(overall_small - frontier["asr_valid"], 4) if frontier else None
    return {"overall": overall, "per_class": per_class,
            "frontier_model": frontier["model"] if frontier else None}


def baseline_report(directory: Path) -> dict[str, Any]:
    """The full Baseline v1 structure over every result file in `directory`."""
    files = sorted(directory.glob("*.jsonl"))
    reports = [model_report(load_rows(p)) for p in files if load_rows(p)]
    corpus_versions = sorted({r["corpus_version"] for r in reports})
    return {
        "baseline": "v1",
        "verifier": "off",
        "corpus_version": corpus_versions[0] if len(corpus_versions) == 1 else corpus_versions,
        "n_models": len(reports),
        "models": reports,
        "gap": small_vs_frontier_gap(reports),
    }


def render_markdown(report: dict[str, Any]) -> str:
    """The published Baseline v1 table (Markdown)."""
    lines = [
        "# Baseline v1 (verifier OFF)",
        "",
        f"Corpus `{report['corpus_version']}` × {report['n_models']} model(s). "
        "ASR_v = attack-success excluding format-invalid; the honest catastrophe rate.",
        "",
        "## Per-model summary",
        "",
        "| model | ASR_v | ASR_all | refuse | invalid | over-action | task-succ | over-refuse |",
        "|---|--:|--:|--:|--:|--:|--:|--:|",
    ]
    for m in report["models"]:
        tag = " *(frontier)*" if m["is_frontier"] else ""
        lines.append(
            f"| {m['model']}{tag} | {m['asr_valid']:.2f} | {m['asr_all']:.2f} | "
            f"{m['refusal_rate']:.2f} | {m['invalid_rate']:.2f} | {m['over_action_rate']:.2f} | "
            f"{m['task_success_rate']:.2f} | {m['over_refusal_rate']:.2f} |"
        )
    gap = report["gap"]
    lines += ["", "## Small-vs-frontier gap (ASR_v: small mean − frontier)", ""]
    if gap["frontier_model"] is None:
        lines.append("_No frontier anchor in these results — gap not computed._")
    else:
        lines.append(f"Overall: **{gap['overall']:+.2f}** vs `{gap['frontier_model']}`.")
        lines += ["", "| floor_class | gap |", "|---|--:|"]
        for c, g in gap["per_class"].items():
            lines.append(f"| {c} | {g:+.2f} |" if g is not None else f"| {c} | — |")
    classes = sorted({c for m in report["models"] for c in m["per_class"]})
    lines += ["", "## ASR_v per floor_class per model", "",
              "| model | " + " | ".join(classes) + " |",
              "|---|" + "--:|" * len(classes)]
    for m in report["models"]:
        cells = [f"{m['per_class'][c]['asr_valid']:.2f}" if c in m["per_class"] else "—"
                 for c in classes]
        lines.append(f"| {m['model']} | " + " | ".join(cells) + " |")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Emit the Baseline v1 report from sweep results.")
    parser.add_argument("--dir", default=None, help="results dir (default: eval/results)")
    parser.add_argument("--out", default=None, help="output dir for baseline_v1.{md,json}")
    args = parser.parse_args(argv)

    directory = Path(args.dir) if args.dir else results_dir()
    files = sorted(directory.glob("*.jsonl"))
    if not files:
        print(f"[report] no result files in {directory} — run the sweep first (E6)")
        return 0

    report = baseline_report(directory)
    out_dir = Path(args.out) if args.out else directory
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "baseline_v1.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    md = render_markdown(report)
    (out_dir / "baseline_v1.md").write_text(md, encoding="utf-8")
    print(md)
    print(f"[report] wrote baseline_v1.md + baseline_v1.json to {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
