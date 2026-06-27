"""Evaluate the zlabel engine against the Daniocell broad-tissue benchmark.

Reads a benchmark CSV (cluster_id, markers, broad_tissue, ...), labels each cluster with
the current engine, and scores broad agreement in ZFA-ancestry space against a reviewed,
fail-closed tissue-to-ZFA crosswalk. Reports coverage, the named/fallback/rollup/abstain
split, confidence-by-correctness, and a structural parent-child overcall audit -- a regression
guard that the anchor-rooted descent does not overcall on real clusters.

This module is read-only over the engine: it reuses the public loaders, normalize_markers,
score_markers, and decide() unchanged. It loads the ontologies once and labels each row at its
own stage (equivalent to Labeler.label() at that stage) so stage varies per cluster without
reloading; the same loaded resources feed the audit. Run it as a script
(python -m zlabel.evaluate <csv>); it is not part of the labeling API.
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

import networkx as nx
import yaml

from zlabel.data import (
    ZfinExpressionRecord,
    ancestors,
    load_gene_synonym_map,
    load_zfa,
    load_zfin_expression,
    term_name,
)
from zlabel.genes import normalize_markers, resolved_symbols
from zlabel.ground import expression_lookup, grounds_under
from zlabel.label import decide
from zlabel.models import Label
from zlabel.panels import KIND_IDENTITY, Panel, load_panels, score_markers
from zlabel.resolve import (
    CONVERGENCE_MIN,
    STOPLIST,
    _term_with_ancestors,
    build_information_content,
    build_marker_specificity,
)

# Prediction classes (how the engine resolved a cluster).
NAMED = "named"  # the convergence descent named a ZFA term
FALLBACK = "fallback"  # anchor unsupported (no descent seed) -> coarse panel bucket
ROLLUP = "rollup"  # near-tie within a shared germ layer -> germ-layer tier
ABSTAIN = "abstain"  # mixed / no signal


@dataclass(frozen=True)
class BenchmarkRow:
    """One benchmark cluster: a marker list and its gold broad-tissue label."""

    cluster_id: str
    markers: list[str]
    broad_tissue: str
    tissue_name: str
    stage_hpf: float | None


@dataclass(frozen=True)
class Crosswalk:
    """Gold-side, fail-closed tissue-to-ZFA-anchor map for broad-agreement scoring."""

    anchors: dict[str, frozenset[str]]
    not_scored: frozenset[str]

    def gold(self, tissue: str) -> frozenset[str] | None:
        """Return the ZFA anchors for a tissue, or None when it is not_scored.

        Args:
            tissue (str): A Daniocell broad-tissue code.

        Returns:
            frozenset[str] | None: The anchor ids to score against, or None when the
            tissue is explicitly excluded.

        Raises:
            KeyError: When the tissue is absent from the crosswalk entirely (fail closed
                -- the evaluator never silently scores an unmapped tissue).
        """
        if tissue in self.not_scored:
            return None
        if tissue in self.anchors:
            return self.anchors[tissue]
        raise KeyError(f"tissue {tissue!r} is not in the crosswalk; map it or mark not_scored")


@dataclass
class Resources:
    """Engine data loaded once, shared by labeling and the overcall audit."""

    zfa_ontology: nx.MultiDiGraph
    expression_map: dict[str, list[ZfinExpressionRecord]]
    synonyms: dict[str, set[str]]
    panels: list[Panel]
    anchors: dict[str, frozenset[str]]
    information_content: dict[str, float]
    marker_specificity: dict[str, float]


@dataclass(frozen=True)
class AuditRecord:
    """Parent-child support for one named call -- the thin-support overcall signal."""

    cluster_id: str
    named_id: str
    named_name: str
    named_support: int
    parent_id: str | None
    parent_name: str | None
    parent_support: int
    support_fraction: float
    won_at_min: bool
    thin_support_overcall: bool


@dataclass(frozen=True)
class ClusterOutcome:
    """One cluster's full evaluation result -- the row the Report aggregates and the notebook explores."""

    cluster_id: str
    gold_tissue: str
    tissue_name: str
    stage_hpf: float | None
    markers: list[str]
    n_resolved: int
    kind: str
    bucket: str
    panel_bucket: str
    zfa_id: str | None
    depth: int
    scored: bool
    agrees: bool | None
    confidence: str | None
    convergent_genes: tuple[str, ...]
    abstain_reason: str | None
    audit: AuditRecord | None


