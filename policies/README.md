# policies/

Compiled-policy JSON, **versioned in git** — Verity has no separate data layer
(PRD §8.4–8.5). The encode-time compiler (`encode/`) emits these; `verity-core`
reads them at runtime as pure data. Empty until Phase 1 (`floor.json`, step 1.0).
