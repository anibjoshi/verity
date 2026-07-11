"""Guards for the deterministic self_mod generator (corpus-spec §8)."""

from verity_eval.corpus_gen import self_mod


def test_attack_paths_match_their_form() -> None:
    # Every attack / authorized target path matches its self-mod form.
    assert self_mod.verify_attack_paths() == []


def test_benign_paths_trip_no_selfmod_regex() -> None:
    # Every benign twin path matches no self-mod regex — the crispness guarantee.
    assert self_mod.verify_controls_safe() == []


def test_generated_scenarios_match_disk() -> None:
    assert self_mod.main(["--check"]) == 0


def test_hallucination_cases_have_no_attacker_channel() -> None:
    scenarios = self_mod.build_all()
    halluc = [s for s in scenarios.values() if s["attack_vector"] == "hallucination"]
    assert len(halluc) >= 10  # ≥10 per code-access class (§8.3)
    for s in halluc:
        assert "injection" not in s or s["injection"] is None
        assert s["untrusted_inputs"] == []


def test_every_attack_has_an_existing_success_twin() -> None:
    scenarios = self_mod.build_all()
    for sid, s in scenarios.items():
        if s["outcome_kind"] != "failure":
            continue
        pair = s["benign_pair"]
        assert pair in scenarios, f"{sid}: benign_pair {pair} missing"
        assert scenarios[pair]["outcome_kind"] == "success"
        assert scenarios[pair]["floor_class"] == "self_mod"


def test_authorized_cases_confirm() -> None:
    scenarios = self_mod.build_all()
    authorized = [s for s in scenarios.values() if s["expected_disposition"] == "confirm"]
    assert len(authorized) == 10
    for s in authorized:
        assert s["outcome_kind"] == "success"
        assert s["floor_class"] == "self_mod"


def test_ids_unique_and_in_lanes() -> None:
    scenarios = self_mod.build_all()
    # 15 injection + 15 halluc = 30 attacks, 30 controls, 10 authorized.
    assert len(scenarios) == 70
    for sid, s in scenarios.items():
        seq = int(sid.split(".")[2])
        if s["attack_vector"] == "hallucination":
            assert 30 <= seq <= 49
        elif s["expected_disposition"] == "confirm":
            assert 900 <= seq <= 949
