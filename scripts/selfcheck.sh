#!/usr/bin/env bash
# selfcheck.sh — mechanical skill-integrity gate (v1.20.0)
#
# Verifies the dewaxguard skill is internally consistent. Run after ANY edit
# to the skill, and before every commit. Exit 0 = all checks pass.
#
# Catches the drift classes found in the v1.20.0 consistency audit:
#   - methodology files missing from INDEX.md (M-13/M-14 class)
#   - stale version banners (SKILL.md said v1.0.0 at VERSION 1.19.1)
#   - file references in SKILL.md pointing at nonexistent paths
#   - invalid trigger frontmatter (bad ERE, brace globs, missing fields)
#   - broken scripts (bash/python syntax)
#
# Usage: scripts/selfcheck.sh   (from anywhere; resolves skill root itself)
set -u
SKILL="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$SKILL" || exit 1

FAIL=0
fail() { echo "FAIL: $*"; FAIL=1; }
ok()   { echo "  ok: $*"; }

echo "== 1. Version sync =="
v_file=$(tr -d ' \n' < VERSION)
v_skill=$(grep -oE '\*\*v[0-9]+\.[0-9]+\.[0-9]+\*\*' SKILL.md | head -1 | tr -d '*v')
v_chlog=$(grep -oE '^## \[[0-9]+\.[0-9]+\.[0-9]+\]' CHANGELOG.md | head -1 | tr -d '#[] ')
[ "$v_file" = "$v_skill" ] || fail "VERSION ($v_file) != SKILL.md banner ($v_skill)"
[ "$v_file" = "$v_chlog" ] || fail "VERSION ($v_file) != CHANGELOG top entry ($v_chlog)"
[ $FAIL -eq 0 ] && ok "v$v_file consistent across VERSION / SKILL.md / CHANGELOG.md"

echo "== 2. Methodology registry bidirectional =="
for f in methodology/M*.md; do
  base=$(basename "$f")
  grep -q "$base" methodology/INDEX.md || fail "methodology/INDEX.md missing entry for $base"
done
for link in $(grep -oE '\]\(M[0-9]+-[a-z0-9-]+\.md\)' methodology/INDEX.md | tr -d ']()'); do
  [ -f "methodology/$link" ] || fail "methodology/INDEX.md links to nonexistent $link"
done
[ $FAIL -eq 0 ] && ok "$(ls methodology/M*.md | wc -l | tr -d ' ') templates all registered, all links resolve"

echo "== 3. Trigger frontmatter validity =="
fm_fail=0
for f in methodology/M*.md; do
  base=$(basename "$f")
  head -1 "$f" | grep -q '^---$' || { fail "$base: no frontmatter fence at line 1"; fm_fail=1; continue; }
  fm=$(awk 'NR==1{next} /^---$/{exit} {print}' "$f")
  id=$(printf '%s\n' "$fm" | sed -n 's/^id:[[:space:]]*//p' | head -1)
  fnum=$(printf '%s' "$base" | sed -n 's/^M\([0-9]*\)-.*/\1/p')
  [ "M-$fnum" = "$id" ] || { fail "$base: id '$id' != filename"; fm_fail=1; }
  ttype=$(printf '%s\n' "$fm" | sed -n 's/^trigger_type:[[:space:]]*//p' | head -1)
  case "$ttype" in
    code)
      pat=$(printf '%s\n' "$fm" | sed -n 's/^trigger_grep:[[:space:]]*//p' | head -1 | sed -e 's/^"//' -e 's/"$//')
      [ -n "$pat" ] || { fail "$base: code type without trigger_grep"; fm_fail=1; continue; }
      echo x | grep -qiE "$pat" 2>/dev/null; [ $? -ge 2 ] && { fail "$base: trigger_grep does not compile"; fm_fail=1; }
      case "$pat" in *'\\'*) fail "$base: double backslash in trigger_grep (consumer is raw, not YAML-parsed)"; fm_fail=1;; esac
      ;;
    artifact)
      g=$(printf '%s\n' "$fm" | sed -n 's/^trigger_glob:[[:space:]]*//p' | head -1)
      [ -n "$g" ] || { fail "$base: artifact type without trigger_glob"; fm_fail=1; }
      case "$g" in *'{'*) fail "$base: brace glob unsupported by find -name"; fm_fail=1;; esac
      ;;
    process)
      printf '%s\n' "$fm" | grep -q '^trigger_event:' || { fail "$base: process type without trigger_event"; fm_fail=1; }
      ;;
    *) fail "$base: invalid trigger_type '$ttype'"; fm_fail=1 ;;
  esac
done
[ $fm_fail -eq 0 ] && ok "all trigger frontmatter valid"

