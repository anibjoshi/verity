"""Verity Phase 0 evaluation harness.

Builds the catastrophe corpus, runs the minimal ReAct loop over small models,
and scores trajectories with deterministic oracles. The harness's tool-dispatch
step is the chokepoint ``verity.verify()`` plugs into at Phase 2.

Scaffold only (Phase G / G1). Corpus schema + seeds land at G3 / E0.
"""

__version__ = "0.0.0"
