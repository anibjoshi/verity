"""The model sweep matrix (eval-plan §10): five small families for
cross-architecture evidence + one frontier anchor.

Small-model behavior is quant- and template-sensitive, so those are pinned per
entry; the tool parser comes from the decode registry (`decode.py`) — the single
source of per-model serving config. `revision` defaults to "main" here; a scored
run pins each to a HF revision SHA (recorded in the manifest).
"""

from __future__ import annotations

from verity_eval.harness.decode import REGISTRY, profile_for
from verity_eval.runner.manifest import ModelSpec


def _parser(family: str) -> str:
    profile = REGISTRY.get(family)
    return profile.tool_parser if profile else "auto"


# The five small families (eval-plan §10). Gemma weights are license-gated on HF.
SMALL_MATRIX: list[ModelSpec] = [
    ModelSpec("Qwen/Qwen2.5-3B-Instruct", "qwen2.5", tool_parser=_parser("qwen2.5"), params_b=3.0),
    ModelSpec(
        "Qwen/Qwen2.5-1.5B-Instruct", "qwen2.5", tool_parser=_parser("qwen2.5"), params_b=1.5
    ),
    # Qwen3 same-family size ladder (0.6B → 8B): isolates parameter size within one
    # lineage. 8B is served fp8 (fp16 won't fit 12 GB).
    ModelSpec("Qwen/Qwen3-0.6B", "qwen3", tool_parser=_parser("qwen3"), params_b=0.6),
    ModelSpec("Qwen/Qwen3-1.7B", "qwen3", tool_parser=_parser("qwen3"), params_b=1.7),
    ModelSpec("Qwen/Qwen3-4B", "qwen3", tool_parser=_parser("qwen3"), params_b=4.0),
    ModelSpec(
        "Qwen/Qwen3-8B", "qwen3", tool_parser=_parser("qwen3"), quantization="fp8", params_b=8.0
    ),
    ModelSpec(
        "meta-llama/Llama-3.2-3B-Instruct", "llama-3.2",
        tool_parser=_parser("llama-3.2"), params_b=3.0,
    ),
    ModelSpec(
        "meta-llama/Llama-3.2-1B-Instruct", "llama-3.2",
        tool_parser=_parser("llama-3.2"), params_b=1.0,
    ),
    ModelSpec(
        "NousResearch/Hermes-3-Llama-3.2-3B", "hermes-3",
        tool_parser=_parser("hermes-3"), params_b=3.0,
    ),
    ModelSpec("google/gemma-4-E4B-it", "gemma-4", tool_parser=_parser("gemma-4"), params_b=4.0),
    ModelSpec("google/gemma-4-E2B-it", "gemma-4", tool_parser=_parser("gemma-4"), params_b=2.0),
    ModelSpec(
        "microsoft/Phi-4-mini-instruct", "phi-4",
        tool_parser=_parser("phi-4"), params_b=3.8,
    ),
]

# The frontier ladder (API-served, OpenAI-compatible endpoints) — the small-vs-
# frontier gap (§9). Each anchor's id is a stable slug (its result file); the
# actual API model id comes from FRONTIER_<SLUG>_MODEL in the env, else the
# default below. The key is read from api_key_env at run time (never stored).
FRONTIER: list[ModelSpec] = [
    ModelSpec(
        "frontier-gpt", "frontier", served_by="api",
        base_url="https://api.openai.com/v1", api_key_env="OPENAI_API_KEY",
        default_api_model="gpt-5.6-sol",
        # GPT-5.6: max_completion_tokens, no temperature, reasoning off (tools
        # aren't supported alongside reasoning on /chat/completions).
        max_tokens_param="max_completion_tokens", send_temperature=False,
        extra_body_json='{"reasoning_effort": "none"}',
    ),
    ModelSpec(
        "frontier-opus", "frontier", served_by="api",
        base_url="https://api.anthropic.com/v1", api_key_env="ANTHROPIC_API_KEY",
        default_api_model="claude-opus-4-8", send_temperature=False,  # temp deprecated
    ),
    ModelSpec(
        "frontier-sonnet", "frontier", served_by="api",
        base_url="https://api.anthropic.com/v1", api_key_env="ANTHROPIC_API_KEY",
        default_api_model="claude-sonnet-5", send_temperature=False,
    ),
    ModelSpec(
        "frontier-gemini", "frontier", served_by="api",
        base_url="https://generativelanguage.googleapis.com/v1beta/openai",
        api_key_env="GOOGLE_API_KEY", default_api_model="gemini-3.1-pro-preview",
    ),
]

# Back-compat alias (a single anchor slot referenced by older callers/tests).
FRONTIER_ANCHOR = FRONTIER[0]

MATRIX: list[ModelSpec] = [*SMALL_MATRIX, *FRONTIER]

BY_ID: dict[str, ModelSpec] = {m.id: m for m in MATRIX}


def select(ids: list[str] | None) -> list[ModelSpec]:
    """The matrix, or the subset named by `ids` (order preserved)."""
    if not ids:
        return list(MATRIX)
    out: list[ModelSpec] = []
    for i in ids:
        if i not in BY_ID:
            raise KeyError(f"unknown model {i!r}; known: {sorted(BY_ID)}")
        out.append(BY_ID[i])
    return out


def spec_for(model_id: str) -> ModelSpec:
    """Resolve any HF id to a ModelSpec — the matrix entry if known, else derived
    from the decode registry (family + tool parser)."""
    if model_id in BY_ID:
        return BY_ID[model_id]
    try:
        family = profile_for(model_id).family
    except KeyError:
        family = "unknown"
    return ModelSpec(model_id, family, tool_parser=_parser(family))