echo "== 4. SKILL.md file references resolve =="
ref_fail=0
while IFS= read -r ref; do
  p="${ref#\`}"; p="${p%\`}"
  p="${p#\~/.claude/skills/dewaxguard/}"
  case "$p" in
    *'{'*|*'*'*|'$'*|/*|http*) continue ;;            # placeholders, globs, vars, abs, urls
    rules/*|references/*|scripts/*|agents/*|prompts/*|methodology/*|patterns/*|improve/*|benchmarks/*|contest/*|platform-quirks/*|refuted/*)
      [ -e "$p" ] || { fail "SKILL.md references missing file: $p"; ref_fail=1; } ;;
  esac
done < <(grep -oE '`[^`]+\.(md|sh|py|json)`' SKILL.md | sort -u)
[ $ref_fail -eq 0 ] && ok "all SKILL.md path references exist"

echo "== 5. Pattern library links =="
pl_fail=0
for link in $(grep -oE '\]\(\.\./methodology/M[0-9]+-[a-z0-9-]+\.md\)' patterns/INDEX.md | sed 's/](\.\.\///; s/)//'); do
  [ -f "$link" ] || { fail "patterns/INDEX.md links to nonexistent $link"; pl_fail=1; }
done
[ $pl_fail -eq 0 ] && ok "patterns/INDEX.md links resolve"

echo "== 6. Platform criteria files =="
cr_fail=0
for c in c4-competitive c4-bounty sherlock-competitive sherlock-bounty cantina immunefi; do
  [ -f "references/criteria/$c.md" ] || { fail "missing references/criteria/$c.md"; cr_fail=1; }
done
[ $cr_fail -eq 0 ] && ok "all 6 criteria files present"

echo "== 7. Script syntax =="
sc_fail=0
for s in scripts/*.sh; do bash -n "$s" 2>/dev/null || { fail "bash syntax: $s"; sc_fail=1; }; done
for p in scripts/*.py scripts/gates/*.py scripts/squeezers/*.py; do
  [ -f "$p" ] && { python3 -m py_compile "$p" 2>/dev/null || { fail "python syntax: $p"; sc_fail=1; }; }
done
[ $sc_fail -eq 0 ] && ok "all scripts compile"

echo "== 8. Benchmarks =="
bm_fail=0
python3 - <<'EOF' || bm_fail=1
import json, os, sys
m = json.load(open("benchmarks/manifest.json"))
bad = False
for b in m["benchmarks"]:
    p = os.path.join("benchmarks", b["path"])
    if not os.path.isdir(os.path.join(p, "src")):
        print(f"FAIL: benchmark src missing: {p}/src"); bad = True
    gt = os.path.join(p, "ground-truth.json")
    if not os.path.isfile(gt):
        print(f"FAIL: ground truth missing: {gt}"); bad = True
    else:
        json.load(open(gt))
sys.exit(1 if bad else 0)
EOF
[ $bm_fail -eq 1 ] && FAIL=1 || ok "manifest + ground truths parse, all paths exist"

echo "== 9. Refuted index =="
if [ -f refuted/INDEX.md ]; then
  n=$(grep -cE '^### RF-[0-9]+' refuted/INDEX.md)
  [ "$n" -ge 1 ] && ok "refuted/INDEX.md present with $n RF entries" || fail "refuted/INDEX.md has no RF entries"
else
  fail "refuted/INDEX.md missing"
fi

echo "== 10. Benchmark blind-stripper removes answer leaks =="
if [ -x scripts/blind_benchmark.sh ]; then
  tmp=$(mktemp -d 2>/dev/null)
  scripts/blind_benchmark.sh --out "$tmp" >/dev/null 2>&1
  leak=$(grep -riElE 'vulnerab|exploit|false positive|should not be flagged|correct pattern' "$tmp" 2>/dev/null)
  gt=$(find "$tmp" -name ground-truth.json 2>/dev/null)
  [ -z "$leak" ] || fail "blind_benchmark.sh left answer leaks in: $leak"
  [ -z "$gt" ]   || fail "blind_benchmark.sh copied ground-truth.json into blind tree: $gt"
  [ -z "$leak" ] && [ -z "$gt" ] && ok "blind copies are answer-free and carry no ground truth"
  rm -rf "$tmp"
else
  fail "scripts/blind_benchmark.sh missing or not executable"
fi

echo "== 11. Disputed benchmark oracles carry review notes =="
do_fail=0
for gt in benchmarks/*/*/ground-truth.json; do
  if grep -q '"disputed"[[:space:]]*:[[:space:]]*true' "$gt"; then
    grep -q '_oracle_review' "$gt" || { fail "$gt has a disputed finding but no _oracle_review note"; do_fail=1; }
  fi
done
[ $do_fail -eq 0 ] && ok "all disputed oracles documented (or none disputed)"

echo
if [ $FAIL -eq 0 ]; then
  echo "SELFCHECK PASS — skill is internally consistent"
  exit 0
else
  echo "SELFCHECK FAIL — fix the items above before committing"
  exit 1
fi
