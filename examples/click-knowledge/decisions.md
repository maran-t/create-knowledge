# Architecture & Design Decisions
[← back to index](index.md)

- **Removed the `colorama` dependency** (`7454647`, 2026-05-22) — reduces install footprint.
- **Nightly CI on both `main` and `stable`** (`5ec03bd`, `aa5a8da`) — runs random/stress
  tests on two branches, signaling investment in catching flaky/intermittent failures.
- **Platform-dependent `testing.CaptureMode` type alias** (`88b8e31`) — abstracts OS
  differences in output capture behind one name.