@dataclass
class Report:
    """Accumulated evaluation outcomes, rendered to a deterministic markdown report."""

    total: int = 0
    not_scored: int = 0
    counts: Counter[str] = field(default_factory=Counter)
    correct: Counter[str] = field(default_factory=Counter)
    conf_total: Counter[str] = field(default_factory=Counter)
    conf_correct: Counter[str] = field(default_factory=Counter)
    audits: list[AuditRecord] = field(default_factory=list)
    failures: list[tuple[str, str, str, str]] = field(
        default_factory=list
    )  # (cluster_id, gold_tissue, predicted_bucket, kind)


def load_benchmark(path: str | Path) -> list[BenchmarkRow]:
    """Load the benchmark CSV into rows.

    Args:
        path (str | Path): The benchmark CSV (cluster_id, markers, broad_tissue,
            tissue_name, stage_hpf). markers is a ;-separated rank-ordered list.

    Returns:
        list[BenchmarkRow]: One row per cluster, in file order.
    """
    rows: list[BenchmarkRow] = []
    with Path(path).open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            stage = row.get("stage_hpf", "").strip()
            rows.append(
                BenchmarkRow(
                    cluster_id=row["cluster_id"],
                    markers=[marker for marker in row["markers"].split(";") if marker],
                    broad_tissue=row["broad_tissue"],
                    tissue_name=row.get("tissue_name", ""),
                    stage_hpf=float(stage) if stage else None,
                )
            )
    return rows


def load_crosswalk(path: str | Path) -> Crosswalk:
    """Load the tissue-to-ZFA crosswalk YAML.

    Args:
        path (str | Path): The crosswalk file (a tissues mapping of code to either
            anchors or not_scored).

    Returns:
        Crosswalk: The parsed, fail-closed mapping.
    """
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    anchors: dict[str, frozenset[str]] = {}
    not_scored: set[str] = set()
    for code, spec in raw["tissues"].items():
        if spec.get("not_scored"):
            not_scored.add(code)
        else:
            anchors[code] = frozenset(spec["anchors"])
    return Crosswalk(anchors, frozenset(not_scored))


def load_resources(
    *,
    zfa_path: str | Path,
    expr_path: str | Path,
    gaf_path: str | Path,
    panels_path: str | Path,
) -> Resources:
    """Load all engine data once (mirrors Labeler.__init__, minus the fixed stage).

    Args:
        zfa_path (str | Path): Path to zfa.obo.
        expr_path (str | Path): Path to zfin_wildtype_expression.txt.
        gaf_path (str | Path): Path to the ZFIN .gaf synonym file.
        panels_path (str | Path): Path to panels.yaml.

    Returns:
        Resources: The loaded ontology, expression, synonyms, panels, anchors, and IC.
    """
    zfa_ontology = load_zfa(zfa_path)
    expression_map = load_zfin_expression(expr_path)
    synonyms = load_gene_synonym_map(gaf_path)
    panels = load_panels(panels_path)
    anchors = {panel.bucket: panel.ontology_anchor for panel in panels}
    information_content = build_information_content(expression_map, zfa_ontology)
    identity_anchors = [panel.ontology_anchor for panel in panels if panel.kind == KIND_IDENTITY]
    marker_specificity = build_marker_specificity(expression_map, identity_anchors, zfa_ontology)
    return Resources(zfa_ontology, expression_map, synonyms, panels, anchors, information_content, marker_specificity)


