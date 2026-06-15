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
       - IC >= INFORMATION_CONTENT_MIN (near-root terms down-weighted)
  4. Rank surviving terms most-specific first: descending IC (the
     selector), then descending gene count (gate magnitude), then
     descending ancestor_depth (specificity tiebreak), then id (stable output).
  5. Return the ranked list; empty means nothing converged.

The background IC model (build_information_content) is computed once from the loaded ZFIN
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
from zlabel.models import TermVoteTrace

# ---------------------------------------------------------------------------
# Named constants — all provisional; calibrated by the eval PR.
# ---------------------------------------------------------------------------

CONVERGENCE_MIN: int = 3
# Distinct normalized genes that must credit a ZFA term before it is
# eligible for naming. Below this, evidence is too thin to call the term.
# Provisional.

INFORMATION_CONTENT_MIN: float = 1.0
# Minimum information content (in bits, -log2 scale) a term must have to
# be eligible. Screens near-root attractors that survive the stoplist:
# INFORMATION_CONTENT_MIN=1.0 means the term must be credited by fewer than half of all
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
# gene counts. INFORMATION_CONTENT_MIN is the second safety net; the stoplist handles terms
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

    The unit of DAG ancestor credit shared by the IC model, the convergence vote, and the
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


# ---------------------------------------------------------------------------
# Convergence vote
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


def resolve_label(
    symbols: list[str],
    *,
    expression_map: Mapping[str, list[ZfinExpressionRecord]],
    zfa_ontology: nx.MultiDiGraph,
    information_content: Mapping[str, float],
    vote_trace: list[TermVoteTrace] | None = None,
) -> list[TermVote]:
    """IC-weighted convergence vote: name a cluster from its normalized markers.

    symbols must be already-normalized current ZFIN symbols (caller normalizes
    first using genes.normalize_symbol; keep only STATUS_RESOLVED). Each
    distinct gene votes for every ZFA term it expresses in and all that term's
    is_a+part_of ancestors (DAG ancestor credit). Terms that clear
    CONVERGENCE_MIN distinct genes, are not in STOPLIST, and have IC >= INFORMATION_CONTENT_MIN
    are returned ranked most-specific first (descending IC, then gene count,
    then ancestor_depth, then id). Empty list means nothing converged.

    Args:
        symbols (list[str]): Already-normalized current ZFIN symbols in rank
            order (most significant first). Duplicates are ignored; each gene
            votes at most once per term.
        expression_map (Mapping[str, list[ZfinExpressionRecord]]): ZFIN expression
            data from data.load_zfin_expression.
        zfa_ontology (nx.MultiDiGraph): ZFA ontology from data.load_zfa.
        information_content (Mapping[str, float]): IC model from build_information_content.
        vote_trace (list[TermVoteTrace] | None): Optional sink for introspection.
            When provided, a TermVoteTrace is appended for every tallied term,
            including gate near-misses; when None (the labeling path) the returned
            candidate list is unchanged and no extra work is done for failing terms.

    Returns:
        list[TermVote]: Candidate terms ranked most-specific first (index 0
        is the best label). Empty when no term clears all three gates.
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

    # Build TermVote candidates that clear all three gates. When vote_trace is
    # provided, also record a TermVoteTrace for every tallied term -- including
    # near-misses -- so an abstention or fallback can be explained gate by gate.
    candidates: list[TermVote] = []
    for term_id, genes in term_to_genes.items():
        gene_count = len(genes)
        passed_convergence = gene_count >= CONVERGENCE_MIN
        passed_stoplist = term_id not in STOPLIST
        term_ic = information_content.get(term_id, 0.0)
        passed_information_content = term_ic >= INFORMATION_CONTENT_MIN
        eligible = passed_convergence and passed_stoplist and passed_information_content
        if eligible:
            # _term_with_ancestors(term_id) includes the term itself; ancestor_depth counts
            # only its ancestors. Reuses the cache, so no term's ancestors are walked twice.
            ancestor_depth = len(_term_with_ancestors(term_id, zfa_ontology, ancestor_cache)) - 1
            candidates.append(
                TermVote(
                    zfa_id=term_id,
                    zfa_name=_display_name(zfa_ontology, term_id),
                    genes=tuple(sorted(genes)),
                    information_content=term_ic,
                    ancestor_depth=ancestor_depth,
                )
            )
        if vote_trace is not None:
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
                )
            )

    # Rank most-specific first: IC is the selector (highest IC = most specific
    # relative to the background); gene count is the gate magnitude;
    # ancestor_depth breaks equal-IC ties; id ensures stable, deterministic output.
    candidates.sort(key=lambda vote: (-vote.information_content, -len(vote.genes), -vote.ancestor_depth, vote.zfa_id))
    return candidates
