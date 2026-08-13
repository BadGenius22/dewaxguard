#!/usr/bin/env bash
# grep_v12.sh — pre-grep V12 / Zellic / similar AI-auditor structured outputs
#
# Usage:
#   ./grep_v12.sh <keyword> [more keywords...]      # OR-mode (default): match any keyword
#   ./grep_v12.sh --strict <kw1> <kw2> [<kw3>...]   # AND-mode: every keyword must match in same finding
#   ./grep_v12.sh --invalid-only                    # list every Invalid finding (read these as platform-semantics corpus)
#   ./grep_v12.sh --count                           # print per-file finding counts
#   ./grep_v12.sh --files <dir>                     # specify search directory (default: pwd)
#
# Behavior:
#   1. Locates V12 output files in current dir (or --files dir): *V12*-output.md, *zellic*.md, K2-V12-*.md
#   2. For each finding (delimited by lines matching "^# Title"), checks if keyword(s) match the finding's body
#   3. Prints: file:line | finding_id | severity | validity | title | one-line Description
#
# Exit code:
#   0 — at least one match found
#   1 — no matches
#   2 — bad arguments / no V12 files found
#
# Designed to run in ~10 seconds for typical V12 corpora (~150k lines).

set -euo pipefail

usage() {
  sed -n '2,15p' "$0" | sed 's|^# ||;s|^#||'
  exit 2
}

MODE="or"
INVALID_ONLY=0
COUNT_ONLY=0
SEARCH_DIR="."
KEYWORDS=()

while (( $# > 0 )); do
  case "$1" in
    --strict) MODE="and"; shift ;;
    --invalid-only) INVALID_ONLY=1; shift ;;
    --count) COUNT_ONLY=1; shift ;;
    --files) SEARCH_DIR="$2"; shift 2 ;;
    -h|--help) usage ;;
    --*) echo "Unknown flag: $1" >&2; usage ;;
    *) KEYWORDS+=("$1"); shift ;;
  esac
done

