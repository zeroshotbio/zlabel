"""Anchor-rooted, support-weighted (TF-IDF) convergence namer for zlabel.

Given a cluster's already-normalized marker genes and the winning panel's
ontology anchor, resolves the most specific ZFA anatomy term the markers
converge on in vivo (via ZFIN curated expression) by descending from the
anchor. The label depth falls out of the evidence: a tight endothelial panel
resolves to a cell type, a broad neural panel resolves to CNS, a mixed cluster
abstains. Panels supply the coarse prior and the anchor (in label.py).

The algorithm (anchor-rooted descent):
  1. For each distinct normalized gene, look up its ZFIN expression
     records and walk the is_a+part_of ZFA ancestors (DAG ancestor
     credit: a gene expressing in muscle cell also votes for musculature
     system and its parents).
  2. Tally distinct genes per ZFA term across all markers.
  3. Seed at the winning panel's ontology anchor (the most-supported anchor id
     with at least CONVERGENCE_MIN genes) and descend the graph: at each step
     take the child the most genes support (TF-IDF: support x IC, support the
     dominant signal), as long as it keeps at least CONVERGENCE_MIN genes AND
     DESCENT_SUPPORT_FRACTION of its parent's support AND uniquely leads its
     siblings (a support tie means the markers spread across subtypes -> stop).
     Stop at the deepest such well-supported term.
  4. Return that terminal term (a one-element list); empty when the anchor
     itself is unsupported (the cluster does not converge under this panel).

Naming descends from the anchor, so the result is at or under it by construction --
the old post-hoc panel guardrail is folded into the walk, and contradiction is
impossible. STOPLIST roots are never seeded or entered. IC is no longer a hard gate
(the relative-support floor plays that role); it weights the per-step choice toward
specificity and is still reported in the trace.

The background IC model (build_information_content) is computed once from the loaded ZFIN
corpus at Labeler init. It is entirely data-derived -- no hardcoded
anatomy knowledge except the content-free STOPLIST.
"""

from __future__ import annotations

import math
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import networkx as nx

from zlabel.data import ZfinExpressionRecord, ancestors, children, term_name
from zlabel.ground import expression_lookup
from zlabel.models import TermVoteTrace

# ---------------------------------------------------------------------------
# Named constants -- all provisional; calibrated by the eval PR.
# ---------------------------------------------------------------------------

CONVERGENCE_MIN: int = 3
# Distinct normalized genes that must credit a ZFA term before it is
# eligible for naming. Below this, evidence is too thin to call the term.
# Provisional.

INFORMATION_CONTENT_MIN: float = 1.0
# Minimum information content (in bits, -log2 scale) for a term to count as eligible
# in the trace. No longer a naming gate (the descent's support floors are) -- kept so
# the trace can still report which terms are corpus-specific. Provisional.

DESCENT_SUPPORT_FRACTION: float = 0.6
# In the anchor-rooted descent, a child term must retain at least this share of its
# parent's distinct-gene support to be descended into. The relative-support floor that
# stops the walk before a coincidental few-gene leaf -- the thin-overcall fix. Chosen on
# principle (a clear majority of the parent's genes must still back the more specific
# call); the eval confirms it kills overcalls without collapsing names onto the anchor.
# Provisional.

