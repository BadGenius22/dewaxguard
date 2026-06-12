#!/usr/bin/env bash
# run_benchmarks.sh — end-to-end blind benchmark regression harness (Tier 2.5)
#
# Closes the loop the self-improvement plan flagged: blind-prep + scoring were two
# separate manual steps with no aggregation. This wraps both into one regression
# runner. The only non-mechanical step is the agent pass itself (an LLM run), which
# the harness scaffolds and then scores.
#
# THREE MODES:
#   --prep [--out DIR] [ids...]
#       Produce answer-blind copies (delegates to blind_benchmark.sh), then print,
#       per benchmark: detected language, blind src path, and the exact scoring
#       command to run after the agent pass. Writes a run-manifest the score step reads.
#
#   --score OUTPUTS_DIR [--results FILE] [--out DIR] [ids...]
#       For each benchmark, score OUTPUTS_DIR/<id>.txt against its ground truth via
#       score_benchmark.py, aggregate recall / trap-precision / severity-delta into a
#       single results markdown (default: benchmarks/results/<version>_<date>.md style,
#       but date must be passed in via --date since scripts cannot read the clock).
#
#   --check
#       Mechanical regression gate for CI: asserts every manifest benchmark has a
#       blind copy that strips cleanly. Exits non-zero on any leak. (Does NOT run agents.)
#
# WHY scoring takes OUTPUTS_DIR not stdin: a full regression scores all 6+ benchmarks;
# one file per benchmark id keeps the harness re-runnable and diffable.
set -u
SKILL="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$SKILL" || exit 1

MODE="" OUT="" OUTPUTS="" RESULTS="" DATE="" IDS=()
while [ $# -gt 0 ]; do
  case "$1" in
    --prep)    MODE=prep; shift ;;
    --score)   MODE=score; OUTPUTS="$2"; shift 2 ;;
    --check)   MODE=check; shift ;;
    --out)     OUT="$2"; shift 2 ;;
    --results) RESULTS="$2"; shift 2 ;;
    --date)    DATE="$2"; shift 2 ;;
    *) IDS+=("$1"); shift ;;
  esac
done
[ -n "$MODE" ] || { echo "usage: run_benchmarks.sh {--prep | --score DIR | --check} [--out DIR] [--results FILE] [--date YYYY-MM-DD] [ids...]" >&2; exit 1; }

VERSION="$(tr -d ' \n' < VERSION)"
manifest_rows() {  # id<TAB>path<TAB>language
  python3 - "$SKILL/benchmarks/manifest.json" "${IDS[@]:-}" <<'PY'
import json, sys
mf = json.load(open(sys.argv[1])); want = set(a for a in sys.argv[2:] if a)
for b in mf["benchmarks"]:
    if not want or b["id"] in want:
        print(f'{b["id"]}\t{b["path"]}\t{b["language"]}')
PY
}

if [ "$MODE" = prep ]; then
  [ -n "$OUT" ] || OUT="$(mktemp -d -t dgbench.XXXXXX)"
  scripts/blind_benchmark.sh --out "$OUT" "${IDS[@]:-}" >/dev/null
  echo "# Blind benchmark run plan (v$VERSION)"
  echo "# blind tree: $OUT"
  echo "# For EACH row: run the breadth/depth agents on the blind src, save raw output to"
  echo "#   <outputs_dir>/<id>.txt, then: scripts/run_benchmarks.sh --score <outputs_dir> --date <today>"
  echo
  printf '%-26s %-8s %s\n' "ID" "LANG" "BLIND_SRC"
  while IFS=$'\t' read -r id path lang; do
    [ -n "$id" ] || continue
    printf '%-26s %-8s %s\n' "$id" "$lang" "$OUT/$id/src"
  done < <(manifest_rows)
  echo
  echo "$OUT"   # last line = blind tree root (machine-readable)
  exit 0
fi

