# Terminal Output & Stream Handling
[← back to index](../index.md)

**What changed:** Several fixes to how Click writes to terminals — not letting the garbage
collector close a borrowed `stdout`, supporting incremental output in the pager, and
ensuring the pager doesn't close standard streams. Also handled empty bytes in `echo`.

**Why it mattered:** These are subtle resource-ownership bugs that surface as truncated
output or unexpectedly closed streams in real programs — hard to reproduce, easy to regress.

**Details:** The pager was the focus of repeated attention: a borrowed-stdout fix, a move
to incremental output, and a fix so it no longer closes std streams. A pager test race was
also fixed by raising before yield. See [Recurring Problem Areas](../problem-areas.md) — the
pager is a fragile spot.

**Notable commits:**
- `051bb0f` (2026-05-29) — do not let the GC close a borrowed `stdout`
- `399919f` (2026-05-29) — support incremental output in the pager
- `becbde5` (2026-05-19) — pager doesn't close std streams
- `4d3db84` (2026-05-21) — handle empty bytes in `echo`
- `7eb57cf` (2026-05-22) — fix pager test race by raising before yield
