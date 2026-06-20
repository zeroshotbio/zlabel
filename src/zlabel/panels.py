"""Panel scoring for zlabel: load curated broad-bucket panels and score a marker list.

Domain knowledge lives in panels.yaml, not in this module. The scorer applies
rank-weighted overlap: a marker at rank r contributes weight 1/log2(r+1), so the
most significant markers drive the score and the tail is down-weighted without
being discarded. The caller normalizes first (genes.normalize_markers); only resolved
markers (STATUS_RESOLVED) enter the denominator, so ambiguous and unresolved markers
never make the scorer guess on an uncertain symbol.

panels.yaml defines two panel kinds:
  identity: a cell-type lineage bucket (neural, muscle, blood, ...).
  state:    a transcriptional program orthogonal to identity (cycling, stress).
Phase 3 treats them differently in the decision; this module scores both identically.
"""

from __future__ import annotations

import math
import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from zlabel.genes import STATUS_RESOLVED, NormalizedSymbol

# --- panel kinds --------------------------------------------------------------

KIND_IDENTITY = "identity"  # a cell-type lineage bucket
KIND_STATE = "state"  # a transcriptional program, not a lineage


# --- value types --------------------------------------------------------------


@dataclass(frozen=True)
class Panel:
    """One curated broad-bucket panel loaded from panels.yaml.

    State panels (kind state) leave germ_layer, tissue, and lineage empty: they
    describe a transcriptional program, not a lineage.

    Attributes:
        bucket (str): Short identifier matching the top-level yaml key
            (e.g. muscle, neural, cycling).
        germ_layer (str): Broad germ-layer origin (e.g. mesoderm, ectoderm).
        tissue (str): Tissue or organ system (e.g. muscle, blood).
        lineage (str): Lineage or cell-type category (e.g. erythroid, skeletal
            muscle).
        markers (frozenset[str]): Lowercased current ZFIN symbols that define
            this bucket. Lowercased at load time so lookup is O(1) and
            case-insensitive.
        cite (str): Citation or provenance of this panel's marker list.
        kind (str): identity or state.
        ontology_anchor (frozenset[str]): ZFA ids the bucket's markers should
            express under. Used by Phase 3 grounding to compute the grounding
            confidence component. Empty for state panels.
    """

    bucket: str
    germ_layer: str
    tissue: str
    lineage: str
    markers: frozenset[str]
    cite: str
    kind: str
    ontology_anchor: frozenset[str] = field(default_factory=frozenset)


@dataclass(frozen=True)
class MatchedMarker:
    """A resolved input marker with its rank weight.

    score_markers builds one MatchedMarker per resolved input marker and
    records, on each BucketScore, those whose symbol is in that panel.

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

    germ_layer, tissue, lineage, and kind are propagated from Panel so Phase 3's
    decision logic can inspect a score without needing the full panel list.

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
        total_weight (float): The shared denominator used when computing score
            (sum of all resolved-marker weights, before any identity-only
            adjustment). Carried here so label.decide() can recompute adjusted
            scores without re-running the scorer.
    """

    bucket: str
    score: float
    germ_layer: str
    tissue: str
    lineage: str
    kind: str
    matched_markers: tuple[MatchedMarker, ...]
    total_weight: float = 0.0


# --- loaders and scorer -------------------------------------------------------


