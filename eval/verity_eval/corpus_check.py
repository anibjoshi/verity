"""Corpus schema validation + integrity checks (the CI corpus job).

Validates every scenario under ``eval/corpus`` against
``scenario.schema.json``, then runs structural integrity checks that the
schema alone can't express, and verifies the ``CORPUS.lock`` content hash so
no scenario changes silently. Green-when-empty: before the corpus is
materialized there is nothing to validate, so this exits 0.

Run:
    python -m verity_eval.corpus_check                # validate (CI gate)
    python -m verity_eval.corpus_check --write-lock   # regenerate CORPUS.lock
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections.abc import Iterator
from pathlib import Path
from typing import Any

# Mirrors scenario.schema.json's id pattern: {source}.{floor_class}.{NNNN}[.control]
ID_RE = re.compile(r"^[a-z0-9_]+\.[a-z_]+\.[0-9]{4}(\.control)?$")
TAINT_RE = re.compile(r"\{taint:([A-Za-z0-9_]+)\}")

LOCK_HINT = "run: python -m verity_eval.corpus_check --write-lock"


def corpus_dir() -> Path:
    """The corpus root (``eval/corpus``), resolved relative to this package."""
    return Path(__file__).resolve().parents[1] / "corpus"


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def iter_strings(obj: Any) -> Iterator[str]:
    """Yield every string value nested anywhere in ``obj``."""
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for value in obj.values():
            yield from iter_strings(value)
    elif isinstance(obj, list):
        for value in obj:
            yield from iter_strings(value)


def compute_lock(
    schema_path: Path, scenario_files: list[Path], root: Path, version: str
) -> dict[str, Any]:
    """The content manifest: sha256 of the schema + every scenario file."""
    files = {
        p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in [schema_path, *scenario_files]
    }
    return {"corpus_version": version, "scenario_count": len(scenario_files), "files": files}


def check_integrity(scenarios: dict[str, Any]) -> list[str]:
    """Structural invariants beyond the JSON Schema (corpus-spec §3)."""
    errs: list[str] = []
    versions: set[str] = set()

    for sid, s in sorted(scenarios.items()):
        versions.add(str(s.get("corpus_version")))

        # id convention + id segments agree with the typed fields
        if not ID_RE.match(sid):
            errs.append(f"{sid}: id violates the naming convention")
        parts = sid.split(".")
        if len(parts) >= 2:
            if parts[0] != s.get("source"):
                errs.append(f"{sid}: id source '{parts[0]}' != source field '{s.get('source')}'")
            if parts[1] != s.get("floor_class"):
                errs.append(
                    f"{sid}: id class '{parts[1]}' != floor_class '{s.get('floor_class')}'"
                )

        # outcome_kind must agree with label.is_violation_possible
        outcome = s.get("outcome_kind")
        ivp = s.get("label", {}).get("is_violation_possible")
        if (outcome == "failure") != (ivp is True):
            errs.append(
                f"{sid}: outcome_kind={outcome!r} inconsistent with is_violation_possible={ivp!r}"
            )

        # expected_disposition (the Phase-2 grading target) must agree with the
        # scenario role: attacks deny, legitimate-high-stakes confirm, else allow.
        disp = s.get("expected_disposition")
        if outcome == "failure" and disp != "deny":
            errs.append(f"{sid}: failure must have expected_disposition='deny' (got {disp!r})")
        if outcome == "success" and disp == "deny":
            errs.append(f"{sid}: success must not have expected_disposition='deny'")
        if disp == "confirm" and s.get("floor_class") == "none":
            errs.append(f"{sid}: confirm disposition requires a real floor_class (not 'none')")

        # taint integrity: every {taint:NAME} placed in the environment must be
        # declared in untrusted_inputs, and vice versa; the injection carrier too
        markers: set[str] = set()
        for text in iter_strings(s.get("environment", {})):
            markers.update(TAINT_RE.findall(text))
        declared = set(s.get("untrusted_inputs", []))
        for marker in sorted(markers - declared):
            errs.append(f"{sid}: taint marker '{marker}' not declared in untrusted_inputs")
        for name in sorted(declared - markers):
            errs.append(f"{sid}: untrusted_input '{name}' has no {{taint:{name}}} in environment")
        injection = s.get("injection")
        if isinstance(injection, dict) and injection.get("carrier") not in declared:
            carrier = injection.get("carrier")
            errs.append(f"{sid}: injection.carrier '{carrier}' not in untrusted_inputs")

        # matched-pair completeness
        pair = s.get("benign_pair")
        if outcome == "failure":
            if not pair:
                errs.append(f"{sid}: failure scenario has no benign_pair")
            elif pair not in scenarios:
                errs.append(f"{sid}: benign_pair '{pair}' does not exist")
            else:
                twin = scenarios[pair]
                if twin.get("outcome_kind") != "success":
                    errs.append(f"{sid}: benign_pair '{pair}' is not a success twin")
                if twin.get("floor_class") != s.get("floor_class"):
                    errs.append(f"{sid}: benign_pair '{pair}' floor_class differs from attack")
        elif pair is not None:
            errs.append(f"{sid}: success scenario should have benign_pair=null (got {pair!r})")

    if len(versions) > 1:
        errs.append(f"mixed corpus_version across scenarios: {sorted(versions)}")

    return errs


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate the Verity scenario corpus.")
    parser.add_argument(
        "--write-lock",
        action="store_true",
        help="regenerate CORPUS.lock from the current files and exit",
    )
    args = parser.parse_args(argv)

    root = corpus_dir()
    schema_path = root / "schema" / "scenario.schema.json"
    scenarios_dir = root / "scenarios"
    lock_path = root / "CORPUS.lock"
    scenario_files = sorted(scenarios_dir.rglob("*.json")) if scenarios_dir.is_dir() else []

    if not schema_path.is_file() or not scenario_files:
        print(
            f"[corpus-check] nothing to validate yet: "
            f"schema={schema_path.is_file()}, scenarios={len(scenario_files)}"
        )
        return 0

    # Load scenarios, checking filename<->id and uniqueness up front.
    errors: list[str] = []
    scenarios: dict[str, Any] = {}
    versions: set[str] = set()
    for path in scenario_files:
        obj = load_json(path)
        sid = obj.get("id")
        if isinstance(sid, str):
            if path.name != f"{sid}.json":
                errors.append(f"{path.name}: filename does not match id '{sid}'")
            if sid in scenarios:
                errors.append(f"{path.name}: duplicate id '{sid}'")
            scenarios[sid] = obj
            versions.add(str(obj.get("corpus_version")))
        else:
            errors.append(f"{path.name}: missing or non-string id")

    if args.write_lock:
        if len(versions) != 1:
            print(f"[corpus-check] cannot write lock: corpus_version is {sorted(versions)}")
            return 1
        lock = compute_lock(schema_path, scenario_files, root, versions.pop())
        lock_path.write_text(json.dumps(lock, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"[corpus-check] wrote CORPUS.lock ({lock['scenario_count']} scenarios)")
        return 0

    # 1. Schema validation
    import jsonschema

    validator = jsonschema.Draft202012Validator(load_json(schema_path))
    for path in scenario_files:
        obj = load_json(path)
        for err in sorted(validator.iter_errors(obj), key=lambda e: e.json_path):
            errors.append(f"{path.name}: schema: {err.json_path}: {err.message}")

    # 2. Structural integrity
    errors.extend(check_integrity(scenarios))

    # 3. Lock check
    if len(versions) == 1:
        expected = compute_lock(schema_path, scenario_files, root, next(iter(versions)))
        if not lock_path.is_file():
            errors.append(f"CORPUS.lock is missing ({LOCK_HINT})")
        else:
            actual = load_json(lock_path)
            if actual != expected:
                exp_files = expected["files"]
                act_files = actual.get("files", {}) if isinstance(actual, dict) else {}
                changed = sorted(
                    f for f in set(exp_files) | set(act_files)
                    if exp_files.get(f) != act_files.get(f)
                )
                errors.append(f"CORPUS.lock out of date ({LOCK_HINT}); differing: {changed}")

    total = len(scenario_files)
    if errors:
        print(f"[corpus-check] {len(errors)} problem(s) across {total} scenario(s):")
        for e in errors:
            print(f"    {e}")
        return 1

    pairs = sum(1 for s in scenarios.values() if s.get("outcome_kind") == "failure")
    print(f"[corpus-check] {total} scenario(s) valid · {pairs} matched pair(s) · lock OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
