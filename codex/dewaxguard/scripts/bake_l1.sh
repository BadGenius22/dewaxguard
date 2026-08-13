#!/usr/bin/env bash
# bake_l1.sh — Phase 0.5 "Bake" step for L1 node-client audits (v1.14+).
#
# Runs ast-grep / opengrep / ripgrep against Go (and Rust, where supported) source
# to extract:
#   - consensus state machine transitions
#   - non-deterministic calls (time.Now, map iteration, floating-point, RNG)
#   - slashing conditions
#   - validator lifecycle (activation / exit / withdrawal)
#   - p2p message handlers
#   - RPC methods with auth annotations
#   - mempool admission predicates
#   - peer scoring rules
#
# Outputs land under {{SCRATCHPAD}}/bake/. The L1 depth agents (depth-consensus-
# invariant + depth-network-surface) read these artifacts to focus their analysis.
#
# Tool fallback ladder: ast-grep -> opengrep -> ripgrep -> standard grep. Each
# rung gradually loses semantic precision but always emits SOMETHING.
#
# Usage:
#   bake_l1.sh --src <path> --out <scratchpad>/bake [--lang go|rust]
#
# Exit codes:
#   0 — bake completed (possibly with tool-fallback warnings)
#   1 — invalid arguments OR --src not found
#   2 — no tools available (not even grep) — pathological environment
set -euo pipefail

SRC=""
OUT=""
BAKE_LANG="go"
VERBOSE=0

while [[ $# -gt 0 ]]; do
    case "$1" in
        --src) SRC="$2"; shift 2 ;;
        --out) OUT="$2"; shift 2 ;;
        --lang) BAKE_LANG="$2"; shift 2 ;;
        --verbose) VERBOSE=1; shift ;;
        -h|--help)
            sed -n '1,30p' "$0" | sed 's/^# \?//'
            exit 0
            ;;
        *) echo "bake_l1: unknown arg: $1" >&2; exit 1 ;;
    esac
done

if [[ -z "$SRC" || -z "$OUT" ]]; then
    echo "bake_l1: --src and --out are required" >&2
    exit 1
fi
if [[ ! -d "$SRC" ]]; then
    echo "bake_l1: --src not found: $SRC" >&2
    exit 1
fi
mkdir -p "$OUT"

log() { [[ $VERBOSE -eq 1 ]] && echo "[bake] $*" >&2 || true; }
note() { echo "[bake] $*" >&2; }

# Tool detection
HAVE_AST_GREP=0
HAVE_OPENGREP=0
HAVE_RIPGREP=0
HAVE_GREP=1   # standard grep is part of POSIX
command -v ast-grep >/dev/null 2>&1 && HAVE_AST_GREP=1
command -v opengrep >/dev/null 2>&1 && HAVE_OPENGREP=1
command -v rg >/dev/null 2>&1 && HAVE_RIPGREP=1

# Selection reflects what run_pattern actually uses: ast-grep (AST) > ripgrep
# (regex) > grep. opengrep is detected for the summary but not used for these
# PCRE-style regex patterns (semgrep won't accept them) — see run_pattern.
TOOL="grep"
[[ $HAVE_RIPGREP -eq 1 ]] && TOOL="rg"
[[ $HAVE_AST_GREP -eq 1 ]] && TOOL="ast-grep"

note "tool selected: $TOOL (ast-grep=$HAVE_AST_GREP opengrep=$HAVE_OPENGREP rg=$HAVE_RIPGREP)"
note "src: $SRC"
note "out: $OUT"
note "lang: $BAKE_LANG"

