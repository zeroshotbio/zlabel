"""IC-weighted convergence namer for zlabel.

Given a cluster's already-normalized marker genes, resolves the most
specific ZFA anatomy term the markers converge on in vivo (via ZFIN
curated expression). The label depth falls out of the evidence: a tight
endothelial panel resolves to a cell type, a broad neural panel resolves
to CNS, a mixed cluster abstains. Panels demote to a coarse prior and
ontology-anchor guardrail upstream (in label.py).

The algorithm:
  1. For each distinct normalized gene, look up its ZFIN expression
     records and walk the is_a+part_of ZFA ancestors (DAG ancestor
     credit: a gene expressing in muscle cell also votes for musculature
     system and its parents).
  2. Tally distinct genes per ZFA term across all markers.
  3. Keep terms that clear all three gates:
       - distinct gene count >= CONVERGENCE_MIN
       - term not in STOPLIST (content-free attractors removed)
       - IC >= IC_MIN (near-root terms down-weighted)
  4. Rank surviving terms most-specific first: descending IC (the
     selector), then descending gene count (gate magnitude), then
     descending ancestor_depth (specificity tiebreak), then id (stable output).
  5. Return the ranked list; empty means nothing converged.

The background IC model (build_ic) is computed once from the loaded ZFIN
corpus at Labeler init. It is entirely data-derived -- no hardcoded
anatomy knowledge except the content-free STOPLIST.
"""

from __future__ import annotations

import math
from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass

import networkx as nx

from zlabel.data import ZfinExpressionRecord, ancestors, term_name
from zlabel.ground import expression_lookup

# ---------------------------------------------------------------------------
# Named constants — all provisional; calibrated by the eval PR.
# ---------------------------------------------------------------------------

CONVERGENCE_MIN: int = 3
# Distinct normalized genes that must credit a ZFA term before it is
# eligible for naming. Below this, evidence is too thin to call the term.
# Provisional.

IC_MIN: float = 1.0
# Minimum information content (in bits, -log2 scale) a term must have to
# be eligible. Screens near-root attractors that survive the stoplist:
# IC_MIN=1.0 means the term must be credited by fewer than half of all
# genes in the corpus. Provisional.

STOPLIST: frozenset[str] = frozenset(
    {
        "ZFA:0100000",  # zebrafish anatomical entity (formal root)
        "ZFA:0001094",  # whole organism
        "ZFA:0000037",  # anatomical structure
        "ZFA:0001512",  # anatomical group
        "ZFA:0001439",  # anatomical system
    }
)
# Content-free attractor terms that are never a useful label even at high
# gene counts. IC_MIN is the second safety net; the stoplist handles terms
# that could otherwise win before the IC gate applies. head (ZFA:0000035)
# is deliberately absent -- it is a legitimate region label and never wins
# on the worked examples.


# ---------------------------------------------------------------------------
# Return type
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TermVote:
    """One candidate ZFA term and the convergent evidence for it.

    Attributes:
        zfa_id (str): The candidate ZFA term id.
        zfa_name (str): Human-readable name, or the raw id when name-less.
        genes (tuple[str, ...]): Distinct normalized gene symbols that
            credited this term, sorted for determinism.
        ic (float): Information content of the term under the background
            model from build_ic (bits, -log2 scale).
        ancestor_depth (int): Number of is_a+part_of ancestors in the ZFA
            graph. A proxy for ontological specificity. 0 when the term is
            not in the loaded graph (e.g. an older id not in the fixture).
    """

    zfa_id: str
    zfa_name: str
    genes: tuple[str, ...]
    ic: float
    ancestor_depth: int


# ---------------------------------------------------------------------------
# Background IC model
# ---------------------------------------------------------------------------


def build_ic(
    expr_map: Mapping[str, list[ZfinExpressionRecord]],
    zfa_graph: nx.MultiDiGraph,
) -> dict[str, float]:
    """Build an information-content model from the loaded ZFIN expression corpus.

    For each gene in expr_map, credits the union of every record's ZFA term
    and all its is_a+part_of ancestors (DAG ancestor credit). Counts each
    term once per distinct gene, then computes IC as -log2(count / n_genes).
    Rare, specific terms score high; near-root terms that almost every gene
    rolls up into score near zero.

    Ancestor walks are memoized by term id so each id is walked at most once.
    Called once at Labeler init; the resulting dict is passed to resolve_label.

    Args:
        expr_map (Mapping[str, list[ZfinExpressionRecord]]): From
            data.load_zfin_expression. Keys are lowercased gene symbols.
        zfa_graph (nx.MultiDiGraph): From data.load_zfa.

    Returns:
        dict[str, float]: ZFA id to information content in bits. Terms
        credited by no gene are absent (callers treat absence as IC 0.0).
    """
    n_genes = len(expr_map)
    if n_genes == 0:
        return {}

    # Memoize ancestor walks: each ZFA id is walked at most once per
    # build_ic call, covering both present and absent-from-graph ids.
    anc_cache: dict[str, frozenset[str]] = {}

    def _credited(zfa_id: str) -> frozenset[str]:
        if zfa_id in anc_cache:
            return anc_cache[zfa_id]
        if zfa_id not in zfa_graph:
            # Older or retired id not in the loaded ontology: credit only
            # itself (no ancestors to walk).
            result: frozenset[str] = frozenset({zfa_id})
        else:
            result = frozenset({zfa_id}) | frozenset(ancestors(zfa_graph, zfa_id))
        anc_cache[zfa_id] = result
        return result

    gene_counts: Counter[str] = Counter()
    for records in expr_map.values():
        # Credit each term at most once per gene (distinct-gene tally).
        credited: set[str] = set()
        for rec in records:
            credited |= _credited(rec.zfa_id)
        gene_counts.update(credited)

    return {t: -math.log2(count / n_genes) for t, count in gene_counts.items() if count > 0}


