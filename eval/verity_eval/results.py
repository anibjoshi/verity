"""The common result row — the single cross-adapter contract (eval-plan §6).

Every adapter (the authored harness, AgentDojo, InjecAgent, BIPIA) emits rows of
this shape; `metrics.py` groups by `source` + `role`. Benchmarks keep their
native environments/tools/oracles — only this thin projection is standardized.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

Role = Literal["attack", "benign", "authorized"]
OutcomeStr = Literal["attempted_violation", "safe", "invalid", "error"]


@dataclass(frozen=True)
class ResultRow:
    source: str  # "authored" | "agentdojo" | "injecagent" | "bipia"
    ref: str  # id within the source
    model: str
    role: Role  # attack | benign | authorized
    outcome: OutcomeStr  # attempted_violation | safe | invalid | error
    executed_success: bool | None  # legit task performed (None if N/A)
    category: str = ""  # floor_class (authored) or suite (agentdojo)
    extra: dict[str, Any] = field(default_factory=dict)  # native richer payload

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        if not d["extra"]:
            d.pop("extra")
        return d


def role_of(outcome_kind: str, expected_disposition: str) -> Role:
    """Derive the role from the authored scenario's typed fields."""
    if outcome_kind == "failure":
        return "attack"
    if expected_disposition == "confirm":
        return "authorized"
    return "benign"


def role_of_row(row: dict[str, Any]) -> Role:
    """Role of a result row — explicit `role` if present, else derived (authored)."""
    role = row.get("role")
    if role == "attack":
        return "attack"
    if role == "benign":
        return "benign"
    if role == "authorized":
        return "authorized"
    return role_of(str(row.get("outcome_kind", "")), str(row.get("expected_disposition", "")))
