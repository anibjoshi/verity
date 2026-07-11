"""Guards for the run provenance manifest (E6, eval-plan §11)."""

import re

from verity_eval.runner import models as matrix
from verity_eval.runner.manifest import ModelSpec, build_manifest, git_sha


def test_git_sha_resolves() -> None:
    sha = git_sha()
    # 40-hex commit, or "unknown" only if there is no .git (there is, here).
    assert re.fullmatch(r"[0-9a-f]{40}", sha), sha


def test_build_manifest_is_complete() -> None:
    spec = matrix.BY_ID["Qwen/Qwen2.5-3B-Instruct"]
    m = build_manifest(spec, corpus_version="1.0", engine_version="0.6.3")
    assert m.is_complete()
    assert m.missing_fields() == []
    d = m.to_dict()
    assert d["harness_sha"] and d["corpus_version"] == "1.0"
    assert d["model"]["tool_parser"] == "hermes"


def test_incomplete_manifest_is_flagged() -> None:
    spec = matrix.BY_ID["Qwen/Qwen2.5-3B-Instruct"]
    m = build_manifest(spec, corpus_version="1.0", engine_version="")
    assert not m.is_complete()
    assert "engine_version" in m.missing_fields()


def test_frontier_anchor_and_derived_specs() -> None:
    # The matrix has the five small families + one frontier anchor.
    assert matrix.FRONTIER_ANCHOR.served_by == "api"
    assert len(matrix.MATRIX) == 9
    # An unknown id still resolves to a usable spec (derived family).
    derived = matrix.spec_for("Qwen/Qwen2.5-0.5B-Instruct")
    assert derived.family == "qwen2.5" and derived.tool_parser == "hermes"


def test_modelspec_identity_fields() -> None:
    d = ModelSpec("x/y", "fam").to_dict()
    for f in ("id", "family", "revision", "quantization", "chat_template", "served_by"):
        assert f in d
