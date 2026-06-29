#!/usr/bin/env python3
"""Extract meaningful commits — with their actual code changes — from a git repo.

Pulls commits since a given date, drops noise (reverts, merges, formatting,
comment/typo churn, version/label bumps, trivial chores), and for every kept
commit also captures *what actually changed in the code*: a per-file line-count
breakdown and a bounded snippet of the real diff. This lets the knowledge-base
synthesis step describe how the project was built from the changes themselves,
not just from commit subjects.

Usage:
  python3 extract_commits.py --repo <path> --since "1 year ago" --out commits.json
  python3 extract_commits.py --repo . --since "2024-01-01" --path src/
  python3 extract_commits.py --repo . --since "1 year ago" --no-diffs        # metadata only
  python3 extract_commits.py --repo . --since "1 year ago" --max-diff-lines 400
"""
import argparse
import json
import re
import subprocess
import sys

# Unique field/record separators unlikely to appear in commit text.
F = "\x1f"   # field sep
R = "\x1e"   # record sep

NOISE_PATTERNS = [
    # reverts
    r"^revert\b", r"\brevert(s|ed)?\b.*commit", r"this reverts commit",
    # merges
    r"^merge\s+(branch|pull request|remote)", r"^merge\b.*\binto\b",
    # formatting / lint
    r"^\s*(chore[:(]?\s*)?(re)?format\b", r"\bprettier\b", r"\beslint\b",
    r"\blint(ing)?\b", r"\bwhitespace\b", r"\bindent(ation)?\b", r"\bfmt\b",
    r"\breformat\b", r"\bgofmt\b", r"\bblack\b.*format",
    # comments / typos / wording
    r"\b(add|fix|update|remove)\s+comments?\b", r"\btypos?\b", r"\bspelling\b",
    r"\bwording\b", r"\bgrammar\b",
    # version / label / metadata bumps
    r"\bbump\s+version\b", r"\bversion\s+bump\b", r"^\s*(chore[:(]?\s*)?release\s+v?\d",
    r"\b(update|add|fix|missing)\b.*\bchangelog\b", r"\bchangelog\s+entry\b",
    r"\bbump\s+(deps|dependencies)\b", r"^\s*v?\d+\.\d+\.\d+\s*$",
    # docs/markup churn with no concept content
    r"\b(convert|move)\b.*\b(changes|docs?)\b.*\b(markdown|markup|heading)",
    r"\bmissing\s+(closing\s+)?(issue|pr)\s+(ref|link)", r"\bmyst\s+syntax\b",
    r"\bheadings?\s+(down|up)\b",
    # trivial chores
    r"^\s*wip\b", r"^\s*(tmp|temp)\b", r"\bgitignore\b", r"^\s*(chore[:(]?\s*)?cleanup\b",
    r"^\s*(chore[:(]?\s*)?rename\b", r"^\s*(chore[:(]?\s*)?move\s+file",
    # pure ci/config
    r"\bupdate\s+(workflow|ci)\b", r"\bfix\s+yaml\b", r"^\s*ci[:(]",
]
NOISE_RE = [re.compile(p, re.IGNORECASE) for p in NOISE_PATTERNS]

# Files whose diffs carry no durable engineering knowledge: lockfiles, generated
# bundles, minified assets, vendored deps, snapshots, binaries. Their *content*
# is excluded from the captured diff (they still count toward line stats so the
# magnitude of a change isn't lost). Matched against the file path.
NOISE_FILE_PATTERNS = [
    # dependency lockfiles
    r"(^|/)(package-lock\.json|yarn\.lock|pnpm-lock\.yaml|composer\.lock)$",
    r"(^|/)(Gemfile\.lock|poetry\.lock|Pipfile\.lock|Cargo\.lock|go\.sum)$",
    r"(^|/)(flake\.lock|pdm\.lock|bun\.lockb)$",
    # generated / vendored / build output
    r"(^|/)(node_modules|vendor|dist|build|out|\.next|\.nuxt|coverage)/",
    r"(^|/)(__pycache__|\.venv|venv|target|bin|obj)/",
    r"(^|/)(gen|generated|__generated__)/",
    # minified / map / snapshot
    r"\.min\.(js|css)$", r"\.(map)$", r"\.snap$", r"\.snapshot$",
    # common binary / asset types
    r"\.(png|jpe?g|gif|webp|ico|svg|pdf|zip|gz|tar|woff2?|ttf|eot|mp4|mov|mp3|wav|"
    r"so|dylib|dll|exe|a|o|class|jar|wasm|bin|lock)$",
]
NOISE_FILE_RE = [re.compile(p, re.IGNORECASE) for p in NOISE_FILE_PATTERNS]


def is_noise(subject: str, body: str) -> bool:
    text = subject.strip()
    if not text:
        return True
    for rx in NOISE_RE:
        if rx.search(text):
            return True
    # "this reverts commit" sometimes only in body
    if "this reverts commit" in body.lower():
        return True
    return False


def is_noise_file(path: str) -> bool:
    for rx in NOISE_FILE_RE:
        if rx.search(path):
            return True
    return False


def run_git(repo, args):
    try:
        out = subprocess.run(
            ["git", "-C", repo] + args,
            capture_output=True, text=True, check=True,
        )
        return out.stdout
    except subprocess.CalledProcessError as e:
        sys.stderr.write(f"git error: {e.stderr}\n")
        sys.exit(1)


