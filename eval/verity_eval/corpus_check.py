"""Corpus schema validation (the CI corpus job).

Schema-validates every scenario under ``eval/corpus`` against
``scenario.schema.json``. Green-when-empty: before G3 materializes the schema
and seeds there is nothing to validate, so this exits 0. At G3 the seeds arrive
and this becomes a real gate; integrity checks (matched-pair completeness, id
convention, taint markers, ``CORPUS.lock``) are added there.

Run: ``python -m verity_eval.corpus_check``.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def corpus_dir() -> Path:
    """The corpus root (``eval/corpus``), resolved relative to this package."""
    return Path(__file__).resolve().parents[1] / "corpus"


def main() -> int:
    root = corpus_dir()
    schema_path = root / "schema" / "scenario.schema.json"
    scenarios_dir = root / "scenarios"
    scenarios = sorted(scenarios_dir.rglob("*.json")) if scenarios_dir.is_dir() else []

    if not schema_path.is_file() or not scenarios:
        print(
            f"[corpus-check] nothing to validate yet (pre-G3): "
            f"schema={schema_path.is_file()}, scenarios={len(scenarios)}"
        )
        return 0

    import jsonschema

    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validator = jsonschema.Draft202012Validator(schema)

    failures = 0
    for path in scenarios:
        instance = json.loads(path.read_text(encoding="utf-8"))
        errors = sorted(validator.iter_errors(instance), key=lambda e: e.json_path)
        if errors:
            failures += 1
            print(f"[corpus-check] FAIL {path.relative_to(root)}")
            for err in errors:
                print(f"    {err.json_path}: {err.message}")

    total = len(scenarios)
    if failures:
        print(f"[corpus-check] {failures}/{total} scenario(s) invalid")
        return 1
    print(f"[corpus-check] {total} scenario(s) valid")
    return 0


if __name__ == "__main__":
    sys.exit(main())
