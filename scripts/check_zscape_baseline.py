"""Held-out ZSCAPE wall: regenerate the 2nd-atlas report and fail on drift, with a directional read.

ZSCAPE (Saunders 2023) is zlabel's held-out generalization atlas: the engine and thresholds are
never tuned on it. This wall mirrors check_baseline.py (regenerate, compare to the committed
benchmarks/zscape_baseline_report.md, fail on any drift so a change is regenerated and reviewed
deliberately), with one difference suited to a held-out, small-N atlas: on drift it prints a
DIRECTIONAL read of the four metrics that say whether the change generalized -- coverage, abstain,
broad agreement, and the thin-support overcall count -- so a reviewer can tell an improvement
(commit the regenerated report) from a regression (reject it) at a glance.

Agreement is treated as a guard band, not a hard line: the named set is small (denominator ~18), so
one flipped call is several points of noise. Only an agreement drop beyond AGREEMENT_TOLERANCE_PCT
is flagged. Coverage-down, abstain-up, and overcall-up are flagged as regressions directly.

Needs data/ontologies (the gitignored ZFIN/ZFA downloads); SKIPS (exit 0) when that data is absent,
so a machine without the corpus is never blocked.
"""

from __future__ import annotations

import difflib
import re
import sys
from pathlib import Path

from zlabel.evaluate import evaluate, load_benchmark, load_crosswalk, load_resources, render_report

REPO = Path(__file__).resolve().parent.parent
DATA = REPO / "data" / "ontologies"
BENCHMARK = REPO / "benchmarks" / "zscape_eval.csv"
CROSSWALK = REPO / "benchmarks" / "zscape_tissue_crosswalk.yaml"
PANELS = REPO / "src" / "zlabel" / "panels.yaml"
COMMITTED = REPO / "benchmarks" / "zscape_baseline_report.md"

# Must match the title run_zscape_eval.py renders, so a clean run is byte-identical to the committed report.
TITLE = "ZSCAPE 2nd-atlas baseline report (anchor-rooted descent engine)"

# An agreement drop smaller than this (percentage points) is small-N noise, not a flagged regression.
AGREEMENT_TOLERANCE_PCT = 5.0

# Each metric's headline line in the rendered report: name -> (regex capturing percent, direction).
# direction "up" means a higher value is better (coverage, agreement); "down" means lower is better.
_METRICS = {
    "coverage": (re.compile(r"coverage \(non-abstain\): ([\d.]+)%"), "up"),
    "abstain": (re.compile(r"- abstain: ([\d.]+)%"), "down"),
    "agreement": (re.compile(r"- agreement: ([\d.]+)%"), "up"),
}
_OVERCALL_LINE = re.compile(r"thin-support overcalls.*\((\d+)/\d+\)")


def _metric(text: str, pattern: re.Pattern[str]) -> float | None:
    """The percentage captured by pattern in a rendered report, or None when the line is absent."""
    match = pattern.search(text)
    return float(match.group(1)) if match else None


def _overcalls(text: str) -> int | None:
    """The thin-support overcall numerator in a rendered report, or None when the line is absent."""
    match = _OVERCALL_LINE.search(text)
    return int(match.group(1)) if match else None


def directional_read(committed: str, fresh: str) -> list[str]:
    """Lines describing how each held-out metric moved committed -> fresh, flagging regressions.

    Args:
        committed (str): The committed ZSCAPE report text.
        fresh (str): The freshly regenerated report text.

    Returns:
        list[str]: One human-readable line per metric (coverage, abstain, agreement, overcall),
        each marked REGRESSION, improved, or flat, for a reviewer to judge the drift.
    """
    lines: list[str] = []
    for name, (pattern, direction) in _METRICS.items():
        was, now = _metric(committed, pattern), _metric(fresh, pattern)
        if was is None or now is None:
            continue
        delta = now - was
        tolerance = AGREEMENT_TOLERANCE_PCT if name == "agreement" else 0.0
        worsened = -delta > tolerance if direction == "up" else delta > tolerance
        mark = "REGRESSION" if worsened else ("improved" if delta else "flat")
        lines.append(f"  {name}: {was:.1f}% -> {now:.1f}% ({delta:+.1f} pts) [{mark}]")

    was_oc, now_oc = _overcalls(committed), _overcalls(fresh)
    if was_oc is not None and now_oc is not None:
        mark = "REGRESSION" if now_oc > was_oc else ("improved" if now_oc < was_oc else "flat")
        lines.append(f"  overcalls: {was_oc} -> {now_oc} [{mark}]")
    return lines


def main() -> int:
    """Regenerate the ZSCAPE report and compare it to the committed one.

    Returns:
        int: 0 when the data is absent (skip) or the report matches; 1 on any drift, after printing
        the directional read and the unified diff.
    """
    required = [DATA / "zfa.obo", DATA / "zfin_wildtype_expression.txt", DATA / "zfin.gaf"]
    if not all(path.exists() for path in required):
        print("SKIP check-zscape-baseline: data/ontologies absent; cannot verify (run scripts/setup_data.sh).")
        return 0

    resources = load_resources(
        zfa_path=DATA / "zfa.obo",
        expr_path=DATA / "zfin_wildtype_expression.txt",
        gaf_path=DATA / "zfin.gaf",
        panels_path=PANELS,
    )
    report = evaluate(load_benchmark(BENCHMARK), load_crosswalk(CROSSWALK), resources)
    fresh = render_report(report, title=TITLE)
    committed = COMMITTED.read_text(encoding="utf-8")

    if fresh == committed:
        print("check-zscape-baseline OK: held-out ZSCAPE report matches.")
        return 0

    print("FAIL check-zscape-baseline: the regenerated ZSCAPE report differs from the committed one.")
    print("  Held-out generalization read (commit a regenerated report only if these are improvements):")
    for line in directional_read(committed, fresh):
        print(line)
    print("  If intentional, run `make eval-zscape` to regenerate the report and review before committing.")
    print("  Unified diff (committed -> fresh):")
    diff = difflib.unified_diff(
        committed.splitlines(keepends=True),
        fresh.splitlines(keepends=True),
        fromfile="committed",
        tofile="fresh",
    )
    sys.stdout.writelines(diff)
    return 1


if __name__ == "__main__":
    sys.exit(main())
