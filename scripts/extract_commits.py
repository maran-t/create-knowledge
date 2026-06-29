#!/usr/bin/env python3
"""Extract meaningful commits from a git repo within a time window.

Pulls commits since a given date, drops noise (reverts, merges, formatting,
comment/typo churn, version/label bumps, trivial chores), and writes clean
JSON for downstream knowledge synthesis.

Usage:
  python3 extract_commits.py --repo <path> --since "1 year ago" --out commits.json
  python3 extract_commits.py --repo . --since "2024-01-01" --path src/
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".")
    ap.add_argument("--since", required=True, help='e.g. "1 year ago" or "2024-01-01"')
    ap.add_argument("--out", default="commits.json")
    ap.add_argument("--path", default=None, help="limit to a subpath")
    args = ap.parse_args()

    # verify repo
    chk = subprocess.run(["git", "-C", args.repo, "rev-parse", "--is-inside-work-tree"],
                         capture_output=True, text=True)
    if chk.returncode != 0 or "true" not in chk.stdout:
        sys.stderr.write("Not a git repository: %s\n" % args.repo)
        sys.exit(1)

    fmt = F.join(["%H", "%h", "%aI", "%an", "%s", "%b"]) + R
    git_args = ["log", "--since=%s" % args.since, "--no-merges", "--pretty=format:" + fmt,
                "--shortstat"]
    if args.path:
        git_args += ["--", args.path]
    raw = run_git(args.repo, git_args)

    # We requested --no-merges, but reverts/etc still need filtering.
    # --shortstat lines follow each record; parse them in.
    records = [r for r in raw.split(R) if r.strip()]
    commits, kept, total = [], 0, 0
    for rec in records:
        # shortstat may trail after the body on its own lines
        parts = rec.split(F)
        if len(parts) < 6:
            continue
        h, sh, date, author, subject, rest = parts[0], parts[1], parts[2], parts[3], parts[4], parts[5]
        # rest = body + possible shortstat lines
        body_lines, files_changed, ins, dels = [], 0, 0, 0
        for ln in rest.splitlines():
            m = re.search(r"(\d+) files? changed", ln)
            if m:
                files_changed = int(m.group(1))
                mi = re.search(r"(\d+) insertions?", ln)
                md = re.search(r"(\d+) deletions?", ln)
                ins = int(mi.group(1)) if mi else 0
                dels = int(md.group(1)) if md else 0
            else:
                body_lines.append(ln)
        body = "\n".join(body_lines).strip()
        total += 1
        if is_noise(subject, body):
            continue
        kept += 1
        commits.append({
            "hash": h.strip(), "short": sh.strip(), "date": date.strip()[:10],
            "author": author.strip(), "subject": subject.strip(),
            "body": body[:1000],
            "files_changed": files_changed, "insertions": ins, "deletions": dels,
        })

    result = {
        "repo": args.repo, "since": args.since,
        "total_commits": total, "kept_commits": kept,
        "date_range": {
            "start": commits[-1]["date"] if commits else None,
            "end": commits[0]["date"] if commits else None,
        },
        "commits": commits,
    }
    with open(args.out, "w") as f:
        json.dump(result, f, indent=2)
    print(f"Kept {kept} of {total} commits → {args.out}")


if __name__ == "__main__":
    main()
