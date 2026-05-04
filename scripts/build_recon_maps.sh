#!/usr/bin/env bash
# build_recon_maps.sh — deterministic recon-artifact builder
#
# Emits the maps consumed by Phase 1 (Recon) and downstream breadth/depth/validator
# agents. Replaces ad-hoc per-agent grep work with a single deterministic pass that
# produces stable, greppable artifacts.
#
# Usage:
#   ./build_recon_maps.sh \
#       --lang   <evm|solana|stellar|aptos|sui|cpp> \
#       --src    <source root, e.g. ./contracts> \
#       --out    <scratchpad dir to receive the maps> \
#       [--docs  <docs root, default: ./docs and ./README.md>]
#
# Outputs (under $OUT):
#   guard-map.md          authorization surface (require_auth/onlyOwner/etc)
#   state-flags.md        every storage-backed flag that gates execution
#   integration-map.md    cross-contract / cross-program / cross-tx call sites
#   math-map.md           every fractional-scaling / division site
#   unsafe-map.md         unsafe blocks, raw pointers, repr(C), assembly
#   logic-anomaly-map.md  public-fn signatures for parameter-passthrough analysis
#   blackhat-maps.md      oracle + flash-loan + price feed surfaces
#   divergence-map.md     unified-diff of curated near-twin function pairs
#   invariant-extract.md  invariants harvested from fuzz/invariants.* / test files
#   docs-intent-map.md    pre-extracted "by design / intentional / out of scope"
#   auth-critical-files.txt  per-audit allowlist consumed by squeezers
#
# The artifact contracts and consumer rules are documented in:
#   rules/docs-intent-map.md
#   rules/auth-critical-files.md
#   rules/agent-tool-budgets.md
#
# Origin: ported from cosminmarian53/skills (`soroban-auditor/SKILL.md` recon block);
# generalized from Soroban/Rust to multi-language (evm/solana/stellar/aptos/sui/cpp).

set -euo pipefail

LANG_TARGET=""
SRC=""
OUT=""
DOCS=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --lang) LANG_TARGET="$2"; shift 2 ;;
        --src)  SRC="$2"; shift 2 ;;
        --out)  OUT="$2"; shift 2 ;;
        --docs) DOCS="$2"; shift 2 ;;
        -h|--help)
            sed -n '2,30p' "$0"; exit 0 ;;
        *) echo "Unknown arg: $1" >&2; exit 1 ;;
    esac
done

if [[ -z "$LANG_TARGET" || -z "$SRC" || -z "$OUT" ]]; then
    echo "usage: $0 --lang <evm|solana|stellar|aptos|sui|cpp> --src <dir> --out <dir> [--docs <dir>]" >&2
    exit 1
fi

mkdir -p "$OUT"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ----- per-language pattern banks ------------------------------------------------

