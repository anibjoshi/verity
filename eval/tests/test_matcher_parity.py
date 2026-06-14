"""Matcher-parity fixtures (testing-ci §2.3). The Python matcher must satisfy the
shared, language-neutral fixture set that the Rust verity-core matcher will later
satisfy byte-for-byte. Add cases to fixtures/matcher_cases.json, not here."""

import json
from pathlib import Path

from verity_eval.harness.matcher import match_action, match_value
from verity_eval.harness.tools import RecordedCall

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "matcher_cases.json"


def _load() -> dict:
    return json.loads(FIXTURES.read_text(encoding="utf-8"))


def test_value_cases() -> None:
    cases = _load()["value_cases"]
    assert cases, "no value cases loaded"
    for c in cases:
        got = match_value(c["matcher"], c["value"])
        assert got is c["expected"], f"match_value({c['matcher']!r}, {c['value']!r}) = {got}"


def test_action_cases() -> None:
    cases = _load()["action_cases"]
    assert cases, "no action cases loaded"
    for c in cases:
        call = RecordedCall(tool=c["call"]["tool"], args=c["call"].get("args", {}))
        got = match_action(c["spec"], call)
        assert got is c["expected"], f"match_action({c['spec']!r}, {call!r}) = {got}"
