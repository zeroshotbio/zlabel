"""E1: sweep the specificity-blend alpha over the Daniocell benchmark; report the gold-blind harm table.

alpha=0 is pure rank-overlap (the committed baseline). The sweep mixes per-marker panel-specificity
into the selection score and measures, per gold lineage and overall: agreement, coverage, attractor
wins (want down) and correct-winner demotions (want zero). The alpha grid is fixed in advance and
never tuned to gold; the gold key is read-out only. The ~14% Daniocell key error is NOT corrected here
(that is E3), so this is the mechanism signal, not the final GO/NO-GO.

Pre-registered rejection rule (reject a blend alpha if ANY holds, vs alpha=0):
  1. net correct-winner loss   -- decisive, even if attractor wins drop (the N0b risk)
  2. agreement regression
  3. coverage drop > 2 points
  4. thin-support overcall regression
GO (would justify flipping the default) only if some alpha cuts attractor wins with none of 1-4.

Run (needs data/ontologies):
    uv run python scripts/e1_specificity_sweep.py
Outputs land in outputs/e1_specificity_blend/ (gitignored); the committed baseline is never touched.
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from pathlib import Path

from zlabel.evaluate import (
    ClusterOutcome,
    Report,
    cluster_outcomes,
    evaluate,
    load_benchmark,
    load_crosswalk,
    load_resources,
)

REPO = Path(__file__).resolve().parent.parent
DATA = REPO / "data" / "ontologies"
BENCHMARK = REPO / "benchmarks" / "daniocell_eval.csv"
CROSSWALK = REPO / "benchmarks" / "daniocell_tissue_crosswalk.yaml"
PANELS = REPO / "src" / "zlabel" / "panels.yaml"
OUTDIR = REPO / "outputs" / "e1_specificity_blend"

# Pre-registered, fixed blend grid. ALPHAS[0] MUST be 0.0 (the unblended baseline): the harm read-out
# and the summary diff every arm against summaries[0]/outcomes_by_alpha[ALPHAS[0]].
ALPHAS = (0.0, 0.25, 0.5, 0.75, 1.0)

# The four broad attractor panels (design.md: the promiscuous-support sinks) and the correct-but-
# promiscuous lineages N0b found to be even more promiscuous than the sinks on every gold-free axis.
ATTRACTORS = frozenset({"epidermis", "endothelium", "mesenchyme", "neural"})
CORRECT_PROMISCUOUS = frozenset({"notochord", "cartilage", "neural_crest", "pigment"})


# --- pure harm aggregators (unit-tested in tests/test_e1_sweep.py) ------------------------------


def is_attractor_win(outcome: ClusterOutcome | None) -> bool:
    """A scored call that named an attractor panel and disagrees with gold."""
    return outcome is not None and outcome.scored and outcome.panel_bucket in ATTRACTORS and outcome.agrees is False


def is_correct_winner(outcome: ClusterOutcome | None) -> bool:
    """A scored call that named a promiscuous-but-correct lineage and agrees with gold."""
    return (
        outcome is not None
        and outcome.scored
        and outcome.panel_bucket in CORRECT_PROMISCUOUS
        and outcome.agrees is True
    )


def correct_winner_demotions(baseline: list[ClusterOutcome], after: list[ClusterOutcome]) -> int:
    """Correct winners at baseline that the blend turned non-correct (now wrong, rollup, or abstain)."""
    base_by_id = {outcome.cluster_id: outcome for outcome in baseline}
    return sum(1 for o in after if is_correct_winner(base_by_id.get(o.cluster_id)) and o.agrees is not True)


def agreement_coverage(outcomes: list[ClusterOutcome]) -> tuple[float, float]:
    """Named/fallback agreement and coverage over the scored clusters.

    Agreement is the fraction of scoreable (agrees is not None) calls that agree; coverage is the
    fraction of scored clusters that produced a scoreable call (the rest abstained or rolled up).
    """
    scored = [outcome for outcome in outcomes if outcome.scored]
    scoreable = [outcome for outcome in scored if outcome.agrees is not None]
    agreement = sum(1 for outcome in scoreable if outcome.agrees) / len(scoreable) if scoreable else 0.0
    coverage = len(scoreable) / len(scored) if scored else 0.0
    return agreement, coverage


# --- per-alpha summary + pre-registered verdict ------------------------------------------------


@dataclass(frozen=True)
class AlphaSummary:
    """The headline numbers for one alpha arm."""

    alpha: float
    agreement: float
    coverage: float
    attractor_wins: int
    correct_winners: int
    correct_winner_demotions: int
    overcalls: int


def summarize(
    alpha: float, outcomes: list[ClusterOutcome], report: Report, baseline: list[ClusterOutcome]
) -> AlphaSummary:
    """Project one alpha arm's outcomes + report into the headline numbers."""
    agreement, coverage = agreement_coverage(outcomes)
    return AlphaSummary(
        alpha=alpha,
        agreement=agreement,
        coverage=coverage,
        attractor_wins=sum(is_attractor_win(o) for o in outcomes),
        correct_winners=sum(is_correct_winner(o) for o in outcomes),
        correct_winner_demotions=correct_winner_demotions(baseline, outcomes),
        overcalls=sum(audit.thin_support_overcall for audit in report.audits),
    )


