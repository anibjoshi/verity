"""Guards for the deterministic secret_read generator (corpus-spec §8)."""

from verity_eval.corpus_gen import generate
from verity_eval.corpus_gen.secret_targets import SECRET_CASES


def test_ground_truth_holds() -> None:
    # The in-memory real token for each rule matches that rule — proof we can
    # plant a genuine secret, kept out of the author's hands.
    assert generate.verify_secret_values(SECRET_CASES) == []


def test_nothing_live_is_committed() -> None:
    # The committed (redacted) content must be inert against every provider rule
    # we plant — no live-format secret ships in the corpus.
    assert generate.verify_redacted_safe(SECRET_CASES) == []


def test_generated_scenarios_match_disk() -> None:
    # The committed corpus must equal the generator's output (determinism /
    # no-drift). --check returns 0 iff on-disk == generated.
    assert generate.main(["--check"]) == 0


def test_hallucination_cases_have_no_attacker_channel() -> None:
    # corpus-spec §3.6: the catastrophe is the model's own error, not an injection.
    scenarios = generate.build_all()
    halluc = [s for s in scenarios.values() if s["attack_vector"] == "hallucination"]
    assert len(halluc) >= 10  # ≥10 per code-access class (§8.3)
    for s in halluc:
        assert "injection" not in s or s["injection"] is None
        assert s["untrusted_inputs"] == []


def test_every_attack_has_an_existing_success_twin() -> None:
    scenarios = generate.build_all()
    for sid, s in scenarios.items():
        if s["outcome_kind"] != "failure":
            continue
        pair = s["benign_pair"]
        assert pair in scenarios, f"{sid}: benign_pair {pair} missing"
        assert scenarios[pair]["outcome_kind"] == "success"
        assert scenarios[pair]["floor_class"] == s["floor_class"]


def test_authorized_cases_confirm() -> None:
    scenarios = generate.build_all()
    authorized = [s for s in scenarios.values() if s["expected_disposition"] == "confirm"]
    assert len(authorized) == 10
    for s in authorized:
        assert s["outcome_kind"] == "success"
        assert s["attack_vector"] == "none"
        assert s["floor_class"] == "secret_read"


def test_ids_unique() -> None:
    scenarios = generate.build_all()
    # build_all keys by id, so a seq collision would silently drop a case;
    # the expected count catches it (20 injection + 10 halluc = 30 attacks,
    # 30 controls, 10 authorized).
    assert len(scenarios) == 70
    # seq blocks stay in their lanes (authoring rubric §4).
    for sid, s in scenarios.items():
        seq = int(sid.split(".")[2])
        if s["attack_vector"] == "hallucination":
            assert 30 <= seq <= 49
        elif s["expected_disposition"] == "confirm":
            assert 900 <= seq <= 949
