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


# --- tier decision (one pure function, reused by the main pass and the sensitivity sweep) -----


def decide_tier(
    *,
    cred: int,
    ic: float,
    direct: int,
    admin: bool,
    structural: bool,
    in_stop: bool,
    dead_only: bool,
    is_curated: bool,
    solid: int,
    ic_broad: float,
) -> tuple[str, str, bool]:
    """Assign a usefulness tier from a term's signals; grounding-driven (credited count is primary).

    Returns the final tier, the pre-curation-floor tier (for de-circularized validation), and the
    pure_grouper flag. pure_grouper (direct==0, credited only via descendants) means the term has no
    expression signature of its own -- it borrows all support from children -- so it can never be T1
    however high its inherited credited count (the ancestor-credit-inflation fix). The curation floor
    lifts a vetted, groundable anchor to at least T2; tier_prefloor is what the data says without it.
    """
    pure_grouper = direct == 0 and cred > 0
    broad_promiscuous = cred >= BROAD_FOOTPRINT and ic <= ic_broad
    groundable = cred >= CONVERGENCE_MIN
    if in_stop or admin or structural:
        tier = "T5"
    elif not groundable:
        tier = "T4"
    elif broad_promiscuous:
        tier = "T3"
    elif cred >= solid and not dead_only and not pure_grouper:
        tier = "T1"
    else:
        tier = "T2"
    tier_prefloor = tier
    if is_curated and groundable and tier in ("T3", "T4", "T5"):
        tier = "T2"
    return tier, tier_prefloor, pure_grouper


