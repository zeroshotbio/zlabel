"""Panel scoring for zlabel: load curated broad-bucket panels and score a marker list.

Domain knowledge lives in panels.yaml, not in this module. The scorer applies
rank-weighted overlap: a marker at rank r contributes weight 1/log2(r+1), so the
most significant markers drive the score and the tail is down-weighted without
being discarded. Only resolved markers (STATUS_RESOLVED from genes.normalize_symbol)
enter the denominator; ambiguous and unresolved markers are excluded so the scorer
never guesses on an uncertain symbol.

panels.yaml defines two panel kinds:
  identity: a cell-type lineage bucket (neural, muscle, blood, ...).
  state:    a transcriptional program orthogonal to identity (cycling, stress).
Phase 3 treats them differently in the decision; this module scores both identically.
"""

from __future__ import annotations

import math
import os
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from zlabel.genes import STATUS_RESOLVED, normalize_symbol

# --- panel kinds --------------------------------------------------------------

KIND_IDENTITY = "identity"   # a cell-type lineage bucket
KIND_STATE = "state"         # a transcriptional program, not a lineage
VALID_KINDS = frozenset({KIND_IDENTITY, KIND_STATE})


# --- value types --------------------------------------------------------------


@dataclass(frozen=True)
class Panel:
    """One curated broad-bucket panel loaded from panels.yaml.

    Attributes:
        bucket (str): Short identifier matching the top-level yaml key
            (e.g. muscle, neural, cycling).
        germ_layer (str): Broad germ-layer origin (e.g. mesoderm, ectoderm).
            Empty string for state panels where germ layer is not applicable.
        tissue (str): Tissue or organ system (e.g. muscle, blood). Empty
            string for state panels.
        lineage (str): Lineage or cell-type category (e.g. erythroid, skeletal
            muscle). Empty string for state panels.
        markers (frozenset[str]): Lowercased current ZFIN symbols that define
            this bucket. Lowercased at load time so lookup is O(1) and
            case-insensitive.
        cite (str): Citation or provenance of this panel's marker list.
        kind (str): identity or state.
        subpanels (Mapping[str, frozenset[str]]): Optional named sub-panels
            (e.g. muscle.fast, muscle.slow). Loaded in Phase 2 but not scored
            here; Phase 3 uses them for finer resolution on subclusters.
            Excluded from __hash__ because dict (the runtime type) is not
            hashable; equality still includes subpanels.
    """

    bucket: str
    germ_layer: str
    tissue: str
    lineage: str
    markers: frozenset[str]
    cite: str
    kind: str
    # hash=False: dict is not hashable, so we exclude subpanels from the
    # auto-generated __hash__ while still including it in __eq__. The hash
    # contract holds because unequal-subpanel panels compare unequal (!=),
    # so two objects with the same hash are not required to be equal.
    subpanels: Mapping[str, frozenset[str]] = field(hash=False)


@dataclass(frozen=True)
class MatchedMarker:
    """One marker that hit a panel during scoring.

    Attributes:
        input (str): The marker symbol as supplied by the caller (before
            normalization), preserved for traceability.
        symbol (str): The resolved current ZFIN symbol used for the lookup.
        rank (int): 1-based position in the input list (rank 1 = most
            differentially expressed / most significant).
        weight (float): Rank weight applied: 1 / log2(rank + 1).
    """

    input: str
    symbol: str
    rank: int
    weight: float


@dataclass(frozen=True)
class BucketScore:
    """Score for one panel bucket against the input marker list.

    Attributes:
        bucket (str): Panel identifier matching Panel.bucket.
        score (float): Fraction of resolved-marker weight that hit this bucket.
            Ranges 0.0 to 1.0. Zero when no resolved markers matched or the
            input contained no resolved markers at all.
        germ_layer (str): Propagated from Panel.germ_layer.
        tissue (str): Propagated from Panel.tissue.
        lineage (str): Propagated from Panel.lineage.
        kind (str): Propagated from Panel.kind.
        matched_markers (tuple[MatchedMarker, ...]): Markers that hit this
            bucket, in input-rank order (highest-weight first).
    """

    bucket: str
    score: float
    germ_layer: str
    tissue: str
    lineage: str
    kind: str
    matched_markers: tuple[MatchedMarker, ...]


# --- loaders and scorer -------------------------------------------------------


