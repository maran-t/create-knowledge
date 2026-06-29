---
name: create-knowledge
description: Build a "second brain" / knowledge base from a git repository's commit history over a chosen time window (e.g. "last 1 year", "last 6 months", "last 2 years"). Produces a navigable knowledge base as multiple linked Markdown files — an index plus one file per theme, scaled to the repo — capturing meaningful engineering decisions, features, fixes, and architecture changes, while filtering out noise like reverts, merge commits, comment/whitespace/formatting tweaks, label/version bumps, and typo fixes. Never dumps everything into one file. Use this whenever the user wants to distill, summarize, document, or extract knowledge/learnings from git commits or a repo's history, mentions turning commit history into notes/docs/a knowledge base, or asks "what happened in this repo over the last N months/years".
---

# Commit Knowledge

Turn a repository's commit history into a durable, human-readable **knowledge base** — a folder of linked Markdown files, not one giant document. The goal is signal, not a changelog: capture *what was built, why, and what was learned*, dropping commits that carry no lasting knowledge.

A single dumped file is hard to navigate and grows unreadable on any real repo. Instead, write a small set of focused files — an index plus one file per major theme — so each file is skimmable on its own and the whole thing reads like a wiki. Scale the number of files to the repo: a tiny project might need just two files; a year of an active codebase might warrant six to ten.

## Workflow

1. **Resolve inputs.** Determine the repo path (default: current directory) and the time window. Map natural-language durations to git's `--since`:
   - "last 1 year" / "past year" → `--since="1 year ago"`
   - "last 6 months" → `--since="6 months ago"`
   - "last 2 years" → `--since="2 years ago"`
   - A specific date works too → `--since="2024-01-01"`
   If the user didn't give a duration, ask once (offer 6 months / 1 year / 2 years as quick options) rather than guessing.

2. **Confirm it's a git repo.** Run `git -C <repo> rev-parse --is-inside-work-tree`. If not, tell the user and stop.

3. **Extract and filter commits.** Run the bundled script:
   ```bash
   python3 scripts/extract_commits.py --repo <repo-path> --since "<git since string>" --out /tmp/commits.json
   ```
   It pulls commits in the window, drops the noise categories (see below), and emits clean JSON with hash, date, author, subject, body, and changed-file stats. Read `scripts/extract_commits.py` only if you need to tweak the filters.

4. **Plan the file split.** Read the JSON and cluster the kept commits into themes (features, subsystems, fixes that share a cause). Decide how many files the knowledge base needs based on volume and distinct themes — see "How many files" below. Don't pre-commit to a fixed number; let the material decide.

5. **Synthesize knowledge into multiple files.** Write the files yourself — do NOT just paste commit subjects. The script gives you raw material; the value you add is interpretation: connecting commits into features, surfacing the *why*, noting recurring problem areas. Use the file layout and per-file templates below.

6. **Save and present.** Write everything into a `<repo-name>-knowledge/` folder, then present the folder (lead with `index.md`).

## What counts as noise (filter OUT)

These carry no durable knowledge and the script drops them. If you spot survivors during synthesis, ignore them too:

- **Reverts** — `revert`/`reverts`/`this reverts commit`. A revert plus its target net to zero knowledge; skip both if the target is in-window.
- **Merge commits** — auto-generated `Merge branch/pull request ...`.
- **Formatting-only** — `format`, `fmt`, `lint`, `prettier`, `whitespace`, `indent`, `eslint --fix`, `reformat`.
- **Comments / docs-typo churn** — `add comment`, `fix comment`, `typo`, `spelling`, `wording` (keep substantive doc commits that explain real concepts).
- **Version / label / metadata bumps** — `bump version`, `version bump`, `release vX`, `update changelog`, `bump deps` *unless* the dependency change is described as fixing/enabling something real.
- **Trivial chores** — `wip`, `tmp`, `temp`, `.gitignore`, `rename file`, `move file`, `chore: cleanup` with no functional change.
- **Pure CI/config tweaks** with no behavioral impact (`update workflow`, `fix yaml`).