# ────────────────────────────────────────────────────────────────────────────
# Helper: run pattern via the best tool, emit normalized FILE:LINE:MATCH lines.
# Args: $1=pattern_label   $2=ast_grep_pattern   $3=fallback_grep_pattern
# ────────────────────────────────────────────────────────────────────────────
run_pattern() {
    local label="$1"
    local agp="$2"   # ast-grep pattern
    local rgp="$3"   # ripgrep PCRE pattern (uses \s, \w, \b)
    log "running pattern: $label"

    if [[ $HAVE_AST_GREP -eq 1 && -n "$agp" ]]; then
        ast-grep --lang "$BAKE_LANG" --pattern "$agp" "$SRC" 2>/dev/null || true
    elif [[ $HAVE_RIPGREP -eq 1 ]]; then
        # ripgrep uses Rust regex syntax — supports \s, \w, \b natively.
        # NOTE: the pattern goes after -e; `-E` is ripgrep's --encoding flag, not
        # extended-regex, and would consume the pattern as an encoding name.
        rg --type "$BAKE_LANG" -n -e "$rgp" "$SRC" 2>/dev/null || true
    else
        # opengrep/semgrep is intentionally skipped here: these rungs use PCRE-style
        # regex patterns, which semgrep does not accept as -e patterns, so it would
        # error and emit nothing. Regex patterns fall through to grep below.
        # POSIX grep — translate Perl-style escapes to POSIX equivalents
        local posix_pat="$rgp"
        posix_pat="${posix_pat//\\s/[[:space:]]}"
        posix_pat="${posix_pat//\\w/[[:alnum:]_]}"
        posix_pat="${posix_pat//\\b/}"   # POSIX has no \b; drop and accept some imprecision
        local ext="*.go"
        [[ "$BAKE_LANG" == "rust" ]] && ext="*.rs"
        # Use -P if available for PCRE; else fall back to the translated POSIX pattern
        if echo a | grep -P 'a' >/dev/null 2>&1; then
            grep -Prn --include="$ext" "$rgp" "$SRC" 2>/dev/null || true
        else
            grep -rn -E --include="$ext" "$posix_pat" "$SRC" 2>/dev/null || true
        fi
    fi
}

# ────────────────────────────────────────────────────────────────────────────
# Section 1 — Non-deterministic calls (HIGH-VALUE for consensus audits)
# ────────────────────────────────────────────────────────────────────────────
{
    echo "# Non-deterministic calls (consensus-relevant only)"
    echo ""
    echo "> Every match is a candidate. The depth-consensus-invariant agent must verify whether the call is in a consensus-relevant path."
    echo ""

    echo "## time.Now() / wall-clock reads"
    echo '```'
    run_pattern "time.Now" 'time.Now()' 'time\.Now\(\)|time\.Since\('
    echo '```'
    echo ""

    echo "## map range (iteration order is non-deterministic in Go)"
    echo '```'
    run_pattern "map-range" '' 'for\s+[a-zA-Z_,\s]+\s*:=\s*range\s+[a-zA-Z_.]+\s*{'
    echo '```'
    echo ""

    echo "## floating-point arithmetic"
    echo '```'
    run_pattern "float-arith" '' 'float(32|64)'
    echo '```'
    echo ""

    echo "## RNG calls (math/rand, crypto/rand)"
    echo '```'
    run_pattern "rng" '' 'rand\.\w+\(|crypto/rand'
    echo '```'
    echo ""

    echo "## goroutine spawning (potential leak or scheduling-order dependency)"
    echo '```'
    run_pattern "go-func" 'go $$$' 'go\s+(func|[a-zA-Z_.]+\()'
    echo '```'
    echo ""
} > "$OUT/non_deterministic_calls.md"

# ────────────────────────────────────────────────────────────────────────────
# Section 2 — Consensus state machine transitions
# ────────────────────────────────────────────────────────────────────────────
{
    echo "# Consensus state machine — transitions and validation"
    echo ""

    echo "## State transition functions"
    echo "(Functions named ProcessBlock / ApplyBlock / ProcessTx / EndBlock / BeginBlock / OnVote / OnProposal)"
    echo '```'
    run_pattern "transitions" '' 'func\s+.*\b(ProcessBlock|ApplyBlock|ProcessTx|EndBlock|BeginBlock|OnVote|OnProposal|StateTransition|ApplyTransaction|ExecuteBlock|ImportBlock)\b'
    echo '```'
    echo ""

    echo "## Fork-choice rules"
    echo '```'
    run_pattern "fork-choice" '' 'func\s+.*\b(ForkChoice|GetHead|FindBestChain|SelectFork|HeadBlock)\b'
    echo '```'
    echo ""

    echo "## Finality / justification"
    echo '```'
    run_pattern "finality" '' '(Finalize|Justif|FinalizedCheckpoint|FinalityFork)'
    echo '```'
    echo ""

    echo "## Block validation"
    echo '```'
    run_pattern "validate-block" '' 'func\s+.*\b(ValidateBlock|VerifyBlock|VerifyHeader|VerifyBody|CheckBlock)\b'
    echo '```'
} > "$OUT/consensus_state_machine.md"

