"""Coverage triage: which useful ZFA terms can the descent reach, and what blocks the rest (read-only).

zlabel's descent walks is_a+part_of down from 42 panel anchors. This characterises the useful (T1/T2)
label space by reachability and, crucially, predicts whether adding the develops_from (develops_into)
axis would actually help once the descent's support floors are applied -- because graph-reachability is
only an upper bound; the DESCENT_SUPPORT_FRACTION floor can still block a broad-progenitor -> specific-
derivative jump. Writes coverage_unreached.csv + coverage.md. No engine change.

Run: uv run python analysis/zfa_usefulness/coverage.py
"""

from __future__ import annotations

import csv
from collections.abc import Iterable, Mapping
from pathlib import Path

import networkx as nx
import yaml

from zlabel.data import ZfinExpressionRecord, children, load_zfa, load_zfin_expression, term_name
from zlabel.resolve import CONVERGENCE_MIN, DESCENT_SUPPORT_FRACTION, _term_with_ancestors

OUT = Path(__file__).resolve().parent
REPO = OUT.parents[1]
DATA = REPO / "data" / "ontologies"


def credited_footprints(
    expression_map: Mapping[str, list[ZfinExpressionRecord]],
    graph: nx.MultiDiGraph,
) -> dict[str, set[str]]:
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
    """Triage the useful label space by reachability and predict the develops_from experiment."""
    graph = load_zfa(DATA / "zfa.obo")
    expression_map = load_zfin_expression(DATA / "zfin_wildtype_expression.txt")
    cred = credited_footprints(expression_map, graph)
    tier = {r["zfa_id"]: r["tier"] for r in csv.DictReader(open(OUT / "zfa_term_usefulness.csv"))}
    cellid = {r["zfa_id"]: r["cell_identity"] == "1" for r in csv.DictReader(open(OUT / "zfa_term_usefulness.csv"))}
    name = lambda i: term_name(graph, i) or i  # noqa: E731

    anchors = {
        a
        for p in yaml.safe_load(open(REPO / "src" / "zlabel" / "panels.yaml")).values()
        for a in (p.get("ontology_anchor") or [])
    }
    base = reach(graph, anchors, {"is_a", "part_of"})
    withdev = reach(graph, anchors, {"is_a", "part_of", "develops_from"})

    useful = [t for t, ti in tier.items() if ti in ("T1", "T2")]
    reachable = [t for t in useful if t in base]
    via_dev = [t for t in useful if t in withdev and t not in base]
    unreachable = [t for t in useful if t not in withdev]

    # Predict the experiment: which develops_into steps would the descent actually TAKE?
    # An edge parent --(child develops_from parent)--> child is a candidate develops_into step when the
    # parent is already reachable and the child is useful. The descent only enters it if the child keeps
    # CONVERGENCE_MIN genes AND >= DESCENT_SUPPORT_FRACTION of the parent's credited support.
    candidate_steps = 0
    pass_floor = 0
    floor_examples: list[str] = []
    for child, parent, k in graph.edges(keys=True):
        if k != "develops_from":
            continue
        if parent in base and tier.get(child) in ("T1", "T2"):
            sp, sc = len(cred.get(parent, ())), len(cred.get(child, ()))
            if sc >= CONVERGENCE_MIN:
                candidate_steps += 1
                if sp and sc >= DESCENT_SUPPORT_FRACTION * sp:
                    pass_floor += 1
                    if len(floor_examples) < 12:
                        floor_examples.append(f"{name(parent)} -> {name(child)} (sup {sp}->{sc})")

    rows = []
    for t in sorted(via_dev + unreachable, key=lambda t: (tier[t], -len(cred.get(t, ())))):
        rows.append(
            {
                "zfa_id": t,
                "name": name(t),
                "tier": tier[t],
                "cell_identity": int(cellid.get(t, False)),
                "credited_genes": len(cred.get(t, ())),
                "reach": "via_develops_from" if t in withdev else "unreachable",
            }
        )
    with (OUT / "coverage_unreached.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    def cell_struct(ids: list[str]) -> str:
        """Format a count as 'N (c cell-type, s structure)'."""
        c = sum(1 for i in ids if cellid.get(i))
        return f"{len(ids)} ({c} cell-type, {len(ids) - c} structure)"

    md = f"""# Coverage triage — what the descent can and cannot reach

Read-only. Useful = T1/T2. Anchors = {len(anchors)} panel ontology_anchors. Reach = descend the given
edges from the anchors (graph reachability, an upper bound; support floors are stricter).

## Useful label space by reachability

| status | count | composition |
|---|---|---|
| reachable today (is_a+part_of) | {len(reachable)} | {cell_struct(reachable)} |
| reachable only via develops_from | {len(via_dev)} | {cell_struct(via_dev)} |
| unreachable even with develops_from | {len(unreachable)} | {cell_struct(unreachable)} |

So **{len(via_dev)} useful terms** sit behind the ignored develops_from axis, and **{len(unreachable)}**
are unreachable by any of the three axes from the current anchors (a different gap: no panel sits in
that lineage, or the term is out of cell-typing scope).

## Will the develops_from experiment actually move outputs? (the support-floor reality check)

Graph-reachability is an upper bound. The descent only *takes* a develops_into step if the derivative
keeps >= CONVERGENCE_MIN ({CONVERGENCE_MIN}) genes AND >= DESCENT_SUPPORT_FRACTION
({DESCENT_SUPPORT_FRACTION}) of the parent's credited support.

- develops_into steps from an already-reachable parent to a useful, >=3-gene child: **{candidate_steps}**
- of those, steps that also clear the {DESCENT_SUPPORT_FRACTION} support-retain floor: **{pass_floor}**

Examples that clear the floor:
{chr(10).join("  - " + e for e in floor_examples) or "  (none)"}

**Prediction:** only ~{pass_floor} develops_into steps can fire under the current floors. If that number
is small, the Phase-3 experiment will move few outputs — i.e. the coverage ceiling rises but the
support floors don't realise it (the same shape design.md found for finer ZFIN grounding). The
experiment run measures the realised effect on `make gate-all`.

Full per-term list: `coverage_unreached.csv` ({len(rows)} rows).
"""
    (OUT / "coverage.md").write_text(md, encoding="utf-8")
    print(md)


if __name__ == "__main__":
    main()
