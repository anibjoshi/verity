"""Per-model decode registry + tool-call parsing (eval-plan §8 "Decoding").

Two responsibilities:
1. The per-model **profile registry** — each family's vLLM `--tool-call-parser`
   and (later) chat-template quirks. E1 needs only Qwen; the rest are registered
   so the five-family sweep (eval-plan §10) drops in.
2. Parsing model output into resolved calls — the native `tool_calls` path plus
   a stringified-JSON-in-`content` **fallback** (the Hermes-3 content-leak trap),
   so a leaked catastrophic call is still recorded as genuine intent.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ModelProfile:
    family: str
    tool_parser: str  # the vLLM --tool-call-parser value


# Registered families (eval-plan §10). Validated locally: qwen2.5 / hermes.
REGISTRY: dict[str, ModelProfile] = {
    "qwen2.5": ModelProfile("qwen2.5", "hermes"),
    "qwen3": ModelProfile("qwen3", "hermes"),  # same <tool_call> format family
    "llama-3.2": ModelProfile("llama-3.2", "llama3_json"),
    "hermes-3": ModelProfile("hermes-3", "hermes"),
    "gemma-4": ModelProfile("gemma-4", "gemma4"),
    "phi-4": ModelProfile("phi-4", "phi4_mini_json"),
}


def profile_for(model_id: str) -> ModelProfile:
    """Resolve a HF model id to its decode profile (raises if unregistered)."""
    m = model_id.lower()
    if "qwen2.5" in m or "qwen2_5" in m:
        return REGISTRY["qwen2.5"]
    if "qwen3" in m:
        return REGISTRY["qwen3"]
    if "llama-3.2" in m or "llama3.2" in m:
        return REGISTRY["hermes-3"] if "hermes" in m else REGISTRY["llama-3.2"]
    if "gemma-4" in m:
        return REGISTRY["gemma-4"]
    if "phi-4" in m or "phi4" in m:
        return REGISTRY["phi-4"]
    raise KeyError(f"no decode profile registered for model {model_id!r}")


def safe_json_args(raw: object) -> dict[str, Any]:
    """Parse a tool call's `arguments` (a JSON string or dict) → dict; {} on fail."""
    if isinstance(raw, dict):
        return dict(raw)
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


# A balanced-brace JSON object scan; good enough to recover a leaked call.
_OBJ_RE = re.compile(r"\{.*\}", re.DOTALL)


def recover_from_content(content: str | None) -> tuple[str, dict[str, Any]] | None:
    """Recover a tool call leaked into assistant `content` (no native tool_calls).

    Looks for an object with a `name` and `arguments`/`parameters`. Returns
    `(name, args)` or None. This is the content-leak fallback, not the main path.
    """
    if not content:
        return None
    match = _OBJ_RE.search(content)
    if not match:
        return None
    try:
        obj = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    if not isinstance(obj, dict):
        return None
    name = obj.get("name")
    if not isinstance(name, str):
        return None
    args = obj.get("arguments")
    if args is None:
        args = obj.get("parameters")
    return name, safe_json_args(args)
