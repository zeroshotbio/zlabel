"""Evaluate the zlabel engine against the Daniocell broad-tissue benchmark.

Reads a benchmark CSV (cluster_id, markers, broad_tissue, ...), labels each cluster with
the current engine, and scores broad agreement in ZFA-ancestry space against a reviewed,
fail-closed tissue-to-ZFA crosswalk. Reports coverage, the named/fallback/rollup/abstain
split, confidence-by-correctness, and a structural parent-child overcall audit -- the
signal for whether IC-first naming overcalls on real clusters.

This module is read-only over the engine: it reuses the public loaders and decide(), and
changes no decision logic. It loads the ontologies once and calls decide() with each row's
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
from zlabel.genes import STATUS_RESOLVED, normalize_markers
from zlabel.ground import expression_lookup, grounds_under
from zlabel.label import decide
from zlabel.models import Label
from zlabel.panels import Panel, load_panels, score_markers
from zlabel.resolve import CONVERGENCE_MIN, build_ic

# Prediction classes (how the engine resolved a cluster).
NAMED = "named"        # the convergence vote named a ZFA term
FALLBACK = "fallback"  # vote found nothing / guardrail fired -> coarse panel bucket
ROLLUP = "rollup"      # near-tie within a shared germ layer -> germ-layer tier
ABSTAIN = "abstain"    # mixed / no signal


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

    zfa: nx.MultiDiGraph
    expr: dict[str, list[ZfinExpressionRecord]]
    synonyms: dict[str, set[str]]
    panels: list[Panel]
    anchors: dict[str, frozenset[str]]
    ic: dict[str, float]


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
    failures: list[tuple[str, str, str, str]] = field(default_factory=list)


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
        for r in csv.DictReader(handle):
            stage = r.get("stage_hpf", "").strip()
            rows.append(
                BenchmarkRow(
                    cluster_id=r["cluster_id"],
                    markers=[m for m in r["markers"].split(";") if m],
                    broad_tissue=r["broad_tissue"],
                    tissue_name=r.get("tissue_name", ""),
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
    zfa = load_zfa(zfa_path)
    expr = load_zfin_expression(expr_path)
    synonyms = load_gene_synonym_map(gaf_path)
    panels = load_panels(panels_path)
    anchors = {p.bucket: p.ontology_anchor for p in panels}
    ic = build_ic(expr, zfa)
    return Resources(zfa, expr, synonyms, panels, anchors, ic)


def _label_row(row: BenchmarkRow, res: Resources) -> tuple[Label, list[str]]:
    """Label one cluster at its own stage; also return its normalized symbols for the audit."""
    norm = normalize_markers(row.markers, res.synonyms)
    symbols = [next(iter(ns.symbols)) for ns in norm if ns.status == STATUS_RESOLVED]
    scores = score_markers(row.markers, res.panels, res.synonyms)
    label = decide(
        scores,
        anchors=res.anchors,
        expr_map=res.expr,
        zfa_graph=res.zfa,
        stage_hpf=row.stage_hpf,
        symbols=symbols,
        ic=res.ic,
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


def _prediction_anchor_ids(label: Label, kind: str, res: Resources) -> frozenset[str]:
    """The ZFA ids to score a prediction by.

    Named calls score by the voted term. Fallback calls are enriched eval-side: Label.zfa_id
    keeps only sorted(anchor)[0], so we recover the full panel ontology_anchor from
    panel_bucket rather than scoring against a truncated anchor.

    Args:
        label (Label): The engine's label for the cluster.
        kind (str): The prediction class from _classify.
        res (Resources): Loaded resources (for the panel anchor lookup).

    Returns:
        frozenset[str]: The ZFA ids the prediction is scored under; empty for
        rollup/abstain (which carry no ZFA handle).
    """
    if kind == NAMED and label.zfa_id is not None:
        return frozenset({label.zfa_id})
    if kind == FALLBACK:
        return res.anchors.get(label.panel_bucket, frozenset())
    return frozenset()


def _replay_tally(
    symbols: list[str],
    expr_map: dict[str, list[ZfinExpressionRecord]],
    zfa_graph: nx.MultiDiGraph,
) -> dict[str, set[str]]:
    """Reconstruct the raw per-term gene tally (all terms, before the IC/stoplist gates).

    Mirrors resolve.resolve_label's tally exactly so the audit can see IC-filtered parent
    terms the engine's gated output drops. A unit test pins this against resolve_label.

    Args:
        symbols (list[str]): Already-normalized current ZFIN symbols (as decide() received).
        expr_map (dict[str, list[ZfinExpressionRecord]]): The loaded expression data.
        zfa_graph (nx.MultiDiGraph): The loaded ZFA ontology.

    Returns:
        dict[str, set[str]]: ZFA term id to the distinct genes that credit it.
    """
    anc_cache: dict[str, frozenset[str]] = {}

    def credited(zfa_id: str) -> frozenset[str]:
        if zfa_id in anc_cache:
            return anc_cache[zfa_id]
        if zfa_id not in zfa_graph:
            result: frozenset[str] = frozenset({zfa_id})
        else:
            result = frozenset({zfa_id}) | frozenset(ancestors(zfa_graph, zfa_id))
        anc_cache[zfa_id] = result
        return result

    tally: dict[str, set[str]] = {}
    seen: set[str] = set()
    for sym in symbols:
        if sym in seen:
            continue
        seen.add(sym)
        records = expression_lookup(expr_map, sym)
        if not records:
            continue
        cred: set[str] = set()
        for rec in records:
            cred |= credited(rec.zfa_id)
        for t in cred:
            tally.setdefault(t, set()).add(sym)
    return tally


def _audit_from_tally(
    cluster_id: str,
    named_id: str,
    named_name: str,
    tally: dict[str, set[str]],
    zfa: nx.MultiDiGraph,
) -> AuditRecord:
    """Compare a named winner's support to its best-supported ancestor (the overcall signal).

    A thin-support overcall is a winner that cleared exactly CONVERGENCE_MIN genes while a
    broader ancestor (often IC-filtered out of the engine's candidates) had strictly more
    support -- the IC-first sort preferring specificity over consensus. Pure over the tally.

    Args:
        cluster_id (str): The cluster id.
        named_id (str): The named ZFA term id.
        named_name (str): The label bucket name (for display).
        tally (dict[str, set[str]]): The raw per-term gene tally from _replay_tally.
        zfa (nx.MultiDiGraph): The ZFA ontology (for the ancestor walk and names).

    Returns:
        AuditRecord: The parent-child support comparison for this call.
    """
    support = len(tally.get(named_id, set()))
    parent_id: str | None = None
    parent_support = 0
    parents = ancestors(zfa, named_id) if named_id in zfa else []
    for a in parents:
        a_support = len(tally.get(a, set()))
        if a_support > parent_support:
            parent_id, parent_support = a, a_support
    fraction = support / parent_support if parent_support else 1.0
    won_at_min = support == CONVERGENCE_MIN
    thin = won_at_min and parent_support > support
    parent_name = (term_name(zfa, parent_id) or parent_id) if parent_id is not None else None
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


def _audit_named(row: BenchmarkRow, label: Label, named_id: str, symbols: list[str], res: Resources) -> AuditRecord:
    """Replay the cluster's tally and audit its named winner (see _audit_from_tally)."""
    tally = _replay_tally(symbols, res.expr, res.zfa)
    return _audit_from_tally(row.cluster_id, named_id, label.bucket, tally, res.zfa)


def evaluate(benchmark: list[BenchmarkRow], crosswalk: Crosswalk, res: Resources) -> Report:
    """Run the engine over the benchmark and accumulate outcomes.

    Args:
        benchmark (list[BenchmarkRow]): The benchmark clusters.
        crosswalk (Crosswalk): The fail-closed gold mapping.
        res (Resources): Loaded engine resources.

    Returns:
        Report: The accumulated metrics, audit records, and failures.
    """
    rep = Report()
    for row in benchmark:
        rep.total += 1
        gold = crosswalk.gold(row.broad_tissue)
        if gold is None:
            rep.not_scored += 1
            continue
        label, symbols = _label_row(row, res)
        kind = _classify(label)
        rep.counts[kind] += 1
        if kind not in (NAMED, FALLBACK):
            continue  # rollup / abstain: counted for coverage, out of agreement
        pred_ids = _prediction_anchor_ids(label, kind, res)
        agrees = any(grounds_under(res.zfa, pid, gold) for pid in pred_ids)
        tier = label.confidence or "none"
        rep.conf_total[tier] += 1
        if agrees:
            rep.correct[kind] += 1
            rep.conf_correct[tier] += 1
        else:
            rep.failures.append((row.cluster_id, row.broad_tissue, label.bucket, kind))
        if kind == NAMED and label.zfa_id is not None:
            rep.audits.append(_audit_named(row, label, label.zfa_id, symbols, res))
    return rep


def _pct(num: int, denom: int) -> str:
    """Format a num/denom percentage, or n/a when the denominator is zero."""
    return f"{100 * num / denom:.1f}% ({num}/{denom})" if denom else "n/a (0)"


def render_report(rep: Report, top_n: int = 15) -> str:
    """Render a deterministic, concise markdown report from accumulated outcomes.

    Args:
        rep (Report): The accumulated outcomes.
        top_n (int): How many failure / overcall examples to list.

    Returns:
        str: The markdown report.
    """
    scored = rep.total - rep.not_scored
    assigned = rep.counts[NAMED] + rep.counts[FALLBACK]
    agree = rep.correct[NAMED] + rep.correct[FALLBACK]
    covered = assigned + rep.counts[ROLLUP]

    lines = ["# Daniocell baseline report (IC-first engine)", ""]
    lines += [f"- clusters: {rep.total}  ·  scored: {scored}  ·  not_scored: {rep.not_scored}", ""]
    lines += ["## Broad agreement (named + fallback, scored against the gold tissue)"]
    lines += [f"- agreement: {_pct(agree, assigned)}", ""]
    lines += ["## Coverage / split (over scored clusters)"]
    lines += [f"- coverage (non-abstain): {_pct(covered, scored)}"]
    for kind in (NAMED, FALLBACK, ROLLUP, ABSTAIN):
        lines.append(f"- {kind}: {_pct(rep.counts[kind], scored)}")
    lines += ["", "## Agreement by prediction class"]
    for kind in (NAMED, FALLBACK):
        lines.append(f"- {kind}: {_pct(rep.correct[kind], rep.counts[kind])}")
    lines += ["", "## Confidence by correctness (named + fallback)"]
    for tier in ("high", "medium", "low", "none"):
        if rep.conf_total[tier]:
            lines.append(f"- {tier}: {_pct(rep.conf_correct[tier], rep.conf_total[tier])}")

    # Parent-child overcall audit.
    won_min = sum(a.won_at_min for a in rep.audits)
    thin = sum(a.thin_support_overcall for a in rep.audits)
    lines += ["", "## Parent-child overcall audit (named calls)"]
    lines += [f"- named calls audited: {len(rep.audits)}"]
    lines += [f"- won with exactly CONVERGENCE_MIN={CONVERGENCE_MIN} genes: {_pct(won_min, len(rep.audits))}"]
    lines += [f"- thin-support overcalls (won at min, broader parent had more support): {_pct(thin, len(rep.audits))}"]
    worst = sorted(rep.audits, key=lambda a: (a.support_fraction, a.cluster_id))[:top_n]
    if worst:
        lines += ["", f"Lowest support-fraction named calls (child support / best-parent support), top {top_n}:"]
        for a in worst:
            parent = f"{a.parent_name} ({a.parent_support})" if a.parent_id else "no broader parent"
            lines.append(
                f"- {a.cluster_id}: {a.named_name} ({a.named_support}) vs {parent}"
                f"  -> fraction {a.support_fraction:.2f}"
            )

    # Failure gallery (stably sorted).
    lines += ["", "## Failure gallery (scored disagreements)"]
    for cluster_id, tissue, bucket, kind in sorted(rep.failures)[:top_n]:
        lines.append(f"- {cluster_id}: gold {tissue}, predicted {bucket!r} ({kind})")
    if len(rep.failures) > top_n:
        lines.append(f"- ... and {len(rep.failures) - top_n} more")
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
    res = load_resources(
        zfa_path=data / "zfa.obo",
        expr_path=data / "zfin_wildtype_expression.txt",
        gaf_path=data / "zfin.gaf",
        panels_path=args.panels,
    )
    benchmark = load_benchmark(args.benchmark)
    crosswalk = load_crosswalk(args.crosswalk)
    report = render_report(evaluate(benchmark, crosswalk, res), top_n=args.top_n)
    Path(args.out).write_text(report, encoding="utf-8")
    sys.stdout.write(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
