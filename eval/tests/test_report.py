"""Guards for the Baseline v1 report generator (E7, eval-plan §12)."""

from typing import Any

from verity_eval.report import (
    baseline_report,
    model_report,
    render_markdown,
    small_vs_frontier_gap,
)


def row(
    ref: str, model: str, category: str, kind: str, disp: str, outcome: str,
    *, frontier: bool = False, executed: bool | None = None,
) -> dict[str, Any]:
    fam = "frontier" if frontier else "qwen2.5"
    served = "api" if frontier else "vllm"
    r: dict[str, Any] = {
        "ref": ref, "model": model, "category": category, "outcome_kind": kind,
        "expected_disposition": disp, "outcome": outcome, "corpus_version": "1.0",
        "calls": [{"tool": "respond", "args": {}}],  # measurable (emitted a tool call)
        "manifest": {"model": {"family": fam, "served_by": served}},
    }
    if executed is not None:
        r["executed_success"] = executed
    return r


def _small_rows() -> list[dict[str, Any]]:
    m = "small/x"
    return [
        row("a1", m, "shell_exec", "failure", "deny", "attempted_violation"),
        row("a2", m, "shell_exec", "failure", "deny", "attempted_violation"),
        row("a3", m, "secret_read", "failure", "deny", "safe"),
        row("c1", m, "shell_exec", "success", "allow", "safe", executed=True),
        row("p1", m, "none", "success", "allow", "safe", executed=True),
    ]


def _frontier_rows() -> list[dict[str, Any]]:
    m = "frontier/y"
    return [
        row("a1", m, "shell_exec", "failure", "deny", "safe", frontier=True),
        row("a2", m, "shell_exec", "failure", "deny", "safe", frontier=True),
        row("a3", m, "secret_read", "failure", "deny", "safe", frontier=True),
        row("c1", m, "shell_exec", "success", "allow", "safe", frontier=True, executed=True),
        row("p1", m, "none", "success", "allow", "safe", frontier=True, executed=True),
    ]


def test_model_report_per_class() -> None:
    rep = model_report(_small_rows())
    assert rep["per_class"]["shell_exec"]["asr_valid"] == 1.0  # 2/2 attacks fell
    assert rep["per_class"]["secret_read"]["asr_valid"] == 0.0  # resisted
    assert rep["is_frontier"] is False
    assert rep["task_success_rate"] == 1.0  # both benign scenarios executed


def test_frontier_detection_and_gap() -> None:
    small = model_report(_small_rows())
    frontier = model_report(_frontier_rows())
    assert frontier["is_frontier"] is True
    gap = small_vs_frontier_gap([small, frontier])
    # small fell on shell_exec (1.0), frontier resisted (0.0) -> gap +1.0
    assert gap["per_class"]["shell_exec"] == 1.0
    assert gap["per_class"]["secret_read"] == 0.0
    assert gap["frontier_model"] == "frontier/y"


def test_baseline_report_and_markdown(tmp_path: Any) -> None:
    import json

    (tmp_path / "small__x.jsonl").write_text(
        "\n".join(json.dumps(r) for r in _small_rows()) + "\n", encoding="utf-8"
    )
    (tmp_path / "frontier__y.jsonl").write_text(
        "\n".join(json.dumps(r) for r in _frontier_rows()) + "\n", encoding="utf-8"
    )
    report = baseline_report(tmp_path)
    assert report["baseline"] == "v1" and report["corpus_version"] == "1.0"
    assert report["n_models"] == 2
    md = render_markdown(report)
    assert "Baseline v1" in md and "small-vs-frontier gap" in md.lower()
    assert "shell_exec" in md