case "$LANG_TARGET" in
    evm)
        EXT="sol"
        EXCLUDE_PATHS=( -not -path "*/node_modules/*" -not -path "*/lib/*" -not -path "*/out/*" -not -path "*/cache/*" -not -path "*/test/*" -not -name "*.t.sol" )
        GUARD_PAT='onlyOwner|onlyRole|onlyAdmin|onlyGovernance|require\s*\(\s*msg\.sender|require\s*\(\s*owner|hasRole|_checkRole|_checkOwner|whenNotPaused|whenPaused|nonReentrant|require\s*\(\s*tx\.origin'
        STATE_PAT='paused|frozen|initialized|isPaused|setPaused|whenNotPaused|emergencyShutdown|inEmergency|deprecated|blacklist|whitelist|killed'
        EXTERNAL_PAT='\.call\s*\(|\.delegatecall\s*\(|\.staticcall\s*\(|\.transfer\s*\(|\.send\s*\(|interface\s+\w+|IERC20|IUniswap|IChainlink'
        UNSAFE_PAT='assembly\s*\{|unchecked\s*\{|delegatecall|extcodesize|extcodecopy|selfdestruct|suicide|create2'
        MATH_PAT='\.mul\s*\(|\.div\s*\(|\.add\s*\(|\.sub\s*\(|FixedPointMath|fixedDiv|fixedMul|wadDiv|wadMul|rayDiv|rayMul|/\s*\d|\*\s*1e[0-9]+'
        ORACLE_PAT='latestAnswer|latestRoundData|getPrice|priceFeed|oracle|getReservesNative|TWAP|cumulativePrice|swapAmount'
        FLASH_PAT='flashLoan|flashLoanSimple|onFlashLoan|executeOperation|flashFee|maxFlashLoan|flashSwap|uniswapV2Call|uniswapV3FlashCallback'
        PUBFN_PAT='function\s+\w+'
        ;;
    solana)
        EXT="rs"
        EXCLUDE_PATHS=( -not -path "*/target/*" -not -path "*/tests/*" -not -path "*/fuzz/*" -not -name "*test*.rs" -not -name "*_mock.rs" )
        GUARD_PAT='Signer|has_one|constraint\s*=|owner\s*=\s*program_id|address\s*=|require_keys_eq|require!|require_eq!|require_neq!|require_gt!|access_control|#\[access_control'
        STATE_PAT='is_paused|is_initialized|is_frozen|paused|frozen|deprecated|blacklist|whitelist|killed|emergency'
        EXTERNAL_PAT='invoke\s*\(|invoke_signed\s*\(|CpiContext|cpi::|cross_program_invocation|associated_token::|spl_token::'
        UNSAFE_PAT='unsafe\s*\{|unsafe\s+fn|mem::transmute\b|\bptr::|\bfrom_raw\b|\bfrom_raw_parts\b|ManuallyDrop\b|uninitialized\(\)|\.set_len\(|#\[repr\(C\)\]'
        MATH_PAT='\.checked_div|\.checked_mul|\.checked_add|\.checked_sub|\.div\(|\.mul\(|wad_mul|wad_div|ray_mul|ray_div|percent_mul|/\s*\d|\*\s*10u'
        ORACLE_PAT='price_oracle|get_price|aggregator|pyth|switchboard|latest_round_data|update_price|chainlink'
        FLASH_PAT='flash_loan|flash_borrow|flash_repay|callback|execute_operation'
        PUBFN_PAT='pub fn |pub async fn '
        ;;
    stellar)
        EXT="rs"
        EXCLUDE_PATHS=( -not -path "*/target/*" -not -path "*/tests/*" -not -path "*/fuzz/*" -not -name "*test*.rs" -not -name "*_mock.rs" )
        GUARD_PAT='require_auth|validate_admin|is_authorized|only_admin|only_owner|admin\.require_auth|require_admin|__check_auth|PROTOCOL_LOCKED|ReentrancyGuard'
        STATE_PAT='is_paused|set_paused|is_frozen|set_frozen|is_initialized|set_initialized|PROTOCOL_LOCKED|blacklist|whitelist|deprecated|Paused|Frozen|Active'
        EXTERNAL_PAT='try_invoke_contract|invoke_contract|authorize_as_current_contract|env\.invoke|env\.try_invoke'
        UNSAFE_PAT='unsafe\s*\{|unsafe\s+fn|mem::transmute\b|\bptr::|\bfrom_raw\b|\bfrom_raw_parts\b|ManuallyDrop\b|uninitialized\(\)|\.set_len\(|#\[repr\(C\)\]'
        MATH_PAT='wad_mul|wad_div|ray_mul|ray_div|percent_mul|percent_mul_up|\.checked_div|\.checked_mul|\.div\(|U256::'
        ORACLE_PAT='get_price|update_price|price_oracle|reflector|aggregator|circuit_breaker|fallback_price'
        FLASH_PAT='flash_loan|flash_loan_simple|flash_liquidation|flash_callback|prepare_liquidation|execute_liquidation'
        PUBFN_PAT='pub fn |#\[contractimpl\]'
        ;;
    aptos|sui)
        EXT="move"
        EXCLUDE_PATHS=( -not -path "*/build/*" -not -path "*/tests/*" )
        GUARD_PAT='assert!|assert_eq!|require!|signer::address_of|signer\s*\)|AdminCap|OwnerCap|UpgradeCap|TreasuryCap|Capability'
        STATE_PAT='is_paused|paused|frozen|initialized|deprecated|killed|emergency|halt'
        EXTERNAL_PAT='public fun |public entry fun |dispatchable_fungible_asset|object::transfer|transfer::public_transfer'
        UNSAFE_PAT='native fun '
        MATH_PAT='math::|fixed_point|/\s*\d|\*\s*\d{4,}|mul_div|safe_mul|safe_div'
        ORACLE_PAT='price|oracle|aggregator|pyth|switchboard'
        FLASH_PAT='flash_loan|flash_borrow|flash_repay|hot_potato'
        PUBFN_PAT='public fun |public entry fun |fun '
        ;;
    cpp)
        EXT="cpp"
        EXCLUDE_PATHS=( -not -path "*/build/*" -not -path "*/test/*" -not -path "*/tests/*" -not -name "*_test.cpp" )
        GUARD_PAT='preflight|preclaim|doApply|checkSign|requireAuth|checkAuth|isAuthorized|hasPermission|require\s*\('
        STATE_PAT='paused|frozen|initialized|deprecated|emergency|halt'
        EXTERNAL_PAT='view\.peek|view\.read|view\.write|sb\.|env\.|TER\s+'
        UNSAFE_PAT='reinterpret_cast|const_cast|memcpy|memmove|alloca|union\s'
        MATH_PAT='div|mul|/\s*\d|\*\s*\d|safe_cast'
        ORACLE_PAT='price|oracle|feed|aggregator'
        FLASH_PAT='flash|atomic|reentrancy'
        PUBFN_PAT='void |bool |int |TER\s+'
        ;;
    *)
        echo "unknown --lang: $LANG_TARGET" >&2; exit 1 ;;
