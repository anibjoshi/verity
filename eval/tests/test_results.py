from verity_eval.results import ResultRow, role_of, role_of_row


def test_role_of() -> None:
    assert role_of("failure", "deny") == "attack"
    assert role_of("success", "confirm") == "authorized"
    assert role_of("success", "allow") == "benign"


def test_role_of_row_explicit_then_derived() -> None:
    assert role_of_row({"role": "attack"}) == "attack"  # explicit wins
    assert role_of_row({"outcome_kind": "failure", "expected_disposition": "deny"}) == "attack"
    confirm = {"outcome_kind": "success", "expected_disposition": "confirm"}
    assert role_of_row(confirm) == "authorized"
    allow = {"outcome_kind": "success", "expected_disposition": "allow"}
    assert role_of_row(allow) == "benign"


def test_result_row_to_dict_drops_empty_extra() -> None:
    row = ResultRow(
        source="authored", ref="x", model="m", role="attack",
        outcome="safe", executed_success=None, category="secret_read",
    )
    d = row.to_dict()
    assert "extra" not in d
    assert d["source"] == "authored" and d["role"] == "attack"


def test_result_row_keeps_extra() -> None:
    row = ResultRow(
        source="agentdojo", ref="banking/ut0+it1", model="m", role="attack",
        outcome="attempted_violation", executed_success=True, category="banking",
        extra={"injection_task": "it1"},
    )
    assert row.to_dict()["extra"] == {"injection_task": "it1"}
