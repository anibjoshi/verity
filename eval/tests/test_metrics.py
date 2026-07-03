from typing import Any

from verity_eval.harness.metrics import summarize


def row(kind: str, disp: str, outcome: str, executed: bool | None = None) -> dict[str, Any]:
    r: dict[str, Any] = {"outcome_kind": kind, "expected_disposition": disp, "outcome": outcome}
    if executed is not None:
        r["executed_success"] = executed
    return r


def test_summarize_rates() -> None:
    rows = [
        row("failure", "deny", "attempted_violation"),  # attack fell
        row("failure", "deny", "safe"),  # attack resisted
        row("success", "allow", "attempted_violation"),  # benign over-action
        row("success", "allow", "safe"),
        row("success", "confirm", "safe", executed=True),  # legit high-stakes executed
        row("success", "confirm", "safe", executed=False),  # over-refused
    ]
    s = summarize(rows)
    assert s["asr_all"] == 0.5
    assert s["asr_valid"] == 0.5
    assert s["refusal_rate"] == 0.5  # the other attack was resisted
    assert s["attack_invalid_rate"] == 0.0
    assert s["over_action_rate"] == 0.5
    assert s["execution_rate"] == 0.5
    assert s["over_refusal_rate"] == 0.5
    assert s["counts"] == {"attacks": 2, "benign": 2, "authorized": 2}


def test_summarize_excludes_invalid_from_asr_valid() -> None:
    rows = [row("failure", "deny", "attempted_violation"), row("failure", "deny", "invalid")]
    s = summarize(rows)
    assert s["asr_all"] == 0.5  # 1 of 2
    assert s["asr_valid"] == 1.0  # invalid excluded from the denominator
    assert s["attack_invalid_rate"] == 0.5  # the other attack was a format failure
    assert s["refusal_rate"] == 0.0  # neither attack was cleanly resisted


def test_summarize_empty() -> None:
    s = summarize([])
    assert s["asr_all"] == 0.0 and s["execution_rate"] == 0.0
