# Model sweep (E6)

Runs the corpus against the model matrix and stamps a **complete provenance
manifest** on every result row — the input to Baseline v1 (E7). The verifier is
OFF here (this is the baseline; verifier-ON is Phase 2).

## The live sweep runs out-of-band (GPU)

Serving needs vLLM on a GPU, **one model at a time** (the RTX 4070 serves each in
turn — see the `local-serving-setup` notes). It is deliberately **not** in PR CI.
The loop:

```bash
# 1. serve one model (separate process)
vllm serve Qwen/Qwen2.5-3B-Instruct --tool-call-parser hermes --gpu-memory-utilization 0.85
# 2. run just that model against the corpus
uv run python -m verity_eval.runner.sweep --models Qwen/Qwen2.5-3B-Instruct
# 3. stop the server, repeat for the next model
```

`--resume` skips models whose results already exist, so the sequential sweep is
restartable. The **frontier ladder** is API-served (OpenAI / Anthropic / Google
all expose an OpenAI-compatible endpoint). Put keys in the env
(`OPENAI_API_KEY` / `ANTHROPIC_API_KEY` / `GEMINI_API_KEY`); the model id per
anchor is overridable via `FRONTIER_<GPT|CLAUDE|GEMINI>_MODEL`:

```bash
uv run python -m verity_eval.runner.sweep --models frontier-gpt,frontier-claude,frontier-gemini
```

An anchor whose key env var is unset is skipped. API sweeps auto-cap concurrency
(gentle on rate limits); the key is read at run time and never stored in a manifest.

## GPU-free smoke

`--dry-run` uses a stub client (no server): every scenario scores `safe`, but the
orchestration, row shape, and manifest stamping are exercised end-to-end. This is
what the `test_sweep` / `test_manifest` suites run in CI.

```bash
uv run python -m verity_eval.runner.sweep --dry-run
```

## Output

Per model, under `eval/results/` (git-ignored):

- `<slug>.jsonl` — one row per scenario, each carrying the full `manifest`
- `<slug>.manifest.json` — the manifest, mirrored for convenience

Every row also carries the common result-row contract (`role`, `outcome`,
`executed_success`, `category`, …) that `metrics.py` groups by.

## The manifest (eval-plan §11)

"Pin everything," so a baseline is reproducible up to documented
batch-nondeterminism:

| field | source |
|---|---|
| `model.{id,revision,quantization,chat_template,tool_parser,served_by,params_b}` | the matrix (`models.py`); `revision` should be pinned to a HF SHA for a scored run |
| `engine` / `engine_version` | `served_by`; version probed from vLLM `/version` (or `--engine-version`) |
| `temperature` / `seed` / `max_tokens` | sampling (temp-0 greedy + fixed seed) |
| `guided_decoding` | decode-constraint tag |
| `corpus_version` | from the loaded corpus |
| `harness_sha` | read from `.git` (no `subprocess` — banned by the harness-purity gate) |
| `max_steps` | ReAct step cap |

`RunManifest.is_complete()` is the E6 exit-gate check — the sweep warns (and exits
non-zero) if any pin is missing before a scored run.
