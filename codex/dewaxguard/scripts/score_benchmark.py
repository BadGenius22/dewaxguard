#!/usr/bin/env python3
"""score_benchmark.py — mechanically score a blind benchmark run against ground truth.

Input: the agent's raw output text (must contain `FINDING | sev | file:lines | class | desc`
lines per the breadth output format) and the benchmark's ground-truth.json.

Scoring:
  - DETECTION: each must_detect ground-truth finding counts as FOUND if any FINDING
    line overlaps its location window (same file, line ranges within ±FUZZ) OR the
    finding's class token appears in the GT class/description. Else MISSED.
  - PRECISION: each false_positive_trap counts as TRIGGERED if any FINDING line lands
    inside the trap's location window. Else CLEAN.
  - SEVERITY: for each FOUND finding, compares reported vs expected severity tier and
    reports the signed tier delta (over-escalation is positive).

Exit 0 if recall==100% AND no traps triggered, else 1 (so it can gate CI).

Usage: score_benchmark.py <agent_output.txt> <ground-truth.json> [--fuzz N] [--json]
"""
import json, re, sys, argparse

TIERS = {"informational": 0, "info": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}
FINDING_RE = re.compile(
    # sev | title | class, where class may be the last field (no trailing pipe)
    r"^\s*FINDING\s*\|\s*([A-Za-z]+)\s*\|\s*([^|]+?)\s*\|\s*([^|]*?)\s*(?:\||$)", re.I | re.M)
LOC_RE = re.compile(r"([\w./-]+?\.\w+)\s*[:#]?\s*L?(\d+)\s*[-–]\s*L?(\d+)")
LOC_SINGLE_RE = re.compile(r"([\w./-]+?\.\w+)\s*[:#]\s*L?(\d+)")


def parse_findings(text):
    out = []
    for m in FINDING_RE.finditer(text):
        sev, loc, cls = m.group(1), m.group(2), m.group(3)
        f, a, b = None, None, None
        lm = LOC_RE.search(loc) or LOC_SINGLE_RE.search(loc)
        if lm:
            f = lm.group(1).split("/")[-1]
            a = int(lm.group(2))
            b = int(lm.group(3)) if lm.lastindex and lm.lastindex >= 3 else a
        out.append({"sev": sev.lower(), "file": f, "a": a, "b": b, "class": cls.lower(), "raw": loc})
    return out


def _same_file(f, gt_file):
    return (f["file"] is not None and gt_file is not None
            and f["file"].split("/")[-1] == gt_file.split("/")[-1] and f["a"] is not None)


def overlaps(f, gt_file, s, e, fuzz):
    """Detection match: finding range intersects the GT window (with small fuzz)."""
    if not _same_file(f, gt_file):
        return False
    return f["a"] <= e + fuzz and f["b"] >= s - fuzz


def centered_in(f, gt_file, s, e):
    """Trap trigger: the finding's MIDPOINT falls inside the trap's function body.
    Midpoint (not range-overlap) avoids phantom triggers when a real finding's body
    merely abuts a safe function's line window in a tiny file."""
    if not _same_file(f, gt_file):
        return False
    mid = (f["a"] + f["b"]) / 2.0
    return s <= mid <= e


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("agent_output")
    ap.add_argument("ground_truth")
    ap.add_argument("--fuzz", type=int, default=5,
                    help="detection range-overlap tolerance in lines (traps use midpoint, no fuzz)")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    text = open(args.agent_output).read()
    gt = json.load(open(args.ground_truth))
    findings = parse_findings(text)

    detection = []
    optional = []
    for g in gt.get("findings", []):
        loc = g.get("location", {})
        gf, s, e = loc.get("file"), loc.get("line_start", 0), loc.get("line_end", 0)
        cls = (g.get("class", "") + " " + g.get("description", "")).lower()
        hit = None
        for f in findings:
            if overlaps(f, gf, s, e, args.fuzz):
                hit = f
                break
        if not hit:  # class-token fallback
            for f in findings:
                tok = re.split(r"[ \-_/]", f["class"])
                if any(t and t in cls for t in tok if len(t) > 3):
                    hit = f
                    break
        exp = TIERS.get(g.get("severity", "").lower())
        got = TIERS.get(hit["sev"]) if hit else None
        delta = (got - exp) if (hit and exp is not None and got is not None) else None
        row = {"gt": g.get("description", "")[:60], "found": bool(hit),
               "exp_sev": g.get("severity"), "got_sev": hit["sev"] if hit else None,
               "sev_delta": delta}
        # must_detect defaults True; disputed/optional findings are reported but not scored for recall.
        (detection if g.get("must_detect", True) else optional).append(row)

    traps = []
    for t in gt.get("false_positive_traps", []):
        loc = t.get("location", {})
        tf, s, e = loc.get("file"), loc.get("line_start", 0), loc.get("line_end", 0)
        triggered = [f for f in findings if centered_in(f, tf, s, e)]
        traps.append({"trap": t.get("description", "")[:60],
                      "triggered": bool(triggered),
                      "by": [f["raw"] for f in triggered]})

    n_must = len(detection)
    n_found = sum(1 for d in detection if d["found"])
    n_traps = len(traps)
    n_clean = sum(1 for t in traps if not t["triggered"])
    recall = (n_found / n_must * 100) if n_must else 100.0
    precision_traps = (n_clean / n_traps * 100) if n_traps else 100.0

    result = {"recall_pct": round(recall, 1), "found": n_found, "must_detect": n_must,
              "traps_clean": n_clean, "traps_total": n_traps,
              "trap_clean_pct": round(precision_traps, 1),
              "detection": detection, "optional": optional, "traps": traps,
              "total_findings_reported": len(findings)}

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"Recall: {n_found}/{n_must} ({recall:.0f}%) | "
              f"Traps clean: {n_clean}/{n_traps} ({precision_traps:.0f}%) | "
              f"Findings reported: {len(findings)}")
        for d in detection:
            mark = "FOUND" if d["found"] else "MISSED"
            sd = f" sev {d['exp_sev']}->{d['got_sev']} (Δ{d['sev_delta']:+d})" if d["sev_delta"] is not None else ""
            print(f"  [{mark}] {d['gt']}{sd}")
        for d in optional:
            mark = "found" if d["found"] else "not reported"
            print(f"  [optional/{mark}] {d['gt']}")
        for t in traps:
            mark = "TRIGGERED" if t["triggered"] else "clean"
            extra = f" by {t['by']}" if t["triggered"] else ""
            print(f"  [trap {mark}] {t['trap']}{extra}")

    sys.exit(0 if (n_found == n_must and n_clean == n_traps) else 1)


if __name__ == "__main__":
    main()
