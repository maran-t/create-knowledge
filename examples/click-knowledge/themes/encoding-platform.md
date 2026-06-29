# Encoding & Platform Edge Cases
[← back to index](../index.md)

**What changed:** Accepting ZFS-style error messages for non-UTF-8 filenames, and a Windows
fix for spaces in file paths when opening URLs.

**Why it mattered:** CLIs run everywhere; filename encoding and platform path quirks are a
recurring source of crashes that only show up on specific filesystems or OSes.

**Notable commits:**
- `9f9ae45` (2026-05-28) — accept ZFS error message for non-UTF-8 names
- `c6bf75f` (2026-05-19) — fix Windows error with spaces in filepaths for `open_url`