esac

DOCS_ROOT="${DOCS:-.}"

find_src() {
    # Forwards extra args (e.g. -print0) to find. Without args, defaults to newline.
    find "$SRC" -type f -name "*.${EXT}" "${EXCLUDE_PATHS[@]}" "$@" 2>/dev/null
}

# (a) guard-map ----------------------------------------------------------------
{
    echo "# Guard Map (authorization surface) — lang=$LANG_TARGET"
    echo
    echo "Every authorization / admin-gate / role-check site in in-scope source."
    echo "If claiming 'missing auth' on a function, GREP THIS FILE FIRST."
    echo "Per rules/auth-critical-files.md, finding must record auth_check."
    echo
    echo '```'
    { find_src -print0 | xargs -0 grep -nE "$GUARD_PAT" 2>/dev/null || true; } | head -800
    echo '```'
} > "$OUT/guard-map.md"

# (b) state-flags --------------------------------------------------------------
{
    echo "# State Flags Map — lang=$LANG_TARGET"
    echo
    echo "Every storage-backed flag that gates function execution."
    echo
    echo '```'
    { find_src -print0 | xargs -0 grep -nE "$STATE_PAT" 2>/dev/null || true; } | head -500
    echo '```'
} > "$OUT/state-flags.md"

# (c) integration-map ----------------------------------------------------------
{
    echo "# Integration Map (cross-contract call sites) — lang=$LANG_TARGET"
    echo
    echo "Every cross-contract / cross-program call site with ±3 lines of context."
    echo "Validate arg order, return-value usage, error drops."
    echo
    { find_src -print0 | xargs -0 grep -nE -B2 -A6 "$EXTERNAL_PAT" 2>/dev/null || true; } | head -1000
} > "$OUT/integration-map.md"

