# Shell Completion Robustness
[← back to index](../index.md)

**What changed:** Fixes for broken fish completion with multiline help strings, Unix line
endings in completion output, and normalized choice handling in autocompletion.

**Why it mattered:** Completion runs across many shells with differing quoting and
line-ending rules; small formatting errors break it entirely for end users.

**Details:** Multiline help strings were breaking fish completion specifically; the fix
also touched line-ending handling to ensure consistent completion output across shells.
Choice autocompletion was updated to route through `normalize_choice()`.

**Notable commits:**
- `b7e5fd4` (2026-05-23) — fix broken fish completion and multiline help string
- `a3321c9` (2026-05-18) — Unix line endings for shell completion output
- `32ae2ac` (2026-05-18) — choice autocompletion uses `normalize_choice()`