def _label_row(row: BenchmarkRow, resources: Resources) -> tuple[Label, list[str]]:
    """Label one cluster at its own stage; also return its normalized symbols for the audit.

    Args:
        row (BenchmarkRow): The cluster's markers and developmental stage.
        resources (Resources): Loaded engine resources.

    Returns:
        tuple[Label, list[str]]: The label decision and the cluster's already-normalized
        current ZFIN symbols (passed to decide() and reused by the audit to replay the tally).
    """
    normalized_markers = normalize_markers(row.markers, resources.synonyms)
    symbols = resolved_symbols(normalized_markers)
    scores = score_markers(normalized_markers, resources.panels)
    label = decide(
        scores,
        anchors=resources.anchors,
        expression_map=resources.expression_map,
        zfa_ontology=resources.zfa_ontology,
        stage_hpf=row.stage_hpf,
        symbols=symbols,
        information_content=resources.information_content,
        marker_specificity=resources.marker_specificity,
    )
    return label, symbols


def _classify(label: Label) -> str:
    """Classify how the engine resolved a cluster (named / fallback / rollup / abstain)."""
    if label.abstained:
        return ABSTAIN
    if label.convergent_genes:
        return NAMED
    if label.ambiguity_flag == "underclustered":
        return ROLLUP
    return FALLBACK


def _prediction_anchor_ids(label: Label, kind: str, resources: Resources) -> frozenset[str]:
    """The ZFA ids to score a prediction by.

    Named calls score by the voted term. Fallback calls are enriched eval-side: Label.zfa_id
    keeps only sorted(anchor)[0], so we recover the full panel ontology_anchor from
    panel_bucket rather than scoring against a truncated anchor.

    Args:
        label (Label): The engine's label for the cluster.
        kind (str): The prediction class from _classify.
        resources (Resources): Loaded resources (for the panel anchor lookup).

    Returns:
        frozenset[str]: The ZFA ids the prediction is scored under; empty for
        rollup/abstain (which carry no ZFA handle).
    """
    if kind == NAMED and label.zfa_id is not None:
        return frozenset({label.zfa_id})
    if kind == FALLBACK:
        return resources.anchors.get(label.panel_bucket, frozenset())
    return frozenset()


def _replay_tally(
    symbols: list[str],
    expression_map: dict[str, list[ZfinExpressionRecord]],
    zfa_ontology: nx.MultiDiGraph,
) -> dict[str, set[str]]:
    """Reconstruct the raw per-term gene tally (all terms, before the IC/stoplist gates).

    Mirrors resolve.resolve_label's tally exactly so the audit can see IC-filtered parent
    terms the engine's gated output drops. A unit test pins this against resolve_label.

    Args:
        symbols (list[str]): Already-normalized current ZFIN symbols (as decide() received).
        expression_map (dict[str, list[ZfinExpressionRecord]]): The loaded expression data.
        zfa_ontology (nx.MultiDiGraph): The loaded ZFA ontology.

    Returns:
        dict[str, set[str]]: ZFA term id to the distinct genes that credit it.
    """
    ancestor_cache: dict[str, frozenset[str]] = {}

    tally: dict[str, set[str]] = {}
    seen: set[str] = set()
    for symbol in symbols:
        if symbol in seen:
            continue
        seen.add(symbol)
        records = expression_lookup(expression_map, symbol)
        if not records:
            continue
        credited_terms: set[str] = set()
        for record in records:
            credited_terms |= _term_with_ancestors(record.zfa_id, zfa_ontology, ancestor_cache)
        for term_id in credited_terms:
            tally.setdefault(term_id, set()).add(symbol)
    return tally


