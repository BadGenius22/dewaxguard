#!/usr/bin/env bash
# detect_language.sh — deterministic language + platform-quirks resolution (Tier 3.8)
#
# WHY THIS EXISTS:
# SKILL.md Phase 1 detects language from a table the orchestrator reads by memory.
# platform-quirks/{lang}.md then loads only if the orchestrator remembers. That is a
# silent-miss risk: a Stellar audit that loads no stellar.md ships archive-restore
# false positives (the bug class platform-quirks/stellar.md #1 exists to kill).
# This script makes detection MECHANICAL: map build files -> LANGUAGE -> the exact
# quirks file the orchestrator must pass to every spawned agent.
#
# Detection is evidence-ordered: the most specific marker wins, so a Soroban repo
# (soroban-sdk, no anchor) is never misread as generic Solana, and an Anchor repo
# is never misread as a bare Rust crate.
#
# Usage:
#   scripts/detect_language.sh --src ./contracts [--root .] [--json]
# Output (text): LANGUAGE=<id>\nQUIRKS=<path or NONE>\nEVIDENCE=<marker>
# Output (--json): {"language":"...","quirks":"...","evidence":"...","l1_candidate":bool}
set -u
SKILL="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC="" ROOT="" JSON=0
while [ $# -gt 0 ]; do
  case "$1" in
    --src)  SRC="$2"; shift 2 ;;
    --root) ROOT="$2"; shift 2 ;;
    --json) JSON=1; shift ;;
    *) echo "unknown arg: $1" >&2; exit 1 ;;
  esac
done
[ -n "$SRC" ] || { echo "usage: detect_language.sh --src DIR [--root DIR] [--json]" >&2; exit 1; }
[ -d "$SRC" ] || { echo "error: --src '$SRC' is not a directory" >&2; exit 1; }
[ -n "$ROOT" ] || ROOT="$(dirname "$SRC")"
[ -d "$ROOT" ] || ROOT="."

# has PATTERN [DIR]  -> true if any file under DIR matches (content grep)
has() { grep -rIlqE "$1" "${2:-$SRC}" "$ROOT" 2>/dev/null \
        --include='*.toml' --include='*.py' --include='*.rs' --include='*.move' \
        --include='*.sol' --include='Cargo.toml' --include='Move.toml'; }
# fhas GLOB -> true if a file named GLOB exists within depth 3 of root or src
fhas() { { find "$ROOT" "$SRC" -maxdepth 3 -name "$1" 2>/dev/null | grep -q .; }; }
ext() { find "$SRC" -maxdepth 4 -name "$1" 2>/dev/null | grep -q .; }

LANGUAGE="" EVIDENCE="" L1=0

# --- evidence-ordered detection (most specific marker first) ---
if ext '*.move' && has 'sui::object|use sui::'; then
  LANGUAGE=sui; EVIDENCE="*.move + sui::object"
elif ext '*.move' && has 'aptos_framework|aptos_std'; then
  LANGUAGE=aptos; EVIDENCE="*.move + aptos_framework"
elif ext '*.move'; then
  LANGUAGE=aptos; EVIDENCE="*.move (framework unspecified — defaulting aptos; verify)"
elif ext '*.rs' && has 'soroban-sdk|soroban_sdk' && ! has 'solana-program|solana_program|anchor-lang|anchor_lang'; then
  LANGUAGE=stellar; EVIDENCE="*.rs + soroban-sdk (no solana/anchor)"
elif ext '*.rs' && { has 'anchor-lang|anchor_lang' || fhas 'Anchor.toml'; }; then
  LANGUAGE=solana; EVIDENCE="*.rs + anchor-lang/Anchor.toml"
elif ext '*.rs' && has 'solana-program|solana_program'; then
  LANGUAGE=solana; EVIDENCE="*.rs + solana-program"
elif ext '*.sol' && { fhas 'foundry.toml' || fhas 'hardhat.config.*'; }; then
  LANGUAGE=evm; EVIDENCE="*.sol + foundry/hardhat config"
elif ext '*.sol'; then
  LANGUAGE=evm; EVIDENCE="*.sol (no build config — verify)"
elif { ext '*.cpp' || ext '*.hpp' || ext '*.h' || ext '*.c'; } && { fhas 'CMakeLists.txt' || fhas 'conanfile.py'; }; then
  LANGUAGE=cpp; EVIDENCE="C/C++ sources + CMake/conan (native ledger node)"
elif { ext '*.go' || fhas 'go.mod'; }; then
  LANGUAGE=go; EVIDENCE="go.mod / *.go (L1 node client)"; L1=1
elif ext '*.rs'; then
  LANGUAGE=stellar; EVIDENCE="*.rs (no platform marker — defaulting stellar; VERIFY, may be solana/L1)"
else
  LANGUAGE=unknown; EVIDENCE="no recognized markers"
fi

# L1 (node-client) candidate signal — Go is always L1; Rust/C++ may be (Reth, rippled).
case "$LANGUAGE" in
  go) L1=1 ;;
  cpp) has 'rippled|Transactor::|CometBFT|bitcoin' && L1=1 ;;
  solana|stellar) has 'reth|erigon|consensus|validator-client|beacon' && L1=1 ;;
esac

# --- resolve the quirks file the orchestrator MUST load ---
case "$LANGUAGE" in
  evm)     QUIRKS="$SKILL/platform-quirks/solidity.md" ;;  # EVM/Solidity family defenses (v1.22.1)
  solana)  QUIRKS="$SKILL/platform-quirks/rust.md" ;;
  stellar) QUIRKS="$SKILL/platform-quirks/stellar.md" ;;
  sui)     QUIRKS="$SKILL/platform-quirks/sui.md" ;;
  aptos)   QUIRKS="$SKILL/platform-quirks/README.md" ;;    # no aptos file yet; README indexes
  cpp)     QUIRKS="$SKILL/platform-quirks/cpp.md" ;;
  go)      QUIRKS="$SKILL/platform-quirks/go.md" ;;
  *)       QUIRKS="NONE" ;;
esac
[ "$QUIRKS" = "NONE" ] || [ -f "$QUIRKS" ] || QUIRKS="$SKILL/platform-quirks/README.md"

if [ "$JSON" -eq 1 ]; then
  printf '{"language":"%s","quirks":"%s","evidence":"%s","l1_candidate":%s}\n' \
    "$LANGUAGE" "$QUIRKS" "$EVIDENCE" "$([ $L1 -eq 1 ] && echo true || echo false)"
else
  # Text mode is consumed via `eval "$(detect_language.sh ...)"` (see SKILL.md),
  # so every value must be single-quoted — EVIDENCE is free text and can contain
  # spaces, globs, and parentheses (e.g. "*.sol (no build config — verify)") that
  # would otherwise be a shell syntax error or glob-expand under eval.
  sq() { printf "'%s'" "${1//\'/\'\\\'\'}"; }
  echo "LANGUAGE=$(sq "$LANGUAGE")"
  echo "QUIRKS=$(sq "$QUIRKS")"
  echo "EVIDENCE=$(sq "$EVIDENCE")"
  echo "L1_CANDIDATE=$([ $L1 -eq 1 ] && echo yes || echo no)"
fi