# ---------------------------------------------------------------------------
# Convergence vote
# ---------------------------------------------------------------------------


def resolve_label(
    symbols: list[str],
    *,
    expr_map: Mapping[str, list[ZfinExpressionRecord]],
    zfa_graph: nx.MultiDiGraph,
    ic: Mapping[str, float],
) -> list[TermVote]:
    """IC-weighted convergence vote: name a cluster from its normalized markers.

    symbols must be already-normalized current ZFIN symbols (caller normalizes
    first using genes.normalize_symbol; keep only STATUS_RESOLVED). Each
    distinct gene votes for every ZFA term it expresses in and all that term's
    is_a+part_of ancestors (DAG ancestor credit). Terms that clear
    CONVERGENCE_MIN distinct genes, are not in STOPLIST, and have IC >= IC_MIN
    are returned ranked most-specific first (descending IC, then gene count,
    then ancestor_depth, then id). Empty list means nothing converged.

    Args:
        symbols (list[str]): Already-normalized current ZFIN symbols in rank
            order (most significant first). Duplicates are ignored; each gene
            votes at most once per term.
        expr_map (Mapping[str, list[ZfinExpressionRecord]]): ZFIN expression
            data from data.load_zfin_expression.
        zfa_graph (nx.MultiDiGraph): ZFA ontology from data.load_zfa.
        ic (Mapping[str, float]): IC model from build_ic.

    Returns:
        list[TermVote]: Candidate terms ranked most-specific first (index 0
        is the best label). Empty when no term clears all three gates.
    """
    # Memoize ancestor walks (mirrors build_ic): each ZFA id is walked at
    # most once, shared between the vote tally below and the per-term depth.
    anc_cache: dict[str, frozenset[str]] = {}

    def _credited(zfa_id: str) -> frozenset[str]:
        if zfa_id in anc_cache:
            return anc_cache[zfa_id]
        if zfa_id not in zfa_graph:
            # Older or retired id not in the loaded ontology: credit only
            # itself (no ancestors to walk).
            result: frozenset[str] = frozenset({zfa_id})
        else:
            result = frozenset({zfa_id}) | frozenset(ancestors(zfa_graph, zfa_id))
        anc_cache[zfa_id] = result
        return result

    # Tally distinct genes per ZFA term (direct expression + DAG ancestors).
    term_to_genes: dict[str, set[str]] = {}
    seen: set[str] = set()

    for sym in symbols:
        if sym in seen:
            continue  # each gene votes at most once
        seen.add(sym)
        records = expression_lookup(expr_map, sym)
        if not records:
            continue
        # Collect all terms this gene credits: the expressed term and every
        # is_a+part_of ancestor (guarded against ids absent from the graph).
        credited: set[str] = set()
        for rec in records:
            credited |= _credited(rec.zfa_id)
        for t in credited:
            term_to_genes.setdefault(t, set()).add(sym)

    # Build TermVote candidates that clear all three gates.
    candidates: list[TermVote] = []
    for t, genes in term_to_genes.items():
        if len(genes) < CONVERGENCE_MIN:
            continue
        if t in STOPLIST:
            continue
        term_ic = ic.get(t, 0.0)
        if term_ic < IC_MIN:
            continue
        if t in zfa_graph:
            name = term_name(zfa_graph, t) or t
        else:
            name = t
        # _credited(t) includes the term itself; ancestor_depth counts only its
        # ancestors. Reuses the cache, so no term's ancestors are walked twice.
        ancestor_depth = len(_credited(t)) - 1
        candidates.append(
            TermVote(
                zfa_id=t,
                zfa_name=name,
                genes=tuple(sorted(genes)),
                ic=term_ic,
                ancestor_depth=ancestor_depth,
            )
        )

    # Rank most-specific first: IC is the selector (highest IC = most specific
    # relative to the background); gene count is the gate magnitude;
    # ancestor_depth breaks equal-IC ties; id ensures stable, deterministic output.
    candidates.sort(key=lambda v: (-v.ic, -len(v.genes), -v.ancestor_depth, v.zfa_id))
    return candidates