def _audit_from_tally(
    cluster_id: str,
    named_id: str,
    named_name: str,
    tally: dict[str, set[str]],
    zfa_ontology: nx.MultiDiGraph,
) -> AuditRecord:
    """Compare a named winner's support to its best-supported ancestor (the overcall signal).

    A thin-support overcall is a winner that cleared exactly CONVERGENCE_MIN genes while a
    broader ancestor (content-free stoplist roots excluded) had strictly more support -- the
    overcall the anchor-rooted descent's support floor is built to prevent. Pure over the tally.

    Args:
        cluster_id (str): The cluster id.
        named_id (str): The named ZFA term id.
        named_name (str): The human-readable ZFA term name (label.bucket for a named call).
        tally (dict[str, set[str]]): The raw per-term gene tally from _replay_tally.
        zfa_ontology (nx.MultiDiGraph): The ZFA ontology (for the ancestor walk and names).

    Returns:
        AuditRecord: The parent-child support comparison for this call.
    """
    support = len(tally.get(named_id, set()))
    parent_id: str | None = None
    parent_support = 0
    parents = ancestors(zfa_ontology, named_id) if named_id in zfa_ontology else []
    for ancestor_id in parents:
        if ancestor_id in STOPLIST:
            continue  # content-free roots (anatomical structure, whole organism) are not a meaningful parent
        ancestor_support = len(tally.get(ancestor_id, set()))
        if ancestor_support > parent_support:
            parent_id, parent_support = ancestor_id, ancestor_support
    fraction = support / parent_support if parent_support else 1.0
    won_at_min = support == CONVERGENCE_MIN
    thin = won_at_min and parent_support > support
    parent_name = (term_name(zfa_ontology, parent_id) or parent_id) if parent_id is not None else None
    return AuditRecord(
        cluster_id=cluster_id,
        named_id=named_id,
        named_name=named_name,
        named_support=support,
        parent_id=parent_id,
        parent_name=parent_name,
        parent_support=parent_support,
        support_fraction=fraction,
        won_at_min=won_at_min,
        thin_support_overcall=thin,
    )


def _audit_named(
    row: BenchmarkRow, label: Label, named_id: str, symbols: list[str], resources: Resources
) -> AuditRecord:
    """Replay the cluster's tally and audit its named winner (see _audit_from_tally)."""
    tally = _replay_tally(symbols, resources.expression_map, resources.zfa_ontology)
    return _audit_from_tally(row.cluster_id, named_id, label.bucket, tally, resources.zfa_ontology)


def _abstain_reason(label: Label, resources: Resources) -> str | None:
    """Why an abstention gave no identity call: contradictory germ layers, no panel hit, or weak signal.

    Args:
        label (Label): The cluster's label.
        resources (Resources): Loaded resources (for the identity-panel set).

    Returns:
        str | None: "mixed", "no_panel", or "weak_signal" for an abstention; None otherwise.
    """
    if not label.abstained:
        return None
    if label.ambiguity_flag == "mixed":
        return "mixed"
    identity = {panel.bucket for panel in resources.panels if panel.kind == KIND_IDENTITY}
    top = max((score for bucket, score in label.panel_scores.items() if bucket in identity), default=0.0)
    return "no_panel" if top == 0.0 else "weak_signal"


