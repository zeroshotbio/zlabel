"""Ranked curation backlog: the ungroundable cell types worth grounding next (read-only).

The only lever that grows zlabel's coverage is adding ZFIN grounding for real cell types it cannot yet
name (Phase-3 proved the descent/edge-set changes do not). This ranks the T4 cell-identity terms by how
close they are to the CONVERGENCE_MIN=3 bar and whether the descent can even reach them (is_a/part_of),
so curation effort goes where one or two added markers flip a term from unnameable to nameable.

Writes backlog.csv (all T4 cell types) + backlog.md (summary + the closest targets). No engine change.
Run: uv run python analysis/zfa_usefulness/backlog.py
"""

from __future__ import annotations

import csv
from collections.abc import Iterable
from pathlib import Path

import networkx as nx
import yaml

from zlabel.data import children, load_zfa, load_zfin_expression, term_name
from zlabel.resolve import CONVERGENCE_MIN, _term_with_ancestors

OUT = Path(__file__).resolve().parent
REPO = OUT.parents[1]
DATA = REPO / "data" / "ontologies"


def credited_footprints(expression_map, graph: nx.MultiDiGraph) -> dict[str, set[str]]:  # noqa: ANN001
    """Per-term credited gene sets (engine ancestor credit over is_a+part_of)."""
    cache: dict[str, frozenset[str]] = {}
    cred: dict[str, set[str]] = {}
    for gene, recs in expression_map.items():
        seen: set[str] = set()
        for r in recs:
            seen |= _term_with_ancestors(r.zfa_id, graph, cache)
        for t in seen:
            cred.setdefault(t, set()).add(gene)
    return cred


def reach(graph: nx.MultiDiGraph, anchors: Iterable[str], edge_types: set[str]) -> set[str]:
    """All terms reachable by descending edge_types from the anchors."""
    seen: set[str] = set()
    stack = [a for a in anchors if a in graph]
    while stack:
        n = stack.pop()
        for c in children(graph, n, edge_types=edge_types):
            if c not in seen:
                seen.add(c)
                stack.append(c)
    return seen


def main() -> None:
    """Rank the T4 cell-type backlog by genes-to-nameable and descent reachability."""
    graph = load_zfa(DATA / "zfa.obo")
    expression_map = load_zfin_expression(DATA / "zfin_wildtype_expression.txt")
    cred = credited_footprints(expression_map, graph)
    terms = {r["zfa_id"]: r for r in csv.DictReader(open(OUT / "zfa_term_usefulness.csv"))}

    anchors = {
        a
        for p in yaml.safe_load(open(REPO / "src" / "zlabel" / "panels.yaml")).values()
        for a in (p.get("ontology_anchor") or [])
    }
    base = reach(graph, anchors, {"is_a", "part_of"})  # the real descent reach
    devonly = reach(graph, anchors, {"is_a", "part_of", "develops_from"}) - base

    def reach_tag(tid: str) -> str:
        if tid in base:
            return "is_a/part_of"  # the descent can reach it -> grounding it makes it nameable
        if tid in devonly:
            return "develops_from_only"  # engine won't reach it (Phase-3 NO-GO) -> needs a panel too
        return "unreachable"  # no axis reaches it from current anchors -> needs a new panel/anchor

    rows = []
    for tid, r in terms.items():
        if r["tier"] != "T4" or r["cell_identity"] != "1":
            continue
        c = len(cred.get(tid, ()))
        rows.append(
            {
                "zfa_id": tid,
                "name": term_name(graph, tid) or tid,
                "credited_genes": c,
                "genes_to_min": max(0, CONVERGENCE_MIN - c),
                "has_cl": r["has_cl"],
                "reach": reach_tag(tid),
                "current_genes": ";".join(sorted(cred.get(tid, ()))),
            }
        )

    reach_rank = {"is_a/part_of": 0, "develops_from_only": 1, "unreachable": 2}
    rows.sort(key=lambda r: (reach_rank[r["reach"]], r["genes_to_min"], -r["credited_genes"], r["name"]))
    with (OUT / "backlog.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    reachable = [r for r in rows if r["reach"] == "is_a/part_of"]
    n_dev = sum(1 for r in rows if r["reach"] == "develops_from_only")
    n_unreach = sum(1 for r in rows if r["reach"] == "unreachable")
    close = [r for r in reachable if r["genes_to_min"] <= 1]  # within 1 gene (have 2 already)
    near = [r for r in reachable if r["genes_to_min"] <= 2]  # within 2 (have >=1)
    top = close[:20]
    md = (
        f"""# Curation backlog — ungroundable cell types, ranked

Read-only. The Phase-3 experiment ruled out edge-set/descent changes, so the only lever that grows
coverage is **adding ZFIN grounding** to real cell types the descent can already reach. This ranks the
**{len(rows)} T4 cell-identity terms** (cell_slim/CL, < {CONVERGENCE_MIN} credited genes today).

| reachability from current anchors | count | meaning |
|---|---|---|
| is_a/part_of (descent-reachable) | {len(reachable)} | ground to >={CONVERGENCE_MIN} genes -> nameable today |
| develops_from only | {n_dev} | engine won't reach it (Phase-3 NO-GO); needs a panel too |
| unreachable | {n_unreach} | no axis reaches it; needs a new panel |

**Priority: {len(near)} descent-reachable cell types are within {CONVERGENCE_MIN - 1} genes of nameable
({len(close)} within 1).** Adding one or two curated markers each flips them from unnameable to
nameable — the highest-yield curation per unit effort.

## Top targets (descent-reachable, 1 gene short — already have 2)

| cell type | ZFA | have | current genes |
|---|---|---|---|
"""
        + "\n".join(f"| {r['name']} | {r['zfa_id']} | {r['credited_genes']} | {r['current_genes']} |" for r in top)
        + f"""

Full ranked list (all {len(rows)}): `backlog.csv`. Grounding strategy (bulk vs targeted) is assessed in
`grounding_augmentation.md`.
"""
    )
    (OUT / "backlog.md").write_text(md, encoding="utf-8")
    print(md)


if __name__ == "__main__":
    main()
