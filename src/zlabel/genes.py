"""Gene-symbol normalization for zlabel.

Converts raw marker gene symbols to their official current ZFIN symbols using
the synonym map produced by data.load_gene_synonym_map. The three possible
outcomes for any one symbol are resolved (exactly one current symbol found),
ambiguous (one previous name maps to several current paralogs), and unresolved
(not found). Ambiguous and unresolved markers are surfaced for the caller to
inspect; they are excluded from panel scoring so the labeler never guesses.

Phase 2 uses the synonym information already available from the downloaded GAF.
This is intentionally a minimal alias source. It is not treated as a complete
ZFIN nomenclature authority. If evaluation reveals normalization misses, a
dedicated ZFIN alias/previous-symbol table will be added in a later phase.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

# --- status constants ---------------------------------------------------------
#
# Three outcomes cover all cases. The scorer acts on STATUS_RESOLVED only;
# ambiguous and unresolved are both excluded from numerator and denominator,
# so scoring needs no separate branch for them.

STATUS_RESOLVED = "resolved"      # exactly one current symbol
STATUS_AMBIGUOUS = "ambiguous"    # one previous name -> several current paralogs
STATUS_UNRESOLVED = "unresolved"  # not found in the synonym map


# --- value type --------------------------------------------------------------


@dataclass(frozen=True)
class NormalizedSymbol:
    """Result of normalizing one gene symbol against the ZFIN GAF synonym map.

    Attributes:
        input (str): The marker symbol exactly as supplied by the caller
            (before lowercasing), so the round-trip is lossless.
        status (str): resolved, ambiguous, or unresolved.
        symbols (frozenset[str]): Current ZFIN symbol(s). Exactly one element
            when resolved, multiple when ambiguous, empty when unresolved.
        note (str | None): One-line human-readable reason when status is not
            resolved. None for a clean single-symbol resolution.
    """

    input: str
    status: str
    symbols: frozenset[str]
    note: str | None


# --- public API --------------------------------------------------------------


def normalize_symbol(symbol: str, synonym_map: dict[str, set[str]]) -> NormalizedSymbol:
    """Normalize one gene symbol to its current ZFIN symbol(s).

    Lowercases the input, looks it up in synonym_map, and returns a
    NormalizedSymbol recording the outcome. A previous name that fans out to
    multiple current paralogs is ambiguous; all candidates are kept in symbols
    and the result is never collapsed. A miss is unresolved with an empty
    symbols set, never a pass-through of the raw input.

    Args:
        symbol (str): Raw marker symbol from the caller (any case).
        synonym_map (dict[str, set[str]]): Mapping from lowercased name to
            current ZFIN symbol(s), as produced by data.load_gene_synonym_map.

    Returns:
        NormalizedSymbol: Resolution result with status, symbols, and note.
    """
    key = symbol.lower()
    candidates = synonym_map.get(key)
    if candidates is None:
        return NormalizedSymbol(
            input=symbol,
            status=STATUS_UNRESOLVED,
            symbols=frozenset(),
            note="not found in GAF synonym map",
        )
    if len(candidates) == 1:
        return NormalizedSymbol(
            input=symbol,
            status=STATUS_RESOLVED,
            symbols=frozenset(candidates),
            note=None,
        )
    # One previous name maps to several current paralogs — keep all of them.
    return NormalizedSymbol(
        input=symbol,
        status=STATUS_AMBIGUOUS,
        symbols=frozenset(candidates),
        note=f"maps to {len(candidates)} current paralogs: {', '.join(sorted(candidates))}",
    )


def normalize_markers(
    markers: Iterable[str],
    synonym_map: dict[str, set[str]],
) -> list[NormalizedSymbol]:
    """Normalize a sequence of marker symbols in rank order.

    Applies normalize_symbol to each marker and preserves input order so that
    rank information (position in the list) is not lost. Callers that need
    only resolved markers can filter by status == STATUS_RESOLVED.

    Args:
        markers (Iterable[str]): Raw marker symbols ordered by significance
            (most significant first, i.e. rank 1 = index 0).
        synonym_map (dict[str, set[str]]): As produced by
            data.load_gene_synonym_map.

    Returns:
        list[NormalizedSymbol]: One NormalizedSymbol per input marker, in the
            same order as the input.
    """
    return [normalize_symbol(m, synonym_map) for m in markers]
