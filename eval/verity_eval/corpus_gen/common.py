"""Shared machinery for the per-class corpus generators (E5, corpus-spec §8).

Each floor class has its own generator module (``generate`` for ``secret_read``,
``shell_exec`` for ``shell_exec``, …) that supplies a ground-truth ``verify`` and
a ``build_all``. The emission, key ordering, byte formatting, and the
``--write``/``--check`` CLI are identical across classes and live here, so a new
class is just a catalog + builders.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

from verity_eval.corpus_check import corpus_dir

# corpus_version stays 1.0 through E5; the bump + freeze is E7's job (CORPUS.lock).
CORPUS_VERSION = "1.0"

# Canonical key order — mirrors the field reference (corpus-spec §2.1) and the
# hand-authored E0 files, so generated files diff cleanly against them.
KEY_ORDER = [
    "id",
    "corpus_version",
    "source",
    "seed_ref",
    "floor_class",
    "attack_vector",
    "outcome_kind",
    "expected_disposition",
    "user_instruction",
    "environment",
    "tools",
    "untrusted_inputs",
    "injection",
    "oracle",
    "label",
    "benign_pair",
]


def scenarios_dir() -> Path:
    """Where materialized scenarios live (``eval/corpus/scenarios``)."""
    return corpus_dir() / "scenarios"


def seeds_dir() -> Path:
    """The vendored seed corpora root (``eval/seeds``)."""
    return corpus_dir().parent / "seeds"


def ordered(d: dict[str, Any]) -> dict[str, Any]:
    """Reorder a scenario dict into the canonical key order."""
    return {k: d[k] for k in KEY_ORDER if k in d}


def dump(scenario: dict[str, Any]) -> str:
    """Serialize a scenario to the corpus's on-disk byte format."""
    return json.dumps(scenario, indent=2, ensure_ascii=False) + "\n"


def run_cli(
    argv: list[str] | None,
    *,
    label: str,
    verify: Callable[[], list[str]],
    build_all: Callable[[], dict[str, dict[str, Any]]],
) -> int:
    """The shared ``--write`` / ``--check`` / summary CLI for a class generator.

    ``verify`` returns ground-truth/safety failures (empty = OK); ``build_all``
    returns ``id -> scenario``. Generation always runs ``verify`` first and aborts
    on any failure, so no run can emit a scenario whose ground truth doesn't hold.
    """
    parser = argparse.ArgumentParser(description=f"Generate the {label} E5 tranche.")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--write", action="store_true", help="materialize scenario files")
    group.add_argument(
        "--check", action="store_true", help="assert on-disk files equal the generated output"
    )
    args = parser.parse_args(argv)

    checks = verify()
    if checks:
        print(f"[corpus-gen:{label}] {len(checks)} ground-truth / safety failure(s):")
        for e in checks:
            print(f"    {e}")
        return 1

    scenarios = build_all()
    scen_dir = scenarios_dir()

    if args.write:
        for sid, obj in scenarios.items():
            (scen_dir / f"{sid}.json").write_text(dump(obj), encoding="utf-8")
        print(f"[corpus-gen:{label}] wrote {len(scenarios)} scenario(s)")
        return 0

    if args.check:
        drift: list[str] = []
        for sid, obj in scenarios.items():
            path = scen_dir / f"{sid}.json"
            if not path.is_file():
                drift.append(f"{sid}: missing on disk")
            elif path.read_text(encoding="utf-8") != dump(obj):
                drift.append(f"{sid}: on-disk content differs from generator output")
        if drift:
            print(f"[corpus-gen:{label}] {len(drift)} drift(s) (run --write):")
            for d in drift:
                print(f"    {d}")
            return 1
        print(f"[corpus-gen:{label}] {len(scenarios)} scenario(s) match on disk")
        return 0

    attacks = sum(1 for o in scenarios.values() if o["outcome_kind"] == "failure")
    halluc = sum(1 for o in scenarios.values() if o["attack_vector"] == "hallucination")
    confirm = sum(1 for o in scenarios.values() if o["expected_disposition"] == "confirm")
    controls = sum(1 for sid in scenarios if sid.endswith(".control"))
    print(
        f"[corpus-gen:{label}] checks OK · {len(scenarios)} scenario(s): "
        f"{attacks} attacks ({halluc} hallucination), {controls} controls, {confirm} authorized"
    )
    return 0
