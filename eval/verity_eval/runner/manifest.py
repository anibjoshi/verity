"""Run provenance — the manifest stamped on every result row (E6, eval-plan §11).

"Pin everything": model id + revision + quantization + chat template, serving
engine + version, sampling params (temp-0 greedy + fixed seed), decode
constraints, corpus version, and the harness git SHA. The manifest is what makes
a baseline reproducible (up to documented batch-nondeterminism, §11) and every
result row self-attributing.

`harness_sha` is read from ``.git`` directly — ``subprocess`` is banned repo-wide
(the harness-purity gate, eval-plan §8), so we resolve HEAD by reading files.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from verity_eval.corpus_check import corpus_dir


@dataclass(frozen=True)
class ModelSpec:
    """A model's full identity — small-model behavior is quant- and
    template-sensitive, so both are part of the identity (eval-plan §10.5/§11)."""

    id: str  # HF repo id, e.g. "Qwen/Qwen2.5-3B-Instruct"
    family: str  # decode-registry family
    revision: str = "main"  # HF revision (pin to a SHA for a scored run)
    quantization: str = "none"  # none | awq | gptq | fp8 | gguf-<q>
    chat_template: str = "default"  # default | <name/path>
    tool_parser: str = "auto"  # vLLM --tool-call-parser (from decode registry)
    served_by: str = "vllm"  # vllm | llamacpp | api (frontier anchor)
    params_b: float = 0.0  # parameter count in billions (for size aggregation)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RunManifest:
    """Complete run provenance (eval-plan §11). Attached to every result row."""

    model: ModelSpec
    engine: str  # "vllm" | "llamacpp" | "api"
    engine_version: str  # queried or configured; "unavailable"/"dry-run" if unknown
    temperature: float
    seed: int
    max_tokens: int
    guided_decoding: str  # off | grammar | outlines | json-schema
    corpus_version: str
    harness_sha: str
    max_steps: int
    extra: dict[str, Any] = field(default_factory=dict)

    # The fields that must be present and non-empty for the E6 exit gate.
    _REQUIRED = (
        "engine", "engine_version", "temperature", "seed", "max_tokens",
        "guided_decoding", "corpus_version", "harness_sha", "max_steps",
    )
    _MODEL_REQUIRED = ("id", "family", "revision", "quantization", "chat_template", "served_by")

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        if not d["extra"]:
            d.pop("extra")
        return d

    def missing_fields(self) -> list[str]:
        """Provenance fields that are absent or empty — [] means complete."""
        d = self.to_dict()
        missing = [f for f in self._REQUIRED if d.get(f) in (None, "")]
        model = d.get("model", {})
        missing += [f"model.{f}" for f in self._MODEL_REQUIRED if model.get(f) in (None, "")]
        return missing

    def is_complete(self) -> bool:
        return not self.missing_fields()


def _read(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError:
        return None


def git_sha(root: Path | None = None) -> str:
    """The harness commit SHA, resolved from ``.git`` without shelling out.

    Handles the common cases: HEAD as a symbolic ref → the ref file or
    packed-refs; HEAD as a detached raw SHA. Returns "unknown" if unresolvable
    (e.g. an exported tree with no ``.git``).
    """
    base = root or corpus_dir().parents[1]  # repo root (eval/.. )
    git = base / ".git"
    # `.git` can be a file ("gitdir: <path>") in worktrees/submodules.
    if git.is_file():
        pointer = _read(git) or ""
        if pointer.startswith("gitdir:"):
            git = (base / pointer.split(":", 1)[1].strip()).resolve()
    head = _read(git / "HEAD")
    if not head:
        return "unknown"
    if not head.startswith("ref:"):
        return head  # detached HEAD — HEAD is the SHA
    ref = head.split(":", 1)[1].strip()
    direct = _read(git / ref)
    if direct:
        return direct
    packed = _read(git / "packed-refs") or ""
    for line in packed.splitlines():
        if line and not line.startswith(("#", "^")) and line.endswith(ref):
            return line.split(" ", 1)[0]
    return "unknown"


def build_manifest(
    model: ModelSpec,
    *,
    corpus_version: str,
    engine_version: str,
    seed: int = 0,
    temperature: float = 0.0,
    max_tokens: int = 512,
    max_steps: int = 6,
    guided_decoding: str = "off",
    root: Path | None = None,
) -> RunManifest:
    """Assemble the run manifest, filling `harness_sha` from `.git`."""
    return RunManifest(
        model=model,
        engine=model.served_by,
        engine_version=engine_version,
        temperature=temperature,
        seed=seed,
        max_tokens=max_tokens,
        guided_decoding=guided_decoding,
        corpus_version=corpus_version,
        harness_sha=git_sha(root),
        max_steps=max_steps,
    )


def probe_engine_version(base_url: str) -> str:
    """Best-effort vLLM engine version (``/version`` at the server root).

    Returns "unavailable" if the server isn't reachable — the sweep records what
    it can and never fails on a missing probe. Uses httpx (the sanctioned client).
    """
    import httpx

    root = base_url.rstrip("/")
    if root.endswith("/v1"):
        root = root[:-3]
    try:
        resp = httpx.get(f"{root}/version", timeout=5.0)
        resp.raise_for_status()
        version = resp.json().get("version")
        return str(version) if version else "unavailable"
    except (httpx.HTTPError, ValueError):
        return "unavailable"