if [ "$MODE" = check ]; then
  tmp="$(mktemp -d)"; scripts/blind_benchmark.sh --out "$tmp" "${IDS[@]:-}" >/dev/null 2>&1
  leak="$(grep -riElE 'vulnerab|exploit|false positive|should not be flagged|correct pattern' "$tmp" 2>/dev/null)"
  rm -rf "$tmp"
  if [ -n "$leak" ]; then echo "FAIL: answer leak survived blind strip: $leak" >&2; exit 1; fi
  echo "ok: all blind copies strip cleanly"; exit 0
fi

# --- score ---
[ -d "$OUTPUTS" ] || { echo "error: --score dir '$OUTPUTS' not found" >&2; exit 1; }
[ -n "$RESULTS" ] || RESULTS="benchmarks/results/${VERSION}_${DATE:-undated}.md"
mkdir -p "$(dirname "$RESULTS")"

total=0 scored=0 recall_hits=0 recall_need=0 traps_clean=0 traps_total=0 missing=()
detail=""
while IFS=$'\t' read -r id path lang; do
  [ -n "$id" ] || continue
  total=$((total+1))
  out=""
  for cand in "$OUTPUTS/$id.txt" "$OUTPUTS/$id.md" "$OUTPUTS/$id"; do
    [ -f "$cand" ] && { out="$cand"; break; }
  done
  gt="benchmarks/$path/ground-truth.json"
  if [ -z "$out" ]; then missing+=("$id"); detail="$detail| $id | $lang | — | NO OUTPUT |\n"; continue; fi
  res="$(scripts/score_benchmark.py "$out" "$gt" --json 2>/dev/null)" || true
  if [ -z "$res" ]; then detail="$detail| $id | $lang | — | SCORE ERROR |\n"; continue; fi
  scored=$((scored+1))
  read -r rf rn tc tt <<<"$(python3 - <<PY
import json,sys
r=json.loads('''$res''')
print(r["found"], r["must_detect"], r["traps_clean"], r["traps_total"])
PY
)"
  recall_hits=$((recall_hits+rf)); recall_need=$((recall_need+rn))
  traps_clean=$((traps_clean+tc)); traps_total=$((traps_total+tt))
  sevs="$(python3 - <<PY
import json
r=json.loads('''$res''')
ds=[d for d in r["detection"] if d["sev_delta"] is not None]
print(",".join(f"{d['exp_sev']}->{d['got_sev']}({d['sev_delta']:+d})" for d in ds) or "—")
PY
)"
  verdict="PASS"; [ "$rf" -eq "$rn" ] && [ "$tc" -eq "$tt" ] || verdict="REGRESS"
  detail="$detail| $id | $lang | $rf/$rn recall, $tc/$tt traps | $verdict |\n  ↳ sev: $sevs\n"
done < <(manifest_rows)

recall_pct=$(( recall_need>0 ? recall_hits*100/recall_need : 100 ))
trap_pct=$(( traps_total>0 ? traps_clean*100/traps_total : 100 ))
{
  echo "# Benchmark Results — DewaxGuard v$VERSION"
  echo
  echo "**Date**: ${DATE:-(pass --date)}"
  echo "**Harness**: scripts/run_benchmarks.sh (blind prep + score_benchmark.py aggregate)"
  echo "**Outputs scored from**: $OUTPUTS"
  echo
  echo "## Summary"
  echo
  echo "| Metric | Value |"
  echo "|--------|-------|"
  echo "| Benchmarks scored | $scored / $total |"
  echo "| must_detect recall | $recall_hits / $recall_need ($recall_pct%) |"
  echo "| FP traps clean | $traps_clean / $traps_total ($trap_pct%) |"
  [ ${#missing[@]} -gt 0 ] && echo "| Missing agent outputs | ${missing[*]} |"
  echo
  echo "## Per-benchmark"
  echo
  echo "| ID | Lang | Result | Verdict |"
  echo "|----|------|--------|---------|"
  printf '%b' "$detail"
} > "$RESULTS"

echo "wrote $RESULTS"
echo "recall $recall_hits/$recall_need ($recall_pct%) | traps clean $traps_clean/$traps_total ($trap_pct%) | scored $scored/$total"
[ "$recall_hits" -eq "$recall_need" ] && [ "$traps_clean" -eq "$traps_total" ] && exit 0 || exit 1