if (( COUNT_ONLY == 0 && INVALID_ONLY == 0 && ${#KEYWORDS[@]} == 0 )); then
  usage
fi

# Locate candidate V12 output files
mapfile -t V12_FILES < <(
  find "$SEARCH_DIR" -maxdepth 3 -type f \
    \( -iname '*V12*output*.md' -o -iname '*zellic*.md' \) \
    2>/dev/null | sort
)

if (( ${#V12_FILES[@]} == 0 )); then
  echo "no V12 output files found under $SEARCH_DIR (looked for *V12*output*.md / *zellic*.md)" >&2
  exit 2
fi

# --count: print finding count per file then exit
# Headings only count outside fenced code blocks.
if (( COUNT_ONLY == 1 )); then
  total=0
  for f in "${V12_FILES[@]}"; do
    n=$(awk '
      /^```/ { in_fence = !in_fence; next }
      !in_fence && /^# / { c++ }
      END { print c+0 }
    ' "$f")
    printf "%6d  %s\n" "$n" "$f"
    total=$(( total + n ))
  done
  printf "%6d  TOTAL\n" "$total"
  exit 0
fi

# --invalid-only: surface every entry with an explicit "Invalid" verdict
# V12 uses two patterns:
#   1. Top-level "- Validity: Invalid" field
#   2. "### Invalid Reason" subsection inside Proof of Concept (Validity may still be "Unreviewed")
# Both indicate the LLM could not construct an exploit. Both are platform-knowledge cards.
flush_invalid() {
  :
}

if (( INVALID_ONLY == 1 )); then
  for f in "${V12_FILES[@]}"; do
    awk -v fname="$f" '
      function flush_finding() {
        if (title == "") return
        if (validity == "Invalid" || invalid_reason != "") {
          title_clean = title; sub(/^# /, "", title_clean)
          tag = (validity == "Invalid") ? "Invalid" : "Unreviewed:HasInvalidReason"
          printf "%s:%d  #%s  [%s|%s]  %s\n", fname, title_line, finding_id, severity, tag, title_clean
          if (invalid_reason != "") printf "    REASON: %s\n", substr(invalid_reason, 1, 220)
          else if (desc != "") printf "    DESC:   %s\n", substr(desc, 1, 220)
        }
        title = ""; finding_id = ""; severity = ""; validity = ""; desc = ""; invalid_reason = ""
        in_desc = 0; in_invalid_reason = 0
      }
      /^```/ { in_fence = !in_fence; next }
      in_fence { next }
      /^# / {
        flush_finding()
        title = $0; title_line = NR; next
      }
      title != "" && /^\*\*#/ { gsub(/^\*\*#|\*\*$/, "", $0); finding_id = $0; next }
      title != "" && /^- Severity:/ { severity = $0; sub(/^- Severity: */, "", severity); next }
      title != "" && /^- Validity:/ { validity = $0; sub(/^- Validity: */, "", validity); next }
      title != "" && /^## Description/ { in_desc = 1; in_invalid_reason = 0; next }
      title != "" && in_desc && NF > 0 && !/^##/ { if (desc == "") desc = $0; next }
      title != "" && /^### Invalid Reason/ { in_invalid_reason = 1; in_desc = 0; next }
      title != "" && in_invalid_reason && NF > 0 && !/^##/ {
        if (invalid_reason == "") invalid_reason = $0
        else invalid_reason = invalid_reason " " $0
        if (length(invalid_reason) > 400) in_invalid_reason = 0
        next
      }
      title != "" && /^##/ { in_desc = 0; in_invalid_reason = 0 }
      END { flush_finding() }
    ' "$f"
  done
  exit 0
fi

# Keyword search mode
# For each file, walk findings (header→header), collect: title, finding_id, severity, validity, body.
# Match keywords against (title + body) per MODE.
any_match=0

awk_program='
  BEGIN { mode = ENVIRON["MODE"]; n_kw = split(ENVIRON["KEYWORDS_PIPE"], KW, "|") }
  function flush() {
    if (title == "") return
    body_lower = tolower(title "\n" body)
    matched = 0
    if (mode == "and") {
      matched = 1
      for (i = 1; i <= n_kw; i++) {
        if (index(body_lower, tolower(KW[i])) == 0) { matched = 0; break }
      }
    } else {
      for (i = 1; i <= n_kw; i++) {
        if (index(body_lower, tolower(KW[i])) > 0) { matched = 1; break }
      }
    }
    if (matched) {
      first_desc_line = "(no description)"
      n = split(body, lines, "\n")
      seen_desc_header = 0
      for (i = 1; i <= n; i++) {
        if (lines[i] ~ /^## Description/) { seen_desc_header = 1; continue }
        if (seen_desc_header && lines[i] !~ /^[ \t]*$/ && lines[i] !~ /^#/) {
          first_desc_line = lines[i]; break
        }
      }
      title_clean = title; sub(/^# /, "", title_clean)
      sev_clean = severity
      val_clean = validity
      printf "%s:%d  #%s  [%s|%s]  %s\n", fname, title_line, finding_id, sev_clean, val_clean, title_clean
      printf "    %s\n", substr(first_desc_line, 1, 200)
    }
    title = ""; body = ""; finding_id = ""; severity = ""; validity = ""
  }
  /^```/ { in_fence = !in_fence; if (title != "") body = body $0 "\n"; next }
  in_fence { if (title != "") body = body $0 "\n"; next }
  /^# / {
    flush()
    title = $0; title_line = NR; body = ""; finding_id = ""; severity = ""; validity = ""
    next
  }
  /^\*\*#/ {
    fid = $0; gsub(/^\*\*#|\*\*$/, "", fid); finding_id = fid
    body = body $0 "\n"
    next
  }
  /^- Severity:/ { severity = $0; sub(/^- Severity: */, "", severity); body = body $0 "\n"; next }
  /^- Validity:/ { validity = $0; sub(/^- Validity: */, "", validity); body = body $0 "\n"; next }
  { if (title != "") body = body $0 "\n" }
  END { flush() }
'

for f in "${V12_FILES[@]}"; do
  KEYWORDS_PIPE=$(IFS='|'; echo "${KEYWORDS[*]}")
  output=$(MODE="$MODE" KEYWORDS_PIPE="$KEYWORDS_PIPE" awk -v fname="$f" "$awk_program" "$f" 2>/dev/null || true)
  if [[ -n "$output" ]]; then
    any_match=1
    echo "$output"
  fi
done

if (( any_match == 0 )); then
  echo "no V12 finding matched the keyword(s): ${KEYWORDS[*]} (mode=$MODE)"
  exit 1
fi

exit 0
