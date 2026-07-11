"""Guards for the benign trigger-word pool generator (corpus-spec §6/§8)."""

from verity_eval.corpus_gen import benign_pool


def test_verify_passes() -> None:
    assert benign_pool.verify() == []


def test_generated_scenarios_match_disk() -> None:
    assert benign_pool.main(["--check"]) == 0


def test_pool_is_all_benign() -> None:
    scenarios = benign_pool.build_all()
    assert len(scenarios) == 150  # 30 triggers x 5 templates
    for sid, s in scenarios.items():
        assert s["floor_class"] == "none"
        assert s["outcome_kind"] == "success"
        assert s["expected_disposition"] == "allow"
        assert s["label"]["is_violation_possible"] is False
        assert s["untrusted_inputs"] == []
        assert "injection" not in s
        assert s["benign_pair"] is None
        assert s["oracle"]["success_actions"], f"{sid}: needs a success action"


def test_all_families_and_templates_represented() -> None:
    families = {t.family for t in benign_pool.TRIGGERS}
    assert families == {"shell", "secret", "self_mod", "financial", "net_egress", "generic"}
    # seq lane: benign pool lives at 9010+ (E0's 9001-9004 predate the block).
    for sid in benign_pool.build_all():
        assert int(sid.split(".")[2]) >= 9010
