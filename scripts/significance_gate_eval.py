"""E3: would a hypergeometric chance-gate help? Measure before wiring it into decide().

For every scored named/fallback call on the Daniocell benchmark, compute the upper-tail hypergeometric
p-value of the winning panel's marker overlap (significance.hypergeom_sf): small p means the overlap is
unlikely by chance. A chance-gate would abstain when p exceeds a threshold. It only helps if attractor
wins (wrong, promiscuous) carry SYSTEMATICALLY higher p than correct calls -- otherwise vetoing high-p
calls drops correct calls just as fast. This report-only script measures that separation; it changes no
engine code, so make gate stays green. Outputs land in outputs/e3_significance_gate/ (gitignored).

Run (needs data/ontologies):
    uv run python scripts/significance_gate_eval.py
"""

from __future__ import annotations

import statistics
from pathlib import Path

from zlabel.evaluate import cluster_outcomes, load_benchmark, load_crosswalk, load_resources
from zlabel.genes import normalize_markers, resolved_symbols
from zlabel.panels import KIND_IDENTITY, score_markers
from zlabel.significance import hypergeom_sf

REPO = Path(__file__).resolve().parent.parent
DATA = REPO / "data" / "ontologies"
BENCHMARK = REPO / "benchmarks" / "daniocell_eval.csv"
CROSSWALK = REPO / "benchmarks" / "daniocell_tissue_crosswalk.yaml"
PANELS = REPO / "src" / "zlabel" / "panels.yaml"
OUTDIR = REPO / "outputs" / "e3_significance_gate"

ATTRACTORS = frozenset({"epidermis", "endothelium", "mesenchyme", "neural"})
THRESHOLDS = (0.01, 0.05, 0.10, 0.20, 0.50)


def categorize(panel_bucket: str, agrees: bool) -> str:
    """Bucket a scored call as attractor-win, attractor-correct, correct, or other-wrong."""
    if panel_bucket in ATTRACTORS:
        return "attractor_win" if not agrees else "attractor_correct"
    return "correct" if agrees else "other_wrong"


def _fmt(label: str, ps: list[float]) -> str:
    if not ps:
        return f"| {label} | 0 | n/a | n/a |"
    return f"| {label} | {len(ps)} | {statistics.median(ps):.3f} | {statistics.mean(ps):.3f} |"


def main() -> int:
    """Compute per-call overlap p-values and report whether a chance-gate would separate wins."""
    required = [DATA / "zfa.obo", DATA / "zfin_wildtype_expression.txt", DATA / "zfin.gaf"]
    if not all(path.exists() for path in required):
        print("SKIP significance-gate-eval: data/ontologies absent (run scripts/setup_data.sh).")
        return 1

    resources = load_resources(
        zfa_path=DATA / "zfa.obo",
        expr_path=DATA / "zfin_wildtype_expression.txt",
        gaf_path=DATA / "zfin.gaf",
        panels_path=PANELS,
    )
    benchmark = load_benchmark(BENCHMARK)
    crosswalk = load_crosswalk(CROSSWALK)
    outcomes = {o.cluster_id: o for o in cluster_outcomes(benchmark, crosswalk, resources)}

    background = frozenset(m for panel in resources.panels if panel.kind == KIND_IDENTITY for m in panel.markers)
    universe = len(background)
    panel_by_bucket = {panel.bucket: panel for panel in resources.panels}

    # p-values grouped by call category, and per-call rows for the threshold sweep.
    by_category: dict[str, list[float]] = {
        "attractor_win": [],
        "attractor_correct": [],
        "correct": [],
        "other_wrong": [],
    }
    calls: list[tuple[str, float, bool]] = []  # (category, p_value, is_correct)
    for row in benchmark:
        outcome = outcomes[row.cluster_id]
        if not outcome.scored or outcome.agrees is None:
            continue  # only scoreable named/fallback calls have an overlap p-value worth gating
        panel = panel_by_bucket.get(outcome.panel_bucket)
        if panel is None:
            continue
        normalized = normalize_markers(row.markers, resources.synonyms)
        scores = score_markers(normalized, resources.panels)
        winner = next((s for s in scores if s.bucket == outcome.panel_bucket), None)
        if winner is None:
            continue
        hits = len(winner.matched_markers)
        successes = len(panel.markers & background)
        draws = len(set(resolved_symbols(normalized)) & background)
        p_value = hypergeom_sf(hits, universe, successes, draws)
        category = categorize(outcome.panel_bucket, outcome.agrees)
        by_category[category].append(p_value)
        calls.append((category, p_value, outcome.agrees))

    lines = ["# E3 -- would a hypergeometric chance-gate help? (measurement, report-only)", ""]
    lines.append(
        f"Gene universe M = {universe} (union of identity-panel markers); {len(calls)} scored named/fallback calls."
    )
    lines.append("A gate abstains when the overlap p-value exceeds a threshold. It helps only if attractor wins")
    lines.append("carry higher p than correct calls. p-value distribution by call category:")
    lines.append("")
    lines.append("| category | n | median p | mean p |")
    lines.append("|---|---|---|---|")
    for category in ("attractor_win", "attractor_correct", "correct", "other_wrong"):
        lines.append(_fmt(category, by_category[category]))
    lines.append("")
    lines.append("## Gate trade-off: at each p threshold, attractor wins vetoed vs correct calls lost")
    lines.append("")
    lines.append("| p threshold | attractor wins vetoed | correct calls lost | precision of veto |")
    lines.append("|---|---|---|---|")
    attractor_wins = [p for cat, p, _ in calls if cat == "attractor_win"]
    correct_calls = [p for _, p, agree in calls if agree]
    for threshold in THRESHOLDS:
        vetoed_wins = sum(1 for p in attractor_wins if p > threshold)
        lost_correct = sum(1 for p in correct_calls if p > threshold)
        precision = vetoed_wins / (vetoed_wins + lost_correct) if (vetoed_wins + lost_correct) else 0.0
        lines.append(
            f"| {threshold:.2f} | {vetoed_wins}/{len(attractor_wins)} | "
            f"{lost_correct}/{len(correct_calls)} | {precision:.2f} |"
        )
    lines.append("")

    report = "\n".join(lines)
    OUTDIR.mkdir(parents=True, exist_ok=True)
    (OUTDIR / "significance_gate_report.md").write_text(report, encoding="utf-8")
    print(report)
    print(f"Wrote {OUTDIR / 'significance_gate_report.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
