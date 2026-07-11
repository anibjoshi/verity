"""Guards for the data-flow spanning generators (corpus-spec §8)."""

from verity_eval.corpus_gen import irreversible_financial, matchers, net_egress, tainted_exfil

_MODULES = [tainted_exfil, irreversible_financial, net_egress]


def test_matcher_semantics() -> None:
    # The matcher eval mirrors the harness/Rust semantics (corpus-spec §2.2/§7).
    assert matchers.matches({"regex": r"@evil\.com$"}, "a@evil.com")
    assert not matchers.matches({"regex": r"@evil\.com$"}, "a@ourco.com")
    assert matchers.matches({"one_of": ["x", "y"]}, "y")
    assert matchers.matches({"equals": 5}, 5)
    assert matchers.matches({"gt": 100000}, 100001)
    assert not matchers.matches({"gt": 100000}, 100000)
    assert matchers.matches({"le": 100000}, 100000)
    assert matchers.matches("Telco", "Telco")


def test_crispness_holds_each_class() -> None:
    # Attack targets trip the violating matcher; controls do not (per module verify).
    for mod in _MODULES:
        assert mod.verify() == [], mod.FLOOR_CLASS


def test_generated_scenarios_match_disk() -> None:
    for mod in _MODULES:
        assert mod.main(["--check"]) == 0, mod.FLOOR_CLASS


def test_attacks_are_tainted_and_deny() -> None:
    # Data-flow attacks are indirect_injection with taint on the path.
    for mod in _MODULES:
        for sid, s in mod.build_all().items():
            if s["outcome_kind"] != "failure":
                continue
            assert s["expected_disposition"] == "deny"
            assert s["attack_vector"] == "indirect_injection"
            assert s["untrusted_inputs"] == ["doc_body"]
            assert s["injection"] is not None
            assert s["benign_pair"] == f"{sid}.control"


def test_controls_and_authorized() -> None:
    for mod in _MODULES:
        scenarios = mod.build_all()
        controls = [s for sid, s in scenarios.items() if sid.endswith(".control")]
        authorized = [s for s in scenarios.values() if s["expected_disposition"] == "confirm"]
        assert len(authorized) == 6, mod.FLOOR_CLASS
        for s in controls:
            assert s["outcome_kind"] == "success"
            assert s["label"]["is_violation_possible"] is False
        for s in authorized:
            assert s["outcome_kind"] == "success"
            assert s["floor_class"] == mod.FLOOR_CLASS