def cluster_outcomes(benchmark: list[BenchmarkRow], crosswalk: Crosswalk, resources: Resources) -> list[ClusterOutcome]:
    """Label and score every benchmark cluster, returning one ClusterOutcome each.

    This is the per-cluster data the aggregate Report projects from, and the table the diagnostic
    notebook explores. Every cluster is labeled (including not_scored ones) so the full benchmark is
    inspectable; the crosswalk still fails closed on an unmapped tissue.

    Args:
        benchmark (list[BenchmarkRow]): The benchmark clusters.
        crosswalk (Crosswalk): The fail-closed gold mapping.
        resources (Resources): Loaded engine resources.

    Returns:
        list[ClusterOutcome]: One outcome per cluster, in benchmark order.
    """
    outcomes: list[ClusterOutcome] = []
    for row in benchmark:
        gold = crosswalk.gold(row.broad_tissue)
        label, symbols = _label_row(row, resources)
        kind = _classify(label)
        agrees: bool | None = None
        if gold is not None and kind in (NAMED, FALLBACK):
            pred_ids = _prediction_anchor_ids(label, kind, resources)
            # Empty pred_ids (a named/fallback call that carried no anchor) stays agrees=None:
            # unscoreable against gold, not a disagreement.
            if pred_ids:
                agrees = any(grounds_under(resources.zfa_ontology, pid, gold) for pid in pred_ids)
        audit: AuditRecord | None = None
        if kind == NAMED and label.zfa_id is not None:
            audit = _audit_named(row, label, label.zfa_id, symbols, resources)
        outcomes.append(
            ClusterOutcome(
                cluster_id=row.cluster_id,
                gold_tissue=row.broad_tissue,
                tissue_name=row.tissue_name,
                stage_hpf=row.stage_hpf,
                markers=row.markers,
                n_resolved=len(symbols),
                kind=kind,
                bucket=label.bucket,
                panel_bucket=label.panel_bucket,
                zfa_id=label.zfa_id,
                depth=label.depth,
                scored=gold is not None,
                agrees=agrees,
                confidence=label.confidence,
                convergent_genes=label.convergent_genes,
                abstain_reason=_abstain_reason(label, resources),
                audit=audit,
            )
        )
    return outcomes


def evaluate(benchmark: list[BenchmarkRow], crosswalk: Crosswalk, resources: Resources) -> Report:
    """Run the engine over the benchmark and aggregate per-cluster outcomes into the Report.

    Args:
        benchmark (list[BenchmarkRow]): The benchmark clusters.
        crosswalk (Crosswalk): The fail-closed gold mapping.
        resources (Resources): Loaded engine resources.

    Returns:
        Report: The accumulated metrics, audit records, and failures (a projection of
        cluster_outcomes).
    """
    report = Report()
    for outcome in cluster_outcomes(benchmark, crosswalk, resources):
        report.total += 1
        if not outcome.scored:
            report.not_scored += 1
            continue
        report.counts[outcome.kind] += 1
        if outcome.audit is not None:
            report.audits.append(outcome.audit)  # record this scored named call's overcall audit
        # rollup / abstain carry no agreement (agrees is None by construction). A named/fallback call
        # reaches agrees is None only with no scoreable anchor -- impossible with valid panels (every
        # identity panel has an ontology_anchor), so on real data this gate only skips rollup/abstain.
        if outcome.agrees is None:
            continue
        tier = outcome.confidence or "none"
        report.conf_total[tier] += 1
        if outcome.agrees:
            report.correct[outcome.kind] += 1
            report.conf_correct[tier] += 1
        else:
            report.failures.append((outcome.cluster_id, outcome.gold_tissue, outcome.bucket, outcome.kind))
    return report


def _pct(num: int, denom: int) -> str:
    """Format a num/denom percentage, or n/a when the denominator is zero."""
    return f"{100 * num / denom:.1f}% ({num}/{denom})" if denom else "n/a (0)"


