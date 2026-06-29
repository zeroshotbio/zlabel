"""Realizable coverage-headroom scan: which eval clusters a missing panel/anchor blocks (read-only).

Phase-3 follow-up to the ZFA usefulness audit. The backlog-grounding lever is dead on the benchmarks
(0 of 629 eval clusters carry even both current markers of any near-bar T4 cell type, so adding a third
curated gene cannot help), which leaves one live coverage lever: adding a panel/anchor for a well-grounded
useful term that has none. This scan runs the current engine over all three eval atlases and, per cluster,
asks whether a NEW panel could convert it to a correct (or deeper-correct) named call -- attributing every
shortfall to a cause so the realizable headroom is an exact, enumerated number rather than a guess.

A cluster is panel-addable when its markers converge (support >= CONVERGENCE_MIN) on a useful (T1/T2) ZFA
term that grounds under the broad gold (so naming it would be correct) yet is unreachable from the current
panel anchors. Reachable-but-unemitted is selection-bound (a support-floor / panel-score issue, not a panel
fix); no useful supported term at all is resolution-bound (a genuinely low-resolution cluster). The
support >= 3 test predicts firing; a confirming panel plus make gate-all is the proof (see the plan).

Correctness uses the overlay-extended gold where an overlay exists (matching the eval's overlay-corrected
agreement), so headroom is not claimed on clusters the overlay already credits. Writes
coverage_headroom.csv (per scored cluster) + coverage_headroom.md. No engine change.

Run: uv run python analysis/zfa_usefulness/coverage_headroom.py
"""

from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path

import networkx as nx
from coverage import reach

from zlabel.data import ancestors, load_zfa, term_name
from zlabel.evaluate import (
    NAMED,
    Resources,
    _classify,
    _label_row,
    _prediction_anchor_ids,
    _replay_tally,
    extend_crosswalk,
    load_benchmark,
    load_crosswalk,
    load_resources,
    overlay_for,
)
from zlabel.ground import grounds_under
from zlabel.resolve import CONVERGENCE_MIN, DESCENT_SUPPORT_FRACTION, STOPLIST

OUT = Path(__file__).resolve().parent
REPO = OUT.parents[1]
DATA = REPO / "data" / "ontologies"
PANELS = REPO / "src" / "zlabel" / "panels.yaml"
BENCH = REPO / "benchmarks"

USEFUL_TIERS = ("T1", "T2")

# Generic tokens dropped before testing whether a candidate term matches the cluster's fine gold label.
# Without these, "X cell" vs "Y cell" would falsely match on "cell"; with them, a real subtype overlap
# (periderm/periderm, pharyngeal arch/pharyngeal arch) survives while a cross-subtype pick (ovary for a
# thyroid follicle cell cluster) is correctly flagged as broad-gold-only.
NAME_STOPWORDS = frozenset(
    {
        "cell",
        "the",
        "of",
        "a",
        "an",
        "and",
        "or",
        "early",
        "mid",
        "late",
        "maybe",
        "contains",
        "progenitor",
        "derived",
        "nc",
        "ventral",
        "dorsal",
        "anterior",
        "posterior",
        "like",
        "type",
        "primordium",
        "anlage",
        "region",
        "structure",
        "tissue",
        "portion",
        "system",
        "gland",
    }
)


def _tokens(name: str) -> set[str]:
    """Content tokens of a term/label name (lowercased, alphabetic, minus generic stopwords)."""
    raw = {tok for tok in "".join(c if c.isalpha() else " " for c in name.lower()).split() if len(tok) > 2}
    return raw - NAME_STOPWORDS


def fine_match(candidate_name: str, fine_gold: str) -> bool:
    """Whether a candidate term plausibly names the cluster's FINE identity (not just the broad gold).

    A content-token overlap between the candidate ZFA term name and the atlas's fine tissue_name. This
    separates a right-subtype add (periderm for a periderm cluster) from a cross-subtype artifact that
    merely grounds under an over-broad gold (ovary for a thyroid follicle cluster). Heuristic, so it is
    reported alongside the raw count rather than used to silently drop rows.

    Args:
        candidate_name (str): The candidate ZFA term name.
        fine_gold (str): The atlas's fine tissue_name for the cluster.

    Returns:
        bool: True when the names share a content token.
    """
    return bool(_tokens(candidate_name) & _tokens(fine_gold))


