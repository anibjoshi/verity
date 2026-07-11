"""The E6 model sweep: the matrix (models × corpus) under full provenance.

The live sweep needs GPU/serving (vLLM, one model at a time — the RTX 4070
serves each model in turn; see the `local-serving-setup` notes). It runs
out-of-band, not in PR CI. ``--dry-run`` exercises the whole orchestration +
manifest path with a stub client and no server, so the plumbing is CI-testable.

    # one served model (server already up for it):
    python -m verity_eval.runner.sweep --models Qwen/Qwen2.5-3B-Instruct
    # the frontier anchor over an OpenAI-compatible API:
    python -m verity_eval.runner.sweep --models frontier-anchor \
        --frontier-id gpt-4o --base-url https://api.example/v1
    # GPU-free smoke of the whole matrix:
    python -m verity_eval.runner.sweep --dry-run
"""

from __future__ import annotations

import argparse
import json
from dataclasses import replace
from pathlib import Path
from typing import Any

from verity_eval.corpus_check import corpus_dir
from verity_eval.harness.scenario import load_scenarios
from verity_eval.harness.serving import ChatResponse, VLLMClient
from verity_eval.runner import models as matrix
from verity_eval.runner.execute import run_model
from verity_eval.runner.manifest import build_manifest, probe_engine_version


class DryRunClient:
    """A no-server stub modelling a maximally-cautious "always explain, never act"
    agent: it emits a single ``respond`` tool call. Proves the orchestration +
    manifest path without a model; every scenario scores `safe`."""

    def chat(
        self, messages: list[dict[str, Any]], tools: list[dict[str, Any]], tool_choice: str = "auto"
    ) -> ChatResponse:
        return ChatResponse(
            message={
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "dryrun",
                        "type": "function",
                        "function": {
                            "name": "respond",
                            "arguments": json.dumps({"text": "Dry-run: no floor action taken."}),
                        },
                    }
                ],
            }
        )


def results_dir() -> Path:
    return corpus_dir().parent / "results"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Run the model × corpus sweep (baseline; verifier OFF)."
    )
    p.add_argument("--models", default="", help="comma-separated model ids (default: full matrix)")
    p.add_argument("--base-url", default="http://localhost:8000/v1")
    p.add_argument("--out", default=None, help="results dir (default: eval/results)")
    p.add_argument("--max-steps", type=int, default=6)
    p.add_argument("--concurrency", type=int, default=1,
                   help="parallel scenarios per model (vLLM batches them); 1 = sequential")
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--temperature", type=float, default=0.0)
    p.add_argument("--max-tokens", type=int, default=512)
    p.add_argument("--tool-choice", default="required",
                   help="vLLM tool_choice: required (forced/guided) | auto")
    p.add_argument("--engine-version", default=None, help="override the engine-version probe")
    p.add_argument("--frontier-id", default=None, help="concrete id for the frontier anchor slot")
    p.add_argument("--dry-run", action="store_true", help="stub client, no server (smoke test)")
    p.add_argument("--resume", action="store_true", help="skip models whose results already exist")
    args = p.parse_args(argv)

    ids = [s.strip() for s in args.models.split(",") if s.strip()]
    specs = matrix.select(ids or None)
    scenarios = load_scenarios()
    out_dir = Path(args.out) if args.out else results_dir()

    corpus_version = scenarios[0].corpus_version if scenarios else "unknown"
    engine_version = args.engine_version or (
        "dry-run" if args.dry_run else probe_engine_version(args.base_url)
    )

    print(f"[sweep] {len(specs)} model(s) × {len(scenarios)} scenario(s) → {out_dir}")
    incomplete = 0
    for spec in specs:
        model = spec
        if model.id == "frontier-anchor" and args.frontier_id:
            model = replace(spec, id=args.frontier_id)
        slug = model.id.replace("/", "__")
        if args.resume and (out_dir / f"{slug}.jsonl").is_file():
            print(f"[sweep] skip {model.id} (resume; results exist)")
            continue

        manifest = build_manifest(
            model,
            corpus_version=corpus_version,
            engine_version=engine_version,
            seed=args.seed,
            temperature=args.temperature,
            max_tokens=args.max_tokens,
            max_steps=args.max_steps,
            guided_decoding=f"tool_choice={args.tool_choice}",
        )
        if not manifest.is_complete():
            incomplete += 1
            print(f"[sweep] WARNING incomplete manifest {model.id}: {manifest.missing_fields()}")

        client: Any
        if args.dry_run:
            client = DryRunClient()
        else:
            client = VLLMClient(
                model=model.id, base_url=args.base_url,
                temperature=args.temperature, max_tokens=args.max_tokens,
                tool_choice=args.tool_choice,
            )
        print(f"[sweep] {model.id} ({model.served_by}, engine={engine_version}, "
              f"concurrency={args.concurrency})")
        jsonl = run_model(
            model, scenarios, client, manifest, out_dir,
            max_steps=args.max_steps, concurrency=args.concurrency,
        )
        print(f"[sweep]   → {jsonl}")

    if incomplete:
        print(f"[sweep] {incomplete} model(s) had an incomplete manifest — fix pins before scoring")
        return 1
    print("[sweep] done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
