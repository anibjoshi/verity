"""AgentDojo adapter tests — the pure projection (no agentdojo needed in CI) and
the oracle-independence firewall (§7.2)."""

from pathlib import Path

from verity_eval.adapters import agentdojo_adapter as ada


def test_rows_from_agentdojo_projection() -> None:
    rows = ada.rows_from_agentdojo(
        model="m",
        suite="banking",
        benign_utility={"user_task_0": True, "user_task_1": False},
        attack_security={("user_task_0", "injection_task_0"): True,
                         ("user_task_1", "injection_task_0"): False},
        attack_utility={("user_task_0", "injection_task_0"): False,
                        ("user_task_1", "injection_task_0"): True},
    )
    by_ref = {r.ref: r for r in rows}

    # benign half maps utility -> executed_success, role=benign, outcome=safe
    b0 = by_ref["banking/user_task_0"]
    assert b0.role == "benign" and b0.outcome == "safe" and b0.executed_success is True

    # attack half: security True -> attempted_violation; False -> safe
    a_hit = by_ref["banking/user_task_0+injection_task_0"]
    assert a_hit.role == "attack" and a_hit.outcome == "attempted_violation"
    a_miss = by_ref["banking/user_task_1+injection_task_0"]
    assert a_miss.role == "attack" and a_miss.outcome == "safe"
    assert a_miss.executed_success is True  # legit task still done under the (failed) attack
    assert a_hit.source == "agentdojo" and a_hit.category == "banking"


def test_oracle_independence_firewall() -> None:
    # §7.2: the adapter's scoring is AgentDojo's own security()/utility(); it must
    # not import or reference any Verity verifier predicate (grading stays honest).
    src = Path(ada.__file__).read_text(encoding="utf-8")
    for forbidden in ("verity_core", "is_secret", "is_external", "is_dangerous_command"):
        assert forbidden not in src, f"adapter must not reference verifier predicate: {forbidden}"
