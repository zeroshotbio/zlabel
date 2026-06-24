"""Stage-G regression wall: fail the commit on baseline drift or a parent-child overcall regression.

zlabel's hard regression gates (see .claude/docs/workflow.md) are the broad-agreement baseline and
the parent-child overcall audit. They are only as strong as someone remembering to run them. This
script turns that habit into a checked wall: it re-runs the evaluator over the committed benchmark
and compares the fresh report to the committed benchmarks/daniocell_baseline_report.md.

  - Any drift fails. A behavior change must be made intentionally: run `make eval` to regenerate the
    report, review the diff, and commit it alongside the change (the regenerate-baseline rule).
  - A rise in the thin-support overcall count fails loudly as a named regression -- the exact trade
    (blind-spot recovery bought with overcalling) the descent design exists to prevent.

The check needs data/ontologies (the gitignored ZFIN/ZFA downloads); when that data is absent it
SKIPS (exit 0) rather than blocking a machine without the corpus.
"""

from __future__ import annotations

import difflib
import re
import sys
from pathlib import Path

from zlabel.evaluate import evaluate, load_benchmark, load_crosswalk, load_resources, render_report

REPO = Path(__file__).resolve().parent.parent
DATA = REPO / "data" / "ontologies"
BENCHMARK = REPO / "benchmarks" / "daniocell_eval.csv"
CROSSWALK = REPO / "benchmarks" / "daniocell_tissue_crosswalk.yaml"
PANELS = REPO / "src" / "zlabel" / "panels.yaml"
COMMITTED = REPO / "benchmarks" / "daniocell_baseline_report.md"

# The committed report's overcall headline, e.g. "...had more support): 4.8% (7/146)".
_OVERCALL_LINE = re.compile(r"thin-support overcalls.*\((\d+)/\d+\)")


def committed_overcall_count(report_text: str) -> int | None:
    """The thin-support overcall numerator parsed from a rendered baseline report.

    Args:
        report_text (str): The committed daniocell_baseline_report.md text.

    Returns:
        int | None: The thin-support overcall count, or None when the line is absent
        (an older or malformed report) so the caller can fall back to a plain drift fail.
    """
    match = _OVERCALL_LINE.search(report_text)
    return int(match.group(1)) if match else None


def main() -> int:
    """Regenerate the baseline and compare it to the committed report.

    Returns:
        int: 0 when the data is absent (skip) or the baseline matches; 1 on any drift,
        with an overcall regression called out before the diff.
    """
    required = [DATA / "zfa.obo", DATA / "zfin_wildtype_expression.txt", DATA / "zfin.gaf"]
    if not all(path.exists() for path in required):
        print("SKIP check-baseline: data/ontologies absent; cannot verify (run scripts/setup_data.sh).")
        return 0

    resources = load_resources(
        zfa_path=DATA / "zfa.obo",
        expr_path=DATA / "zfin_wildtype_expression.txt",
        gaf_path=DATA / "zfin.gaf",
        panels_path=PANELS,
    )
    report = evaluate(load_benchmark(BENCHMARK), load_crosswalk(CROSSWALK), resources)
    fresh = render_report(report)
    committed = COMMITTED.read_text(encoding="utf-8")

    fresh_overcalls = sum(audit.thin_support_overcall for audit in report.audits)
    if fresh == committed:
        print(f"check-baseline OK: baseline matches; thin-support overcalls = {fresh_overcalls}.")
        return 0

    print("FAIL check-baseline: the regenerated baseline differs from the committed report.")
    prior = committed_overcall_count(committed)
    if prior is not None and fresh_overcalls > prior:
        print(f"  OVERCALL AUDIT REGRESSION: thin-support overcalls {prior} -> {fresh_overcalls}.")
        print("  This is a hard regression gate (.claude/docs/workflow.md) -- do not commit unless")
        print("  the overcalls are intended and reviewed.")
    print("  If the labeling change is intentional, run `make eval` to regenerate the report and review")
    print("  the diff before committing. Unified diff (committed -> fresh):")
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
