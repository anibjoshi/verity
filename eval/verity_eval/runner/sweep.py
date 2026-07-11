"""The E6 model sweep: the matrix (models × corpus) under full provenance.

The live sweep needs GPU/serving (vLLM, one model at a time — the RTX 4070
serves each model in turn; see the `local-serving-setup` notes). It runs
out-of-band, not in PR CI. ``--dry-run`` exercises the whole orchestration +
manifest path with a stub client and no server, so the plumbing is CI-testable.

    # one served model (server already up for it):
    python -m verity_eval.runner.sweep --models Qwen/Qwen2.5-3B-Instruct
    # the frontier ladder (keys in the env: OPENAI_API_KEY / ANTHROPIC_API_KEY /
    # GEMINI_API_KEY; model id overridable via FRONTIER_<GPT|CLAUDE|GEMINI>_MODEL):
    python -m verity_eval.runner.sweep --models frontier-gpt,frontier-claude,frontier-gemini
    # GPU-free smoke of the whole matrix:
    python -m verity_eval.runner.sweep --dry-run
"""

from __future__ import annotations

import argparse
import json
import os
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
        # Resolve the target: a local vLLM server, or a frontier API (its own
        # OpenAI-compatible endpoint + key). For API anchors the concrete model id
        # comes from FRONTIER_<SLUG>_MODEL, else the spec's default.
        api_key: str | None = None
        if spec.served_by == "api":
            slug_env = spec.id.rsplit("-", 1)[-1].upper()  # frontier-gpt -> GPT
            api_model = os.environ.get(f"FRONTIER_{slug_env}_MODEL", spec.default_api_model)
            api_key = os.environ.get(spec.api_key_env)
            if not api_key and not args.dry_run:
                print(f"[sweep] skip {spec.id}: {spec.api_key_env} not set in env")
                continue
            model = replace(spec, id=api_model)
            base_url, eng = spec.base_url, spec.base_url
            conc = min(args.concurrency, 8)  # be gentle on API rate limits
        else:
            model = spec
            base_url, eng, conc = args.base_url, engine_version, args.concurrency

        slug = model.id.replace("/", "__")
        if args.resume and (out_dir / f"{slug}.jsonl").is_file():
            print(f"[sweep] skip {model.id} (resume; results exist)")
            continue

        manifest = build_manifest(
            model, corpus_version=corpus_version, engine_version=eng, seed=args.seed,
            temperature=args.temperature, max_tokens=args.max_tokens,
            max_steps=args.max_steps, guided_decoding=f"tool_choice={args.tool_choice}",
        )
        if not manifest.is_complete():
            incomplete += 1
            print(f"[sweep] WARNING incomplete manifest {model.id}: {manifest.missing_fields()}")

        client: Any
        if args.dry_run:
            client = DryRunClient()
        else:
            client = VLLMClient(
                model=model.id, base_url=base_url,
                temperature=args.temperature, max_tokens=args.max_tokens,
                tool_choice=args.tool_choice, api_key=api_key,
            )
        print(f"[sweep] {model.id} ({model.served_by}, engine={eng}, concurrency={conc})")
        jsonl = run_model(
            model, scenarios, client, manifest, out_dir, max_steps=args.max_steps, concurrency=conc,
        )
        print(f"[sweep]   → {jsonl}")

    if incomplete:
        print(f"[sweep] {incomplete} model(s) had an incomplete manifest — fix pins before scoring")
        return 1
    print("[sweep] done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