# ────────────────────────────────────────────────────────────────────────────
# Section 3 — Slashing conditions
# ────────────────────────────────────────────────────────────────────────────
{
    echo "# Slashing conditions"
    echo ""
    echo "> Every match is a slashing rule. Verify SOUND / COMPLETE / PRIVATE / EFFICIENT per the 4-question slashing matrix in depth-consensus-invariant."
    echo ""

    echo "## Slashing functions"
    echo '```'
    run_pattern "slashing" '' 'func\s+.*\b(Slash|HandleEquivocation|DoubleSign|DetectMisbehavior|EvidenceHandler)\b'
    echo '```'
    echo ""

    echo "## Evidence handling"
    echo '```'
    run_pattern "evidence" '' '\b(Evidence|FraudProof|DoubleVote|DoubleProposal|Surround)\b'
    echo '```'
} > "$OUT/slashing_conditions.md"

# ────────────────────────────────────────────────────────────────────────────
# Section 4 — Validator lifecycle
# ────────────────────────────────────────────────────────────────────────────
{
    echo "# Validator lifecycle"
    echo ""
    echo "> Activation, exit, withdrawal sequencing. Bugs here typically manifest as reward miscalculation or pending-slashing race."
    echo ""

    echo "## Activation"
    echo '```'
    run_pattern "activation" '' '\b(Activat|Bond|Deposit|RegisterValidator|StakeTo)\b'
    echo '```'
    echo ""

    echo "## Exit / withdrawal"
    echo '```'
    run_pattern "exit" '' '\b(Exit|Unbond|Withdraw|Undelegate|UnstakeFrom)\b'
    echo '```'
} > "$OUT/validator_lifecycle.md"

# ────────────────────────────────────────────────────────────────────────────
# Section 5 — p2p message handlers
# ────────────────────────────────────────────────────────────────────────────
{
    echo "# p2p message handlers"
    echo ""
    echo "> Every match is an entry point for peer-controlled input. The depth-network-surface agent must verify resource bounds and auth on each."
    echo ""

    echo "## Handler functions"
    echo '```'
    run_pattern "p2p-handlers" '' 'func\s+.*\b(HandleMessage|OnMessage|HandlePeer|HandleStream|OnNewBlock|OnNewTransaction|HandleRequest|HandleGossip)\b'
    echo '```'
    echo ""

    echo "## libp2p stream handlers"
    echo '```'
    run_pattern "libp2p-streams" '' '(SetStreamHandler|RegisterProtocol|HandleStream|NewStream)'
    echo '```'
    echo ""

    echo "## Gossipsub topic subscriptions"
    echo '```'
    run_pattern "gossipsub" '' '(Subscribe|JoinTopic|TopicValidator|RegisterTopicValidator)'
    echo '```'
} > "$OUT/p2p_message_handlers.md"

# ────────────────────────────────────────────────────────────────────────────
# Section 6 — RPC methods + auth annotations
# ────────────────────────────────────────────────────────────────────────────
{
    echo "# RPC methods and authentication annotations"
    echo ""
    echo "> Every public RPC method is an entry point. Verify auth requirement matches the method's privilege level."
    echo ""

    echo "## RPC method registrations"
    echo '```'
    run_pattern "rpc-register" '' '(RegisterMethod|RegisterRPC|JSONRPCService|RegisterService|RPCRegister|RegisterAPI|jsonrpc\.RegisterName)'
    echo '```'
    echo ""

    echo "## Method definitions (likely RPC handlers)"
    echo '```'
    run_pattern "rpc-methods" '' 'func\s+\(.*\)\s+\b(Get|Set|List|Send|Subscribe|Call|Eth|Net|Web3|Debug|Admin|Miner|Personal)[A-Z]\w+\('
    echo '```'
    echo ""

    echo "## HTTP handlers (potential RPC routes)"
    echo '```'
    run_pattern "http-handlers" '' '(http\.HandleFunc|mux\.Handle|router\.\w+\(|HandlerFunc)'
    echo '```'
    echo ""

    echo "## Auth checks (look for missing ones)"
    echo '```'
    run_pattern "auth-checks" '' '(checkAuth|RequireAuth|isAdmin|isLocal|jwt\.Parse|Authenticate)'
    echo '```'
} > "$OUT/rpc_methods.md"