# (d) unsafe-map ---------------------------------------------------------------
{
    echo "# Unsafe & Memory Surface — lang=$LANG_TARGET"
    echo
    MATCHES=$({ find_src -print0 | xargs -0 grep -nE "$UNSAFE_PAT" 2>/dev/null || true; } | head -200)
    if [[ -z "$MATCHES" ]]; then
        echo "_No unsafe blocks / raw pointer ops / FFI reprs detected. Memory-corruption attack surface is effectively nil for this codebase — focus elsewhere._"
    else
        echo '```'
        echo "$MATCHES"
        echo '```'
        echo
        echo "**Every site above warrants direct audit.** A non-empty list is a yellow flag."
    fi
} > "$OUT/unsafe-map.md"

# (e) math-map -----------------------------------------------------------------
{
    echo "# Math & Precision Map — lang=$LANG_TARGET"
    echo
    echo "Every use of fractional scaling or explicit division. Inspect for"
    echo "WAD/RAY precision mismatches, division-before-multiplication, and"
    echo "rounding-direction asymmetry."
    echo
    echo '```'
    { find_src -print0 | xargs -0 grep -nE "$MATH_PAT" 2>/dev/null || true; } | head -500
    echo '```'
} > "$OUT/math-map.md"

# (f) logic-anomaly-map (parameter passthrough) -------------------------------
{
    echo "# Logic Anomaly Map (Parameter Passthrough) — lang=$LANG_TARGET"
    echo
    echo "Public function signatures. Track parameters that exist in a wrapper"
    echo "but are silently dropped or hardcoded when the wrapper calls an"
    echo "internal engine. (Cf. M19 — path-selection determinism × asymmetry.)"
    echo
    echo '```'
    { find_src -print0 | xargs -0 grep -nE "$PUBFN_PAT" 2>/dev/null || true; } | head -800
    echo '```'
} > "$OUT/logic-anomaly-map.md"

# (g) blackhat-maps (oracle + flash) ------------------------------------------
{
    echo "# Blackhat Targeting Maps — lang=$LANG_TARGET"
    echo
    echo "## Oracle Trust Map"
    echo '```'
    { find_src -print0 | xargs -0 grep -nE -B1 -A2 "$ORACLE_PAT" 2>/dev/null || true; } | head -400
    echo '```'
    echo
    echo "## Flash Loan / Atomic Composition Map"
    echo '```'
    { find_src -print0 | xargs -0 grep -nE -B1 -A3 "$FLASH_PAT" 2>/dev/null || true; } | head -400
    echo '```'
} > "$OUT/blackhat-maps.md"

# (h) divergence-map (curated twin pairs) -------------------------------------
python3 - "$LANG_TARGET" "$SRC" "$EXT" "$OUT" << 'PYDIV'
import os, sys, re, subprocess, difflib
from pathlib import Path

lang, src_root, ext, out_dir = sys.argv[1:5]

# Curated near-twins — lending/DEX/staking/lifecycle pairs known to diverge in
# practice. Per-language naming. Add per-protocol pairs in $OUT/divergence-pairs.txt
# (one `a,b` per line) for repo-specific augmentation.
PAIRS = {
    "evm": [
        ("supply", "supplyOnBehalf"), ("deposit", "depositFor"),
        ("withdraw", "withdrawOnBehalf"), ("borrow", "borrowOnBehalf"),
        ("repay", "repayOnBehalf"), ("liquidationCall", "liquidate"),
        ("flashLoan", "flashLoanSimple"), ("transfer", "transferFrom"),
    ],
    "solana": [
        ("deposit", "deposit_for"), ("withdraw", "withdraw_for"),
        ("transfer", "transfer_with_fee"), ("initialize", "initialize_v2"),
    ],
    "stellar": [
        ("supply", "supply_on_behalf"), ("deposit", "deposit_on_behalf"),
        ("withdraw", "withdraw_on_behalf"), ("borrow", "borrow_on_behalf"),
        ("repay", "repay_on_behalf"), ("repay", "repay_with_a_tokens"),
        ("liquidation_call", "internal_liquidation_call"),
        ("prepare_liquidation", "execute_liquidation"),
        ("flash_loan", "flash_loan_simple"),
    ],
    "aptos": [
        ("deposit", "deposit_for"), ("withdraw", "withdraw_for"),
        ("transfer", "transfer_to"),
    ],
    "sui": [
        ("deposit", "deposit_for"), ("withdraw", "withdraw_for"),
        ("transfer", "public_transfer"),
    ],
    "cpp": [
        ("preflight", "preclaim"), ("doApply", "doApplyChild"),
    ],
}.get(lang, [])