def sensitivity_sweep(signals: list[dict]) -> list[dict]:
    """Re-tier every term across a grid of SOLID_GENES x IC_BROAD; report stability vs the defaults.

    signals is one dict per term with the precomputed inputs to decide_tier. For each (solid, ic_broad)
    pair this reports the tier counts, how many terms move tier vs the committed defaults, and the
    curated-anchor agreement (anchors landing T1/T2) -- the evidence that the boundaries are stable,
    not hand-tuned to one operating point.
    """

    def tiers_for(solid: int, ic_broad: float) -> dict[str, str]:
        out: dict[str, str] = {}
        for s in signals:
            tier, _, _ = decide_tier(
                cred=s["cred"],
                ic=s["ic"],
                direct=s["direct"],
                admin=s["admin"],
                structural=s["structural"],
                in_stop=s["in_stop"],
                dead_only=s["dead_only"],
                is_curated=s["is_curated"],
                solid=solid,
                ic_broad=ic_broad,
            )
            out[s["zfa_id"]] = tier
        return out

    base = tiers_for(SOLID_GENES, IC_BROAD)
    curated_ids = [s["zfa_id"] for s in signals if s["is_curated"]]
    rows: list[dict] = []
    for solid in (5, 8, 10, 15, 20):
        for ic_broad in (2.0, 3.0, 4.0, 5.0):
            t = tiers_for(solid, ic_broad)
            counts = Counter(t.values())
            moved = sum(1 for k in t if t[k] != base[k])
            cur_ok = sum(1 for c in curated_ids if t[c] in ("T1", "T2"))
            rows.append(
                {
                    "SOLID_GENES": solid,
                    "IC_BROAD": ic_broad,
                    "is_default": solid == SOLID_GENES and ic_broad == IC_BROAD,
                    "T1": counts["T1"],
                    "T2": counts["T2"],
                    "T3": counts["T3"],
                    "T4": counts["T4"],
                    "T5": counts["T5"],
                    "moved_vs_default": moved,
                    "curated_in_T1T2": f"{cur_ok}/{len(curated_ids)}",
                }
            )
    return rows


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
    signals: list[dict] = []  # decide_tier inputs per term, reused by the sensitivity sweep
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

        # Tier from the pure decision function (grounding-driven; pure-grouper + dead-step guards
        # inside). tier_prefloor is the data-only verdict before the curation floor -- reported so the
        # curated-anchor validation is independent, not a tautology of the floor it is validating.
        tier, tier_prefloor, pure_grouper = decide_tier(
            cred=cred,
            ic=term_ic,
            direct=dire,
            admin=admin,
            structural=structural_container,
            in_stop=in_stop,
            dead_only=dead_only,
            is_curated=is_curated,
            solid=SOLID_GENES,
            ic_broad=IC_BROAD,
        )
        signals.append(
            {
                "zfa_id": tid,
                "cred": cred,
                "ic": term_ic,
                "direct": dire,
                "admin": admin,
                "structural": structural_container,
                "in_stop": in_stop,
                "dead_only": dead_only,
                "is_curated": is_curated,
            }
        )

        # Flags (transparency; not tier determinants except where decide_tier already used them).
        if is_curated and admin:
            flags.append("curated_but_admin")  # curation used a container-style name -> investigate
        if is_curated and not groundable:
            flags.append("curated_but_thin")  # vetted anchor lacks >=3 ZFIN genes -> curation backlog
        if pure_grouper:
            flags.append("pure_grouper")  # no own signature; capped below T1 (ancestor-credit inflation fix)
        if tid in attractors:
            flags.append("attractor_prone")  # known selection hazard, still a useful label
        # dead_step_only only on the ABSTRACT member of a renaming pair (direct==0): a directly grounded
        # child like neuron must not be flagged just because an abstract parent renames onto it.
        if dead_only and dire == 0:
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
                "tier_prefloor": tier_prefloor,
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
                "pure_grouper": int(pure_grouper),
                "curated": int(is_curated),
                "on_discernible_step": int(tid in child_is_discernible),
                "flags": ";".join(flags),
            }
        )

    term_rows.sort(key=lambda r: (-r["usefulness_score"], r["zfa_id"]))
    edge_rows.sort(key=lambda r: (-r["support_parent"], r["parent_id"], r["child_id"]))

    _write_csv(OUT / "zfa_term_usefulness.csv", term_rows)
    _write_csv(OUT / "zfa_edges.csv", edge_rows)

    # ---- curation validation: where do the vetted anchors land, WITH and WITHOUT the floor? ----
    # The un-floored (tier_prefloor) distribution is the honest check -- the floor can't manufacture
    # agreement because it isn't applied. Closeness of the two is the real evidence.
    by_id = {r["zfa_id"]: r for r in term_rows}
    curated_in_graph = sorted(c for c in curated if c in graph)
    curated_tiers = Counter(by_id[c]["tier"] for c in curated_in_graph)
    curated_tiers_prefloor = Counter(by_id[c]["tier_prefloor"] for c in curated_in_graph)
    stoplist_tiers = Counter(by_id[s]["tier"] for s in STOPLIST if s in graph)

    # ---- threshold sensitivity (the stability evidence) ----
    sweep = sensitivity_sweep(signals)
    _write_csv(OUT / "sensitivity.csv", sweep)

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
        "curated_anchor_tiers_prefloor": dict(sorted(curated_tiers_prefloor.items())),
        "pure_grouper_terms": sum(1 for r in term_rows if r["pure_grouper"]),
        "stoplist_tiers": dict(sorted(stoplist_tiers.items())),
        "edges_total": len(edge_rows),
        "edges_sufficient": sum(r["sufficient"] for r in edge_rows),
        "edges_discernible": sum(r["discernible"] for r in edge_rows),
        "edges_dead": sum(r["dead_step"] for r in edge_rows),
        "naive_jaccard_says_discernible": naive_says_discernible,
        "naive_but_insufficient": naive_but_insufficient,
        "credited_bands": _credited_bands(term_rows),
        "sensitivity_stability": {
            "grid": "SOLID_GENES x IC_BROAD = 5x4",
            "T1_range": [min(r["T1"] for r in sweep), max(r["T1"] for r in sweep)],
            "T5_range": [min(r["T5"] for r in sweep), max(r["T5"] for r in sweep)],
            "max_moved_vs_default": max(r["moved_vs_default"] for r in sweep),
            "curated_T1T2_worst": min(r["curated_in_T1T2"] for r in sweep),
        },
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
    print("\nThreshold sensitivity (SOLID_GENES x IC_BROAD); * = committed default:")
    print(
        f"  {'SOLID':>5} {'IC_BROAD':>8} {'T1':>5} {'T2':>5} {'T3':>4} {'T4':>5} {'T5':>4} {'moved':>6}  curated_T1T2"
    )
    for r in sweep:
        star = " *" if r["is_default"] else "  "
        print(
            f"{star}{r['SOLID_GENES']:>4} {r['IC_BROAD']:>8} {r['T1']:>5} {r['T2']:>5} {r['T3']:>4} "
            f"{r['T4']:>5} {r['T5']:>4} {r['moved_vs_default']:>6}  {r['curated_in_T1T2']}"
        )
    print(
        f"\nCurated anchors T1/T2: floored {curated_tiers.get('T1', 0) + curated_tiers.get('T2', 0)}"
        f"/{len(curated_in_graph)}  |  UN-floored (independent) "
        f"{curated_tiers_prefloor.get('T1', 0) + curated_tiers_prefloor.get('T2', 0)}/{len(curated_in_graph)}"
    )
    print(f"pure_grouper terms (capped below T1): {summary['pure_grouper_terms']}")
    print("\nCurated anchors NOT in T1/T2 (investigate):")
    for c in curated_in_graph:
        row = by_id[c]
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
