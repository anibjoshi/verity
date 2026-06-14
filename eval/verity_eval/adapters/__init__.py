"""Benchmark adapters (eval-plan §6, multi-adapter architecture).

Each harvested benchmark keeps its native environment/tools/oracle and gets its
own adapter here; all adapters emit the common `ResultRow` (verity_eval.results)
that `metrics.py` consumes. The authored corpus is the `authored` adapter
(verity_eval.harness).
"""
