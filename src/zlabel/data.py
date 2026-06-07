"""Pure data layer: load the ontology files zlabel grounds marker genes against.

Three loaders turn the files `scripts/setup_data.sh` downloads into in-memory
structures — no network, no labeling logic:

- `load_zfa` — the ZFA anatomy ontology as a graph (+ `term_name` / `ancestors`).
- `load_zfin_expression` — ZFIN wildtype expression: gene -> in-vivo anatomy + stage.
- `load_gene_synonym_map` — alias / previous-name -> current symbol(s), from the
  ZFIN GAF, for gene-symbol normalization.

The querying that composes these into converging evidence lives in `ground.py`
(Phase 3); this module only reads files into data structures.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import networkx as nx
import obonet

# --- ZFA: zebrafish anatomy ontology -----------------------------------------
#
# ZFA mixes `is_a` (subsumption), `part_of` (mereology), and `develops_from`
# (lineage) edges. Most ancestor queries want `is_a + part_of` (the defaults):
# both imply a term is a "kind-of" or "part-of" its ancestor. `develops_from` is
# lineage history and should be queried on its own when needed.

DEFAULT_ANCESTOR_EDGE_TYPES = frozenset({"is_a", "part_of"})

# All ZFA edge types zlabel tracks.
ALL_RELATION_EDGE_TYPES = frozenset({"is_a", "part_of", "develops_from"})


def load_zfa(path: Path) -> nx.MultiDiGraph:
    """Load a ZFA OBO file into a networkx MultiDiGraph.

    Args:
        path (Path): Path to a `.obo` file (full ZFA release or a test subset).

    Returns:
        A `MultiDiGraph` whose nodes are OBO term IDs and whose edges go from
        child term to parent term, keyed by relationship type (`"is_a"`,
        `"part_of"`, `"develops_from"`, ...).

    Raises:
        FileNotFoundError: If `path` does not exist.
    """
    return obonet.read_obo(str(path))


def get_term(graph: nx.MultiDiGraph, term_id: str) -> dict[str, Any]:
    """Look up a term's full attribute dict.

    Args:
        graph (nx.MultiDiGraph): Loaded ZFA graph.
        term_id (str): OBO term id, e.g. `"ZFA:0005307"`.

    Returns:
        The term's attribute dict (name, namespace, def, synonyms, etc.).

    Raises:
        KeyError: If `term_id` is not in the graph.
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
        The term's `name` attribute, or None (some OBO terms are name-less stubs).

    Raises:
        KeyError: If `term_id` is not in the graph.
    """
    name = get_term(graph, term_id).get("name")
    return str(name) if isinstance(name, str) else None


def ancestors(
    graph: nx.MultiDiGraph,
    term_id: str,
    edge_types: Iterable[str] = DEFAULT_ANCESTOR_EDGE_TYPES,
) -> list[str]:
    """Walk a term's ancestors, following only the given relationship types.

    BFS over parent edges, restricted to `edge_types` (the edge key is the
    relationship type). Cycles are guarded against — ZFA shouldn't have cycles in
    `is_a`/`part_of`, but defensive coding keeps the loader robust to ontology
    errors.

    Args:
        graph (nx.MultiDiGraph): Loaded ZFA graph.
        term_id (str): OBO term id to start from.
        edge_types (Iterable[str]): Relationship types to follow. Defaults to
            `is_a + part_of`.

    Returns:
        Ancestor term IDs in BFS order, excluding `term_id` itself.

    Raises:
        KeyError: If `term_id` is not in the graph.
    """
    if term_id not in graph:
        raise KeyError(term_id)
    allowed = frozenset(edge_types)
    seen: set[str] = set()
    out: list[str] = []
    frontier = [term_id]
    while frontier:
        next_frontier: list[str] = []
        for node in frontier:
            for _, parent, key in graph.out_edges(node, keys=True):
                # `parent != term_id` covers the self-link / start-node case;
                # `seen` covers longer cycles further out from the start.
                if key in allowed and parent not in seen and parent != term_id:
                    seen.add(parent)
                    out.append(parent)
                    next_frontier.append(parent)
        frontier = next_frontier
    return out


# --- ZFIN wildtype expression: gene -> in-vivo anatomy (ZFA) + stage (ZFS) ----
#
# The curated `wildtype-expression_fish.txt` ZFIN distributes is the labeler's
# primary in-vivo grounding evidence — "where do this cluster's markers express?"
# It is tab-delimited with NO header and 15 columns; only the gene symbol, the
# super/sub anatomy (ZFA id + name), and the start/end stages are consumed.

_COL_SYMBOL = 1
_COL_SUPER_ID = 3
_COL_SUPER_NAME = 4
_COL_SUB_ID = 5
_COL_SUB_NAME = 6
_COL_START_STAGE = 7
_COL_END_STAGE = 8


@dataclass(frozen=True)
class ZfinExpressionRecord:
    """One ZFIN wildtype-expression observation for a gene.

    Attributes:
        zfa_id (str): The most specific ZFA anatomy id the gene expresses in (the
            sub-structure when the row has one, else the super-structure).
        zfa_name (str): That structure's human-readable name.
        start_stage (str): ZFS developmental start stage — a name, not hours
            (e.g. `Long-pec`, `Gastrula:Bud`, `Adult`).
        end_stage (str): ZFS developmental end stage.
    """

    zfa_id: str
    zfa_name: str
    start_stage: str
    end_stage: str


def load_zfin_expression(path: Path) -> dict[str, list[ZfinExpressionRecord]]:
    """Load ZFIN wildtype expression into a `{gene_symbol: [records]}` map.

    Keys are lowercased gene symbols (matching normalized marker symbols). The
    structure recorded per row is the most specific available — the sub-structure
    when present, else the super-structure — so a footprint favors precise anatomy
    (e.g. `dorsal aorta` over `blood vessel`); the coarser term stays recoverable
    via `ancestors`.

    Args:
        path (Path): Path to `wildtype-expression_fish.txt` (or a subset).

    Returns:
        A `{lowercased gene symbol: list[ZfinExpressionRecord]}` map. Empty dict
        if `path` does not exist — the table is optional, and absent simply means
        the grounding step has no expression footprint for a gene.
    """
    if not path.exists():
        return {}
    table: dict[str, list[ZfinExpressionRecord]] = {}
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            fields = line.rstrip("\n").split("\t")
            if len(fields) <= _COL_END_STAGE:
                continue
            symbol = fields[_COL_SYMBOL].strip()
            if not symbol:
                continue
            sub_id = fields[_COL_SUB_ID].strip()
            if sub_id:
                zfa_id, zfa_name = sub_id, fields[_COL_SUB_NAME].strip()
            else:
                zfa_id, zfa_name = fields[_COL_SUPER_ID].strip(), fields[_COL_SUPER_NAME].strip()
            if not zfa_id:
                continue
            table.setdefault(symbol.lower(), []).append(
                ZfinExpressionRecord(
                    zfa_id=zfa_id,
                    zfa_name=zfa_name,
                    start_stage=fields[_COL_START_STAGE].strip(),
                    end_stage=fields[_COL_END_STAGE].strip(),
                ),
            )
    return table


# --- ZFIN GAF: gene-symbol synonyms ------------------------------------------


def load_gene_synonym_map(path: Path) -> dict[str, set[str]]:
    """Build a `{name -> {current symbols}}` map from the GAF's synonym column.

    The GAF (column 11, `DB Object Synonym`) lists each gene's synonyms and ZFIN
    previous-names alongside its current symbol (column 3). This inverts that into
    a case-folded lookup from any name/previous-name to the *current* symbol(s)
    that declare it — so a marker citing a deprecated symbol (e.g. `hbae1`, a ZFIN
    previous-name of `hbae1.1`/`.2`) resolves to the symbols actually present in a
    dataset. `genes.normalize_symbol` (Phase 2) consumes this. Reuses the GAF
    already downloaded for grounding — no extra data authority.

    Args:
        path (Path): Path to the GAF 2.x file (`zfin.gaf`).

    Returns:
        `{lowercased name -> {current symbols}}`. A gene's current symbol maps to
        itself, and every synonym/previous-name maps to it too — one previous-name
        may map to several current paralogs. Empty when the GAF has no usable rows.

    Raises:
        FileNotFoundError: If `path` does not exist.
    """
    synonym_map: dict[str, set[str]] = {}
    with path.open(encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.rstrip("\r\n")
            if not line or line.startswith("!"):
                continue
            fields = line.split("\t")
            if len(fields) < 11:  # need through column 11 (synonyms); skip malformed rows
                continue
            symbol = fields[2].strip()
            if not symbol:
                continue
            names = [symbol, *fields[10].split("|")] if fields[10] else [symbol]
            for name in names:
                key = name.strip().lower()
                if key:
                    synonym_map.setdefault(key, set()).add(symbol)
    return synonym_map
