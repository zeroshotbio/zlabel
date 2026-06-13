"""Converging-evidence decision for zlabel — the heart of Phase 3.

decide() is pure and I/O-free: it takes the panel-score table plus already-loaded
grounding data and returns a Label evidence packet. Labeler wraps decide() with the
data-loading boilerplate so callers need only Labeler(stage_hpf=48).label([...]).

The decision follows a three-stage algorithm:
  1. Prechecks — abstain immediately on obvious no-evidence cases (A/B).
  2. Dominance ladder — assign a single bucket (C) or attempt a germ-layer rollup
     when the top two identities are near-tied (D).
  3. Confidence rubric — four named components (coherence, margin, grounding,
     stage), each in [0, 1], combined into a scalar and bucketed into a tier.
     Two caps apply: a convergence cap (high requires real grounding/stage
     corroboration) and a rollup cap (max medium). Floor: any assigned label is
     at least low.

State panels (cycling, stress_response) are detected denominator-free and reported
on every Label — including abstentions — without affecting the identity call.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path

import networkx as nx

from zlabel.data import ZfinExpressionRecord, load_gene_synonym_map, load_zfa, load_zfin_expression, term_name
from zlabel.ground import expression_lookup, grounds_under, stage_plausibility
from zlabel.models import TIER_HIGH_NAME, TIER_LOW_NAME, TIER_MEDIUM_NAME, Confidence, ExprHit, Label
from zlabel.panels import KIND_IDENTITY, KIND_STATE, BucketScore, MatchedMarker, Panel, load_panels, score_markers

# ---------------------------------------------------------------------------
# Decision constants
# ---------------------------------------------------------------------------

MIN_SIGNAL: float = 0.15
# Top identity adjusted-score must clear this to avoid an abstention. A cluster
# whose markers hit no identity panel (all off-panel, or all unresolved) scores
# effectively 0 and abstains honestly rather than picking the least-bad bucket.

DOMINANCE_GAP: float = 0.30
# Minimum gap (adj_top - adj_second) for a confident single-bucket call.
# Doubles as the margin component's normaliser: margin = clamp01(gap / DOMINANCE_GAP).

COHERENCE_SAT: float = 2.13
# Matched weight that saturates the coherence component at 1.0.
# 2.13 ≈ 1/log2(2) + 1/log2(3) + 1/log2(4), i.e. three top-ranked markers
# each hitting the panel — "enough breadth that more markers don't keep raising
# the bar."

STATE_MIN_WEIGHT: float = 1.0
# A state panel needs at least this raw matched weight to be called present.

N_STATE_MIN: int = 2
# A state panel needs at least this many distinct matched markers (avoids
# calling cycling from a single mki67 hit).

NEUTRAL: float = 0.5
# Used when a confidence component has no gradable evidence. Neither rewards
# nor penalises the call; keeps the rubric honest on sparse data.

W_COHERENCE: float = 0.40
W_MARGIN: float = 0.30
W_GROUNDING: float = 0.20
W_STAGE: float = 0.10
# Component weights; must sum to 1.0.

TIER_HIGH: float = 0.80
TIER_MEDIUM: float = 0.60
# Thresholds for naming a confidence tier. "low" is the else branch (and the
# floor for any assigned label). TIER_LOW is not a threshold — it is the floor
# name used when the weighted score would otherwise round down to unresolved.

_ABSTAIN_BUCKET = "mixed/unresolved"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def _tier(score: float) -> Confidence:
    if score >= TIER_HIGH:
        return TIER_HIGH_NAME
    if score >= TIER_MEDIUM:
        return TIER_MEDIUM_NAME
    return TIER_LOW_NAME


def _adj(bucket_score: BucketScore, identity_denom: float) -> float:
    """Adjusted identity score: hit_weight / identity_denom."""
    if identity_denom <= 0.0:
        return 0.0
    hit_weight = sum(m.weight for m in bucket_score.matched_markers)
    return hit_weight / identity_denom


def _state_only_weight(scores: list[BucketScore]) -> float:
    """Weight of markers that hit a state panel and no identity panel.

    These markers legitimately belong in the denominator for state detection
    but should not suppress identity scores. Subtracting their weight from
    total_weight gives the identity-only denominator.

    Args:
        scores (list[BucketScore]): Full score table from score_markers.

    Returns:
        float: Sum of weights of markers that hit only state panels.
    """
    identity_symbols = {m.symbol for bs in scores if bs.kind == KIND_IDENTITY for m in bs.matched_markers}
    state_weight = {m.symbol: m.weight for bs in scores if bs.kind == KIND_STATE for m in bs.matched_markers}
    return sum(weight for symbol, weight in state_weight.items() if symbol not in identity_symbols)


def _compute_grounding_evidence(
    matched_markers: tuple[MatchedMarker, ...],
    anchor: frozenset[str],
    expr_map: Mapping[str, list[ZfinExpressionRecord]],
    zfa_graph: nx.MultiDiGraph,
    stage_hpf: float | None,
) -> tuple[tuple[ExprHit, ...], dict[str, int]]:
    """Compute per-marker grounding and stage signals for the confidence rubric.

    Counts markers per category (gradable, grounded, datable, plausible) and
    collects ExprHit evidence for grounded markers. All counts are per marker,
    not per record: a marker with many expression records contributes once to
    each relevant counter.

    Args:
        matched_markers (tuple[MatchedMarker, ...]): MatchedMarker objects for the winner's panel hits.
        anchor (frozenset[str]): Bucket ontology anchor ids.
        expr_map (Mapping[str, list[ZfinExpressionRecord]]): ZFIN expression data.
        zfa_graph (nx.MultiDiGraph): ZFA ontology graph.
        stage_hpf (float | None): Dataset stage in hpf, or None.

    Returns:
        tuple[tuple[ExprHit, ...], dict[str, int]]: Grounded anatomy hits and a
        dict with keys gradable, grounded, datable, plausible.
    """
    hits: list[ExprHit] = []
    counts = {"gradable": 0, "grounded": 0, "datable": 0, "plausible": 0}

    for mm in matched_markers:
        records = expression_lookup(expr_map, mm.symbol)
        if not records:
            continue  # no records -> not gradable for either component
        counts["gradable"] += 1

        # Grounding: the first record (if any) that sits under the anchor.
        grounded_rec = next((rec for rec in records if grounds_under(zfa_graph, rec.zfa_id, anchor)), None)
        if grounded_rec is not None:
            counts["grounded"] += 1
            zfa_name = term_name(zfa_graph, grounded_rec.zfa_id) or grounded_rec.zfa_id
            hits.append(ExprHit(symbol=mm.symbol, zfa_id=grounded_rec.zfa_id, zfa_name=zfa_name))

        # Stage: is any datable record on-stage?
        plausibility = stage_plausibility(records, stage_hpf)
        if plausibility is not None:
            counts["datable"] += 1
            if plausibility:
                counts["plausible"] += 1

    return tuple(hits), counts


def _supports_high(grounding: float | None, stage: float | None) -> bool:
    """Whether grounding/stage corroboration justifies high confidence.

    High needs converging evidence, not strong panels alone. When grounding is
    gradable it decides on its own: supportive (>= NEUTRAL) allows high, and
    contradictory anatomy (< NEUTRAL) blocks high even if stage is on -- anatomy
    is the stronger anchor, stage is the soft 0.10 signal. Only when grounding is
    not gradable does stage stand in as the corroborator.

    Args:
        grounding (float | None): grounded/gradable fraction, or None when no
            matched marker had an expression record.
        stage (float | None): plausible/datable fraction, or None when stage is
            not gradable (no stage given, or no datable record).

    Returns:
        bool: True when high confidence is warranted.
    """
    if grounding is not None:
        return grounding >= NEUTRAL
    return stage is not None and stage >= NEUTRAL


def _grade_confidence(
    top: BucketScore,
    second_adj: float,
    top_adj: float,
    counts: dict[str, int],
    stage_hpf: float | None,
    *,
    rollup: bool,
) -> tuple[float, Confidence, dict[str, float]]:
    """Grade an assigned bucket: weighted score -> tier, with the caps and floor.

    The 0-1 score is W_COHERENCE*coherence + W_MARGIN*margin + W_GROUNDING*grounding
    + W_STAGE*stage, each component in [0, 1] (absent grounding/stage use NEUTRAL).
    All confidence policy lives here, in one place:
      convergence cap -- a single-bucket high needs real corroboration (see
        _supports_high); strong panels alone top out at medium.
      rollup cap -- a germ-layer rollup never exceeds medium (it makes no single-
        anatomy high claim).
      floor -- any assigned label is at least low.

    Args:
        top (BucketScore): The winning bucket (the top contender for a rollup).
        second_adj (float): Adjusted score of the runner-up (0 when none).
        top_adj (float): Adjusted score of the winner.
        counts (dict[str, int]): Marker-level counts from _compute_grounding_evidence.
        stage_hpf (float | None): Dataset stage in hpf, or None.
        rollup (bool): True for a germ-layer rollup (capped at medium).

    Returns:
        tuple[float, Confidence, dict[str, float]]: (score, tier, components).
    """
    coherence = _clamp01(sum(m.weight for m in top.matched_markers) / COHERENCE_SAT)
    margin = _clamp01((top_adj - second_adj) / DOMINANCE_GAP)
    grounding = counts["grounded"] / counts["gradable"] if counts["gradable"] else None
    stage = counts["plausible"] / counts["datable"] if stage_hpf is not None and counts["datable"] else None

    g = grounding if grounding is not None else NEUTRAL
    s = stage if stage is not None else NEUTRAL
    score = W_COHERENCE * coherence + W_MARGIN * margin + W_GROUNDING * g + W_STAGE * s
    components = {"coherence": coherence, "margin": margin, "grounding": g, "stage": s}

    tier = _tier(score)
    if rollup:
        if tier == TIER_HIGH_NAME:
            tier = TIER_MEDIUM_NAME
    elif tier == TIER_HIGH_NAME and not _supports_high(grounding, stage):
        tier = TIER_MEDIUM_NAME
    if tier not in (TIER_HIGH_NAME, TIER_MEDIUM_NAME):
        tier = TIER_LOW_NAME
    return score, tier, components


def _detect_states(scores: list[BucketScore]) -> tuple[str, ...]:
    """Return detected state-program bucket names.

    A state panel is present when its raw matched weight is at least
    STATE_MIN_WEIGHT AND it has at least N_STATE_MIN distinct matched markers.
    Detected denominator-free (state detection should not be affected by how
    many identity markers the cluster also carries).

    Args:
        scores (list[BucketScore]): Full score table from score_markers.

    Returns:
        tuple[str, ...]: State bucket names in alphabetical order (stable output).
    """
    detected: list[str] = []
    for bs in scores:
        if bs.kind != KIND_STATE:
            continue
        hit_weight = sum(m.weight for m in bs.matched_markers)
        if hit_weight >= STATE_MIN_WEIGHT and len(bs.matched_markers) >= N_STATE_MIN:
            detected.append(bs.bucket)
    return tuple(sorted(detected))


def _abstain(flag: str, states: tuple[str, ...], panel_scores: dict[str, float]) -> Label:
    """Build a mixed/unresolved abstention Label.

    Args:
        flag (str): Ambiguity flag (provisional, mixed).
        states (tuple[str, ...]): Detected state programs.
        panel_scores (dict[str, float]): Raw panel scores.

    Returns:
        Label: An abstained evidence packet.
    """
    return Label(
        bucket=_ABSTAIN_BUCKET,
        levels=(),
        abstained=True,
        confidence=None,
        confidence_score=None,
        confidence_components={},
        ambiguity_flag=flag,
        states=states,
        zfa_id=None,
        panel_scores=panel_scores,
        positive_markers=(),
        expression_evidence=(),
        rationale=f"abstained: {flag}",
        next_step=None,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def decide(
    scores: list[BucketScore],
    *,
    anchors: Mapping[str, frozenset[str]],
    expr_map: Mapping[str, list[ZfinExpressionRecord]],
    zfa_graph: nx.MultiDiGraph,
    stage_hpf: float | None,
) -> Label:
    """Converging-evidence decision: turn a score table into a Label.

    Pure and I/O-free. Takes the output of score_markers plus already-loaded
    grounding data; returns a Label evidence packet.

    The decision ladder:
      A. No resolved markers or no identity panel hit at all -> abstain (provisional).
      B. Top adjusted identity score < MIN_SIGNAL -> abstain (provisional).
      C. Top score dominates (gap >= DOMINANCE_GAP, or only one identity bucket) ->
         assign the top bucket.
      D. Near-tie: contenders within DOMINANCE_GAP of the top.
         All share a non-empty germ layer -> assign at germ-layer tier (underclustered).
         Otherwise -> abstain (mixed).

    Args:
        scores (list[BucketScore]): From score_markers; must include total_weight.
        anchors (Mapping[str, frozenset[str]]): Bucket name to ZFA anchor ids.
            Passed explicitly so decide() stays pure; Labeler builds this from
            the loaded Panel objects.
        expr_map (Mapping[str, list[ZfinExpressionRecord]]): From
            data.load_zfin_expression.
        zfa_graph (nx.MultiDiGraph): From data.load_zfa.
        stage_hpf (float | None): Dataset developmental stage in hpf, or None.

    Returns:
        Label: Evidence packet with bucket, confidence, expression evidence, etc.
    """
    panel_scores = {bs.bucket: bs.score for bs in scores}
    states = _detect_states(scores)

    # Recover total_weight from the first score (all BucketScores share it).
    total_weight = scores[0].total_weight if scores else 0.0

    # Compute state-only weight to derive the identity-only denominator.
    s_only = _state_only_weight(scores)
    identity_denom = total_weight - s_only

    # Sort identity buckets that actually matched markers, by adjusted score
    # descending. Dropping zero-marker buckets here is what keeps them from
    # padding the near-tie contender set and forcing a false "mixed" abstention.
    identity = sorted(
        [bs for bs in scores if bs.kind == KIND_IDENTITY and bs.matched_markers],
        key=lambda bs: (-_adj(bs, identity_denom), bs.bucket),
    )

    # --- Precheck A: no identity evidence at all ---
    if not identity:
        return _abstain("provisional", states, panel_scores)

    top = identity[0]
    top_adj = _adj(top, identity_denom)
    second_adj = _adj(identity[1], identity_denom) if len(identity) > 1 else 0.0

    # --- Precheck B: signal too weak ---
    if top_adj < MIN_SIGNAL:
        return _abstain("provisional", states, panel_scores)

    # --- C / D: dominance test ---
    gap = top_adj - second_adj
    if len(identity) == 1 or gap >= DOMINANCE_GAP:
        # Clear winner: assign the top bucket.
        return _assign_top(
            top=top,
            top_adj=top_adj,
            second_adj=second_adj,
            anchors=anchors,
            expr_map=expr_map,
            zfa_graph=zfa_graph,
            stage_hpf=stage_hpf,
            states=states,
            panel_scores=panel_scores,
        )

    # Near-tie: collect contenders within DOMINANCE_GAP of the top.
    contenders = [bs for bs in identity if top_adj - _adj(bs, identity_denom) <= DOMINANCE_GAP]
    germ_layers = {bs.germ_layer for bs in contenders if bs.germ_layer}

    if len(germ_layers) == 1:
        # All contenders share a germ layer — assign at germ-layer tier.
        germ_layer = next(iter(germ_layers))
        return _assign_rollup(
            germ_layer=germ_layer,
            contenders=contenders,
            top_adj=top_adj,
            second_adj=second_adj,
            anchors=anchors,
            expr_map=expr_map,
            zfa_graph=zfa_graph,
            stage_hpf=stage_hpf,
            states=states,
            panel_scores=panel_scores,
        )

    # Contradictory germ layers -> mixed.
    return _abstain("mixed", states, panel_scores)


def _assign_top(
    *,
    top: BucketScore,
    top_adj: float,
    second_adj: float,
    anchors: Mapping[str, frozenset[str]],
    expr_map: Mapping[str, list[ZfinExpressionRecord]],
    zfa_graph: nx.MultiDiGraph,
    stage_hpf: float | None,
    states: tuple[str, ...],
    panel_scores: dict[str, float],
) -> Label:
    """Build a Label for a clear single-bucket assignment.

    Args:
        top (BucketScore): The winning bucket.
        top_adj (float): Its adjusted identity score.
        second_adj (float): Runner-up adjusted score (0 when none).
        anchors (Mapping[str, frozenset[str]]): Bucket -> ZFA anchor ids.
        expr_map (Mapping[str, list[ZfinExpressionRecord]]): Expression data.
        zfa_graph (nx.MultiDiGraph): ZFA ontology graph.
        stage_hpf (float | None): Dataset stage in hpf, or None.
        states (tuple[str, ...]): Detected state programs.
        panel_scores (dict[str, float]): Raw panel scores.

    Returns:
        Label: Assigned evidence packet.
    """
    anchor = anchors.get(top.bucket, frozenset())
    hits, counts = _compute_grounding_evidence(
        top.matched_markers, anchor, expr_map, zfa_graph, stage_hpf
    )

    conf_score, tier, components = _grade_confidence(top, second_adj, top_adj, counts, stage_hpf, rollup=False)

    levels = tuple(x for x in (top.germ_layer, top.tissue, top.lineage) if x)
    positive = tuple(m.symbol for m in top.matched_markers)
    markers = ", ".join(m.symbol for m in top.matched_markers[:3])

    # zfa_id: sorted-first anchor id for determinism (None when no anchor).
    zfa_id = sorted(anchor)[0] if anchor else None

    return Label(
        bucket=top.bucket,
        levels=levels,
        abstained=False,
        confidence=tier,
        confidence_score=round(conf_score, 4),
        confidence_components={k: round(v, 4) for k, v in components.items()},
        ambiguity_flag="none",
        states=states,
        zfa_id=zfa_id,
        panel_scores=panel_scores,
        positive_markers=positive,
        expression_evidence=hits,
        rationale=f"{top.bucket} supported by {markers} (adj_score={top_adj:.2f})",
        next_step="subcluster",
    )


def _assign_rollup(
    *,
    germ_layer: str,
    contenders: list[BucketScore],
    top_adj: float,
    second_adj: float,
    anchors: Mapping[str, frozenset[str]],
    expr_map: Mapping[str, list[ZfinExpressionRecord]],
    zfa_graph: nx.MultiDiGraph,
    stage_hpf: float | None,
    states: tuple[str, ...],
    panel_scores: dict[str, float],
) -> Label:
    """Build a germ-layer rollup Label.

    Grounding spans the union of all contenders' markers and anchors, while
    coherence and margin come from the top contender alone (a rollup has no
    single dominant bucket to measure breadth from). Tier capped at medium.

    Args:
        germ_layer (str): The shared germ layer.
        contenders (list[BucketScore]): All near-tied identity buckets.
        top_adj (float): Adjusted score of the top contender.
        second_adj (float): Adjusted score of the second contender.
        anchors (Mapping[str, frozenset[str]]): Bucket -> ZFA anchor ids.
        expr_map (Mapping[str, list[ZfinExpressionRecord]]): Expression data.
        zfa_graph (nx.MultiDiGraph): ZFA ontology graph.
        stage_hpf (float | None): Dataset stage in hpf, or None.
        states (tuple[str, ...]): Detected state programs.
        panel_scores (dict[str, float]): Raw panel scores.

    Returns:
        Label: Rollup evidence packet.
    """
    # Union of all contenders' matched markers (deduplicated by symbol).
    seen: set[str] = set()
    union_markers = []
    for bs in contenders:
        for mm in bs.matched_markers:
            if mm.symbol not in seen:
                seen.add(mm.symbol)
                union_markers.append(mm)
    union_matched = tuple(union_markers)

    # Union of all contenders' anchors.
    union_anchor: frozenset[str] = frozenset().union(*(anchors.get(bs.bucket, frozenset()) for bs in contenders))

    hits, counts = _compute_grounding_evidence(
        union_matched, union_anchor, expr_map, zfa_graph, stage_hpf
    )

    # Use the top contender as a proxy for coherence/margin.
    top = contenders[0]
    conf_score, tier, components = _grade_confidence(top, second_adj, top_adj, counts, stage_hpf, rollup=True)

    positive = tuple(mm.symbol for mm in union_matched)

    return Label(
        bucket=germ_layer,
        levels=(germ_layer,),
        abstained=False,
        confidence=tier,
        confidence_score=round(conf_score, 4),
        confidence_components={k: round(v, 4) for k, v in components.items()},
        ambiguity_flag="underclustered",
        states=states,
        zfa_id=None,
        panel_scores=panel_scores,
        positive_markers=positive,
        expression_evidence=hits,
        rationale=f"{germ_layer} rollup: contenders {[bs.bucket for bs in contenders]}",
        next_step="subcluster",
    )


# ---------------------------------------------------------------------------
# Labeler facade
# ---------------------------------------------------------------------------

# Default data directory (gitignored; populated by scripts/setup_data.sh).
_DEFAULT_DATA_DIR = Path(__file__).parent.parent.parent / "data" / "ontologies"
_DEFAULT_PANELS = Path(__file__).parent / "panels.yaml"


class Labeler:
    """Facade that loads all data once and exposes a single label() entry point.

    Accepts explicit path overrides for every data file so tests can run over
    small committed fixtures without downloading the ~94 MB ontology files.

    Attributes:
        stage_hpf (float | None): Developmental stage in hpf for the sample.
            Passed to decide() unchanged. None means stage plausibility is not
            evaluated (all stage components are NEUTRAL).
    """

    def __init__(
        self,
        stage_hpf: float | None = None,
        *,
        zfa_path: str | os.PathLike[str] | None = None,
        expr_path: str | os.PathLike[str] | None = None,
        gaf_path: str | os.PathLike[str] | None = None,
        panels_path: str | os.PathLike[str] | None = None,
        data_dir: str | os.PathLike[str] | None = None,
    ) -> None:
        """Load all data once and cache it.

        Explicit path arguments take precedence over data_dir. When neither is
        given, data_dir defaults to data/ontologies/ relative to the repo root
        (the location populated by scripts/setup_data.sh).

        Args:
            stage_hpf (float | None): Developmental stage in hpf (e.g. 48.0
                for Long-pec). None disables stage-plausibility grounding.
            zfa_path (str | os.PathLike[str] | None): Path to zfa.obo.
            expr_path (str | os.PathLike[str] | None): Path to
                zfin_wildtype_expression.txt.
            gaf_path (str | os.PathLike[str] | None): Path to the ZFIN .gaf
                synonym file.
            panels_path (str | os.PathLike[str] | None): Path to panels.yaml.
            data_dir (str | os.PathLike[str] | None): Directory containing the
                three standard ontology files. Ignored when explicit paths are
                provided.
        """
        self.stage_hpf = stage_hpf

        base = Path(data_dir) if data_dir is not None else _DEFAULT_DATA_DIR
        zfa_p = Path(zfa_path) if zfa_path is not None else base / "zfa.obo"
        expr_p = Path(expr_path) if expr_path is not None else base / "zfin_wildtype_expression.txt"
        gaf_p = Path(gaf_path) if gaf_path is not None else base / "zfin.gaf"
        panels_p = Path(panels_path) if panels_path is not None else _DEFAULT_PANELS

        self._zfa = load_zfa(zfa_p)
        self._expr = load_zfin_expression(expr_p)
        self._synonyms = load_gene_synonym_map(gaf_p)
        self._panels: list[Panel] = load_panels(panels_p)
        self._anchors: dict[str, frozenset[str]] = {
            p.bucket: p.ontology_anchor for p in self._panels
        }

    def label(self, markers: list[str]) -> Label:
        """Label one cluster from its marker gene list.

        Normalises the markers via the loaded synonym map, scores them against
        all panels, then calls decide() with the loaded ZFA ontology and ZFIN
        expression data.

        Args:
            markers (list[str]): Marker gene symbols ordered by significance
                (rank 1 = most significant = index 0). May use old ZFIN names;
                they are normalised via the GAF synonym map before scoring.

        Returns:
            Label: Evidence packet with bucket, confidence, grounding evidence,
            and next_step.
        """
        scores = score_markers(markers, self._panels, self._synonyms)
        return decide(
            scores,
            anchors=self._anchors,
            expr_map=self._expr,
            zfa_graph=self._zfa,
            stage_hpf=self.stage_hpf,
        )
