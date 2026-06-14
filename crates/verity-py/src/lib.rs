//! Python bindings for `verity-core`, published as the `verity` wheel.
//!
//! A thin shim over the audited Rust core: the binding changes nothing
//! semantic, so the same scenario yields the identical verdict through the Rust
//! API and the Python API (the parity guarantee, testing-ci §2.2).
//!
//! Scaffold only (Phase G / G1). Real `Action` / `VerdictReport` marshaling
//! lands at execution-plan step 1.7.
use pyo3::prelude::*;

/// The `verity` Python module.
#[pymodule]
fn verity(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add("__version__", env!("CARGO_PKG_VERSION"))?;
    Ok(())
}
