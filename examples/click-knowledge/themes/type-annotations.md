# Type Annotation Coverage
[← back to index](../index.md)

**What changed:** Instance-attribute type annotations were added module by module across
`click.core`, `formatting`, `exceptions`, `shell_completion`, and `testing`, plus variance
fixes in `types`.

**Why it mattered:** Comprehensive typing improves IDE support and lets downstream users
type-check their CLIs against Click; it also catches a class of bugs at author time.

**Details:** The sweep landed largely on 2026-05-18 as a coordinated set of per-module
commits, followed by fixes for issues the stricter typing exposed — a generic TypedDict
error on Python 3.10 and variance problems in the `types` module. A flake8 import-convention
rule for typing was added to keep the style consistent going forward.

**Notable commits:**
- `d5da635` (2026-05-18) — annotate `click.core` instance attributes
- `e39679a` (2026-05-18) — annotate `testing` attributes
- `77bd81f` (2026-05-18) — fix variance issues, improve type coverage in `types`
- `9a2d169` (2026-05-18) — fix generic TypedDict TypeError on Python 3.10
- `ac2cd07` (2026-05-19) — add flake8-import-conventions rule for typing
