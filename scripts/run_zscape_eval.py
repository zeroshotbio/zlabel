"""Run zlabel (committed default config) on the ZSCAPE 2nd-atlas eval set; write the report.

A held-out generalization check (E3): zlabel is UNCHANGED and the thresholds are the committed
defaults -- the ZSCAPE benchmark is never tuned on. Scores broad agreement against the gold-blind
benchmarks/zscape_tissue_crosswalk.yaml. Report-only -> benchmarks/zscape_baseline_report.md (this is
NOT the gated Daniocell baseline). The ZSCAPE gold key is itself fallible, so read agreement as a
generalization signal, not an absolute.

Run (needs data/ontologies):
    uv run python scripts/run_zscape_eval.py
"""

from __future__ import annotations

from pathlib import Path

from zlabel.evaluate import evaluate, load_benchmark, load_crosswalk, load_resources, render_report

REPO = Path(__file__).resolve().parent.parent
DATA = REPO / "data" / "ontologies"
PANELS = REPO / "src" / "zlabel" / "panels.yaml"
BENCH = REPO / "benchmarks" / "zscape_eval.csv"
CROSS = REPO / "benchmarks" / "zscape_tissue_crosswalk.yaml"
OUT = REPO / "benchmarks" / "zscape_baseline_report.md"


def main() -> int:
    """Score zlabel on the ZSCAPE eval set and write/print the report. Returns 0, or 1 if data is absent."""
    required = [DATA / "zfa.obo", DATA / "zfin_wildtype_expression.txt", DATA / "zfin.gaf"]
    if not all(path.exists() for path in required):
        print("run-zscape-eval: cannot regenerate, data/ontologies absent (run scripts/setup_data.sh).")
        return 1

    resources = load_resources(
        zfa_path=DATA / "zfa.obo",
        expr_path=DATA / "zfin_wildtype_expression.txt",
        gaf_path=DATA / "zfin.gaf",
        panels_path=PANELS,
    )
    report = evaluate(load_benchmark(BENCH), load_crosswalk(CROSS), resources)
    rendered = render_report(report, title="ZSCAPE 2nd-atlas baseline report (anchor-rooted descent engine)")
    OUT.write_text(rendered, encoding="utf-8")
    print(rendered)
    print(f"\nWrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
