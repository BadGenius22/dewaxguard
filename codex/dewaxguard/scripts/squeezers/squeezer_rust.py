#!/usr/bin/env python3
"""Rust source minifier for LLM context packing.

Modes:
  default           — strip comments, blank-line-collapse, keep full bodies.
  --collapse-bodies — same, but replace each `fn ... { body }` body with `{ ... }`.
                      Brace-counted (handles nested `}` inside bodies, strings, chars).
  --numbered        — prepend 1-based line numbers to every output code line
                      (post-minification, so numbers map to what the LLM sees).
  --keep-full F,G   — comma-separated substring match; any input path that contains
                      one of these substrings bypasses --collapse-bodies and emits
                      its full body. Use for auth-critical files.

Attribution
-----------
Ported from cosminmarian53/skills (`soroban-auditor/scripts/soroban_token_squeezer.py`),
which is itself derived from Pashov's `skills`. Both upstream sources are MIT-licensed.
This file remains MIT — see UPSTREAM_LICENSE.txt.

dewaxguard adds:
- This module-level docstring, attribution, and the `--keep-full` recipe lookup
  driven by `rules/auth-critical-files.md` (when invoked from `build_recon_maps.sh`).
- The `[full-bodies]` / `[collapsed]` header tags consumed by `rules/auth-critical-files.md`
  and the breadth/depth agent prompts.
- Stable behavior on Solana programs (Anchor + native), not just Soroban — the
  brace-counter / string-escape logic is language-feature-agnostic Rust.
"""
import sys
import re
import argparse
from pathlib import Path


_FN_HEAD = re.compile(r'\bfn\s+[A-Za-z_][A-Za-z0-9_]*\s*(?:<[^{>]*>)?\s*\([^)]*\)(?:\s*->\s*[^ {]+(?:\s*<[^{>]*>)?)?\s*(?:where[^{]+)?\{')


def _skip_string(code: str, i: int) -> int:
    """Advance past a Rust string literal starting at code[i] == '\"'."""
    assert code[i] == '"'
    i += 1
    while i < len(code):
        c = code[i]
        if c == '\\':
            i += 2
            continue
        if c == '"':
            return i + 1
        i += 1
    return i


def _skip_char(code: str, i: int) -> int:
    """Advance past a Rust char literal starting at code[i] == \"'\" (best-effort).

    Also handles lifetimes like `'a` by returning i+1 when no closing ' found soon.
    """
    j = i + 1
    if j < len(code) and code[j] == '\\':
        j += 2
    else:
        j += 1
    if j < len(code) and code[j] == "'":
        return j + 1
    return i + 1  # lifetime, not a char literal


def _skip_raw_string(code: str, i: int) -> int:
    """Advance past r#"..."#-style raw strings. i points at 'r'."""
    j = i + 1
    hashes = 0
    while j < len(code) and code[j] == '#':
        hashes += 1
        j += 1
    if j >= len(code) or code[j] != '"':
        return i + 1
    j += 1
    term = '"' + ('#' * hashes)
    end = code.find(term, j)
    if end == -1:
        return len(code)
    return end + len(term)


def _collapse_fn_bodies(code: str) -> str:
    """Replace each function body `{ ... }` with `{ ... }` using brace counting.

    Scans for `fn <ident>(...)<ret>? {`. When the opening brace is found, walks
    forward with a brace counter that respects strings, chars, raw strings, and
    line/block comments.
    """
    out = []
    i = 0
    n = len(code)
    while i < n:
        m = _FN_HEAD.search(code, i)
        if not m:
            out.append(code[i:])
            break
        out.append(code[i:m.end() - 1])  # up to just before '{'
        out.append('{ ... }')
        depth = 1
        j = m.end()  # one past '{'
        while j < n and depth > 0:
            c = code[j]
            if c == '"':
                j = _skip_string(code, j)
                continue
            if c == "'":
                j = _skip_char(code, j)
                continue
            if c == 'r' and j + 1 < n and code[j + 1] in '#"':
                j = _skip_raw_string(code, j)
                continue
            if c == '/' and j + 1 < n and code[j + 1] == '/':
                nl = code.find('\n', j)
                j = n if nl == -1 else nl
                continue
            if c == '/' and j + 1 < n and code[j + 1] == '*':
                end = code.find('*/', j + 2)
                j = n if end == -1 else end + 2
                continue
            if c == '{':
                depth += 1
            elif c == '}':
                depth -= 1
                if depth == 0:
                    j += 1
                    break
            j += 1
        i = j
    return ''.join(out)


def squeeze_rust_code(code: str, collapse_bodies: bool = False) -> str:
    code = re.sub(r'/\*.*?\*/', '', code, flags=re.DOTALL)
    code = re.sub(r'(?<!:)//.*', '', code)
    code = re.sub(r'#\[doc\s*=\s*".*?"\]', '', code)
    code = re.sub(r'#!\[doc\s*=\s*".*?"\]', '', code)

    if '#[cfg(test)]' in code:
        parts = code.split('#[cfg(test)]')
        out_code = parts[0]
        for part in parts[1:]:
            mod_idx = part.find('mod ')
            if mod_idx != -1:
                brace_start = part.find('{', mod_idx)
                if brace_start != -1:
                    brace_count = 1
                    i = brace_start + 1
                    while i < len(part) and brace_count > 0:
                        if part[i] == '{':
                            brace_count += 1
                        elif part[i] == '}':
                            brace_count -= 1
                        i += 1
                    out_code += part[i:]
                    continue
            out_code += part
        code = out_code

    if collapse_bodies:
        code = _collapse_fn_bodies(code)

    code = re.sub(r'\n{3,}', '\n\n', code)
    return code.strip()


def _with_line_numbers(text: str) -> str:
    lines = text.split('\n')
    width = len(str(len(lines)))
    return '\n'.join(f"{str(i + 1).rjust(width)}: {line}" for i, line in enumerate(lines))


def main():
    parser = argparse.ArgumentParser(description="Minify Rust code for LLM token reduction.")
    parser.add_argument("file", nargs="+", help="Rust file(s) to process")
    parser.add_argument("--collapse-bodies", action="store_true",
                        help="Collapse function bodies to `{ ... }` (brace-counted).")
    parser.add_argument("--numbered", action="store_true",
                        help="Prefix each output line with its 1-based line number.")
    parser.add_argument("--keep-full", default="",
                        help="Comma-separated substrings; matching paths emit full bodies "
                             "even when --collapse-bodies is set. Use for auth-critical files.")

    args = parser.parse_args()
    keep_full_patterns = [p.strip() for p in args.keep_full.split(',') if p.strip()]

    for filepath in args.file:
        try:
            content = Path(filepath).read_text(encoding="utf-8")
            collapse = args.collapse_bodies and not any(p in filepath for p in keep_full_patterns)
            minified = squeeze_rust_code(content, collapse)
            if args.numbered:
                minified = _with_line_numbers(minified)
            tag = "[collapsed]" if collapse else "[full-bodies]"
            # The tag is consumed by rules/auth-critical-files.md — agents trust full
            # bodies and must Read collapsed files before claiming missing-guard bugs.
            marker = f" {tag}" if args.collapse_bodies else ""
            print(f"### path: {filepath}{marker}")
            print(f"```rust\n{minified}\n```\n")
        except Exception as e:
            print(f"Error reading {filepath}: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
