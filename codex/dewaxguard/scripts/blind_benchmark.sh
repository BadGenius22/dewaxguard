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
# Strips: full-line and trailing // comments (Sol/Rust/Move/Go/C++), /* */ blocks
#         (multi-line aware), and — for hash-comment languages ONLY (Vyper/Cairo/
#         Python/TOML) — full-line # comments. Rust/Move `#[attr]` / `#![attr]`
#         lines are code, not comments, and are preserved. Block comments are
#         replaced with the same number of blank lines so ground-truth line
#         numbers stay aligned with the blind copy.
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

strip_comments() { # $1=file  $2=language ; writes stripped code to stdout
  python3 - "$1" "$2" <<'PY'
import re, sys
text = open(sys.argv[1], encoding="utf-8", errors="replace").read()
lang = sys.argv[2].lower()
# Languages where a leading '#' starts a line comment. Rust/Move/Solidity/Go/C++
# are NOT here — '#' there is an attribute (#[...]) and must survive.
HASH_COMMENT = {"vyper", "vy", "cairo", "python", "py", "toml", "sh", "bash"}
# 1) block comments /* ... */ (multi-line), replaced by equal newlines so line
#    numbers stay aligned with ground-truth.
text = re.sub(r"/\*.*?\*/", lambda m: "\n" * m.group(0).count("\n"), text, flags=re.S)
out = []
for line in text.split("\n"):
    line = re.sub(r"//.*$", "", line)          # // line + trailing comments
    if lang in HASH_COMMENT:
        line = re.sub(r"^\s*#.*$", "", line)    # full-line # comments (hash langs only)
    out.append(re.sub(r"[ \t]+$", "", line))    # strip trailing whitespace
sys.stdout.write("\n".join(out))
PY
}

count=0
leaked=0
for row in "${ROWS[@]}"; do
  id="${row%%	*}"; rest="${row#*	}"; path="${rest%%	*}"; lang="${rest##*	}"
  srcdir="$SKILL/benchmarks/$path/src"
  [ -d "$srcdir" ] || { echo "WARN: no src for $id ($srcdir)"; continue; }
  dst="$OUT/$id/src"; mkdir -p "$dst"
  for f in "$srcdir"/*; do
    [ -f "$f" ] || continue
    strip_comments "$f" "$lang" > "$dst/$(basename "$f")"
  done
  # Leak guard: fail loudly (and, at the end, exit nonzero) if any answer
  # keyword survived — selfcheck's leak gate relies on this exit code.
  if grep -riqE 'vulnerab|exploit|attack|race condition|false positive|should not be flagged|correct pattern' "$dst" 2>/dev/null; then
    echo "ERROR: leak survived stripping in $id — inspect $dst" >&2
    grep -rinE 'vulnerab|exploit|attack|false positive' "$dst" >&2
    leaked=1
  fi
  count=$((count+1))
done

echo "$OUT"
echo "# wrote $count blind benchmark(s) to $OUT (ground-truth.json intentionally NOT copied)" >&2
[ "$leaked" -eq 0 ] || { echo "# FAIL: answer leak survived in at least one benchmark" >&2; exit 1; }