def load_panels(path: str | os.PathLike[str]) -> list[Panel]:
    """Load all panels from a YAML file.

    Expects a top-level mapping from bucket name to a dict with keys
    germ_layer, tissue, lineage, kind, markers, cite, and an optional
    ontology_anchor list. Markers are lowercased at load time. Raises ValueError
    for an unrecognized kind or an empty marker list.

    Args:
        path (str | os.PathLike[str]): Path to a YAML panel file (typically
            panels.yaml shipped with the package, or a test fixture).

    Returns:
        list[Panel]: One Panel per top-level yaml entry, in file order.

    Raises:
        ValueError: If the file is empty or not a top-level mapping, or if any
            entry is missing kind, has an unrecognized kind, has an empty marker
            list, or has a non-list ontology_anchor.
        FileNotFoundError: If path does not exist.
    """
    with Path(path).open(encoding="utf-8") as handle:
        raw: dict[str, dict[str, object]] = yaml.safe_load(handle)
    # safe_load yields None for an empty file and a list for a sequence-topped one;
    # both would crash on .items() below. Fail the same way the per-entry checks do.
    if not isinstance(raw, dict) or not raw:
        raise ValueError(f"panel file {Path(path)} must be a non-empty mapping of bucket -> panel")

    panels: list[Panel] = []
    for bucket, entry in raw.items():
        # yaml.safe_load values are typed object; coerce each scalar we store to str
        # (this also guards a field mistyped in the file, e.g. a bare int).
        kind = str(entry.get("kind", ""))
        if not kind:
            raise ValueError(f"panel {bucket!r} is missing required field 'kind'")
        if kind not in (KIND_IDENTITY, KIND_STATE):
            raise ValueError(
                f"panel {bucket!r} has invalid kind {kind!r}; expected {KIND_IDENTITY!r} or {KIND_STATE!r}"
            )
        markers_raw: list[str] = entry.get("markers", [])  # type: ignore[assignment]
        if not markers_raw:
            raise ValueError(f"panel {bucket!r} has no markers")
        markers = frozenset(marker.lower() for marker in markers_raw)

        # Anchor must be a list of ids; a bare scalar (ontology_anchor: ZFA:0000548)
        # would otherwise become a frozenset of characters instead of failing.
        anchor_raw = entry.get("ontology_anchor", [])
        if not isinstance(anchor_raw, list):
            raise ValueError(f"panel {bucket!r} ontology_anchor must be a list of ZFA ids, not a scalar")
        ontology_anchor = frozenset(str(anchor_id) for anchor_id in anchor_raw)

        panels.append(
            Panel(
                bucket=bucket,
                germ_layer=str(entry.get("germ_layer", "")),
                tissue=str(entry.get("tissue", "")),
                lineage=str(entry.get("lineage", "")),
                markers=markers,
                cite=str(entry.get("cite", "")),
                kind=kind,
                ontology_anchor=ontology_anchor,
            )
        )
    return panels


def score_markers(
    normalized_markers: list[NormalizedSymbol],
    panels: list[Panel],
) -> list[BucketScore]:
    """Score already-normalized markers against all panels using rank-weighted overlap.

    Weight for rank r (1-based): 1 / log2(r + 1). Rank 1 weighs 1.0,
    decaying toward zero as r grows. Only resolved markers enter the
    denominator; ambiguous and unresolved markers are excluded from both
    numerator and denominator so uncertainty never inflates or deflates a
    score. When no resolved markers exist, every bucket scores 0.0.

    The caller normalizes once (genes.normalize_markers) and passes the result
    here, so a cluster's markers are normalized a single time and shared with the
    convergence descent rather than re-normalized per consumer.

    The returned list contains one BucketScore per panel, sorted by
    (-score, bucket). The top candidate is always at index 0. All panels are
    always returned even when their score is zero, so the caller can inspect
    any bucket without searching.

    Args:
        normalized_markers (list[NormalizedSymbol]): Markers already normalized
            by genes.normalize_markers, in significance rank order (rank 1 =
            index 0). Unresolved and ambiguous entries stay in the list (they
            hold their rank) but are excluded from scoring.
        panels (list[Panel]): Panels to score against, as returned by
            load_panels.

    Returns:
        list[BucketScore]: One score per panel, sorted descending by score
            then ascending by bucket name for a stable, readable order.
    """
    # Keep only resolved markers; rank is the 1-based input position (unresolved
    # entries still consume a rank, so the resolved markers keep their weights).
    resolved: list[MatchedMarker] = []
    for rank, normalized_marker in enumerate(normalized_markers, start=1):
        if normalized_marker.status == STATUS_RESOLVED:
            weight = 1.0 / math.log2(rank + 1)
            symbol = next(iter(normalized_marker.symbols))
            resolved.append(MatchedMarker(input=normalized_marker.input, symbol=symbol, rank=rank, weight=weight))

    # Denominator is the total weight of all resolved markers, whether or not
    # they hit any panel. A cluster with mostly off-panel markers cannot
    # score any bucket highly — this allows Phase 3 to abstain honestly.
    total_weight = sum(matched_marker.weight for matched_marker in resolved)

    scores: list[BucketScore] = []
    for panel in panels:
        matched = tuple(matched_marker for matched_marker in resolved if matched_marker.symbol in panel.markers)
        hit_weight = sum(matched_marker.weight for matched_marker in matched)
        score = hit_weight / total_weight if total_weight > 0.0 else 0.0
        scores.append(
            BucketScore(
                bucket=panel.bucket,
                score=score,
                germ_layer=panel.germ_layer,
                tissue=panel.tissue,
                lineage=panel.lineage,
                kind=panel.kind,
                matched_markers=matched,
                total_weight=total_weight,
            )
        )

    scores.sort(key=lambda bucket_score: (-bucket_score.score, bucket_score.bucket))
    return scores
