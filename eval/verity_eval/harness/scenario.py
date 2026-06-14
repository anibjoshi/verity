"""Scenario loading — corpus JSON → typed `Scenario` objects.

Reads the validated corpus (the schema/integrity gate is `corpus_check.py`), so
parsing here is straightforward. This is harness I/O (reading the corpus), not a
tool, so it legitimately touches the filesystem.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from verity_eval.corpus_check import corpus_dir


@dataclass(frozen=True)
class ToolSpec:
    name: str
    params: dict[str, str]  # param name -> JSON-schema type ("string"/"number"/...)


@dataclass(frozen=True)
class Injection:
    carrier: str
    payload: str


@dataclass(frozen=True)
class Scenario:
    id: str
    corpus_version: str
    source: str
    floor_class: str
    attack_vector: str
    outcome_kind: str
    user_instruction: str
    tools: list[ToolSpec]
    environment: dict[str, Any]
    untrusted_inputs: list[str]
    injection: Injection | None
    oracle: dict[str, Any]
    label: dict[str, Any]
    benign_pair: str | None

    @property
    def injection_pair(self) -> tuple[str, str] | None:
        return None if self.injection is None else (self.injection.carrier, self.injection.payload)

    @staticmethod
    def from_dict(d: dict[str, Any]) -> Scenario:
        inj = d.get("injection")
        return Scenario(
            id=d["id"],
            corpus_version=d["corpus_version"],
            source=d["source"],
            floor_class=d["floor_class"],
            attack_vector=d["attack_vector"],
            outcome_kind=d["outcome_kind"],
            user_instruction=d["user_instruction"],
            tools=[ToolSpec(name=t["name"], params=dict(t["params"])) for t in d["tools"]],
            environment=d.get("environment") or {},
            untrusted_inputs=list(d.get("untrusted_inputs") or []),
            injection=(
                None if inj is None else Injection(carrier=inj["carrier"], payload=inj["payload"])
            ),
            oracle=d["oracle"],
            label=d.get("label") or {},
            benign_pair=d.get("benign_pair"),
        )


def load_scenarios(root: Path | None = None) -> list[Scenario]:
    """Load all scenarios under `eval/corpus/scenarios`, sorted by id."""
    scenarios_dir = (root or corpus_dir()) / "scenarios"
    out: list[Scenario] = []
    for path in sorted(scenarios_dir.rglob("*.json")):
        out.append(Scenario.from_dict(json.loads(path.read_text(encoding="utf-8"))))
    return out