Keep anything that represents a **feature, bug fix with a real cause, refactor with rationale, architecture/design decision, performance work, security fix, API change, or data-model change.**

## Output: a multi-file knowledge base

Write a folder, not a single file. Default layout:

```
<repo-name>-knowledge/
├── index.md              # entry point: overview, links to every file, stats
├── themes/
│   ├── <theme-1>.md      # one file per major theme
│   ├── <theme-2>.md
│   └── ...
├── decisions.md          # durable architecture & design decisions
└── problem-areas.md      # recurring bug clusters — "here be dragons"
```

Use lowercase-hyphenated filenames derived from the theme (e.g. `themes/type-annotations.md`, `themes/terminal-output.md`). Link between files with relative Markdown links so the base is navigable.

### How many files

Let volume and distinctness decide — never dump everything into one file, and never split so finely that files become stubs:

- **Tiny window/repo (≤ ~15 kept commits, 1–2 themes):** `index.md` + maybe one `themes/` file, or fold themes into the index. Two files total is fine.
- **Moderate (~15–80 kept commits):** `index.md`, 2–4 theme files, and `decisions.md` / `problem-areas.md` if there's real content for them.
- **Large (80+ kept commits or many distinct subsystems):** `index.md`, 4–10 theme files, plus `decisions.md` and `problem-areas.md`. If one theme file would exceed ~150 lines, split it further.

A file should earn its existence: if a would-be theme has only one or two commits and no story, merge it into a related file or a "Smaller changes" section in the index rather than creating a near-empty file.

### `index.md` template

ALWAYS use this structure for the index:

```markdown
# <Repo Name> — Engineering Knowledge Base
_Window: <start> → <end> · <N> meaningful commits (of <total> total)_

## Overview
2–4 sentences: what this codebase is and the main thrust of work in this period.

## Contents
- [<Theme 1 name>](themes/<theme-1>.md) — one-line summary
- [<Theme 2 name>](themes/<theme-2>.md) — one-line summary
- [Architecture & Design Decisions](decisions.md)
- [Recurring Problem Areas](problem-areas.md)

## Timeline Highlights
Chronological list of the handful of most significant milestones with dates.

## Smaller Changes
(Optional) Brief bullets for noteworthy commits that didn't warrant their own theme.
```

### Theme file template (`themes/<name>.md`)

```markdown
# <Theme Name>
[← back to index](../index.md)

**What changed:** plain-language summary of the work in this theme.

**Why it mattered:** the problem or goal driving it.

**Details:** 1–3 short paragraphs connecting the commits into a coherent story —
how the work evolved, what approaches were tried, what it enabled.

**Notable commits:**
- `<short-hash>` (<date>) — one-line description
- `<short-hash>` (<date>) — one-line description
```

### `decisions.md` and `problem-areas.md`

- **decisions.md** — durable decisions worth remembering (tech choices, patterns adopted, dependencies added/removed, trade-offs). Bullet list, each with a one-line rationale and the commit hash.
- **problem-areas.md** — where fixes clustered, framed as guidance for future work ("the pager is fragile — test stream handling carefully"). Link to the relevant theme file where useful.

Drop `decisions.md` or `problem-areas.md` entirely if there's genuinely nothing for them rather than writing a hollow file.

## Notes

- Write the knowledge base as a folder of linked files — never a single dump. Even a small repo gets at least an `index.md`.
- For large histories, the script caps detail per commit but keeps all qualifying subjects; if a window has thousands of commits, tell the user and suggest narrowing the window or filtering by path (`--path src/`).
- Don't fabricate rationale. If a commit's "why" isn't evident from its message or diff stats, describe what changed and leave intent out.
- This reads history only; it never modifies the repo.
