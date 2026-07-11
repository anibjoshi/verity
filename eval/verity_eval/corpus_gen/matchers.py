"""Matcher evaluation for the data-flow generators (corpus-spec §2.2).

Mirrors the harness/Rust matcher semantics (`equals`/`regex`/`one_of`/`gt|ge|lt|le`,
or a bare scalar = equals) so a generator can verify its own crispness: the attack
target matches the violating matcher, the benign control target does not. This is
the data-flow analog of secret_read's "nothing live committed" and shell_exec's
"benign command trips no danger regex".
"""

from __future__ import annotations

import re
from collections.abc import Callable
from typing import Any

_ORDER: tuple[tuple[str, Callable[[float, float], bool]], ...] = (
    ("gt", lambda a, b: a > b),
    ("ge", lambda a, b: a >= b),
    ("lt", lambda a, b: a < b),
    ("le", lambda a, b: a <= b),
)


def matches(matcher: Any, value: Any) -> bool:
    """True iff ``value`` satisfies ``matcher`` (corpus-spec §2.2 / §7 semantics)."""
    if isinstance(matcher, dict):
        if "regex" in matcher:
            return re.search(str(matcher["regex"]), str(value)) is not None
        if "one_of" in matcher:
            return bool(value in matcher["one_of"])
        if "equals" in matcher:
            return bool(value == matcher["equals"])
        for op, fn in _ORDER:
            if op in matcher:
                return isinstance(value, (int, float)) and fn(value, matcher[op])
        return False
    return bool(value == matcher)


def matches_all(args: dict[str, Any], values: dict[str, Any]) -> bool:
    """True iff every field's matcher in ``args`` is satisfied by ``values``."""
    return all(f in values and matches(m, values[f]) for f, m in args.items())