STOPLIST: frozenset[str] = frozenset(
    {
        "ZFA:0100000",  # zebrafish anatomical entity (formal root)
        "ZFA:0001094",  # whole organism
        "ZFA:0000037",  # anatomical structure
        "ZFA:0001512",  # anatomical group
        "ZFA:0001439",  # anatomical system
    }
)
# Content-free attractor terms that are never a useful label and are never seeded or
# descended into. head (ZFA:0000035) is deliberately absent -- it is a legitimate region
# label and the support floors govern it.


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
        information_content (float): Information content of the term under the background
            model from build_information_content (bits, -log2 scale).
        ancestor_depth (int): Number of is_a+part_of ancestors in the ZFA
            graph. A proxy for ontological specificity. 0 when the term is
            not in the loaded graph (e.g. an older id not in the fixture).
    """

    zfa_id: str
    zfa_name: str
    genes: tuple[str, ...]
    information_content: float
    ancestor_depth: int


# ---------------------------------------------------------------------------
# Shared ancestor credit
# ---------------------------------------------------------------------------


def _term_with_ancestors(
    zfa_id: str,
    zfa_ontology: nx.MultiDiGraph,
    cache: dict[str, frozenset[str]],
) -> frozenset[str]:
    """The credited set for a gene expressing in zfa_id: the term plus all its ancestors.

    The unit of DAG ancestor credit shared by the IC model, the convergence descent, and the
    eval's tally replay. Memoized in cache so each id is walked at most once per pass; an id
    absent from the loaded ontology (older or retired) credits only itself.

    Args:
        zfa_id (str): The ZFA term a gene directly expresses in.
        zfa_ontology (nx.MultiDiGraph): The loaded ZFA ontology.
        cache (dict[str, frozenset[str]]): Per-pass memo from id to its credited set.

    Returns:
        frozenset[str]: zfa_id and all its is_a+part_of ancestors (just zfa_id when the id
        is absent from the ontology).
    """
    if zfa_id not in cache:
        if zfa_id not in zfa_ontology:
            cache[zfa_id] = frozenset({zfa_id})
        else:
            cache[zfa_id] = frozenset({zfa_id}) | frozenset(ancestors(zfa_ontology, zfa_id))
    return cache[zfa_id]


# ---------------------------------------------------------------------------
# Background IC model
# ---------------------------------------------------------------------------


def build_information_content(
    expression_map: Mapping[str, list[ZfinExpressionRecord]],
    zfa_ontology: nx.MultiDiGraph,
) -> dict[str, float]:
    """Build an information-content model from the loaded ZFIN expression corpus.

    For each gene in expression_map, credits the union of every record's ZFA term
    and all its is_a+part_of ancestors (DAG ancestor credit). Counts each
    term once per distinct gene, then computes IC as -log2(count / n_genes).
    Rare, specific terms score high; near-root terms that almost every gene
    rolls up into score near zero.

    Ancestor walks are memoized by term id so each id is walked at most once.
    Called once at Labeler init; the resulting dict is passed to resolve_label.

    Args:
        expression_map (Mapping[str, list[ZfinExpressionRecord]]): From
            data.load_zfin_expression. Keys are lowercased gene symbols.
        zfa_ontology (nx.MultiDiGraph): From data.load_zfa.

    Returns:
        dict[str, float]: ZFA id to information content in bits. Terms
        credited by no gene are absent (callers treat absence as IC 0.0).
    """
    n_genes = len(expression_map)
    if n_genes == 0:
        return {}

    # Memoize ancestor walks across this build (each id walked at most once).
    ancestor_cache: dict[str, frozenset[str]] = {}

    gene_counts: Counter[str] = Counter()
    for records in expression_map.values():
        # Credit each term at most once per gene (distinct-gene tally).
        credited: set[str] = set()
        for record in records:
            credited |= _term_with_ancestors(record.zfa_id, zfa_ontology, ancestor_cache)
        gene_counts.update(credited)

    return {term_id: -math.log2(count / n_genes) for term_id, count in gene_counts.items() if count > 0}


def build_marker_specificity(
    expression_map: Mapping[str, list[ZfinExpressionRecord]],
    identity_anchors: Sequence[frozenset[str]],
    zfa_ontology: nx.MultiDiGraph,
) -> dict[str, float]:
    """Per-gene inverse panel-frequency (IDF): how lineage-specific a marker's expression is.

    For each gene in the loaded ZFIN corpus, counts how many identity-panel anchor sets its
    expression grounds under (a record's term, or any of its is_a/part_of ancestors, lands
    at-or-under the anchor), and returns 1 / that count -- 1.0 when the gene marks a single
    lineage, smaller when it is promiscuous. label.decide uses it to rescue a weak_signal
    cluster from the dilution veto when one matched marker is sharply lineage-specific.
    Data-derived from the loaded corpus + panel anchors; no hardcoded biology. Ancestor walks
    are memoized so each id is walked at most once.

    Args:
        expression_map (Mapping[str, list[ZfinExpressionRecord]]): ZFIN expression from
            data.load_zfin_expression. Keys are lowercased gene symbols.
        identity_anchors (Sequence[frozenset[str]]): The ontology_anchor of each identity
            panel (one frozenset of ZFA ids per panel).
        zfa_ontology (nx.MultiDiGraph): ZFA ontology from data.load_zfa.

    Returns:
        dict[str, float]: gene symbol to 1 / (number of identity-panel anchors it grounds
        under), in (0, 1]. A gene that grounds under no anchor is absent from the map; callers
        treat absence as maximally promiscuous (it never triggers the rescue).
    """
    ancestor_cache: dict[str, frozenset[str]] = {}
    specificity: dict[str, float] = {}
    for gene, records in expression_map.items():
        credited: set[str] = set()
        for record in records:
            credited |= _term_with_ancestors(record.zfa_id, zfa_ontology, ancestor_cache)
        count = sum(1 for anchor in identity_anchors if anchor & credited)
        if count:
            specificity[gene] = 1.0 / count
    return specificity


# ---------------------------------------------------------------------------
# Convergence descent
# ---------------------------------------------------------------------------


def _display_name(zfa_ontology: nx.MultiDiGraph, term_id: str) -> str:
    """Human-readable term name, falling back to the id when name-less or absent.

    Args:
        zfa_ontology (nx.MultiDiGraph): The loaded ZFA ontology.
        term_id (str): A ZFA term id.

    Returns:
        str: The term's name, or the id itself when it has none or is not in the graph.
    """
    if term_id in zfa_ontology:
        return term_name(zfa_ontology, term_id) or term_id
    return term_id


def _descend(
    anchor: frozenset[str],
    term_to_genes: dict[str, set[str]],
    information_content: Mapping[str, float],
    zfa_ontology: nx.MultiDiGraph,
    ancestor_cache: dict[str, frozenset[str]],
) -> tuple[str | None, list[str]]:
    """Seed at the best-supported anchor id and descend into the best-scored supported child.

    The naming half of the vote. Roots at the panel anchor (a reliable broad term) and walks
    DOWN the is_a+part_of graph, at each step taking the child the most genes support (scored
    by support x IC, support dominant) as long as it keeps at least CONVERGENCE_MIN genes AND
    DESCENT_SUPPORT_FRACTION of its parent's support, AND it uniquely leads its siblings on support.
    The relative-support floor stops the walk before a coincidental few-gene leaf; the unique-winner
    rule stops it when two children tie on support (the markers then spread across sibling subtypes
    rather than converging on one, so the parent is the right level). STOPLIST roots are never seeded
    or entered; the walk never goes above the seed, so the terminal is at or under the anchor.

    Args:
        anchor (frozenset[str]): The winning panel's ontology anchor ids (the descent roots).
        term_to_genes (dict[str, set[str]]): The per-term distinct-gene tally.
        information_content (Mapping[str, float]): IC model (the IDF half of the score).
        zfa_ontology (nx.MultiDiGraph): ZFA ontology graph.
        ancestor_cache (dict[str, frozenset[str]]): Per-pass memo for depth lookups.

    Returns:
        tuple[str | None, list[str]]: The terminal term id and the seed-to-terminal path, or
        (None, []) when no anchor id is in the tally with at least CONVERGENCE_MIN support
        (the cluster does not converge under this panel; the caller then falls back).
    """

    def support(term_id: str) -> int:
        return len(term_to_genes.get(term_id, ()))

    def depth(term_id: str) -> int:
        return len(_term_with_ancestors(term_id, zfa_ontology, ancestor_cache)) - 1

    def score(term_id: str) -> float:
        return support(term_id) * information_content.get(term_id, 0.0)

    seeds = [a for a in anchor if a in zfa_ontology and a not in STOPLIST and support(a) >= CONVERGENCE_MIN]
    if not seeds:
        return None, []
    # Most-supported anchor id; on a support tie prefer the rarer, then the broader (shallower) root.
    current = sorted(seeds, key=lambda a: (-support(a), -information_content.get(a, 0.0), depth(a), a))[0]
    path = [current]
    visited = {current}
    while True:
        supported = [
            child
            for child in children(zfa_ontology, current)
            if child in term_to_genes
            and child not in STOPLIST
            and child not in visited
            and support(child) >= CONVERGENCE_MIN
            and support(child) >= DESCENT_SUPPORT_FRACTION * support(current)
        ]
        if not supported:
            return current, path
        # Rank by support (then IC, specificity, id). Descend ONLY when the markers converge on a
        # single subtype: if the top two children tie on support, the cluster spreads across
        # siblings, so the current term is the right level -- stop rather than pick one arbitrarily.
        ranked = sorted(supported, key=lambda c: (-support(c), -score(c), -depth(c), c))
        if len(ranked) >= 2 and support(ranked[1]) == support(ranked[0]):
            return current, path
        current = ranked[0]
        visited.add(current)
        path.append(current)


def resolve_label(
    symbols: list[str],
    *,
    expression_map: Mapping[str, list[ZfinExpressionRecord]],
    zfa_ontology: nx.MultiDiGraph,
    information_content: Mapping[str, float],
    anchor: frozenset[str] = frozenset(),
    vote_trace: list[TermVoteTrace] | None = None,
) -> list[TermVote]:
    """Anchor-rooted, support-weighted convergence namer: name a cluster from its markers.

    symbols must be already-normalized current ZFIN symbols (caller normalizes first using
    genes.normalize_symbol; keep only STATUS_RESOLVED). Each distinct gene votes for every ZFA
    term it expresses in and all that term's is_a+part_of ancestors (DAG ancestor credit). The
    cluster is then named by descending from the winning panel's ontology anchor along
    well-supported child paths (see _descend): the result is the deepest term that keeps a clear
    majority of its parent's support, at or under the anchor by construction.

    Args:
        symbols (list[str]): Already-normalized current ZFIN symbols in rank
            order (most significant first). Duplicates are ignored; each gene
            votes at most once per term.
        expression_map (Mapping[str, list[ZfinExpressionRecord]]): ZFIN expression
            data from data.load_zfin_expression.
        zfa_ontology (nx.MultiDiGraph): ZFA ontology from data.load_zfa.
        information_content (Mapping[str, float]): IC model from build_information_content.
        anchor (frozenset[str]): The winning panel's ontology anchor ids -- the descent roots.
            Empty (the default, e.g. pure decide() tests) means no descent and an empty result.
        vote_trace (list[TermVoteTrace] | None): Optional sink for introspection.
            When provided, a TermVoteTrace is appended for every tallied term, with its
            (still-computed) gates plus the descent annotations on_descent_path and
            support_fraction; when None (the labeling path) no per-term work is done.

    Returns:
        list[TermVote]: A one-element list with the named terminal term, or empty when no
        anchor id is supported (the cluster does not converge under this panel -> fallback).
    """
    # Memoize ancestor walks across this vote (each id walked at most once).
    ancestor_cache: dict[str, frozenset[str]] = {}

    # Tally distinct genes per ZFA term (direct expression + DAG ancestors).
    term_to_genes: dict[str, set[str]] = {}
    seen: set[str] = set()
    for symbol in symbols:
        if symbol in seen:
            continue  # each gene votes at most once
        seen.add(symbol)
        records = expression_lookup(expression_map, symbol)
        if not records:
            continue
        # Collect all terms this gene credits: the expressed term and every
        # is_a+part_of ancestor (guarded against ids absent from the graph).
        credited: set[str] = set()
        for record in records:
            credited |= _term_with_ancestors(record.zfa_id, zfa_ontology, ancestor_cache)
        for term_id in credited:
            term_to_genes.setdefault(term_id, set()).add(symbol)

    # Name by descending from the panel anchor along well-supported child paths.
    terminal, path = _descend(anchor, term_to_genes, information_content, zfa_ontology, ancestor_cache)
    path_position = {term_id: index for index, term_id in enumerate(path)}

    # Trace (when requested): record every tallied term with its gates plus the descent
    # annotations, so the walk -- and why a deeper term was not entered -- can be explained.
    # The three gates no longer filter naming (the descent's support floors do); they remain in
    # the trace as transparency, so passed_information_content is now informational only.
    if vote_trace is not None:
        max_support = max((len(genes) for genes in term_to_genes.values()), default=1)
        for term_id, genes in term_to_genes.items():
            gene_count = len(genes)
            passed_convergence = gene_count >= CONVERGENCE_MIN
            passed_stoplist = term_id not in STOPLIST
            term_ic = information_content.get(term_id, 0.0)
            passed_information_content = term_ic >= INFORMATION_CONTENT_MIN
            eligible = passed_convergence and passed_stoplist and passed_information_content
            on_path = term_id in path_position
            if on_path and path_position[term_id] > 0:
                parent_support = len(term_to_genes[path[path_position[term_id] - 1]])
                support_fraction = gene_count / parent_support if parent_support else 1.0
            elif on_path:
                support_fraction = 1.0
            else:
                support_fraction = gene_count / max_support
            vote_trace.append(
                TermVoteTrace(
                    zfa_id=term_id,
                    zfa_name=_display_name(zfa_ontology, term_id),
                    gene_count=gene_count,
                    genes=tuple(sorted(genes)),
                    information_content=term_ic,
                    ancestor_depth=len(_term_with_ancestors(term_id, zfa_ontology, ancestor_cache)) - 1,
                    passed_convergence=passed_convergence,
                    passed_stoplist=passed_stoplist,
                    passed_information_content=passed_information_content,
                    eligible=eligible,
                    support_fraction=round(support_fraction, 4),
                    on_descent_path=on_path,
                )
            )

    if terminal is None:
        return []
    return [
        TermVote(
            zfa_id=terminal,
            zfa_name=_display_name(zfa_ontology, terminal),
            genes=tuple(sorted(term_to_genes[terminal])),
            information_content=information_content.get(terminal, 0.0),
            ancestor_depth=len(_term_with_ancestors(terminal, zfa_ontology, ancestor_cache)) - 1,
        )
    ]
