//! # verity-core
//!
//! The deterministic verification kernel for Verity — a model-independent
//! reference monitor for autonomous-agent tool calls.
//!
//! This crate is the trusted computing base (TCB): intentionally tiny, with no
//! async, no LLM, and (from kernel-spec M1) `serde` as its only dependency.
//! `verify()` is a pure function of its arguments — no clock, no RNG, no
//! filesystem, no network — so verdicts are deterministic and auditable.
//!
//! Scaffold only (Phase G / G1). The data model and `verify()` land across
//! kernel-spec milestones M1–M7 (execution-plan Phase 1).
#![forbid(unsafe_code)]
