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

# One frontier anchor (API-served, OpenAI-compatible) — the small-vs-frontier gap
# (§9). The concrete id + endpoint are supplied at run time; this is the slot.
FRONTIER_ANCHOR = ModelSpec(
    "frontier-anchor", "frontier", tool_parser="auto", served_by="api", params_b=0.0
)

MATRIX: list[ModelSpec] = [*SMALL_MATRIX, FRONTIER_ANCHOR]

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
