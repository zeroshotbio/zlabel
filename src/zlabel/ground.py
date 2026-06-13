"""Pure grounding lookups for zlabel.

Three small exported functions consumed by label.decide():

  expression_lookup  — fetch a gene's ZFIN in-vivo expression records.
  grounds_under      — per-record predicate: does a ZFA term sit under an anchor?
  stage_plausibility — per-marker tri-state: are the gene's records on-stage?

None of these functions do I/O; they operate on data already loaded by the
data-layer loaders. The ZFS stage table is lifted verbatim from daniotype
(Kimmel 1995, verified against ZFIN 2026-06-06) and kept private here —
callers interact only with stage_plausibility, not the raw hpf table.

Only these three names are exported; the stage table and anatomy helpers are
private (prefixed _) and intentionally not in __all__.
"""

from __future__ import annotations

from collections.abc import Mapping

import networkx as nx

from zlabel.data import ZfinExpressionRecord, ancestors

# ---------------------------------------------------------------------------
# ZFS stage table (private) — lifted from daniotype zfs_stages.py
# Kimmel et al. 1995 staging series (hpf at 28.5 C), verified 2026-06-06.
# ---------------------------------------------------------------------------

_STAGE_BEGIN_HPF: tuple[tuple[str, float], ...] = (
    ("Zygote:1-cell", 0.0),
    ("Cleavage:2-cell", 0.75),
    ("Cleavage:4-cell", 1.0),
    ("Cleavage:8-cell", 1.25),
    ("Cleavage:16-cell", 1.5),
    ("Cleavage:32-cell", 1.75),
    ("Cleavage:64-cell", 2.0),
    ("Blastula:128-cell", 2.25),
    ("Blastula:256-cell", 2.5),
    ("Blastula:512-cell", 2.75),
    ("Blastula:1k-cell", 3.0),
    ("Blastula:High", 3.33),
    ("Blastula:Oblong", 3.66),
    ("Blastula:Sphere", 4.0),
    ("Blastula:Dome", 4.33),
    ("Blastula:30%-epiboly", 4.66),
    ("Gastrula:50%-epiboly", 5.25),
    ("Gastrula:Germ-ring", 5.66),
    ("Gastrula:Shield", 6.0),
    ("Gastrula:75%-epiboly", 8.0),
    ("Gastrula:90%-epiboly", 9.0),
    ("Gastrula:Bud", 10.0),
    ("Segmentation:1-4 somites", 10.33),
    ("Segmentation:5-9 somites", 11.66),
    ("Segmentation:10-13 somites", 14.0),
    ("Segmentation:14-19 somites", 16.0),
    ("Segmentation:20-25 somites", 19.0),
    ("Segmentation:26+ somites", 22.0),
    ("Pharyngula:Prim-5", 24.0),
    ("Pharyngula:Prim-15", 30.0),
    ("Pharyngula:Prim-25", 36.0),
    ("Pharyngula:High-pec", 42.0),
    ("Hatching:Long-pec", 48.0),
    ("Hatching:Pec-fin", 60.0),
    ("Larval:Protruding-mouth", 72.0),
    ("Larval:Day 4", 96.0),
    ("Larval:Day 5", 120.0),
    ("Larval:Day 6", 144.0),
    ("Larval:Days 7-13", 168.0),
    ("Larval:Days 14-20", 336.0),
    ("Larval:Days 21-29", 504.0),
    ("Juvenile:Days 30-44", 720.0),
    ("Juvenile:Days 45-89", 1080.0),
    ("Adult", 2160.0),
)


def _build_windows() -> dict[str, tuple[float, float]]:
    """Build a stage-name -> (begin_hpf, end_hpf) map.

    The end of each stage is the begin of the next; the last (Adult) is open.

    Returns:
        dict[str, tuple[float, float]]: Prefixed stage name to (begin, end).
    """
    windows: dict[str, tuple[float, float]] = {}
    for i, (name, begin) in enumerate(_STAGE_BEGIN_HPF):
        end = _STAGE_BEGIN_HPF[i + 1][1] if i + 1 < len(_STAGE_BEGIN_HPF) else float("inf")
        windows[name] = (begin, end)
    return windows


_STAGE_WINDOW: dict[str, tuple[float, float]] = _build_windows()

# Bare substage names (period prefix dropped) -> window.
# ZFIN distributes the prefixed form (Hatching:Long-pec) but some exports
# carry only the bare substage (Long-pec); tolerate both.
# No substage name repeats across periods, so the mapping is unambiguous.
_BARE_STAGE_WINDOW: dict[str, tuple[float, float]] = {
    name.split(":", 1)[-1]: window for name, window in _STAGE_WINDOW.items()
}

# Default half-width of the on-stage window around the query hpf.
# +/- 12 h spans roughly one ZFS substage either side of a Pharyngula/Hatching
# query, keeping stage evidence informative without being a hard gate.
_DEFAULT_WINDOW_HPF: float = 12.0