# (atlas label, benchmark csv, tissue crosswalk) for the three committed eval substrates.
ATLASES = (
    ("daniocell", "daniocell_eval.csv", "daniocell_tissue_crosswalk.yaml"),
    ("zscape", "zscape_eval.csv", "zscape_tissue_crosswalk.yaml"),
    ("zebrahub", "zebrahub_eval.csv", "zebrahub_tissue_crosswalk.yaml"),
)

# Category order for stable reporting.
CATEGORIES = (
    "covered",
    "panel_addable_new_correct",
    "panel_addable_deeper_correct",
    "selection_bound",
    "resolution_bound",
)


def load_tiers() -> dict[str, str]:
    """Map each ZFA id to its usefulness tier (from the audit's per-term CSV).

    Returns:
        dict[str, str]: ZFA id to tier label (T1..T5).
    """
    with (OUT / "zfa_term_usefulness.csv").open(encoding="utf-8") as handle:
        return {row["zfa_id"]: row["tier"] for row in csv.DictReader(handle)}


def reachable_terms(resources: Resources, graph: nx.MultiDiGraph) -> set[str]:
    """All ZFA terms reachable by is_a+part_of descent from the panel anchors (anchors themselves included).

    Args:
        resources (Resources): Loaded engine resources (for the per-bucket anchors).
        graph (nx.MultiDiGraph): The ZFA ontology.

    Returns:
        set[str]: Every term the current descent can in principle reach from a panel anchor.
    """
    anchor_ids = {anchor for anchors in resources.anchors.values() for anchor in anchors}
    return anchor_ids | reach(graph, anchor_ids, {"is_a", "part_of"})


def depth(graph: nx.MultiDiGraph, term: str | None) -> int:
    """Specificity proxy: a term's is_a+part_of ancestor count (deeper = more specific).

    Args:
        graph (nx.MultiDiGraph): The ZFA ontology.
        term (str | None): A ZFA id, or None.

    Returns:
        int: The ancestor count, or -1 when the term is None or absent.
    """
    if term is None or term not in graph:
        return -1
    return len(set(ancestors(graph, term)))


def best_parent_support(graph: nx.MultiDiGraph, term: str, tally: dict[str, set[str]]) -> int:
    """Max support among a term's ancestors (content-free stoplist roots excluded): the 0.6-floor denominator.

    Args:
        graph (nx.MultiDiGraph): The ZFA ontology.
        term (str): The candidate ZFA id.
        tally (dict[str, set[str]]): The cluster's per-term gene tally.

    Returns:
        int: The largest credited-gene count over the term's meaningful ancestors.
    """
    best = 0
    if term in graph:
        for ancestor_id in ancestors(graph, term):
            if ancestor_id in STOPLIST:
                continue
            best = max(best, len(tally.get(ancestor_id, ())))
    return best


def classify_cluster(
    atlas: str,
    row: object,
    resources: Resources,
    graph: nx.MultiDiGraph,
    gold: frozenset[str],
    reachable: set[str],
    tiers: dict[str, str],
) -> dict[str, object]:
    """Classify one scored cluster and, when panel-addable, record the term a new panel would name.

    Args:
        atlas (str): The atlas label.
        row (object): A BenchmarkRow (cluster markers, broad/fine gold, stage).
        resources (Resources): Loaded engine resources.
        graph (nx.MultiDiGraph): The ZFA ontology.
        gold (frozenset[str]): The (overlay-extended) gold anchors for this cluster's tissue.
        reachable (set[str]): Terms reachable from the current panel anchors.
        tiers (dict[str, str]): ZFA id to usefulness tier.

    Returns:
        dict[str, object]: One CSV row -- the cluster, its current call, the category, and the
        best panel-addable candidate term (when any).
    """
    label, symbols = _label_row(row, resources)  # type: ignore[arg-type]
    kind = _classify(label)
    pred_ids = _prediction_anchor_ids(label, kind, resources)
    current_correct = bool(pred_ids and any(grounds_under(graph, pid, gold) for pid in pred_ids))
    tally = _replay_tally(symbols, resources.expression_map, resources.zfa_ontology)

    # Terms a NEW panel could name: enough cluster support, useful, correct vs gold, currently unreachable.
    candidates = [
        term
        for term, genes in tally.items()
        if len(genes) >= CONVERGENCE_MIN
        and tiers.get(term) in USEFUL_TIERS
        and term not in reachable
        and grounds_under(graph, term, gold)
    ]
    best = max(candidates, key=lambda term: (depth(graph, term), len(tally[term])), default=None)
    current_depth = depth(graph, label.zfa_id) if kind == NAMED else -1

    if best is not None:
        if not current_correct:
            category = "panel_addable_new_correct"
        elif depth(graph, best) > current_depth:
            category = "panel_addable_deeper_correct"
        else:
            category = "covered"
    elif current_correct:
        category = "covered"
    else:
        reachable_useful = any(
            len(genes) >= CONVERGENCE_MIN and tiers.get(term) in USEFUL_TIERS and grounds_under(graph, term, gold)
            for term, genes in tally.items()
        )
        category = "selection_bound" if reachable_useful else "resolution_bound"

    parent_support = best_parent_support(graph, best, tally) if best else 0
    candidate_support = len(tally[best]) if best else 0
    return {
        "atlas": atlas,
        "cluster_id": row.cluster_id,  # type: ignore[attr-defined]
        "broad_gold": row.broad_tissue,  # type: ignore[attr-defined]
        "fine_gold": row.tissue_name,  # type: ignore[attr-defined]
        "current_kind": kind,
        "current_bucket": label.bucket,
        "current_correct": int(current_correct),
        "category": category,
        "candidate_zfa": best or "",
        "candidate_name": (term_name(graph, best) or best) if best else "",
        "candidate_tier": tiers.get(best, "") if best else "",
        "candidate_support": candidate_support,
        "candidate_depth": depth(graph, best) if best else -1,
        "best_parent_support": parent_support,
        "clears_06_floor": int(candidate_support >= DESCENT_SUPPORT_FRACTION * parent_support) if best else 0,
        "fine_match": int(fine_match(term_name(graph, best) or "", row.tissue_name)) if best else 0,  # type: ignore[attr-defined]
    }