# ────────────────────────────────────────────────────────────────────────────
# Section 7 — Mempool admission
# ────────────────────────────────────────────────────────────────────────────
{
    echo "# Mempool admission predicates"
    echo ""
    echo "> The function that decides whether a tx enters the mempool. DoS vectors live here."
    echo ""

    echo "## Mempool entry functions"
    echo '```'
    run_pattern "mempool-add" '' 'func\s+.*\b(AddTx|AddTransaction|Enqueue|InsertTx|Admit|CheckTx|MempoolValidate|Pool\.Add)\b'
    echo '```'
    echo ""

    echo "## Per-sender quotas"
    echo '```'
    run_pattern "per-sender" '' '(MaxAccountQueue|MaxAccountSlots|perSender|PerAccount|TxByAccount)'
    echo '```'
    echo ""

    echo "## Fee floor / priority"
    echo '```'
    run_pattern "fee-floor" '' '(MinGasPrice|PriceLimit|FeeFloor|MinFee|BaseFee)'
    echo '```'
} > "$OUT/mempool_admission.md"

# ────────────────────────────────────────────────────────────────────────────
# Section 8 — Peer scoring rules
# ────────────────────────────────────────────────────────────────────────────
{
    echo "# Peer scoring rules"
    echo ""
    echo "> Score-change events and the conditions that trigger them. Check symmetry (can a peer drive their own score?)."
    echo ""

    echo "## Score change events"
    echo '```'
    run_pattern "scoring" '' '(PeerScore|UpdateScore|RecordScore|ApplyScore|PenalizePeer|BanPeer|DisconnectPeer)'
    echo '```'
    echo ""

    echo "## libp2p scoring parameters"
    echo '```'
    run_pattern "libp2p-score" '' '(PeerScoringParams|TopicScoreParams|InvalidMessageDeliveriesWeight)'
    echo '```'
} > "$OUT/peer_scoring_rules.md"

# ────────────────────────────────────────────────────────────────────────────
# Summary
# ────────────────────────────────────────────────────────────────────────────
{
    echo "# L1 Bake Summary — $(date -u +%Y-%m-%dT%H:%M:%SZ)"
    echo ""
    echo "**Source**: $SRC"
    echo "**Language**: $BAKE_LANG"
    echo "**Tool selected**: $TOOL"
    echo "**Tool availability**: ast-grep=$HAVE_AST_GREP opengrep=$HAVE_OPENGREP rg=$HAVE_RIPGREP"
    echo ""
    echo "## Artifacts emitted"
    echo ""
    for f in non_deterministic_calls consensus_state_machine slashing_conditions validator_lifecycle p2p_message_handlers rpc_methods mempool_admission peer_scoring_rules; do
        local_size=0
        if [[ -f "$OUT/$f.md" ]]; then
            local_size=$(wc -c < "$OUT/$f.md")
        fi
        echo "- \`$f.md\` ($local_size bytes)"
    done
    echo ""
    echo "## Consumer mapping"
    echo ""
    echo "| Artifact | Consumed by |"
    echo "|----------|-------------|"
    echo "| non_deterministic_calls.md | depth-consensus-invariant |"
    echo "| consensus_state_machine.md | depth-consensus-invariant |"
    echo "| slashing_conditions.md | depth-consensus-invariant (slashing matrix step 5) |"
    echo "| validator_lifecycle.md | depth-consensus-invariant (lifecycle race step 6) |"
    echo "| p2p_message_handlers.md | depth-network-surface |"
    echo "| rpc_methods.md | depth-network-surface (auth ladder step 4) |"
    echo "| mempool_admission.md | depth-network-surface |"
    echo "| peer_scoring_rules.md | depth-network-surface (scoring symmetry step 3) |"
    echo ""
    if [[ $HAVE_AST_GREP -eq 0 ]]; then
        echo "## ⚠️ Tool fallback note"
        echo ""
        echo "ast-grep is NOT installed. Patterns ran via $TOOL (regex-only). Semantic precision is reduced — expect more false positives in the bake output. Install ast-grep for AST-aware matching: \`brew install ast-grep\` or \`cargo install ast-grep\`."
    fi
} > "$OUT/_bake_summary.md"

note "bake complete — 8 artifacts + summary written to $OUT/"
exit 0
