#!/usr/bin/env python3
"""Determine whether a finding's code has already been patched upstream.

Answers one question mechanically: has the remote default branch moved past the
audited commit in a way that touches this finding's file?

Design rule — there is NO path that reports a false "already patched". Every
failure (no network, shallow clone, fork, rewritten history, local-mirror
origin) resolves to `unavailable`, which means "a human must check". The cost
of a wrong answer here is a dropped real bug, so the asymmetry is deliberate:
we waste triage rather than lose a finding.

Usage:
    patch_status.py --repo <path> --path <repo-relative-file> [--commit <sha>]
                    [--upstream <remote-or-url>] [--pickaxe <expr>] [--pretty]

Output: a JSON object on stdout. Paste it into a triage prompt under a
`Patch-history context:` heading. Exit code is 0 whenever the tool ran, even if
the status is `unavailable` — read `status`, not the exit code. Exit 2 means the
tool itself could not run (bad arguments, missing git).

Stdlib only. No network access beyond a single `git fetch` of one ref.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

# Private ref namespace. Never touch origin/HEAD or the worktree.
NS = "refs/remotes/dewaxguard-patched-since"
DEFAULT_REF = f"{NS}/default"

DIFF_LIMIT = 24_000
LOG_LIMIT = 20
DESCENDANT_CAP = 12
FETCH_TIMEOUT = 60
LOCAL_TIMEOUT = 60


# ── git plumbing ────────────────────────────────────────────────────────────
def git(repo: str, *args: str, timeout: int = LOCAL_TIMEOUT) -> tuple[int, str, str]:
    """Run git. Returns (returncode, stdout, stderr) — stderr is NOT swallowed.

    open-kritt's equivalent returns "" on failure, which makes "no output"
    indistinguishable from "git errored". That is fine inside an engine and
    actively harmful in a CLI a human reads.
    """
    try:
        p = subprocess.run(
            ["git", "-C", repo, *args],
            capture_output=True, text=True, timeout=timeout,
        )
        return p.returncode, p.stdout.strip(), p.stderr.strip()
    except subprocess.TimeoutExpired:
        return 124, "", f"timeout after {timeout}s"
    except FileNotFoundError:
        return 127, "", "git executable not found on PATH"


def git_out(repo: str, *args: str, timeout: int = LOCAL_TIMEOUT) -> str | None:
    code, out, _ = git(repo, *args, timeout=timeout)
    return out if code == 0 else None


def rev_parse(repo: str, rev: str) -> str | None:
    # --end-of-options stops a ref named like a flag from being parsed as one.
    return git_out(repo, "rev-parse", "--verify", "--end-of-options", f"{rev}^{{commit}}")


def safe_finding_path(raw: str | None) -> str:
    """Normalise an agent-supplied path to a repo-relative one, or "" if unsafe.

    Agents emit paths in several shapes (absolute, ./-prefixed, or carrying a
    workspace prefix). Anything that escapes the repo is rejected outright
    rather than normalised, so a malformed path can never widen the diff scope.
    """
    if not raw or not isinstance(raw, str):
        return ""
    path = raw.strip().replace("\\", "/")
    if not path:
        return ""
    for prefix in ("/workspace/", "workspace/", "./"):
        if path.startswith(prefix):
            path = path[len(prefix):]
    path = path.lstrip("/")
    parts = [p for p in path.split("/") if p not in ("", ".")]
    if any(p == ".." for p in parts):
        return ""
    return "/".join(parts)


# ── upstream identity ───────────────────────────────────────────────────────
def resolve_upstream(repo: str, requested: str | None) -> dict:
    """Identify the fetch remote and decide whether it is a REAL upstream.

    This check does not exist in open-kritt and is the reason its production
    path silently degrades: its job workspaces are `git clone --shared` of a
    local cache, so `origin` is a local directory whose HEAD is the pinned
    commit. Fetching it always yields "nothing moved" no matter what the real
    upstream did. A local-path origin must therefore be treated as
    `unavailable`, never as `current_default`.
    """
    remote = requested or "origin"
    if "://" in remote or remote.startswith("git@"):
        url = remote  # a URL was passed directly
    else:
        url = git_out(repo, "remote", "get-url", remote)

    if not url:
        return {"remote": remote, "url": None, "is_real_upstream": False,
                "why": f"remote {remote!r} is not configured"}

    looks_local = (
        url.startswith("/")
        or url.startswith("file://")
        or url.startswith(".")
        or (len(url) > 1 and url[1] == ":")  # windows drive letter
    )
    if looks_local and Path(url.replace("file://", "")).exists():
        return {"remote": remote, "url": url, "is_real_upstream": False,
                "why": "origin points at a local path (mirror/shared clone), "
                       "so a comparison against it proves nothing about upstream"}

    return {"remote": remote, "url": url, "is_real_upstream": True, "why": None}


def unshallow(repo: str, remote: str) -> str:
    """Deepen a shallow clone so ancestry tests are meaningful.

    On a --depth=1 checkout `merge-base --is-ancestor` cannot see the shared
    history and everything collapses to `unavailable`. open-kritt accepts that
    degradation; dewaxguard usually runs on a clone the user already has, so
    deepening is cheap and strictly better.
    """
    if git_out(repo, "rev-parse", "--is-shallow-repository") != "true":
        return "not_shallow"
    if git(repo, "fetch", "--quiet", "--no-tags", "--unshallow", remote,
           timeout=FETCH_TIMEOUT)[0] == 0:
        return "unshallowed"
    if git(repo, "fetch", "--quiet", "--no-tags", "--deepen=500", remote,
           timeout=FETCH_TIMEOUT)[0] == 0:
        return "deepened"
    return "still_shallow"


# ── evidence collection ─────────────────────────────────────────────────────
def path_evidence(repo: str, pin: str, default: str, path: str) -> dict:
    """Path-scoped comparison. Scoping keeps a busy default branch from
    producing a 40k-line diff that a model then hallucinates a fix out of."""
    target_has = git(repo, "cat-file", "-e", f"{pin}:{path}")[0] == 0
    default_has = git(repo, "cat-file", "-e", f"{default}:{path}")[0] == 0

    diff = git_out(repo, "diff", "--no-ext-diff", "--unified=20",
                   pin, default, "--", path) or ""
    truncated = len(diff) > DIFF_LIMIT
    if truncated:
        diff = diff[:DIFF_LIMIT] + "\n[... diff truncated ...]"

    commits = []
    raw = git_out(repo, "log", f"--max-count={LOG_LIMIT}",
                  "--format=%H%x09%aI%x09%s", f"{pin}..{default}", "--", path)
    for line in (raw or "").splitlines():
        bits = line.split("\t", 2)
        if len(bits) == 3:
            commits.append({"commit": bits[0], "date": bits[1], "subject": bits[2]})

    # Rename detection — open-kritt has none, so an upstream file move reads as
    # "no evidence" instead of "moved". --follow makes that case explicit.
    renamed = []
    if target_has and not default_has:
        raw_follow = git_out(repo, "log", "--follow", f"--max-count={LOG_LIMIT}",
                             "--name-status", "--format=%H", f"{pin}..{default}",
                             "--", path)
        for line in (raw_follow or "").splitlines():
            if line.startswith("R"):
                bits = line.split("\t")
                if len(bits) >= 3:
                    renamed.append({"from": bits[1], "to": bits[2]})

    return {
        "path": path,
        "target_has_path": target_has,
        "default_has_path": default_has,
        "diff": diff,
        "diff_truncated": truncated,
        "diff_is_empty": diff == "",
        "commits_touching_path": commits,
        "renamed_upstream": renamed,
    }


def pickaxe(repo: str, pin: str, default: str, expr: str, is_regex: bool = False) -> list[dict]:
    """Find the commit that changed a specific expression, even across renames.

    Catches the fix when the file moved or the finding's line drifted — the case
    a path-scoped diff misses entirely. Not present in open-kritt.

    Uses -G, not -S. `-S` only fires when the NUMBER of occurrences changes, so
    a fix that rewrites a line while keeping the expression in it (the common
    shape: `return a+b` -> `require(a>0); return a+b`) is invisible to it. `-G`
    fires whenever a line containing the pattern is added or removed, which is
    what "was this expression touched upstream" actually means.

    The pattern is escaped to a LITERAL by default. `-G` takes a regex, and real
    audited code is full of regex metacharacters — `balances[msg.sender] += amt`
    or `require(x > 0)` silently match nothing, which reads as "no upstream fix"
    and is a false negative in the one direction this tool must never produce.
    Pass is_regex=True (--pickaxe-regex) to opt into regex semantics.
    """
    hits = []
    pattern = expr if is_regex else re.escape(expr)
    raw = git_out(repo, "log", "--max-count=40", f"-G{pattern}",
                  "--format=%H%x09%aI%x09%s", f"{pin}..{default}")
    for line in (raw or "").splitlines():
        bits = line.split("\t", 2)
        if len(bits) == 3:
            hits.append({"commit": bits[0], "date": bits[1], "subject": bits[2]})
    return hits


def descendant_refs(repo: str, pin: str) -> list[dict]:
    """Locally-known refs that strictly descend from the pinned commit.

    Includes refs/tags (open-kritt deliberately omits them) because "is the fix
    in a released tag?" is exactly what bounty triage needs to know.
    """
    fmt = "%(objecttype)%00%(objectname)%00%(committerdate:iso-strict)%00%(subject)%00%(refname)"
    raw = git_out(repo, "for-each-ref", "--sort=-committerdate", f"--format={fmt}",
                  "refs/heads", "refs/remotes/origin", "refs/tags", NS)
    out = []
    seen = set()
    rows = [line.split("\0") for line in (raw or "").splitlines()]
    rows = [r for r in rows if len(r) == 5]
    # Tags first: when a tag and a branch point at the SAME commit, the tag is
    # the more useful label ("the fix shipped in v1.2.0" beats "it is on main"),
    # and the sha-dedup below keeps only whichever ref is seen first.
    rows.sort(key=lambda r: 0 if r[4].startswith("refs/tags/") else 1)
    for bits in rows:
        objtype, sha, date, subject, refname = bits
        if objtype == "tag":  # annotated tag → peel to its commit
            sha = rev_parse(repo, refname) or sha
        if not sha or sha == pin or sha in seen:
            continue
        if git(repo, "merge-base", "--is-ancestor", pin, sha)[0] != 0:
            continue
        ahead = git_out(repo, "rev-list", "--count", f"{pin}..{sha}")
        try:
            ahead_n = int(ahead or "0")
        except ValueError:
            ahead_n = 0
        if ahead_n <= 0:  # not strictly ahead → cannot contain a fix
            continue
        seen.add(sha)
        out.append({"commit": sha, "date": date, "subject": subject,
                    "refname": refname, "commits_ahead": ahead_n})
    out.sort(key=lambda r: (r["date"], r["commits_ahead"]), reverse=True)
    return out[:DESCENDANT_CAP]


# ── main ────────────────────────────────────────────────────────────────────
def build(repo: str, commit: str, raw_path: str, upstream_arg: str | None,
          pickaxe_expr: str | None, pickaxe_is_regex: bool = False) -> dict:
    result: dict = {
        "status": "unavailable",
        "reason": "",
        "comparison_performed": False,
        "target_revision": commit,
        "target_commit": None,
        "worktree_remains_pinned": None,
        "upstream": None,
        "default_branch": None,
        "path_comparison": None,
        "pickaxe_hits": [],
        "newer_descendants": [],
    }

    if git(repo, "rev-parse", "--git-dir")[0] != 0:
        result["reason"] = f"{repo} is not a git repository; patch status requires manual review."
        return result

    pin = rev_parse(repo, commit)
    if not pin:
        result["reason"] = (f"The audited revision {commit!r} is not present in this checkout, "
                            "so no comparison is possible; manual review required.")
        return result
    result["target_commit"] = pin
    result["worktree_remains_pinned"] = git_out(repo, "rev-parse", "HEAD") == pin

    up = resolve_upstream(repo, upstream_arg)
    result["upstream"] = up
    if not up["is_real_upstream"]:
        result["reason"] = (f"Cannot verify patch status: {up['why']}. "
                            "Pass --upstream <url> pointing at the real upstream, "
                            "or review manually.")
        return result

    result["upstream"]["shallow_fix"] = unshallow(repo, up["remote"])

    # +HEAD: follows the remote's own default branch — never hardcode main/master.
    fetch_code, _, fetch_err = git(repo, "fetch", "--quiet", "--prune", "--no-tags",
                                   up["remote"], f"+HEAD:{DEFAULT_REF}",
                                   timeout=FETCH_TIMEOUT)
    if fetch_code != 0:
        result["reason"] = (f"Could not fetch the remote default branch ({fetch_err or 'unknown error'}); "
                            "patch status requires manual review.")
        return result

    default = rev_parse(repo, DEFAULT_REF)
    if not default:
        result["reason"] = "The fetched default branch could not be resolved; manual review required."
        return result

    ahead = git_out(repo, "rev-list", "--count", f"{pin}..{default}") or "0"
    result["default_branch"] = {"commit": default, "commits_ahead": int(ahead or 0)}

    if default == pin:
        result["status"] = "current_default"
        result["comparison_performed"] = True
        result["reason"] = ("The audited commit IS the current upstream default-branch commit. "
                            "The comparison succeeded and nothing has moved: the code is unchanged upstream.")
    elif git(repo, "merge-base", "--is-ancestor", pin, default)[0] == 0:
        result["status"] = "available"
        result["comparison_performed"] = True
        result["reason"] = ("The upstream default branch descends from the audited commit. "
                            "Inspect the supplied diff and commit log.")
    else:
        result["reason"] = ("The upstream default branch does not descend from the audited commit "
                            "(fork, rewritten history, or unrelated branch). Comparing them would be "
                            "meaningless, so patch status requires manual review.")
        return result

    path = safe_finding_path(raw_path)
    if path:
        result["path_comparison"] = path_evidence(repo, pin, default, path)
    else:
        result["path_comparison"] = {"path": None,
                                     "note": "No safe repo-relative path supplied; "
                                             "comparison is repo-wide only."}

    if pickaxe_expr and result["status"] == "available":
        result["pickaxe_hits"] = pickaxe(repo, pin, default, pickaxe_expr, pickaxe_is_regex)

    result["newer_descendants"] = descendant_refs(repo, pin)
    return result


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Check whether a finding's code was already patched upstream.")
    ap.add_argument("--repo", required=True, help="path to the git checkout")
    ap.add_argument("--path", required=True, help="repo-relative file the finding is in")
    ap.add_argument("--commit", default="HEAD", help="audited revision (default: HEAD)")
    ap.add_argument("--upstream", default=None,
                    help="remote name or URL to compare against (default: origin)")
    ap.add_argument("--pickaxe", default=None,
                    help="code expression to search for upstream (finds fixes across renames). "
                         "Matched LITERALLY — paste the vulnerable line as-is.")
    ap.add_argument("--pickaxe-regex", action="store_true",
                    help="treat --pickaxe as a regex instead of a literal string")
    ap.add_argument("--pretty", action="store_true", help="indent the JSON output")
    args = ap.parse_args(argv)

    repo = str(Path(args.repo).expanduser().resolve())
    if not Path(repo).is_dir():
        print(f"error: --repo {args.repo!r} is not a directory", file=sys.stderr)
        return 2

    result = build(repo, args.commit, args.path, args.upstream,
                   args.pickaxe, args.pickaxe_regex)
    print(json.dumps(result, indent=2 if args.pretty else None, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