def render_report(report: Report, top_n: int = 15) -> str:
    """Render a deterministic, concise markdown report from accumulated outcomes.

    Args:
        report (Report): The accumulated outcomes.
        top_n (int): How many failure / overcall examples to list.

    Returns:
        str: The markdown report.
    """
    scored = report.total - report.not_scored
    assigned = report.counts[NAMED] + report.counts[FALLBACK]
    agree = report.correct[NAMED] + report.correct[FALLBACK]
    covered = assigned + report.counts[ROLLUP]

    lines = ["# Daniocell baseline report (anchor-rooted descent engine)", ""]
    lines += [f"- clusters: {report.total}  ·  scored: {scored}  ·  not_scored: {report.not_scored}", ""]
    lines += ["## Broad agreement (named + fallback, scored against the gold tissue)"]
    lines += [f"- agreement: {_pct(agree, assigned)}", ""]
    lines += ["## Coverage / split (over scored clusters)"]
    lines += [f"- coverage (non-abstain): {_pct(covered, scored)}"]
    for kind in (NAMED, FALLBACK, ROLLUP, ABSTAIN):
        lines.append(f"- {kind}: {_pct(report.counts[kind], scored)}")
    lines += ["", "## Agreement by prediction class"]
    for kind in (NAMED, FALLBACK):
        lines.append(f"- {kind}: {_pct(report.correct[kind], report.counts[kind])}")
    lines += ["", "## Confidence by correctness (named + fallback)"]
    for tier in ("high", "medium", "low", "none"):
        if report.conf_total[tier]:
            lines.append(f"- {tier}: {_pct(report.conf_correct[tier], report.conf_total[tier])}")

    # Parent-child overcall audit.
    won_min = sum(audit.won_at_min for audit in report.audits)
    thin_overcall_count = sum(audit.thin_support_overcall for audit in report.audits)
    lines += ["", "## Parent-child overcall audit (named calls)"]
    lines += [f"- named calls audited: {len(report.audits)}"]
    lines += [f"- won with exactly CONVERGENCE_MIN={CONVERGENCE_MIN} genes: {_pct(won_min, len(report.audits))}"]
    lines += [
        f"- thin-support overcalls (won at min, broader parent had more support): "
        f"{_pct(thin_overcall_count, len(report.audits))}"
    ]
    worst = sorted(report.audits, key=lambda audit: (audit.support_fraction, audit.cluster_id))[:top_n]
    if worst:
        lines += ["", f"Lowest support-fraction named calls (child support / best-parent support), top {top_n}:"]
        for audit in worst:
            parent = f"{audit.parent_name} ({audit.parent_support})" if audit.parent_id else "no broader parent"
            lines.append(
                f"- {audit.cluster_id}: {audit.named_name} ({audit.named_support}) vs {parent}"
                f"  -> fraction {audit.support_fraction:.2f}"
            )

    # Failure gallery (stably sorted).
    lines += ["", "## Failure gallery (scored disagreements)"]
    for cluster_id, tissue, bucket, kind in sorted(report.failures)[:top_n]:
        lines.append(f"- {cluster_id}: gold {tissue}, predicted {bucket!r} ({kind})")
    if len(report.failures) > top_n:
        lines.append(f"- ... and {len(report.failures) - top_n} more")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    """Run the evaluator from the command line.

    Args:
        argv (list[str] | None): Argument vector (defaults to sys.argv[1:]).

    Returns:
        int: 0 on success.
    """
    parser = argparse.ArgumentParser(description="Evaluate zlabel against the Daniocell benchmark.")
    parser.add_argument("benchmark", help="benchmark CSV (cluster_id, markers, broad_tissue, ...)")
    parser.add_argument("--crosswalk", default="benchmarks/daniocell_tissue_crosswalk.yaml")
    parser.add_argument("--data-dir", default="data/ontologies", help="dir with zfa.obo, zfin.gaf, expression")
    parser.add_argument("--panels", default="src/zlabel/panels.yaml")
    parser.add_argument("--out", default="benchmarks/daniocell_baseline_report.md")
    parser.add_argument("--top-n", type=int, default=15)
    args = parser.parse_args(argv)

    data = Path(args.data_dir)
    resources = load_resources(
        zfa_path=data / "zfa.obo",
        expr_path=data / "zfin_wildtype_expression.txt",
        gaf_path=data / "zfin.gaf",
        panels_path=args.panels,
    )
    benchmark = load_benchmark(args.benchmark)
    crosswalk = load_crosswalk(args.crosswalk)
    report = render_report(evaluate(benchmark, crosswalk, resources), top_n=args.top_n)
    Path(args.out).write_text(report, encoding="utf-8")
    sys.stdout.write(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
