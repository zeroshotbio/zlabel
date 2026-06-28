"""Gene-symbol normalization for zlabel.

Converts raw marker gene symbols to their official current ZFIN symbols using
the synonym map produced by data.load_gene_synonym_map. The three possible
outcomes for any one symbol are resolved (the input is itself a current symbol,
or an alias of exactly one), ambiguous (a previous name that fans out to several
current paralogs), and unresolved (not found). Ambiguous and unresolved markers
are surfaced for the caller to inspect; they are excluded from panel scoring so
the labeler never guesses.

Phase 2 uses the synonym information already available from the downloaded GAF.
This is intentionally a minimal alias source. It is not treated as a complete
ZFIN nomenclature authority. If evaluation reveals normalization misses, a
dedicated ZFIN alias/previous-symbol table will be added in a later phase.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass

# --- status constants ---------------------------------------------------------
# Callers filter by STATUS_RESOLVED; ambiguous and unresolved are excluded from scoring.

STATUS_RESOLVED = "resolved"  # exactly one current symbol
STATUS_AMBIGUOUS = "ambiguous"  # one previous name -> several current paralogs
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

    Strips and lowercases the input, looks it up in synonym_map, and returns a
    NormalizedSymbol recording the outcome. An input that is itself a current
    symbol resolves to that symbol, even when it is also a paralog's legacy
    alias — its own identity wins. A previous name that fans out to multiple
    current paralogs is ambiguous; all candidates are kept in symbols and the
    result is never collapsed. A miss is unresolved with an empty symbols set,
    never a pass-through of the raw input.

    Args:
        symbol (str): Raw marker symbol from the caller (any case).
        synonym_map (dict[str, set[str]]): Mapping from lowercased name to
            current ZFIN symbol(s), as produced by data.load_gene_synonym_map.

    Returns:
        NormalizedSymbol: Resolution result with status, symbols, and note.
    """
    # Strip before folding so a marker carrying stray whitespace from a CSV/TSV
    # (" kdrl", "kdrl\n") still matches; synonym_map keys are stripped at build time.
    key = symbol.strip().lower()
    candidates = synonym_map.get(key)
    if candidates is None:
        return NormalizedSymbol(
            input=symbol,
            status=STATUS_UNRESOLVED,
            symbols=frozenset(),
            note="not found in GAF synonym map",
        )
    # An input that is itself a current symbol resolves to that symbol, even when
    # it is also listed as a paralog's legacy alias (kdr is a current gene and an
    # old alias of kdrl). Its own identity wins, so it is never called ambiguous.
    if key in candidates:
        return NormalizedSymbol(
            input=symbol,
            status=STATUS_RESOLVED,
            symbols=frozenset({key}),
            note=None,
        )
    if len(candidates) == 1:
        return NormalizedSymbol(
            input=symbol,
            status=STATUS_RESOLVED,
            symbols=frozenset(candidates),
            note=None,
        )
    # A previous name (not itself a current symbol) that fans out to several
    # current paralogs is genuinely ambiguous — keep them all, never collapse.
    return NormalizedSymbol(
        input=symbol,
        status=STATUS_AMBIGUOUS,
        symbols=frozenset(candidates),
        note=f"previous name maps to {len(candidates)} current paralogs: {', '.join(sorted(candidates))}",
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
    return [normalize_symbol(marker, synonym_map) for marker in markers]


def resolved_symbols(normalized_markers: list[NormalizedSymbol]) -> list[str]:
    """Return the single current symbol of each resolved marker, in input order.

    The resolved markers (ambiguous and unresolved are dropped) are exactly what panel
    scoring and the convergence descent operate on; each carries exactly one symbol. A small
    convenience so callers do not re-implement the same filter-and-unwrap.

    Args:
        normalized_markers (list[NormalizedSymbol]): Output of normalize_markers.

    Returns:
        list[str]: One current ZFIN symbol per resolved marker, in rank order.
    """
    return [
        next(iter(normalized_marker.symbols))
        for normalized_marker in normalized_markers
        if normalized_marker.status == STATUS_RESOLVED
    ]


# Clone/provisional/accession token patterns -- not curated gene symbols. Differential-expression
# marker lists carry these; they never match a panel and only dilute the scorer when they resolve.
_PROVISIONAL_PREFIXES = ("si:", "zgc:", "zmp:", "wu:", "im:", "sb:")  # Sanger/genomic clone names
_LOC_RE = re.compile(r"^LOC\d+")  # NCBI placeholder gene ids, e.g. LOC100537342
_MITO_CONTIG_RE = re.compile(r"^NC-")  # mito-genome contig tokens, e.g. NC-002333.4
_ACCESSION_RE = re.compile(r"^[A-Z]{2,}\d+\.\d+")  # clone/contig accessions, e.g. BX000438.2, CABZ01021592.1


def is_uninformative(symbol: str) -> bool:
    """Whether a marker token is a clone/provisional name or accession, not a real gene symbol.

    Differential-expression marker lists often carry tokens that are not curated gene symbols:
    Sanger/genomic clone names (the si:, zgc:, zmp:, wu:, im:, sb: prefixes), NCBI placeholder ids
    (LOC...), mito-contig tokens (NC-...), and clone/contig accessions (BX..., CABZ...). These never
    match a panel and, when they resolve through the GAF, only dilute the scorer; dropping them at
    marker-selection time lets real markers backfill. The accession check is case-sensitive: a real
    zebrafish symbol is lowercase (cd63, id1, fn1a), so the uppercase rule never catches one.

    Args:
        symbol (str): A marker token.

    Returns:
        bool: True when the token is a clone/provisional name or an accession, not a gene symbol.
    """
    stripped = symbol.strip()
    if stripped.lower().startswith(_PROVISIONAL_PREFIXES):
        return True
    return bool(_LOC_RE.match(stripped) or _MITO_CONTIG_RE.match(stripped) or _ACCESSION_RE.match(stripped))


def drop_uninformative(markers: Iterable[str]) -> list[str]:
    """Drop clone/provisional/accession tokens, preserving input (rank) order.

    Args:
        markers (Iterable[str]): Marker tokens, most significant first.

    Returns:
        list[str]: The informative markers, order preserved (see is_uninformative).
    """
    return [marker for marker in markers if not is_uninformative(marker)]
