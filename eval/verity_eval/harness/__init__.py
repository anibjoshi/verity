"""Verity Phase 0 evaluation harness (eval-plan §8).

A minimal, hand-written ReAct loop whose tool-dispatch step is the instrumented
chokepoint `verify()` plugs into at Phase 2. Tools are simulated and operate
only on a per-scenario in-memory world — the harness has no execution channel to
the host (eval-plan §8 "Safety model"). Scaffold milestone E1 (one model).
"""

__all__ = ["__version__"]
__version__ = "0.0.0"