def parse_numstat(repo, commit_hash, path_filter):
    """Return per-file line-change records for a commit (noise files flagged)."""
    args = ["show", "--numstat", "--format=", commit_hash]
    if path_filter:
        args += ["--", path_filter]
    raw = run_git(repo, args)
    files = []
    for ln in raw.splitlines():
        ln = ln.strip()
        if not ln:
            continue
        cols = ln.split("\t")
        if len(cols) < 3:
            continue
        added_s, deleted_s, fpath = cols[0], cols[1], "\t".join(cols[2:])
        binary = (added_s == "-" or deleted_s == "-")
        files.append({
            "path": fpath,
            "added": 0 if binary else int(added_s),
            "deleted": 0 if binary else int(deleted_s),
            "binary": binary,
            "noise": is_noise_file(fpath),
        })
    return files


def collect_diff(repo, commit_hash, signal_paths, max_lines, context):
    """Capture the real diff for the signal (non-noise) paths, bounded in size.

    Returns (diff_text, truncated_bool). Only the listed paths are diffed, so
    lockfiles/generated output never bloat the snippet. The diff is truncated to
    `max_lines` lines with a marker so downstream synthesis stays focused on the
    most informative changes.
    """
    if not signal_paths:
        return "", False
    args = ["show", "--format=", "--no-color", "--unified=%d" % context, commit_hash, "--"]
    args += signal_paths
    raw = run_git(repo, args)
    lines = raw.splitlines()
    if len(lines) > max_lines:
        kept = lines[:max_lines]
        kept.append("... [diff truncated: %d of %d lines shown] ..." % (max_lines, len(lines)))
        return "\n".join(kept), True
    return "\n".join(lines), False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".")
    ap.add_argument("--since", required=True, help='e.g. "1 year ago" or "2024-01-01"')
    ap.add_argument("--out", default="commits.json")
    ap.add_argument("--path", default=None, help="limit to a subpath")
    ap.add_argument("--no-diffs", action="store_true",
                    help="skip capturing diff content (metadata + file stats only)")
    ap.add_argument("--max-diff-lines", type=int, default=300,
                    help="max diff lines captured per commit (default 300)")
    ap.add_argument("--max-files", type=int, default=20,
                    help="max signal files diffed per commit, largest churn first (default 20)")
    ap.add_argument("--context", type=int, default=3,
                    help="diff context lines (git --unified, default 3)")
    args = ap.parse_args()

    # verify repo
    chk = subprocess.run(["git", "-C", args.repo, "rev-parse", "--is-inside-work-tree"],
                         capture_output=True, text=True)
    if chk.returncode != 0 or "true" not in chk.stdout:
        sys.stderr.write("Not a git repository: %s\n" % args.repo)
        sys.exit(1)

    # Pull message metadata only; per-file line stats come from numstat below
    # (mixing --shortstat into --pretty=format output corrupts record parsing).
    fmt = F.join(["%H", "%h", "%aI", "%an", "%s", "%b"]) + R
    git_args = ["log", "--since=%s" % args.since, "--no-merges", "--pretty=format:" + fmt]
    if args.path:
        git_args += ["--", args.path]
    raw = run_git(args.repo, git_args)

    # We requested --no-merges, but reverts/etc still need filtering.
    records = [r for r in raw.split(R) if r.strip()]
    commits, kept, total = [], 0, 0
    for rec in records:
        parts = rec.split(F)
        if len(parts) < 6:
            continue
        h, sh, date, author, subject, body = (
            parts[0].strip(), parts[1], parts[2], parts[3], parts[4], parts[5])
        body = body.strip()
        total += 1
        if is_noise(subject, body):
            continue
        kept += 1

        # Per-file breakdown (always cheap and very informative).
        files = parse_numstat(args.repo, h, args.path)
        files_changed = len(files)
        ins = sum(f["added"] for f in files)
        dels = sum(f["deleted"] for f in files)

        entry = {
            "hash": h, "short": sh.strip(), "date": date.strip()[:10],
            "author": author.strip(), "subject": subject.strip(),
            "body": body[:1000],
            "files_changed": files_changed, "insertions": ins, "deletions": dels,
        }
        entry["files"] = files
        signal_files = [f for f in files if not f["noise"] and not f["binary"]]
        entry["signal_files"] = [f["path"] for f in signal_files]
        entry["excluded_files"] = [f["path"] for f in files if f["noise"] or f["binary"]]

        # Actual changed lines for the signal files, bounded.
        if not args.no_diffs:
            # diff the highest-churn signal files first, capped by --max-files
            ranked = sorted(signal_files,
                            key=lambda f: f["added"] + f["deleted"], reverse=True)
            chosen = [f["path"] for f in ranked[:args.max_files]]
            diff_text, truncated = collect_diff(
                args.repo, h, chosen, args.max_diff_lines, args.context)
            entry["diff"] = diff_text
            entry["diff_truncated"] = truncated
            entry["diff_files_omitted"] = max(0, len(signal_files) - len(chosen))

        commits.append(entry)

    result = {
        "repo": args.repo, "since": args.since,
        "total_commits": total, "kept_commits": kept,
        "diffs_included": (not args.no_diffs),
        "max_diff_lines": args.max_diff_lines,
        "date_range": {
            "start": commits[-1]["date"] if commits else None,
            "end": commits[0]["date"] if commits else None,
        },
        "commits": commits,
    }
    with open(args.out, "w") as f:
        json.dump(result, f, indent=2)
    extra = "" if args.no_diffs else " (with diffs)"
    print(f"Kept {kept} of {total} commits{extra} → {args.out}")


if __name__ == "__main__":
    main()