# Repo-augmented pairs
extra_path = Path(out_dir) / "divergence-pairs.txt"
if extra_path.exists():
    for line in extra_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "," in line:
            a, b = [s.strip() for s in line.split(",", 1)]
            PAIRS.append((a, b))

if lang in ("solana", "stellar"):
    fn_kw = "fn"
elif lang in ("aptos", "sui"):
    fn_kw = "fun"
elif lang == "cpp":
    fn_kw = "TER|void|bool|int"
else:
    fn_kw = "function"

def find_fn(name: str):
    pattern = rf"\b({fn_kw})\s+{re.escape(name)}\b"
    out = subprocess.run(
        ["grep", "-rnE", pattern, src_root],
        capture_output=True, text=True,
    )
    bad = ("/target/", "/tests/", "/fuzz/", "/build/", "/node_modules/", "/lib/", "/cache/", "/out/")
    return [ln for ln in out.stdout.splitlines() if not any(b in ln for b in bad)]

def body(path: str, start_line: int, max_lines: int = 250):
    try:
        src = Path(path).read_text(errors="ignore").splitlines()
    except Exception:
        return []
    i = start_line - 1
    depth = 0
    started = False
    out = []
    while i < len(src) and i - start_line < max_lines:
        line = src[i]
        out.append(line)
        for c in line:
            if c == "{":
                depth += 1
                started = True
            elif c == "}":
                depth -= 1
        i += 1
        if started and depth == 0:
            break
    return out

emitted = 0
buf = ["# Divergence Map", "",
       f"_Curated near-twin function pairs for lang={lang}, diffed via difflib.unified_diff._",
       ""]
for a, b in PAIRS:
    la = find_fn(a); lb = find_fn(b)
    if not la or not lb:
        continue
    pa = la[0].split(":", 2)
    pb = lb[0].split(":", 2)
    if len(pa) < 2 or len(pb) < 2:
        continue
    try:
        ba = body(pa[0], int(pa[1]))
        bb = body(pb[0], int(pb[1]))
    except Exception:
        continue
    diff = list(difflib.unified_diff(
        ba, bb,
        fromfile=f"{pa[0]}:{pa[1]}",
        tofile=f"{pb[0]}:{pb[1]}",
        lineterm="", n=2,
    ))
    if len(diff) < 3:
        continue
    buf.append(f"## {a}  vs  {b}")
    buf.append("")
    buf.append("```diff")
    buf.extend(diff[:120])
    buf.append("```")
    buf.append("")
    emitted += 1

if emitted == 0:
    buf.append("_No near-twin pairs resolved for this repo._")

Path(out_dir, "divergence-map.md").write_text("\n".join(buf))
PYDIV

# (i) invariant-extract --------------------------------------------------------
{
    echo "# Protocol-Declared Invariants — lang=$LANG_TARGET"
    echo
    echo "Extracted from the protocol's own fuzz / property-test / invariant"
    echo "modules. These are the invariants the protocol itself believes must"
    echo "hold — attack them directly."
    echo
    FOUND=0
    case "$LANG_TARGET" in
        solana|stellar)
            for f in $(find "$SRC" -type f \( -path "*/fuzz/*invariant*.rs" -o -path "*/fuzz/*properties*.rs" -o -name "*invariants*.rs" \) 2>/dev/null); do
                FOUND=1
                echo; echo "## $f"; echo
                echo '```rust'; sed -n '1,300p' "$f"; echo '```'
            done ;;
        evm)
            for f in $(find "$SRC" -type f \( -name "*invariant*.t.sol" -o -name "*Invariant*.sol" \) 2>/dev/null); do
                FOUND=1
                echo; echo "## $f"; echo
                echo '```solidity'; sed -n '1,300p' "$f"; echo '```'
            done ;;
        aptos|sui)
            for f in $(find "$SRC" -type f -name "*invariant*.move" 2>/dev/null); do
                FOUND=1
                echo; echo "## $f"; echo
                echo '```move'; sed -n '1,300p' "$f"; echo '```'
            done ;;
        cpp)
            for f in $(grep -rlE "MPTInvariant::visit|InvariantChecker|class\s+\w*Invariant" "$SRC" 2>/dev/null | head -20); do
                FOUND=1
                echo; echo "## $f"; echo
                echo '```cpp'; sed -n '1,300p' "$f"; echo '```'
            done ;;
    esac
    if [[ "$FOUND" == "0" ]]; then
        echo "_No invariant module found in the repo._"
    fi
} > "$OUT/invariant-extract.md"

