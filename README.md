# create-knowledge

A [Claude](https://claude.ai) / [Claude Code](https://docs.claude.com/en/docs/claude-code) skill that turns a Git repository's **commit history into a structured Markdown knowledge base** — a "second brain" for a codebase.

Point it at a repo and a time window ("last 1 year", "last 6 months", "last 2 years"). It reads the commit log, filters out the noise (reverts, merges, formatting, label/version bumps, typo fixes), and synthesizes what's left into themed engineering knowledge: what was built, why, and where the dragons live.

It reads history only — it never modifies your repo.

## Why

`git log` is a flat wall of commits. Changelog generators give you a categorized list but no interpretation. This skill does the opposite of the usual "store notes in Git" pattern: it pulls durable knowledge *out* of commit history and writes it up the way a thoughtful engineer would summarize a year of work — grouping related commits into features, surfacing rationale, and flagging recurring problem areas.

Good for: onboarding onto an unfamiliar codebase, writing up "what we shipped" for reviews or retros, or rebuilding lost context on an old project.

## Example

See [`examples/click-knowledge/`](examples/click-knowledge/) — a real run against
[pallets/click](https://github.com/pallets/click) over ~1 year (253 meaningful commits kept
out of 304). Note the output is a **folder of linked files** — an [`index.md`](examples/click-knowledge/index.md)
that links out to per-theme files, plus `decisions.md` and `problem-areas.md` — not one dump.

## Installation

```
/plugin marketplace add maran-t/create-knowledge
/plugin install create-knowledge@create-knowledge
or

npx skills add maran-t/create-knowledge
```

### Manual (any Claude environment with skills)

Copy the skill into your skills directory:

```bash
# Claude Code, project-local
cp -r create-knowledge .claude/skills/

# Claude Code, global
cp -r create-knowledge ~/.claude/skills/
```

Or, on claude.ai, upload the packaged `.skill` file via your skills settings.

## Usage

Once installed, just ask naturally:

```
Build a knowledge base from this repo's last 2 years of commits
```
```
Summarize what happened in ~/projects/api over the past 6 months
```
```
Extract the key engineering decisions from this repository's last year
```

The skill resolves the repo and time window, runs the extractor, clusters commits into themes, and writes a `<repo-name>-knowledge/` **folder** — an `index.md` plus one file per theme, with `decisions.md` and `problem-areas.md` where warranted. The number of files scales to the repo; it never dumps everything into a single file.

### Running the extractor directly

The filtering/extraction step is a standalone script if you want the cleaned JSON yourself:

```bash
python3 scripts/extract_commits.py --repo /path/to/repo --since "1 year ago" --out commits.json

# limit to a subpath
python3 scripts/extract_commits.py --repo . --since "6 months ago" --path src/ --out commits.json
```

`--since` accepts anything Git accepts (`"1 year ago"`, `"2024-01-01"`, etc.). Output is JSON with per-commit hash, date, author, subject, body, and diff stats, plus kept/total counts.

## What gets filtered out

Commits carrying no durable knowledge are dropped: reverts, merge commits, formatting/lint-only changes, comment & typo churn, version/label/changelog bumps, and trivial chores (wip, file renames, gitignore tweaks, pure CI config). Anything representing a feature, real bug fix, refactor with rationale, architecture decision, performance work, security fix, or API/data-model change is kept.

## Limitations

Filtering is regex-based on commit messages plus diff stats, so output quality tracks commit-message quality. On a repo with vague messages or heavily squashed PRs, it can both keep noise and drop signal — it errs toward keeping borderline cases. Always sanity-check the result against the repo. It does not (yet) read PR descriptions, issues, or diffs in depth.

## Requirements

- `git`
- Python 3.x (standard library only — no dependencies)

## License

MIT — see [LICENSE](LICENSE).
