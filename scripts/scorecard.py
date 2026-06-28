"""Multi-atlas scorecard: accuracy + coverage + visibility across every eval atlas, in one table.

Prints (does not commit) a consolidated view so a broadening change is judged on all atlases at once,
rather than reading three separate baseline reports. Accuracy (broad agreement) is shown next to its
named-call count N and coverage on purpose: accuracy alone is meaningless without them (a labeler that
abstains on everything scores 100% on zero calls). On the small held-out atlases N is tiny, so read
coverage / abstain / vocab-hit-rate, not accuracy.

This is a read-only convenience over the committed benchmark CSVs + crosswalks (it reuses
evaluate.evaluate and the atlas_eval registry); it writes no file and gates nothing.

Run (needs data/ontologies):
    uv run python scripts/scorecard.py        (or: make scorecard)
"""

from __future__ import annotations

import statistics
import sys

from atlas_eval import ATLASES, BENCH, DATA, PANELS, AtlasConfig

from zlabel.evaluate import (
    ABSTAIN,
    FALLBACK,
    NAMED,
    ROLLUP,
    Resources,
    evaluate,
    load_benchmark,
    load_crosswalk,
    load_resources,
)

# The hard Daniocell baseline is not in the held-out registry; add it here so the scorecard spans all three.
DANIOCELL = AtlasConfig(
    name="daniocell",
    benchmark=BENCH / "daniocell_eval.csv",
    crosswalk=BENCH / "daniocell_tissue_crosswalk.yaml",
    report=BENCH / "daniocell_baseline_report.md",
    title="",  # unused: the scorecard calls evaluate(), not render_report()
)


def scorecard_row(cfg: AtlasConfig, resources: Resources) -> str:
    """Score one atlas's committed benchmark and format its scorecard row.

    Args:
        cfg (AtlasConfig): The atlas's benchmark + crosswalk paths.
        resources (Resources): Engine data loaded once, shared across atlases.

    Returns:
        str: A markdown table row: atlas, scored, called (N), accuracy, coverage, abstain,
        overcalls, vocab-hit.
    """
    report = evaluate(load_benchmark(cfg.benchmark), load_crosswalk(cfg.crosswalk), resources)
    scored = report.total - report.not_scored
    called = report.counts[NAMED] + report.counts[FALLBACK]
    correct = report.correct[NAMED] + report.correct[FALLBACK]
    covered = called + report.counts[ROLLUP]
    overcalls = sum(audit.thin_support_overcall for audit in report.audits)
    vocab = statistics.median(report.vocab_hit_rates) if report.vocab_hit_rates else 0.0
    accuracy = f"{100 * correct / called:.1f}% ({correct}/{called})" if called else "n/a"
    coverage = f"{100 * covered / scored:.1f}%" if scored else "n/a"
    abstain = f"{100 * report.counts[ABSTAIN] / scored:.1f}%" if scored else "n/a"
    cells = [cfg.name, scored, called, accuracy, coverage, abstain, overcalls, f"{100 * vocab:.1f}%"]
    return "| " + " | ".join(str(cell) for cell in cells) + " |"


def main() -> int:
    """Print the multi-atlas scorecard. Returns 0 (skips cleanly when data is absent)."""
    required = [DATA / "zfa.obo", DATA / "zfin_wildtype_expression.txt", DATA / "zfin.gaf"]
    if not all(path.exists() for path in required):
        print("SKIP scorecard: data/ontologies absent (run scripts/setup_data.sh).")
        return 0
    resources = load_resources(
        zfa_path=DATA / "zfa.obo",
        expr_path=DATA / "zfin_wildtype_expression.txt",
        gaf_path=DATA / "zfin.gaf",
        panels_path=PANELS,
    )
    print("# Multi-atlas scorecard (committed baselines)\n")
    print("Accuracy = broad agreement over named+fallback calls (N). Read it WITH N and coverage:")
    print("on the small held-out atlases N is tiny, so coverage / abstain / vocab-hit are the real signal.\n")
    print("| atlas | scored | called (N) | accuracy | coverage | abstain | overcalls | vocab-hit |")
    print("|---|---|---|---|---|---|---|---|")
    for cfg in (DANIOCELL, *ATLASES.values()):
        print(scorecard_row(cfg, resources))
    return 0


if __name__ == "__main__":
    sys.exit(main())