def load_panels(path: str | os.PathLike[str]) -> list[Panel]:
    """Load all panels from a YAML file.

    Expects a top-level mapping from bucket name to a dict with keys
    germ_layer, tissue, lineage, kind, markers, cite, and an optional
    subpanels mapping. Markers are lowercased at load time. Raises ValueError
    for an unrecognized kind or an empty marker list.

    Args:
        path (str | os.PathLike[str]): Path to a YAML panel file (typically
            panels.yaml shipped with the package, or a test fixture).

    Returns:
        list[Panel]: One Panel per top-level yaml entry, in file order.

    Raises:
        ValueError: If any entry has an unrecognized kind or an empty
            marker list.
        FileNotFoundError: If path does not exist.
    """
    with Path(path).open(encoding="utf-8") as handle:
        raw: dict[str, dict[str, object]] = yaml.safe_load(handle)

    panels: list[Panel] = []
    for bucket, entry in raw.items():
        kind = entry["kind"]
        if kind not in VALID_KINDS:
            raise ValueError(
                f"panel {bucket!r} has invalid kind {kind!r}; "
                f"expected one of {sorted(VALID_KINDS)}"
            )
        markers_raw: list[str] = entry.get("markers", [])  # type: ignore[assignment]
        if not markers_raw:
            raise ValueError(f"panel {bucket!r} has no markers")
        markers = frozenset(m.lower() for m in markers_raw)

        # Subpanels load into the same frozenset convention; not scored here.
        subpanels_raw: dict[str, list[str]] = entry.get("subpanels", {})  # type: ignore[assignment]
        subpanels: dict[str, frozenset[str]] = {
            name: frozenset(m.lower() for m in sub_markers)
            for name, sub_markers in subpanels_raw.items()
        }

        panels.append(
            Panel(
                bucket=bucket,
                germ_layer=str(entry.get("germ_layer", "")),
                tissue=str(entry.get("tissue", "")),
                lineage=str(entry.get("lineage", "")),
                markers=markers,
                cite=str(entry.get("cite", "")),
                kind=str(kind),
                subpanels=subpanels,
            )
        )
    return panels


def score_markers(
    markers: Iterable[str],
    panels: list[Panel],
    synonym_map: dict[str, set[str]],
) -> list[BucketScore]:
    """Score a ranked marker list against all panels using rank-weighted overlap.

    Weight for rank r (1-based): 1 / log2(r + 1). Rank 1 weighs 1.0,
    decaying toward zero as r grows. Only resolved markers enter the
    denominator; ambiguous and unresolved markers are excluded from both
    numerator and denominator so uncertainty never inflates or deflates a
    score. When no resolved markers exist, every bucket scores 0.0.

    The returned list contains one BucketScore per panel, sorted by
    (-score, bucket). The top candidate is always at index 0. All panels are
    always returned even when their score is zero, so the caller can inspect
    any bucket without searching.

    Args:
        markers (Iterable[str]): Raw marker symbols ordered by significance
            (rank 1 = most significant = index 0). The order determines the
            rank weights.
        panels (list[Panel]): Panels to score against, as returned by
            load_panels.
        synonym_map (dict[str, set[str]]): From data.load_gene_synonym_map;
            maps lowercased names to current ZFIN symbol(s).

    Returns:
        list[BucketScore]: One score per panel, sorted descending by score
            then ascending by bucket name for a stable, readable order.
    """
    # Normalize in rank order; keep only resolved markers for scoring.
    # Tuple layout: (rank, weight, original_input, resolved_symbol).
    resolved: list[tuple[int, float, str, str]] = []
    for rank, raw in enumerate(markers, start=1):
        result = normalize_symbol(raw, synonym_map)
        if result.status == STATUS_RESOLVED:
            weight = 1.0 / math.log2(rank + 1)
            symbol = next(iter(result.symbols))
            resolved.append((rank, weight, raw, symbol))

    # Denominator is the total weight of all resolved markers, whether or not
    # they hit any panel. A cluster with mostly off-panel markers cannot
    # score any bucket highly — this allows Phase 3 to abstain honestly.
    total_weight = sum(w for _, w, _, _ in resolved)

    scores: list[BucketScore] = []
    for panel in panels:
        matched: list[MatchedMarker] = []
        hit_weight = 0.0
        for rank, weight, raw, symbol in resolved:
            if symbol in panel.markers:
                hit_weight += weight
                matched.append(MatchedMarker(input=raw, symbol=symbol, rank=rank, weight=weight))
        score = hit_weight / total_weight if total_weight > 0.0 else 0.0
        scores.append(
            BucketScore(
                bucket=panel.bucket,
                score=score,
                germ_layer=panel.germ_layer,
                tissue=panel.tissue,
                lineage=panel.lineage,
                kind=panel.kind,
                matched_markers=tuple(matched),
            )
        )

    scores.sort(key=lambda s: (-s.score, s.bucket))
    return scores