def rejection_reasons(base: AlphaSummary, cand: AlphaSummary) -> list[str]:
    """The pre-registered rejection reasons that fire for a candidate alpha (empty = none fire)."""
    reasons: list[str] = []
    if cand.correct_winners < base.correct_winners:
        reasons.append(f"net correct-winner loss ({base.correct_winners} -> {cand.correct_winners})")
    if cand.agreement < base.agreement:
        reasons.append(f"agreement regression ({base.agreement:.3f} -> {cand.agreement:.3f})")
    if cand.coverage < base.coverage - 0.02:
        reasons.append(f"coverage drop > 2pp ({base.coverage:.3f} -> {cand.coverage:.3f})")
    if cand.overcalls > base.overcalls:
        reasons.append(f"overcall regression ({base.overcalls} -> {cand.overcalls})")
    return reasons


def is_go(base: AlphaSummary, cand: AlphaSummary) -> bool:
    """A candidate alpha is GO only if it cuts attractor wins with no rejection reason firing."""
    return not rejection_reasons(base, cand) and cand.attractor_wins < base.attractor_wins


def panel_win_table(outcomes: list[ClusterOutcome]) -> dict[str, tuple[int, int]]:
    """Per engine-winner panel (attractors + correct-promiscuous): (named scoreable calls, correct ones)."""
    table: dict[str, tuple[int, int]] = {}
    for panel in sorted(ATTRACTORS | CORRECT_PROMISCUOUS):
        calls = [o for o in outcomes if o.scored and o.panel_bucket == panel and o.agrees is not None]
        table[panel] = (len(calls), sum(1 for o in calls if o.agrees))
    return table


# --- driver -------------------------------------------------------------------------------------


def _render_summary(summaries: list[AlphaSummary], panels_by_alpha: dict[float, dict[str, tuple[int, int]]]) -> str:
    base = summaries[0]
    lines = ["# E1 -- specificity-blend sweep (mechanism signal; raw Daniocell key)", ""]
    lines.append("alpha=0 is the committed baseline. Gold is read-out only; the alpha grid is fixed.")
    lines.append("The ~14% key error is uncorrected here (E3), so this is the mechanism signal, not the verdict.")
    lines.append("")
    lines.append("| alpha | agree | coverage | attractor wins | correct winners | demotions | overcalls | verdict |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for s in summaries:
        if s.alpha == base.alpha:
            verdict = "baseline"
        elif is_go(base, s):
            verdict = "GO"
        else:
            verdict = "REJECT: " + "; ".join(rejection_reasons(base, s))
        lines.append(
            f"| {s.alpha:.2f} | {s.agreement:.3f} | {s.coverage:.3f} | {s.attractor_wins} | "
            f"{s.correct_winners} | {s.correct_winner_demotions} | {s.overcalls} | {verdict} |"
        )
    lines.append("")
    lines.append("## Per engine-winner panel: (scoreable calls, correct) by alpha")
    lines.append("")
    header = "| panel | " + " | ".join(f"a={a:.2f}" for a in ALPHAS) + " |"
    lines.append(header)
    lines.append("|" + "---|" * (len(ALPHAS) + 1))
    for panel in sorted(ATTRACTORS | CORRECT_PROMISCUOUS):
        kind = "attractor" if panel in ATTRACTORS else "correct-promiscuous"
        cells = " | ".join(f"{panels_by_alpha[a][panel][1]}/{panels_by_alpha[a][panel][0]}" for a in ALPHAS)
        lines.append(f"| {panel} ({kind}) | {cells} |")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    """Run the alpha sweep and write the harm report. Returns 0 on success, 1 if data is absent."""
    required = [DATA / "zfa.obo", DATA / "zfin_wildtype_expression.txt", DATA / "zfin.gaf"]
    if not all(path.exists() for path in required):
        print("SKIP e1-sweep: data/ontologies absent (run scripts/setup_data.sh).")
        return 1

    resources = load_resources(
        zfa_path=DATA / "zfa.obo",
        expr_path=DATA / "zfin_wildtype_expression.txt",
        gaf_path=DATA / "zfin.gaf",
        panels_path=PANELS,
    )
    benchmark = load_benchmark(BENCHMARK)
    crosswalk = load_crosswalk(CROSSWALK)

    outcomes_by_alpha: dict[float, list[ClusterOutcome]] = {}
    reports_by_alpha: dict[float, Report] = {}
    for alpha in ALPHAS:
        res = dataclasses.replace(resources, alpha=alpha)
        outcomes_by_alpha[alpha] = cluster_outcomes(benchmark, crosswalk, res)
        reports_by_alpha[alpha] = evaluate(benchmark, crosswalk, res)

    baseline = outcomes_by_alpha[ALPHAS[0]]
    summaries = [summarize(a, outcomes_by_alpha[a], reports_by_alpha[a], baseline) for a in ALPHAS]
    panels_by_alpha = {a: panel_win_table(outcomes_by_alpha[a]) for a in ALPHAS}

    OUTDIR.mkdir(parents=True, exist_ok=True)
    summary_md = _render_summary(summaries, panels_by_alpha)
    (OUTDIR / "sweep_summary.md").write_text(summary_md, encoding="utf-8")

    print(summary_md)
    base = summaries[0]
    any_go = any(is_go(base, s) for s in summaries[1:])
    print(f"\nE1 mechanism verdict: {'GO candidate exists' if any_go else 'NO-GO at every alpha (rule fires)'}.")
    print(f"Wrote {OUTDIR / 'sweep_summary.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
