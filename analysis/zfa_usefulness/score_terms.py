"""Examine ZFA term usefulness as cell-type / anatomy labels for zlabel (read-only).

This is an analysis script, NOT part of the engine. It scores every ZFA term on a
"usefulness" rubric grounded in one principle: a useful label names a biologically
real entity whose place in the hierarchy corresponds to a real, expression-discernible
distinction. Pure administrative containers (anatomical system, cell, portion of tissue)
score lowest; specific, well-grounded, discernible cell types score highest.

It reuses zlabel's own loaders and IC / specificity models so the metrics match the
engine exactly (data.load_zfa, data.load_zfin_expression, resolve.build_information_content,
resolve._term_with_ancestors / CONVERGENCE_MIN / STOPLIST). It writes three artifacts next
to itself and prints a summary:

    zfa_term_usefulness.csv  -- per term: sub-signals, composite, tier, flags
    zfa_edges.csv            -- per is_a/part_of edge: sufficiency-gated discernibility
    summary.json             -- the aggregate numbers the REPORT.md cites

Run from the zlabel repo root:  uv run python analysis/zfa_usefulness/score_terms.py
Nothing in src/ is imported for mutation and no engine behavior is changed.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from collections.abc import Mapping
from pathlib import Path

import networkx as nx

from zlabel.data import (
    DEFAULT_ANCESTOR_EDGE_TYPES,
    ZfinExpressionRecord,
    load_zfa,
    load_zfin_expression,
    term_name,
)
from zlabel.panels import ATTRACTOR_BUCKETS, load_panels
from zlabel.resolve import (
    CONVERGENCE_MIN,
    STOPLIST,
    _term_with_ancestors,
    build_information_content,
)

# --- paths -------------------------------------------------------------------

REPO = Path(__file__).resolve().parents[2]
DATA = REPO / "data" / "ontologies"
BENCH = REPO / "benchmarks"
PANELS_YAML = REPO / "src" / "zlabel" / "panels.yaml"
OUT = Path(__file__).resolve().parent

# --- rubric thresholds (provisional; calibrated against curation below) -------
#
# Grounding (credited-gene count) is the PRIMARY axis, not IC: a term credited by only 3
# genes has IC ~12 (looks "specific") purely because the corpus is sparse. So sufficiency
# decides the tier; IC is used only at the LOW end, where it reliably flags breadth (a term
# almost every gene rolls up into has near-zero IC).

SOLID_GENES = 10  # >= this many credited genes: a confident expression signature -> Tier 1 eligible
BROAD_FOOTPRINT = 1000  # >= this many credited genes + low IC + non-curated -> broad/promiscuous (Tier 3)
IC_BROAD = 3.0  # <= this IC: the term's footprint spans a large share of the corpus (broad)
FANOUT_CONTAINER = 40  # >= this many children + low IC + non-cell + non-curated -> structural container
IC_CONTAINER = 1.5
SUFFICIENT_GENES = CONVERGENCE_MIN  # both edge endpoints need this many credited genes to judge a step
RETAINED_DISCERNIBLE_MAX = 0.95  # a discernible step drops > 5% of the parent's footprint
RETAINED_DEAD_MIN = 0.98  # a dead step retains ~all of the parent's footprint (a renaming)

# Administrative / abstract container names that are never a useful label, however deep.
ADMIN_EXACT = {
    "unspecified",
    "cell",
    "tissue",
    "structure",
    "organ",
    "organ part",
    "organ system",
    "compound organ",
    "organ subunit",
    "body part",
    "anatomical structure",
    "anatomical system",
    "anatomical group",
    "anatomical cluster",
    "anatomical entity",
    "anatomical space",
    "anatomical region",
    "anatomical conduit",
    "anatomical junction",
    "anatomical line",
    "anatomical surface",
    "zebrafish anatomical entity",
    "whole organism",
    "multicellular anatomical structure",
    "multi-tissue structure",
    "embryonic structure",
    "presumptive structure",
    "portion of tissue",
    "portion of organism substance",
    "organism subdivision",
    "material anatomical entity",
    "immaterial anatomical entity",
}
ADMIN_PREFIX = ("anatomical ",)
ADMIN_SUBSTR = ("portion of ",)
# NB: a generic " cluster"/" group" suffix is deliberately NOT treated as admin -- it would sweep
# real (if obscure) developmental domains (proneural cluster, forerunner cell group) into T5. Those
# are real-but-ungroundable (T4); only the explicit content-free names in ADMIN_EXACT are dropped.


def is_admin_name(name: str) -> bool:
    """Whether a term name is a content-free administrative container.

    These name an aggregation ("anatomical system", "portion of tissue", "cell") with no
    expression signature of their own, so naming a cluster with one says nothing useful.
    """
    low = name.lower().strip()
    if low in ADMIN_EXACT:
        return True
    if any(low.startswith(p) for p in ADMIN_PREFIX):
        return True
    return any(s in low for s in ADMIN_SUBSTR)


# --- attribute helpers (obonet stores node attrs as str or list) -------------


def _as_list(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    return [str(v) for v in value]  # type: ignore[arg-type]


def subsets_of(attrs: dict) -> set[str]:
    """The OBO subset tags on a term (e.g. cell_slim)."""
    return set(_as_list(attrs.get("subset")))


def has_cl_xref(attrs: dict) -> bool:
    """Whether a term cross-references the Cell Ontology (CL) -- the cell-type-axis signal."""
    return any(x.startswith("CL:") for x in _as_list(attrs.get("xref")))


def is_obsolete(attrs: dict) -> bool:
    """Whether a term is flagged obsolete (obonet drops these from the graph, so it is ~always False)."""
    flag = attrs.get("is_obsolete")
    return flag is True or (isinstance(flag, str) and flag.lower() == "true")


# --- curation: terms a human already vetted as useful labels ------------------


def load_curated_anchors() -> set[str]:
    """Every ZFA id used as a curated anchor in panels, crosswalks, or the coverage checklist."""
    curated: set[str] = set()
    for panel in load_panels(PANELS_YAML):
        curated |= set(panel.ontology_anchor)
    for yaml_path in sorted(BENCH.glob("*_tissue_crosswalk.yaml")):
        import yaml

        doc = yaml.safe_load(yaml_path.read_text(encoding="utf-8")) or {}
        for entry in (doc.get("tissues") or {}).values():
            curated |= set(entry.get("anchors", []) if isinstance(entry, dict) else [])
    coverage_path = BENCH / "cell_population_coverage.yaml"
    if coverage_path.exists():
        import yaml

        doc = yaml.safe_load(coverage_path.read_text(encoding="utf-8")) or {}
        for pop in doc.get("populations", []):
            curated |= set(pop.get("anchor", []))
    return curated


def attractor_anchor_ids() -> set[str]:
    """Anchor ids of the known attractor panels (epidermis, endothelium, mesenchyme, neural)."""
    ids: set[str] = set()
    for panel in load_panels(PANELS_YAML):
        if panel.bucket in ATTRACTOR_BUCKETS:
            ids |= set(panel.ontology_anchor)
    return ids


# --- gene footprints per term -------------------------------------------------


def build_footprints(
    expression_map: Mapping[str, list[ZfinExpressionRecord]],
    graph: nx.MultiDiGraph,
) -> tuple[dict[str, set[str]], dict[str, set[str]]]:
    """Two per-term gene tallies.

    credited: genes localizing to a term OR anything under it (the engine's support; uses
        the same DAG ancestor credit as resolve_label). This is monotone toward the root.
    direct: genes whose most-specific ZFIN record IS exactly this term (its own signature,
        no ancestor credit) -- used only for the naive-Jaccard caveat comparison.
    """
    cache: dict[str, frozenset[str]] = {}
    credited: dict[str, set[str]] = defaultdict(set)
    direct: dict[str, set[str]] = defaultdict(set)
    for gene, records in expression_map.items():
        gene_credit: set[str] = set()
        for rec in records:
            direct[rec.zfa_id].add(gene)
            gene_credit |= _term_with_ancestors(rec.zfa_id, graph, cache)
        for term_id in gene_credit:
            credited[term_id].add(gene)
    return credited, direct


# --- edges --------------------------------------------------------------------


def edge_relations(graph: nx.MultiDiGraph) -> dict[tuple[str, str], set[str]]:
    """Map (child, parent) -> set of is_a/part_of relation keys connecting them."""
    rels: dict[tuple[str, str], set[str]] = defaultdict(set)
    for child, parent, key in graph.edges(keys=True):
        if key in DEFAULT_ANCESTOR_EDGE_TYPES:
            rels[(child, parent)].add(key)
    return rels


def jaccard(a: set[str], b: set[str]) -> float:
    """Jaccard similarity of two gene sets (0 when both are empty)."""
    union = a | b
    return len(a & b) / len(union) if union else 0.0


# --- main ---------------------------------------------------------------------


def main() -> None:
    """Score every ZFA term, score every edge, validate against curation, and write the artifacts."""
    graph = load_zfa(DATA / "zfa.obo")
    expression_map = load_zfin_expression(DATA / "zfin_wildtype_expression.txt")
    ic = build_information_content(expression_map, graph)
    credited, direct = build_footprints(expression_map, graph)
    curated = load_curated_anchors()
    attractors = attractor_anchor_ids()
    rels = edge_relations(graph)

    zfa_nodes = [n for n in graph.nodes if isinstance(n, str) and n.startswith("ZFA:")]

    # ---- per-edge discernibility (sufficiency-gated), with the naive-Jaccard caveat ----
    edge_rows: list[dict] = []
    child_is_discernible: set[str] = set()  # child appears in >= 1 discernible step
    child_has_parent: set[str] = set()
    child_all_dead: dict[str, bool] = {}  # child -> all its sufficient parent-steps are dead
    naive_says_discernible = 0  # direct-Jaccard < 0.3 (the inflated metric)
    naive_but_insufficient = 0  # ... of those, the credited gate can't actually judge

    per_child_sufficient: dict[str, list[bool]] = defaultdict(list)  # child -> [is_dead per sufficient parent]
    for (child, parent), keys in rels.items():
        if not (child.startswith("ZFA:") and parent.startswith("ZFA:")):
            continue
        child_has_parent.add(child)
        sup_p = len(credited.get(parent, ()))
        sup_c = len(credited.get(child, ()))
        retained = sup_c / sup_p if sup_p else 0.0
        # share of the child's footprint that is unique to it among the parent's children
        siblings = [c for c, p in rels if p == parent]
        sib_counter: Counter[str] = Counter()
        for sib in siblings:
            sib_counter.update(credited.get(sib, ()))
        unique_to_child = sum(1 for g in credited.get(child, ()) if sib_counter[g] == 1)
        child_unique_frac = unique_to_child / sup_c if sup_c else 0.0

        sufficient = sup_p >= SUFFICIENT_GENES and sup_c >= SUFFICIENT_GENES
        discernible = sufficient and retained <= RETAINED_DISCERNIBLE_MAX
        dead = sufficient and retained >= RETAINED_DEAD_MIN

        naive_j = jaccard(direct.get(parent, set()), direct.get(child, set()))
        if naive_j < 0.3:
            naive_says_discernible += 1
            if not sufficient:
                naive_but_insufficient += 1

        if discernible:
            child_is_discernible.add(child)
        if sufficient:
            per_child_sufficient[child].append(dead)

        edge_rows.append(
            {
                "parent_id": parent,
                "parent_name": term_name(graph, parent) or parent,
                "child_id": child,
                "child_name": term_name(graph, child) or child,
                "relation": "+".join(sorted(keys)),
                "support_parent": sup_p,
                "support_child": sup_c,
                "retained": round(retained, 4),
                "child_unique_frac": round(child_unique_frac, 4),
                "sufficient": int(sufficient),
                "discernible": int(discernible),
                "dead_step": int(dead),
                "naive_direct_jaccard": round(naive_j, 4),
            }
        )

    for child, deads in per_child_sufficient.items():
        child_all_dead[child] = len(deads) > 0 and all(deads)

    # ---- per-term scoring + tiering ----
    term_rows: list[dict] = []
    tier_counts: Counter[str] = Counter()
    for tid in zfa_nodes:
        attrs = graph.nodes[tid]
        name = term_name(graph, tid) or ""
        subs = subsets_of(attrs)
        cell_slim = "cell_slim" in subs
        has_cl = has_cl_xref(attrs)
        cell_identity = cell_slim or has_cl
        term_ic = ic.get(tid, 0.0)
        cred = len(credited.get(tid, ()))
        dire = len(direct.get(tid, ()))
        kids = [c for c, _ in rels if _ == tid]
        n_children = len(set(kids))
        parents = list(graph.out_edges(tid, keys=True))
        n_is_a = sum(1 for _, _, k in parents if k == "is_a")
        n_part_of = sum(1 for _, _, k in parents if k == "part_of")
        obsolete = is_obsolete(attrs)
        in_stop = tid in STOPLIST
        admin = is_admin_name(name)
        is_curated = tid in curated
        structural_container = (
            n_children >= FANOUT_CONTAINER and not cell_identity and term_ic < IC_CONTAINER and not is_curated
        )
        groundable = cred >= CONVERGENCE_MIN

        dead_only = child_all_dead.get(tid, False)
        flags: list[str] = []

        # --- tier decision (grounding-driven) ---
        # T5 not useful: content-free / structural containers. T4 real but ungroundable: a real
        # entity with too few ZFIN genes to prove any signature. Then sufficiency + breadth split
        # the groundable real entities into T1 (solid, discernible), T2 (useful), T3 (broad/coarse).
        # Breadth is judged by footprint + low IC only. Attractor membership is a FLAG, not a tier
        # determinant: it would wrongly sink specific attractor-panel anchors (endothelial cell) while
        # the real hazard is the broad anchor (vasculature), which low IC already catches.
        broad_promiscuous = cred >= BROAD_FOOTPRINT and term_ic <= IC_BROAD
        if in_stop or admin or structural_container:
            tier = "T5"
        elif not groundable:
            tier = "T4"
        elif broad_promiscuous:
            tier = "T3"
        elif cred >= SOLID_GENES and not dead_only:
            tier = "T1"
        else:
            tier = "T2"

        # --- curation floor: a human-vetted, groundable anchor is at least T2 ---
        if is_curated:
            if admin:
                flags.append("curated_but_admin")  # curation disagrees with the name rule -> investigate
            if not groundable:
                flags.append("curated_but_thin")  # vetted anchor lacks >=3 ZFIN genes -> curation backlog
            elif tier in ("T3", "T4", "T5"):
                tier = "T2"

        if tid in attractors:
            flags.append("attractor_prone")  # known selection hazard (out-scores true lineages), still a useful label
        if dead_only:
            flags.append("dead_step_only")  # every grounded step into this term is a renaming

        tier_counts[tier] += 1

        # composite score for sorting: tier band + within-tier refinement (grounding-driven,
        # not IC: IC rewards sparsity). More credited genes, a cell identity, and sitting on a
        # discernible step all raise a term within its tier.
        on_disc = tid in child_is_discernible
        tier_base = {"T1": 4, "T2": 3, "T3": 2, "T4": 1, "T5": 0}[tier]
        refine = (
            0.45 * min(cred / 50.0, 1.0) + 0.30 * (1.0 if cell_identity else 0.0) + 0.25 * (1.0 if on_disc else 0.0)
        )
        usefulness = round(tier_base + refine, 4)

        term_rows.append(
            {
                "zfa_id": tid,
                "name": name,
                "tier": tier,
                "usefulness_score": usefulness,
                "cell_slim": int(cell_slim),
                "has_cl": int(has_cl),
                "cell_identity": int(cell_identity),
                "ic": round(term_ic, 4),
                "credited_genes": cred,
                "direct_genes": dire,
                "n_children": n_children,
                "n_is_a_parents": n_is_a,
                "n_part_of_parents": n_part_of,
                "is_leaf": int(n_children == 0),
                "obsolete": int(obsolete),
                "in_stoplist": int(in_stop),
                "admin_container": int(admin),
                "structural_container": int(structural_container),
                "curated": int(is_curated),
                "on_discernible_step": int(tid in child_is_discernible),
                "flags": ";".join(flags),
            }
        )

    term_rows.sort(key=lambda r: (-r["usefulness_score"], r["zfa_id"]))
    edge_rows.sort(key=lambda r: (-r["support_parent"], r["parent_id"], r["child_id"]))

    _write_csv(OUT / "zfa_term_usefulness.csv", term_rows)
    _write_csv(OUT / "zfa_edges.csv", edge_rows)

    # ---- curation validation: where do the vetted anchors land? ----
    curated_in_graph = sorted(c for c in curated if c in graph)
    curated_tiers = Counter(next(r["tier"] for r in term_rows if r["zfa_id"] == c) for c in curated_in_graph)
    stoplist_tiers = Counter(next(r["tier"] for r in term_rows if r["zfa_id"] == s) for s in STOPLIST if s in graph)

    n_terms = len(term_rows)
    grounded_terms = sum(1 for r in term_rows if r["credited_genes"] > 0)
    summary = {
        "zfa_release": _zfa_release(DATA / "zfa.obo"),
        "n_zfa_terms": n_terms,
        "n_genes_in_corpus": len(expression_map),
        "grounded_terms": grounded_terms,
        "ungrounded_terms": n_terms - grounded_terms,
        "cell_slim_terms": sum(r["cell_slim"] for r in term_rows),
        "cl_xref_terms": sum(r["has_cl"] for r in term_rows),
        "obsolete_terms": sum(r["obsolete"] for r in term_rows),
        "tier_counts": dict(sorted(tier_counts.items())),
        "curated_anchor_count": len(curated_in_graph),
        "curated_anchor_tiers": dict(sorted(curated_tiers.items())),
        "stoplist_tiers": dict(sorted(stoplist_tiers.items())),
        "edges_total": len(edge_rows),
        "edges_sufficient": sum(r["sufficient"] for r in edge_rows),
        "edges_discernible": sum(r["discernible"] for r in edge_rows),
        "edges_dead": sum(r["dead_step"] for r in edge_rows),
        "naive_jaccard_says_discernible": naive_says_discernible,
        "naive_but_insufficient": naive_but_insufficient,
        "credited_bands": _credited_bands(term_rows),
        "thresholds": {
            "SOLID_GENES": SOLID_GENES,
            "BROAD_FOOTPRINT": BROAD_FOOTPRINT,
            "IC_BROAD": IC_BROAD,
            "FANOUT_CONTAINER": FANOUT_CONTAINER,
            "IC_CONTAINER": IC_CONTAINER,
            "SUFFICIENT_GENES": SUFFICIENT_GENES,
            "RETAINED_DISCERNIBLE_MAX": RETAINED_DISCERNIBLE_MAX,
            "RETAINED_DEAD_MIN": RETAINED_DEAD_MIN,
        },
    }
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    # ---- console summary ----
    print(json.dumps(summary, indent=2))
    print("\nCurated anchors NOT in T1/T2 (investigate):")
    for c in curated_in_graph:
        row = next(r for r in term_rows if r["zfa_id"] == c)
        if row["tier"] not in ("T1", "T2"):
            print(
                f"  {c} {row['name']!r}: {row['tier']} ic={row['ic']} cred={row['credited_genes']} flags={row['flags']}"
            )
    print("\nTop 15 dead steps (renaming edges the descent could collapse):")
    dead = [r for r in edge_rows if r["dead_step"]]
    dead.sort(key=lambda r: -r["support_parent"])
    for r in dead[:15]:
        print(
            f"  {r['parent_id']} {r['parent_name']!r} -> {r['child_id']} {r['child_name']!r} "
            f"retained={r['retained']} sup {r['support_parent']}->{r['support_child']}"
        )


def _credited_bands(rows: list[dict]) -> dict[str, int]:
    """Distribution of terms across credited-gene bands (the grounding/sufficiency axis)."""

    def band(c: int) -> str:
        if c == 0:
            return "0 (ungrounded)"
        if c < CONVERGENCE_MIN:
            return "1-2 (trace)"
        if c < SOLID_GENES:
            return "3-9 (thin)"
        if c < 30:
            return "10-29 (solid)"
        if c < 100:
            return "30-99 (strong)"
        return ">=100 (broad)"

    counts: Counter[str] = Counter(band(r["credited_genes"]) for r in rows)
    order = ["0 (ungrounded)", "1-2 (trace)", "3-9 (thin)", "10-29 (solid)", "30-99 (strong)", ">=100 (broad)"]
    return {b: counts.get(b, 0) for b in order}


def _write_csv(path: Path, rows: list[dict]) -> None:
    import csv

    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _zfa_release(path: Path) -> str:
    for line in path.read_text(encoding="utf-8").splitlines()[:10]:
        if line.startswith("data-version:"):
            return line.split(":", 1)[1].strip()
    return "unknown"


if __name__ == "__main__":
    main()