def render_md(rows: list[dict[str, object]], unmapped: int) -> str:
    """Render the headroom summary markdown from the per-cluster rows.

    Args:
        rows (list[dict[str, object]]): One row per scored cluster (classify_cluster output).
        unmapped (int): Clusters skipped because their tissue was absent from the crosswalk.

    Returns:
        str: The markdown report.
    """
    by_cat = Counter(r["category"] for r in rows)
    addable = [r for r in rows if str(r["category"]).startswith("panel_addable")]
    new_correct = [r for r in addable if r["category"] == "panel_addable_new_correct"]
    new_correct_fine = [r for r in new_correct if r["fine_match"] == 1]
    floor_ok = [r for r in addable if r["clears_06_floor"] == 1]
    by_term = Counter(f"{r['candidate_name']} ({r['candidate_zfa']})" for r in addable)
    by_atlas_cat: dict[str, Counter[str]] = {}
    for r in rows:
        by_atlas_cat.setdefault(str(r["atlas"]), Counter())[str(r["category"])] += 1

    lines = [
        "# Realizable coverage headroom — what a missing panel/anchor blocks",
        "",
        "Read-only. Runs the current engine over all committed eval clusters and asks, per cluster, whether",
        "a NEW panel/anchor could turn it into a correct (or deeper-correct) named call. Useful = T1/T2.",
        "Correctness is overlay-extended where an overlay exists (matches the eval's overlay-corrected",
        f"agreement), so headroom is conservative. Firing is predicted by support >= {CONVERGENCE_MIN}; a confirming",
        "panel + make gate-all is the proof. The 0.6-floor flag estimates whether the call would also clear",
        f"DESCENT_SUPPORT_FRACTION={DESCENT_SUPPORT_FRACTION} when descended from a higher anchor (anchoring",
        "directly at the term avoids that floor).",
        "",
        f"Scored clusters classified: **{len(rows)}** (plus {unmapped} skipped as unmapped/out-of-scope).",
        "",
        "## Categories",
        "",
        "| category | count | meaning |",
        "|---|---|---|",
        f"| covered | {by_cat['covered']} | clean correct call — no headroom |",
        f"| **panel_addable_new_correct** | **{by_cat['panel_addable_new_correct']}** | "
        "not correctly covered, but markers converge on an unreachable useful correct term — a NEW panel "
        "would add a correct call |",
        f"| panel_addable_deeper_correct | {by_cat['panel_addable_deeper_correct']} | "
        "already correct, but an unreachable finer useful term is supported — a panel would deepen it |",
        f"| selection_bound | {by_cat['selection_bound']} | a useful correct term IS reachable but the "
        "engine did not emit it (support-floor / panel-score) — not a panel fix |",
        f"| resolution_bound | {by_cat['resolution_bound']} | no useful term reaches support >= "
        f"{CONVERGENCE_MIN} — a genuinely low-resolution cluster |",
        "",
        f"**Headline (upper bound): {len(new_correct)} new-correct + {by_cat['panel_addable_deeper_correct']} "
        f"deeper-correct = {len(addable)} panel-addable clusters** ({len(floor_ok)} also clear the 0.6 floor).",
        f"**Of the {len(new_correct)} new-correct, {len(new_correct_fine)} have a candidate that matches the "
        "cluster's FINE label** (likely right subtype); the rest only ground under an over-broad gold "
        "(e.g. ovary for a thyroid follicle cluster) and are probably not real panels.",
        "",
        "## Panel-addable by candidate term (the actionable curation list)",
        "",
        "`fine` = clusters whose candidate matches the fine label (the trustworthy subset).",
        "",
    ]
    if by_term:
        lines += ["| candidate term | clusters | fine | atlases |", "|---|---|---|---|"]
        for term, count in by_term.most_common():
            term_rows = [r for r in addable if f"{r['candidate_name']} ({r['candidate_zfa']})" == term]
            fine = sum(1 for r in term_rows if r["fine_match"] == 1)
            atlases = sorted({str(r["atlas"]) for r in term_rows})
            lines.append(f"| {term} | {count} | {fine} | {', '.join(atlases)} |")
    else:
        lines.append("(none — no cluster is panel-addable)")
    lines += ["", "## Panel-addable clusters (detail)", ""]
    if addable:
        lines.append("| atlas | cluster | broad gold | fine gold | current | candidate | sup | floor |")
        lines.append("|---|---|---|---|---|---|---|---|")
        for r in sorted(addable, key=lambda r: (str(r["candidate_name"]), str(r["atlas"]), str(r["cluster_id"]))):
            floor = "ok" if r["clears_06_floor"] == 1 else "risk"
            kindmark = r["current_kind"] if r["current_correct"] == 0 else f"{r['current_kind']}*"
            lines.append(
                f"| {r['atlas']} | {r['cluster_id']} | {r['broad_gold']} | {r['fine_gold']} | {kindmark} | "
                f"{r['candidate_name']} | {r['candidate_support']} | {floor} |"
            )
        lines.append("")
        lines.append("(* current call already correct at a coarser term; the candidate would deepen it.)")
    else:
        lines.append("(none)")
    lines += ["", "## By atlas", "", "| atlas | " + " | ".join(CATEGORIES) + " |", "|---|" + "---|" * len(CATEGORIES)]
    for atlas in (a[0] for a in ATLASES):
        if atlas in by_atlas_cat:
            counts = by_atlas_cat[atlas]
            lines.append(f"| {atlas} | " + " | ".join(str(counts[c]) for c in CATEGORIES) + " |")
    lines += [
        "",
        "## Reading this",
        "",
        "panel_addable_new_correct is the realizable coverage gain from adding panels. If it is small, the",
        "two earlier coverage levers (develops_from, backlog grounding) plus this one are all exhausted and",
        "coverage is anchor/resolution-bound — document and close. If it is material, each candidate term is",
        "a curation target: add a panel anchored at (or just above) it, then confirm with make gate-all that",
        "it yields real new/deeper correct calls with the thin-overcall line unchanged.",
        "",
        "Full per-cluster classification: coverage_headroom.csv.",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    """Scan all eval atlases, classify each scored cluster, and write the CSV + markdown."""
    graph = load_zfa(DATA / "zfa.obo")
    resources = load_resources(
        zfa_path=DATA / "zfa.obo",
        expr_path=DATA / "zfin_wildtype_expression.txt",
        gaf_path=DATA / "zfin.gaf",
        panels_path=PANELS,
    )
    tiers = load_tiers()
    reachable = reachable_terms(resources, graph)

    rows: list[dict[str, object]] = []
    unmapped = 0
    for atlas, csv_name, cross_name in ATLASES:
        bench_path = BENCH / csv_name
        if not bench_path.exists():
            continue
        benchmark = load_benchmark(bench_path)
        crosswalk = load_crosswalk(BENCH / cross_name)
        overlay = overlay_for(BENCH / cross_name)
        extended = extend_crosswalk(crosswalk, overlay) if overlay else crosswalk
        for row in benchmark:
            try:
                gold = extended.gold(row.broad_tissue)
            except KeyError:
                unmapped += 1
                continue
            if gold is None:  # not_scored tissue
                continue
            rows.append(classify_cluster(atlas, row, resources, graph, gold, reachable, tiers))

    fieldnames = list(rows[0].keys())
    with (OUT / "coverage_headroom.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    md = render_md(rows, unmapped)
    (OUT / "coverage_headroom.md").write_text(md, encoding="utf-8")
    print(md)


if __name__ == "__main__":
    main()