def _stage_to_hpf(stage: str) -> tuple[float, float] | None:
    """Return a ZFS stage's (begin_hpf, end_hpf) window, or None if unmapped.

    Accepts the prefixed form (Hatching:Long-pec) or the bare substage
    (Long-pec); both resolve.

    Args:
        stage (str): A ZFS stage name as it appears in the ZFIN expression file.

    Returns:
        tuple[float, float] | None: The [begin, end) window in hpf, or None
        when the name is not a known ZFS stage.
    """
    s = stage.strip()
    window = _STAGE_WINDOW.get(s)
    if window is not None:
        return window
    return _BARE_STAGE_WINDOW.get(s.split(":", 1)[-1])


# ---------------------------------------------------------------------------
# Exported grounding functions
# ---------------------------------------------------------------------------

# Half-width of the stage window exported so callers can reference the default
# without importing the private table.
STAGE_WINDOW_HPF: float = _DEFAULT_WINDOW_HPF


def expression_lookup(
    expr_map: Mapping[str, list[ZfinExpressionRecord]],
    symbol: str,
) -> list[ZfinExpressionRecord]:
    """Return all ZFIN wildtype-expression records for a gene symbol.

    Lowercases the symbol before lookup to match the expr_map key convention
    (data.load_zfin_expression lowercases keys at load time). Returns an empty
    list when the gene has no curated expression data — not an error.

    Args:
        expr_map (Mapping[str, list[ZfinExpressionRecord]]): From
            data.load_zfin_expression; maps lowercased gene symbol to records.
        symbol (str): The resolved current ZFIN symbol to look up.

    Returns:
        list[ZfinExpressionRecord]: All expression records for the gene, or
        an empty list when the gene is absent from the map.
    """
    return list(expr_map.get(symbol.lower(), []))


def grounds_under(
    zfa_graph: nx.MultiDiGraph,
    rec_zfa_id: str,
    anchor: frozenset[str],
) -> bool:
    """Whether a ZFA anatomy term sits at or under a set of anchor terms.

    Checks three cases in order: the term is in the anchor (self-match);
    the term is not in the loaded ontology (absent -> False, not a crash);
    the term's is_a+part_of ancestors include any anchor member.

    This is a per-record predicate. label.py counts how many of the winner's
    matched markers ground under the anchor (aggregating across records).

    Args:
        zfa_graph (nx.MultiDiGraph): ZFA ontology graph from data.load_zfa.
        rec_zfa_id (str): The ZFA id from a ZFIN expression record.
        anchor (frozenset[str]): The bucket's ontology anchor ids. May be empty
            for state panels; grounds_under always returns False for an empty
            anchor.

    Returns:
        bool: True when rec_zfa_id is in anchor or is a descendant of any
        anchor member under is_a+part_of edges.
    """
    if not anchor:
        return False
    if rec_zfa_id in anchor:
        return True
    if rec_zfa_id not in zfa_graph:
        # Expression record points at a ZFA term not present in the loaded
        # ontology subset (e.g. an older id not in the fixture). Treat as
        # ungrounded rather than raising.
        return False
    return bool(anchor & set(ancestors(zfa_graph, rec_zfa_id)))


def stage_plausibility(
    records: list[ZfinExpressionRecord],
    stage_hpf: float | None,
    *,
    window: float = _DEFAULT_WINDOW_HPF,
) -> bool | None:
    """Whether a gene's expression records are on-stage at the query hpf.

    Per-marker tri-state: called once per matched marker over all of that
    marker's records. None means the marker cannot be evaluated for stage
    (no hpf given, or none of the records have a parseable ZFS stage name) and
    it drops out of the stage denominator in label.py. True/False reports
    whether ANY datable record's [start_stage, end_stage] span overlaps
    stage_hpf +/- window.

    Args:
        records (list[ZfinExpressionRecord]): All ZFIN expression records for
            one gene (from expression_lookup).
        stage_hpf (float | None): The dataset's developmental stage in hpf. If
            None, the result is always None.
        window (float): Half-width of the on-stage window in hpf. Defaults to
            _DEFAULT_WINDOW_HPF (12 h), spanning roughly one ZFS substage.

    Returns:
        bool | None: None when not datable; True when at least one datable
        record's developmental span overlaps [stage_hpf - window,
        stage_hpf + window]; False when all datable records fall outside.
    """
    if stage_hpf is None:
        return None
    found_datable = False
    for rec in records:
        start_w = _stage_to_hpf(rec.start_stage)
        end_w = _stage_to_hpf(rec.end_stage)
        if start_w is None or end_w is None:
            continue  # unparseable stage name -> skip, don't count as datable
        found_datable = True
        rec_lo = min(start_w[0], end_w[0])
        rec_hi = max(start_w[1], end_w[1])
        if rec_lo <= stage_hpf + window and rec_hi >= stage_hpf - window:
            return True  # any datable record on-stage -> plausible
    return None if not found_datable else False
