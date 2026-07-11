"""Deterministic corpus generators (E5, corpus-spec §8).

Ground truth comes from vendored, pinned real corpora (``eval/seeds``) and
deterministic checks; prose wrappers are templated. No LLM in the loop, no RNG,
no clock — re-running emits byte-identical scenarios. See ``generate`` for the
``secret_read`` class.
"""
