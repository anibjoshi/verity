"""The matcher algebra (corpus-spec §2.3 `$defs/matcher`).

A field maps to a scalar (exact equality) or one of `{equals}`, `{regex}`,
`{one_of}`, `{gt|ge|lt|le}`. Semantics (corpus-spec §7 / "notes for the build"):
scalar/`equals` = deep-equal; `regex` = `re.search` over the stringified arg;
`one_of` = membership; `gt|ge|lt|le` = numeric compare (i64 minor units).

This is the Python reference; E2 makes it agree byte-for-byte with the Rust
`verity-core` matcher (testing-ci §2.3 matcher-parity).
"""

from __future__ import annotations

import re
from typing import Any

from .tools import RecordedCall

_NUM_OPS = ("gt", "ge", "lt", "le")


def _is_number(v: Any) -> bool:
    # bool is a subclass of int; numeric comparators never apply to bools here
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def match_value(matcher: Any, value: Any) -> bool:
    """True if `value` satisfies `matcher` under the algebra above."""
    if isinstance(matcher, dict):
        if "equals" in matcher:
            return bool(value == matcher["equals"])
        if "regex" in matcher:
            return re.search(str(matcher["regex"]), str(value)) is not None
        if "one_of" in matcher:
            return value in matcher["one_of"]
        if any(op in matcher for op in _NUM_OPS):
            if not _is_number(value):
                return False
            if "gt" in matcher and not value > matcher["gt"]:
                return False
            if "ge" in matcher and not value >= matcher["ge"]:
                return False
            if "lt" in matcher and not value < matcher["lt"]:
                return False
            if "le" in matcher and not value <= matcher["le"]:
                return False
            return True
        return False  # unknown matcher shape → no match (fail closed)
    # scalar matcher → deep equality
    return bool(value == matcher)


def match_action(spec: dict[str, Any], call: RecordedCall) -> bool:
    """True if a recorded call satisfies an action spec `{tool, args_match?}`.

    A spec with no `args_match` matches *any* call to that tool (corpus-spec
    "notes for the build").
    """
    if call.tool != spec.get("tool"):
        return False
    args_match = spec.get("args_match")
    if not args_match:
        return True
    for key, m in args_match.items():
        if key not in call.args or not match_value(m, call.args[key]):
            return False
    return True
