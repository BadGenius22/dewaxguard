#!/usr/bin/env bash
# blind_benchmark.sh — produce ANSWER-BLIND copies of benchmarks before a run.
#
# WHY THIS EXISTS (v1.21.0 accuracy fix):
# The committed benchmark sources contain answer-leaking comments like
# `// VULNERABLE: external call before state update`. Auditing a file whose
# comments name the bug measures the agent's reading comprehension, not its
# bug-finding ability — recall is meaningless on a leaked benchmark. This script
# strips every comment (and trailing `/// CHECK:` rationales) so the audited copy
# contains ONLY code. The ground-truth.json is never copied into the blind tree.
#
# Usage:
#   scripts/blind_benchmark.sh [--out DIR] [benchmark-id ...]
#     no ids  -> all benchmarks in manifest.json
#     --out   -> blind tree root (default: a fresh temp dir, path printed on exit)
#
# Strips: full-line and trailing // comments (Sol/Rust/Move), /* */ blocks,
#         and # comments — while preserving // inside string literals heuristically
#         (benchmarks have none, so the simple rule is safe here).
set -u
SKILL="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT=""
IDS=()
while [ $# -gt 0 ]; do
  case "$1" in
    --out) OUT="$2"; shift 2 ;;
    *) IDS+=("$1"); shift ;;
  esac
done
[ -n "$OUT" ] || OUT="$(mktemp -d -t dgblind.XXXXXX)"
mkdir -p "$OUT"

# Derive benchmark path list from manifest (id -> path), filtered by IDS if given.
mapfile -t ROWS < <(python3 - "$SKILL/benchmarks/manifest.json" "${IDS[@]:-}" <<'PY'
import json, sys
mf = json.load(open(sys.argv[1]))
want = set(a for a in sys.argv[2:] if a)
for b in mf["benchmarks"]:
    if not want or b["id"] in want:
        print(f'{b["id"]}\t{b["path"]}\t{b["language"]}')
PY
)

strip_comments() { # stdin -> stdout, comments removed, blank-comment-lines dropped
  sed -E \
    -e 's@/\*.*\*/@@g' \
    -e 's@//.*$@@' \
    -e 's@^[[:space:]]*#.*$@@' \
    "$1" \
  | sed -E 's/[[:space:]]+$//'
}

count=0
for row in "${ROWS[@]}"; do
  id="${row%%	*}"; rest="${row#*	}"; path="${rest%%	*}"
  srcdir="$SKILL/benchmarks/$path/src"
  [ -d "$srcdir" ] || { echo "WARN: no src for $id ($srcdir)"; continue; }
  dst="$OUT/$id/src"; mkdir -p "$dst"
  for f in "$srcdir"/*; do
    [ -f "$f" ] || continue
    strip_comments "$f" > "$dst/$(basename "$f")"
  done
  # Leak guard: fail loudly if any answer keyword survived.
  if grep -riqE 'vulnerab|exploit|attack|race condition|false positive|should not be flagged|correct pattern' "$dst" 2>/dev/null; then
    echo "ERROR: leak survived stripping in $id — inspect $dst" >&2
    grep -rinE 'vulnerab|exploit|attack|false positive' "$dst" >&2
  fi
  count=$((count+1))
done

echo "$OUT"
echo "# wrote $count blind benchmark(s) to $OUT (ground-truth.json intentionally NOT copied)" >&2