# (j) docs-intent-map ----------------------------------------------------------
# Per rules/docs-intent-map.md.
{
    echo "# Documented Intent Map"
    echo
    echo "Pre-extracted 'by design' / 'intentional' / 'accepted trade-off' /"
    echo "'out of scope' signals. Phase 5d Gate 1a hard-fails any finding"
    echo "without docs_intent_check populated."
    echo
    INTENT_PAT='by design|intentional|internal helper|not for direct|expected behavio|on purpose|deliberately|accepted trade.?off|known limitation|out of scope|documented exception|this is fine|note:.*always'
    DOCS_FOUND=0
    for f in $(find "$DOCS_ROOT" -type f -name '*.md' \
                  \( -path '*/docs/*' -o -name 'README*.md' -o -name '*security*.md' -o -name '*architecture*.md' -o -name '*spec*.md' -o -name '*invariant*.md' -o -name '*design*.md' \) \
                  -not -path '*/target/*' -not -path '*/node_modules/*' -not -path '*/skills/*' 2>/dev/null); do
        MATCHES=$(grep -nEi -B1 -A3 "$INTENT_PAT" "$f" 2>/dev/null || true)
        if [[ -n "$MATCHES" ]]; then
            DOCS_FOUND=1
            echo "## $f"
            echo
            echo '```'
            echo "$MATCHES" | head -200
            echo '```'
            echo
        fi
    done
    if [[ "$DOCS_FOUND" == "0" ]]; then
        echo "_No documented intent signals found._"
    fi
} > "$OUT/docs-intent-map.md"

# (k) auth-critical-files allowlist -------------------------------------------
# Per rules/auth-critical-files.md. Substrings that flag a file as auth-critical.
AUTH_SUBSTRINGS='admin|access_control|access-control|auth|authorize|authorization|emergency|upgrade|ownable|ownership|multisig|governance|permissions|roles|rbac|acl'
{
    { find_src 2>/dev/null | grep -iE "$AUTH_SUBSTRINGS" || true; } | sort -u
    case "$LANG_TARGET" in
        evm)
            { find_src 2>/dev/null | grep -E "(Ownable|AccessControl|Pausable|TimelockController|Governor|Permit)\.sol$" || true; } | sort -u ;;
        stellar)
            { find_src 2>/dev/null | grep -E "(token|a-token|debt-token|pool-configurator)/src/contract\.rs$" || true; } | sort -u ;;
        solana)
            { find_src 2>/dev/null | grep -E "(instructions/admin|instructions/initialize|state/config|state/admin)" || true; } | sort -u ;;
        aptos|sui)
            { find_src 2>/dev/null | grep -iE "(governance|admin|access_control|capabilit)" || true; } | sort -u ;;
        cpp)
            { find_src 2>/dev/null | grep -iE "(Transactor|Permissions)" || true; } | sort -u ;;
    esac
} | sort -u > "$OUT/auth-critical-files.txt"

echo "build_recon_maps.sh done — lang=$LANG_TARGET, out=$OUT"
echo "  artifacts:"
ls -1 "$OUT" | sed 's/^/    /'
