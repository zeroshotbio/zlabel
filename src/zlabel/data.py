"""Pure data layer: load the ontology files zlabel grounds marker genes against.

Three loaders turn the files scripts/setup_data.sh downloads into in-memory
structures, with no network and no labeling logic. load_zfa reads the ZFA anatomy
ontology into a graph (with term_name and edge-type-aware ancestors helpers).
load_zfin_expression parses ZFIN wildtype expression into a gene-to-anatomy-and-stage
map. load_gene_synonym_map inverts the ZFIN GAF synonym column into an
alias-to-current-symbol map for gene normalization.

The querying that composes these into converging evidence lives in ground.py
(Phase 3); this module only reads files into data structures.
"""

import os
from collections import deque
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import networkx as nx
import obonet

# --- ZFA: zebrafish anatomy ontology -----------------------------------------
#
# ZFA mixes is_a (subsumption), part_of (mereology), and develops_from (lineage)
# edges. Most ancestor queries want is_a + part_of (the defaults): both imply a
# term is a "kind-of" or "part-of" its ancestor. develops_from is lineage history
# and should be queried on its own when needed.

DEFAULT_ANCESTOR_EDGE_TYPES = frozenset({"is_a", "part_of"})

# All ZFA edge types zlabel tracks.
ALL_RELATION_EDGE_TYPES = frozenset({"is_a", "part_of", "develops_from"})


def load_zfa(path: str | os.PathLike[str]) -> nx.MultiDiGraph:
    """Load a ZFA OBO file into a networkx MultiDiGraph.

    Args:
        path (str | os.PathLike[str]): Path to a .obo file (full ZFA release or a
            test subset).

    Returns:
        nx.MultiDiGraph: Graph whose nodes are OBO term IDs and whose edges go
            from child term to parent term, keyed by relationship type (is_a,
            part_of, develops_from, ...).

    Raises:
        FileNotFoundError: If path does not exist.
    """
    return obonet.read_obo(Path(path))


def get_term(graph: nx.MultiDiGraph, term_id: str) -> dict[str, Any]:
    """Look up a term's full attribute dict.

    Args:
        graph (nx.MultiDiGraph): Loaded ZFA graph.
        term_id (str): OBO term id, e.g. ZFA:0005307.

    Returns:
        dict[str, Any]: The term's attributes (name, namespace, def, synonyms,
            etc.).

    Raises:
        KeyError: If term_id is not in the graph.
    """
    if term_id not in graph:
        raise KeyError(term_id)
    return dict(graph.nodes[term_id])


def term_name(graph: nx.MultiDiGraph, term_id: str) -> str | None:
    """Return a term's human-readable name, or None if it has none.

    Args:
        graph (nx.MultiDiGraph): Loaded ZFA graph.
        term_id (str): OBO term id.

    Returns:
        str | None: The term's name, or None (some OBO terms are name-less stubs).

    Raises:
        KeyError: If term_id is not in the graph.
    """
    name = get_term(graph, term_id).get("name")
    # The attribute dict is loosely typed; guard against a non-string name.
    return name if isinstance(name, str) else None


def ancestors(
    graph: nx.MultiDiGraph,
    term_id: str,
    edge_types: Iterable[str] = DEFAULT_ANCESTOR_EDGE_TYPES,
) -> list[str]:
    """Walk a term's ancestors, following only the given relationship types.

    BFS over parent edges, restricted to edge_types (the edge key is the
    relationship type). Cycles are guarded against — ZFA shouldn't have cycles in
    is_a/part_of, but defensive coding keeps the loader robust to ontology errors.

    Args:
        graph (nx.MultiDiGraph): Loaded ZFA graph.
        term_id (str): OBO term id to start from.
        edge_types (Iterable[str]): Relationship types to follow. Defaults to
            is_a + part_of.

    Returns:
        list[str]: Ancestor term IDs in BFS order, excluding term_id itself.

    Raises:
        KeyError: If term_id is not in the graph.
    """
    if term_id not in graph:
        raise KeyError(term_id)
    allowed = frozenset(edge_types)
    # Seeding seen with term_id means the start node can't be rediscovered as an
    # ancestor, so a single membership check covers the self-link and any cycle.
    seen: set[str] = {term_id}
    result: list[str] = []
    queue: deque[str] = deque([term_id])
    while queue:
        node = queue.popleft()
        # keys=True yields the edge key, which obonet sets to the relationship type.
        for _, parent, rel in graph.out_edges(node, keys=True):
            if rel in allowed and parent not in seen:
                seen.add(parent)
                result.append(parent)
                queue.append(parent)
    return result


