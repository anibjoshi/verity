"""Guards for the model sweep orchestration (E6) — GPU-free via the stub client."""

import json
from pathlib import Path

from verity_eval.harness.scenario import load_scenarios
from verity_eval.runner import models as matrix
from verity_eval.runner.execute import run_model, run_scenario
from verity_eval.runner.manifest import build_manifest
from verity_eval.runner.sweep import DryRunClient, main


def test_run_scenario_never_raises_and_shapes_row() -> None:
    sc = load_scenarios()[0]
    row = run_scenario(sc, "test-model", DryRunClient(), max_steps=6)
    for key in ("source", "ref", "model", "role", "outcome", "category", "corpus_version"):
        assert key in row
    assert row["outcome"] in ("attempted_violation", "safe", "invalid", "error")


def test_run_model_stamps_complete_manifest_on_every_row(tmp_path: Path) -> None:
    spec = matrix.BY_ID["Qwen/Qwen2.5-3B-Instruct"]
    scenarios = load_scenarios()[:5]
    manifest = build_manifest(spec, corpus_version="1.0", engine_version="dry-run")
    jsonl = run_model(spec, scenarios, DryRunClient(), manifest, tmp_path)
    assert (tmp_path / "Qwen__Qwen2.5-3B-Instruct.manifest.json").is_file()
    rows = [json.loads(line) for line in jsonl.read_text().splitlines()]
    assert len(rows) == 5
    for r in rows:
        assert r["manifest"] == manifest.to_dict()  # complete manifest on every row
        assert r["outcome"] == "safe"  # dry-run: benign respond


def test_sweep_cli_dry_run(tmp_path: Path) -> None:
    rc = main(["--dry-run", "--models", "Qwen/Qwen2.5-1.5B-Instruct", "--out", str(tmp_path)])
    assert rc == 0
    jsonl = tmp_path / "Qwen__Qwen2.5-1.5B-Instruct.jsonl"
    assert jsonl.is_file()
    first = json.loads(jsonl.read_text().splitlines()[0])
    assert first["manifest"]["engine_version"] == "dry-run"
    assert first["manifest"]["harness_sha"]


def test_sweep_resume_skips_existing(tmp_path: Path) -> None:
    args = ["--dry-run", "--models", "Qwen/Qwen2.5-1.5B-Instruct", "--out", str(tmp_path)]
    assert main(args) == 0
    mtime = (tmp_path / "Qwen__Qwen2.5-1.5B-Instruct.jsonl").stat().st_mtime_ns
    assert main([*args, "--resume"]) == 0
    # resume left the file untouched
    assert (tmp_path / "Qwen__Qwen2.5-1.5B-Instruct.jsonl").stat().st_mtime_ns == mtime
