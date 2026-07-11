"""The model-sweep runner (E6): matrix over models × the corpus, with a complete
provenance manifest stamped on every result row.

The live sweep needs GPU/serving (vLLM, one model at a time — see the
`local-serving-setup` notes); it runs out-of-band, not in PR CI. This package is
the orchestration + provenance, testable GPU-free via a stub client.
"""