def children(
    graph: nx.MultiDiGraph,
    term_id: str,
    edge_types: Iterable[str] = DEFAULT_ANCESTOR_EDGE_TYPES,
) -> list[str]:
    """Direct is_a/part_of children of a term -- the one-hop inverse of ancestors.

    A child is a node c with an edge c -> term_id whose relationship is in edge_types
    (the same child-to-parent edges ancestors walks, read one hop the other way). Only
    direct children, not the full descendant closure. The convergence descent uses it to
    step from a broad anchor toward the more specific terms the markers support.

    Args:
        graph (nx.MultiDiGraph): Loaded ZFA graph.
        term_id (str): OBO term id whose children to list.
        edge_types (Iterable[str]): Relationship types to follow. Defaults to is_a + part_of.

    Returns:
        list[str]: Direct child term ids, sorted for deterministic output.

    Raises:
        KeyError: If term_id is not in the graph.
    """
    if term_id not in graph:
        raise KeyError(term_id)
    allowed = frozenset(edge_types)
    return sorted({child for child, _, rel in graph.in_edges(term_id, keys=True) if rel in allowed})


# --- ZFIN wildtype expression: gene -> in-vivo anatomy (ZFA) + stage (ZFS) ----
#
# The curated wildtype-expression_fish.txt ZFIN distributes is the labeler's
# primary in-vivo grounding evidence — "where do this cluster's markers express?"
# It is tab-delimited with NO header and 15 columns; only the gene symbol, the
# super/sub anatomy (ZFA id + name), and the start/end stages are consumed.

# 0-indexed field positions in the 15-column row (1-based column in parens).
_COL_SYMBOL = 1  # gene symbol (col 2)
_COL_SUPER_ID = 3  # super-structure ZFA id (col 4)
_COL_SUPER_NAME = 4  # super-structure name (col 5)
_COL_SUB_ID = 5  # sub-structure ZFA id (col 6)
_COL_SUB_NAME = 6  # sub-structure name (col 7)
_COL_START_STAGE = 7  # ZFS start stage (col 8)
_COL_END_STAGE = 8  # ZFS end stage (col 9)


@dataclass(frozen=True)
class ZfinExpressionRecord:
    """One ZFIN wildtype-expression observation for a gene.

    Attributes:
        zfa_id (str): The most specific ZFA anatomy id the gene expresses in (the
            sub-structure when the row has one, else the super-structure).
        zfa_name (str): That structure's human-readable name.
        start_stage (str): ZFS developmental start stage — a name, not hours
            (e.g. Long-pec, Gastrula:Bud, Adult).
        end_stage (str): ZFS developmental end stage.
    """

    zfa_id: str
    zfa_name: str
    start_stage: str
    end_stage: str


def _most_specific_structure(fields: list[str]) -> tuple[str, str]:
    """Pick a row's most specific anatomy: the sub-structure, else the super.

    ZFIN records a broad super-structure and (sometimes) a narrower sub-structure.
    The narrower one is the better grounding, so it wins; the coarser term stays
    recoverable later via ancestors.

    Args:
        fields (list[str]): The tab-split, already-stripped columns of one row.

    Returns:
        tuple[str, str]: The chosen (zfa_id, zfa_name). Either may be empty when
            the row records no anatomy.
    """
    if fields[_COL_SUB_ID]:
        return fields[_COL_SUB_ID], fields[_COL_SUB_NAME]
    return fields[_COL_SUPER_ID], fields[_COL_SUPER_NAME]


