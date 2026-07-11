"""Single-model baseline run — a thin wrapper over the E6 runner.

Runs the corpus against one model and writes a manifest-stamped JSONL under
`eval/results/` (git-ignored); the verifier is OFF (baseline). For the full
matrix use `verity_eval.runner.sweep`. Needs a local vLLM server — see the
`local-serving-setup` notes.

    python -m verity_eval.harness.run --model Qwen/Qwen2.5-3B-Instruct
"""

from __future__ import annotations

import argparse
from pathlib import Path

from verity_eval.runner import models as matrix
from verity_eval.runner.execute import run_model
from verity_eval.runner.manifest import build_manifest, probe_engine_version
from verity_eval.runner.sweep import results_dir

from .scenario import load_scenarios
from .serving import VLLMClient


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run the Verity corpus against one model (baseline; verifier OFF)."
    )
    parser.add_argument("--model", default="Qwen/Qwen2.5-3B-Instruct")
    parser.add_argument("--base-url", default="http://localhost:8000/v1")
    parser.add_argument("--max-steps", type=int, default=6)
    parser.add_argument("--out", default=None, help="results dir (default: eval/results)")
    args = parser.parse_args(argv)

    scenarios = load_scenarios()
    model = matrix.spec_for(args.model)
    client = VLLMClient(model=model.id, base_url=args.base_url)
    manifest = build_manifest(
        model,
        corpus_version=scenarios[0].corpus_version if scenarios else "unknown",
        engine_version=probe_engine_version(args.base_url),
        max_steps=args.max_steps,
    )
    out_dir = Path(args.out) if args.out else results_dir()
    jsonl = run_model(
        model, scenarios, client, manifest, out_dir, max_steps=args.max_steps, progress=True
    )
    print(f"\nwrote {jsonl}")
    if not manifest.is_complete():
        print(f"WARNING incomplete manifest: {manifest.missing_fields()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