def load_zfin_expression(path: str | os.PathLike[str]) -> dict[str, list[ZfinExpressionRecord]]:
    """Load ZFIN wildtype expression into a per-gene record map.

    Keys are lowercased gene symbols (matching normalized marker symbols). Each
    row contributes one record under its most specific anatomy, so a gene's value
    is the union of every structure it was observed in.

    Args:
        path (str | os.PathLike[str]): Path to wildtype-expression_fish.txt (or a
            subset).

    Returns:
        dict[str, list[ZfinExpressionRecord]]: Map from lowercased gene symbol to
            its expression records. Empty dict if path does not exist — the table
            is optional, and absent simply means the grounding step has no
            expression footprint for a gene.
    """
    path = Path(path)
    if not path.exists():
        return {}
    table: dict[str, list[ZfinExpressionRecord]] = {}
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            # Split into columns once, trimming stray whitespace (and the newline)
            # so every field read below is clean — no per-field strip needed.
            fields = [field.strip() for field in line.split("\t")]
            if len(fields) <= _COL_END_STAGE:  # row too short to hold the columns we read
                continue
            symbol = fields[_COL_SYMBOL]
            if not symbol:
                continue
            zfa_id, zfa_name = _most_specific_structure(fields)
            if not zfa_id:  # a row with neither sub- nor super-structure carries no anatomy
                continue
            table.setdefault(symbol.lower(), []).append(
                ZfinExpressionRecord(
                    zfa_id=zfa_id,
                    zfa_name=zfa_name,
                    start_stage=fields[_COL_START_STAGE],
                    end_stage=fields[_COL_END_STAGE],
                ),
            )
    return table


# --- ZFIN GAF: gene-symbol synonyms ------------------------------------------
#
# The GAF is tab-delimited GO annotations; we read only two columns to map any
# alias / previous-name to the current symbol(s) that declare it.

_GAF_COL_SYMBOL = 2  # DB Object Symbol — the current symbol (col 3)
_GAF_COL_SYNONYMS = 10  # DB Object Synonym — pipe-separated aliases (col 11)
_GAF_MIN_COLS = 11  # a usable row reaches at least through the synonym column


def load_gene_synonym_map(path: str | os.PathLike[str]) -> dict[str, set[str]]:
    """Build a name-to-current-symbols map from the GAF's synonym column.

    The GAF (column 11, DB Object Synonym) lists each gene's synonyms and ZFIN
    previous-names alongside its current symbol (column 3). This inverts that into
    a case-folded lookup from any name/previous-name to the current symbol(s) that
    declare it — so a marker citing a deprecated symbol (e.g. hbae1, a ZFIN
    previous-name of hbae1.1/.2) resolves to the symbols actually present in a
    dataset. genes.normalize_symbol (Phase 2) consumes this. Reuses the GAF
    already downloaded for grounding — no extra data authority.

    Args:
        path (str | os.PathLike[str]): Path to the GAF 2.x file (zfin.gaf).

    Returns:
        dict[str, set[str]]: Map from lowercased name to the current symbol(s)
            that declare it. A gene's current symbol maps to itself, every
            synonym/previous-name maps to it too, and one previous-name may map to
            several current paralogs. Empty when the GAF has no usable rows.

    Raises:
        FileNotFoundError: If path does not exist.
    """
    synonym_map: dict[str, set[str]] = {}
    with Path(path).open(encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.rstrip("\r\n")
            if not line or line.startswith("!"):  # skip blanks and GAF comment lines
                continue
            fields = line.split("\t")
            if len(fields) < _GAF_MIN_COLS:  # skip rows missing the synonym column
                continue
            symbol = fields[_GAF_COL_SYMBOL].strip()
            if not symbol:
                continue
            # The current symbol maps to itself; add any pipe-separated synonyms.
            names = [symbol]
            if fields[_GAF_COL_SYNONYMS]:
                names.extend(fields[_GAF_COL_SYNONYMS].split("|"))
            for name in names:
                key = name.strip().lower()
                if key:
                    synonym_map.setdefault(key, set()).add(symbol)
    return synonym_map
