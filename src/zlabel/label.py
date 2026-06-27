"""Converging-evidence decision for zlabel — the heart of the labeling loop.

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

Naming: the winning panel is a coarse prior, and its ontology anchor is the root the
namer descends from. The bucket name comes from a support-weighted anchor-rooted descent over
the cluster's ZFIN in-vivo expression (resolve.resolve_label). The depth of the resulting label
falls out of the evidence -- a tight endothelial panel resolves to cell type while a broad
neural cluster stays at CNS. A named term is always at or under the anchor by construction (no
separate guardrail check); when no anchor id is supported the label falls back to the coarse panel bucket.

State panels (cycling, stress_response) are detected denominator-free and reported
on every Label -- including abstentions -- without affecting the identity call.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

import networkx as nx

from zlabel.data import (
    ZfinExpressionRecord,
    ancestors,
    load_gene_synonym_map,
    load_zfa,
    load_zfin_expression,
    term_name,
)
from zlabel.genes import STATUS_RESOLVED, NormalizedSymbol, normalize_markers, resolved_symbols
from zlabel.ground import expression_lookup, grounds_under, stage_plausibility
from zlabel.models import (
    OOD_IN_SET,
    TIER_HIGH_NAME,
    TIER_LOW_NAME,
    TIER_MEDIUM_NAME,
    BucketScoreTrace,
    Candidate,
    Confidence,
    ExprHit,
    Label,
    LabelTrace,
    NormalizedMarkerTrace,
    Ood,
    TermVoteTrace,
)
from zlabel.panels import KIND_IDENTITY, KIND_STATE, BucketScore, MatchedMarker, Panel, load_panels, score_markers
from zlabel.resolve import STOPLIST, TermVote, build_information_content, build_marker_specificity, resolve_label

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

MARKER_SPECIFICITY_MIN: float = 1.0 / 3.0
# Specificity-rescue threshold (Stage S "F2"): a weak-signal cluster (top adjusted score below
# MIN_SIGNAL) is rescued from the dilution veto when one matched identity marker is sharply
# lineage-specific -- its inverse panel-frequency (resolve.build_marker_specificity) is >= this,
# i.e. it grounds under at most 3 of the ~31 lineage anchors. It is then named from that marker's
# panel. The fraction denominator alone vetoes a single canonical marker among many off-panel ones;
# this is what a human does instead (call the lineage from the one specific marker). Measured: ~4x
# coverage at the named-agreement floor. Contained to precheck B; the descent is unchanged.

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

# Decision-ladder branch names, recorded in a LabelTrace so introspection can
# show which path the engine took (and, for abstentions, why).
BRANCH_PRECHECK_A = "precheck-a-no-identity"
BRANCH_PRECHECK_B = "precheck-b-weak-signal"
BRANCH_PRECHECK_B_RESCUE = "precheck-b-specificity-rescue"
BRANCH_CLEAR_WINNER = "clear-winner"
BRANCH_ROLLUP = "germ-layer-rollup"
BRANCH_MIXED = "mixed-abstain"


@dataclass
class _Recorder:
    """Mutable scratch sink for trace(): the intermediates decide() computes.

    Threaded through decide() (and resolve_label) as a keyword-only argument that
    defaults to None, so the labeling path is byte-for-byte unchanged when not
    tracing. Every field is written only after the value is already computed for
    the real decision, so the recorder never alters behavior. trace() converts a
    finished recorder into the pydantic LabelTrace.

    Attributes:
        branch (str): Which decision-ladder branch was taken (a BRANCH_ constant).
        adj_by_bucket (dict[str, float]): Adjusted identity score per ranked bucket.
        winner_bucket (str | None): The bucket decide() selected, if any.
        contender_buckets (tuple[str, ...]): Buckets in the near-tie set, if any.
        term_votes (list[TermVoteTrace]): Every tallied ZFA term; resolve_label fills this.
        selected_zfa_id (str | None): The named term id, if the descent named one (None on fallback).
        grounded_winner (bool): Whether the named term grounds under the panel anchor. Always True
            when a term is named -- the descent stays at or under the anchor by construction.
    """

    branch: str = ""
    adj_by_bucket: dict[str, float] = field(default_factory=dict)
    winner_bucket: str | None = None
    contender_buckets: tuple[str, ...] = ()
    term_votes: list[TermVoteTrace] = field(default_factory=list)
    selected_zfa_id: str | None = None
    grounded_winner: bool = False


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def _levels_chain(zfa_ontology: nx.MultiDiGraph, zfa_id: str, zfa_name: str) -> tuple[str, ...]:
    """Build a broad-to-specific name chain ending at zfa_name.

    Takes the ZFA ancestor ids in BFS order (nearest first), filters out
    stoplist entries and terms absent from the graph, reverses so the
    broadest comes first, then appends the named term. Best-effort: the
    ZFA DAG may have multiple paths; BFS gives shortest paths first.

    Args:
        zfa_ontology (nx.MultiDiGraph): ZFA ontology graph.
        zfa_id (str): The named ZFA term id.
        zfa_name (str): Human-readable name of the named term.

    Returns:
        tuple[str, ...]: Chain of names broad to specific, ending at zfa_name.
    """
    if zfa_id not in zfa_ontology:
        return (zfa_name,)
    ancestor_ids = ancestors(zfa_ontology, zfa_id)  # BFS order, nearest ancestor first
    names = [
        term_name(zfa_ontology, ancestor_id) or ancestor_id
        for ancestor_id in reversed(ancestor_ids)  # reverse so broadest (farthest) ancestor is first
        if ancestor_id not in STOPLIST and ancestor_id in zfa_ontology
    ]
    return tuple(names + [zfa_name])


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
    hit_weight = sum(matched_marker.effective_weight for matched_marker in bucket_score.matched_markers)
    return hit_weight / identity_denom


def _best_marker_specificity(bucket_score: BucketScore, marker_specificity: Mapping[str, float]) -> float:
    """The panel-IDF of this bucket's single most lineage-specific matched marker, 0.0 if none.

    The precheck-B specificity rescue uses this to pick the bucket carrying the sharpest marker
    and to test it against MARKER_SPECIFICITY_MIN.

    Args:
        bucket_score (BucketScore): One identity bucket's score, with its matched markers.
        marker_specificity (Mapping[str, float]): Per-gene panel-IDF from build_marker_specificity.

    Returns:
        float: The maximum marker_specificity over this bucket's matched markers, or 0.0 when none.
    """
    return max((marker_specificity.get(matched.symbol, 0.0) for matched in bucket_score.matched_markers), default=0.0)


def _candidates(identity: list[BucketScore], identity_denom: float, top_adj: float) -> tuple[Candidate, ...]:
    """The near-tie candidate set: identity buckets within DOMINANCE_GAP of the top, best-first.

    Surfaces the contender band decide() already trusts so a caller sees the types the evidence is
    consistent with. identity is sorted by descending adjusted score, so the band is a prefix and the
    walk stops at the first bucket outside it. A clear winner yields one member; a near-tie yields the
    competing types with their margins. On an abstention with identity signal candidates[0] is the
    honest force-the-top target (precheck-A yields an empty set); on an assigned call the named
    bucket is panel_bucket and candidates is the context.

    Args:
        identity (list[BucketScore]): Identity buckets that matched markers, sorted by -adj.
        identity_denom (float): The identity-only weight denominator for _adj.
        top_adj (float): The top bucket's adjusted score.

    Returns:
        tuple[Candidate, ...]: Ordered best-first; each carries its adjusted score and its margin
        (top_adj minus its adjusted score) to the top member.
    """
    out: list[Candidate] = []
    for bucket_score in identity:
        adj = _adj(bucket_score, identity_denom)
        if top_adj - adj > DOMINANCE_GAP:
            break
        out.append(
            Candidate(
                bucket=bucket_score.bucket,
                germ_layer=bucket_score.germ_layer,
                adjusted_score=round(adj, 4),
                margin_to_top=round(top_adj - adj, 4),
            )
        )
    return tuple(out)


def _state_only_weight(scores: list[BucketScore]) -> float:
    """Weight of markers that hit a state panel and no identity panel.

    These markers legitimately belong in the denominator for state detection
    but should not suppress identity scores. Subtracting their effective weight
    from the effective total gives the identity-only denominator, so the
    specificity blend and the denominator stay in the same weight space.

    Args:
        scores (list[BucketScore]): Full score table from score_markers.

    Returns:
        float: Sum of effective weights of markers that hit only state panels.
    """
    identity_symbols = {
        matched_marker.symbol
        for bucket_score in scores
        if bucket_score.kind == KIND_IDENTITY
        for matched_marker in bucket_score.matched_markers
    }
    state_weight = {
        matched_marker.symbol: matched_marker.effective_weight
        for bucket_score in scores
        if bucket_score.kind == KIND_STATE
        for matched_marker in bucket_score.matched_markers
    }
    return sum(weight for symbol, weight in state_weight.items() if symbol not in identity_symbols)


def _compute_grounding_evidence(
    matched_markers: tuple[MatchedMarker, ...],
    anchor: frozenset[str],
    expression_map: Mapping[str, list[ZfinExpressionRecord]],
    zfa_ontology: nx.MultiDiGraph,
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
        expression_map (Mapping[str, list[ZfinExpressionRecord]]): ZFIN expression data.
        zfa_ontology (nx.MultiDiGraph): ZFA ontology graph.
        stage_hpf (float | None): Dataset stage in hpf, or None.

    Returns:
        tuple[tuple[ExprHit, ...], dict[str, int]]: Grounded anatomy hits and a
        dict with keys gradable, grounded, datable, plausible.
    """
    hits: list[ExprHit] = []
    counts = {"gradable": 0, "grounded": 0, "datable": 0, "plausible": 0}

    for matched_marker in matched_markers:
        records = expression_lookup(expression_map, matched_marker.symbol)
        if not records:
            continue  # no records -> not gradable for either component
        counts["gradable"] += 1

        # Grounding: the first record (if any) that sits under the anchor.
        grounded_rec = next((record for record in records if grounds_under(zfa_ontology, record.zfa_id, anchor)), None)
        if grounded_rec is not None:
            counts["grounded"] += 1
            zfa_name = term_name(zfa_ontology, grounded_rec.zfa_id) or grounded_rec.zfa_id
            hits.append(ExprHit(symbol=matched_marker.symbol, zfa_id=grounded_rec.zfa_id, zfa_name=zfa_name))

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
    """Grade an assigned bucket: weighted score -> tier, with the high-confidence caps.

    The 0-1 score is W_COHERENCE*coherence + W_MARGIN*margin + W_GROUNDING*grounding
    + W_STAGE*stage, each component in [0, 1] (absent grounding/stage use NEUTRAL).
    Only a high call is ever capped down to medium:
      convergence cap -- a single-bucket high needs real corroboration (see
        _supports_high); strong panels alone top out at medium.
      rollup cap -- a germ-layer rollup never exceeds medium (it makes no single-
        anatomy high claim).
    low is _tier's natural minimum, so no separate floor step is needed.

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
    coherence = _clamp01(sum(matched_marker.weight for matched_marker in top.matched_markers) / COHERENCE_SAT)
    margin = _clamp01((top_adj - second_adj) / DOMINANCE_GAP)
    grounding = counts["grounded"] / counts["gradable"] if counts["gradable"] else None
    stage = counts["plausible"] / counts["datable"] if stage_hpf is not None and counts["datable"] else None

    grounding_component = grounding if grounding is not None else NEUTRAL
    stage_component = stage if stage is not None else NEUTRAL
    score = W_COHERENCE * coherence + W_MARGIN * margin + W_GROUNDING * grounding_component + W_STAGE * stage_component
    components = {"coherence": coherence, "margin": margin, "grounding": grounding_component, "stage": stage_component}

    # Cap a high call down to medium: a rollup makes no single-bucket high claim, and
    # a single-bucket high needs real grounding/stage corroboration (convergence cap).
    tier = _tier(score)
    if tier == TIER_HIGH_NAME and (rollup or not _supports_high(grounding, stage)):
        tier = TIER_MEDIUM_NAME
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
    for bucket_score in scores:
        if bucket_score.kind != KIND_STATE:
            continue
        hit_weight = sum(matched_marker.weight for matched_marker in bucket_score.matched_markers)
        if hit_weight >= STATE_MIN_WEIGHT and len(bucket_score.matched_markers) >= N_STATE_MIN:
            detected.append(bucket_score.bucket)
    return tuple(sorted(detected))


def _abstain(
    flag: str,
    states: tuple[str, ...],
    panel_scores: dict[str, float],
    *,
    ood: Ood = OOD_IN_SET,
    candidates: tuple[Candidate, ...] = (),
    margin: float = 0.0,
) -> Label:
    """Build a mixed/unresolved abstention Label.

    Args:
        flag (str): Ambiguity flag (provisional, mixed).
        states (tuple[str, ...]): Detected state programs.
        panel_scores (dict[str, float]): Raw panel scores.
        ood (Ood): The out-of-distribution flag for this abstention (no_signal, structural, doublet,
            or in_set for a reachable near-tie the gate vetoed).
        candidates (tuple[Candidate, ...]): The near-tie candidate set (empty when no identity hit).
        margin (float): Raw lead of the top adjusted score over the runner-up.

    Returns:
        Label: An abstained evidence packet.
    """
    return Label(
        bucket=_ABSTAIN_BUCKET,
        levels=(),
        depth=0,
        abstained=True,
        confidence=None,
        confidence_score=None,
        confidence_components={},
        ambiguity_flag=flag,
        states=states,
        panel_bucket="",
        panel_germ_layer="",
        zfa_id=None,
        panel_scores=panel_scores,
        positive_markers=(),
        convergent_genes=(),
        expression_evidence=(),
        rationale=f"abstained: {flag}",
        next_step=None,
        candidates=candidates,
        ood=ood,
        margin=margin,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def decide(
    scores: list[BucketScore],
    *,
    anchors: Mapping[str, frozenset[str]],
    expression_map: Mapping[str, list[ZfinExpressionRecord]],
    zfa_ontology: nx.MultiDiGraph,
    stage_hpf: float | None,
    symbols: list[str] | None = None,
    information_content: Mapping[str, float] | None = None,
    marker_specificity: Mapping[str, float] | None = None,
    recorder: _Recorder | None = None,
) -> Label:
    """Converging-evidence decision: turn a score table into a Label.

    Pure and I/O-free. Takes the output of score_markers plus already-loaded
    grounding data; returns a Label evidence packet.

    The decision ladder:
      A. No resolved markers or no identity panel hit at all -> abstain (provisional).
      B. Top adjusted identity score < MIN_SIGNAL -> rescue on a sharply lineage-specific marker
         (IDF >= MARKER_SPECIFICITY_MIN), else abstain (provisional).
      C. Top score dominates (gap >= DOMINANCE_GAP, or only one identity bucket) ->
         name from ZFA convergence descent (symbols + information_content required) or fall back to the
         panel bucket; emit the named label.
      D. Near-tie: contenders within DOMINANCE_GAP of the top.
         All share a non-empty germ layer -> assign at germ-layer tier (underclustered).
         Otherwise -> abstain (mixed).

    Args:
        scores (list[BucketScore]): From score_markers; must include total_weight.
        anchors (Mapping[str, frozenset[str]]): Bucket name to ZFA anchor ids.
            Passed explicitly so decide() stays pure; Labeler builds this from
            the loaded Panel objects.
        expression_map (Mapping[str, list[ZfinExpressionRecord]]): From
            data.load_zfin_expression.
        zfa_ontology (nx.MultiDiGraph): From data.load_zfa.
        stage_hpf (float | None): Dataset developmental stage in hpf, or None.
        symbols (list[str] | None): Already-normalized current ZFIN symbols of the
            cluster's markers, in rank order. When provided (with information_content), drives the
            anchor-rooted convergence descent that names the bucket from ZFA anatomy.
            When None, the descent is skipped and the panel bucket is used directly.
        information_content (Mapping[str, float] | None): IC model from resolve.build_information_content. Required
            alongside symbols for the convergence descent.
        marker_specificity (Mapping[str, float] | None): Per-gene panel-IDF from
            resolve.build_marker_specificity. When provided, a weak-signal cluster carrying a
            sharply lineage-specific matched marker (IDF >= MARKER_SPECIFICITY_MIN) is rescued from
            precheck B and named from that marker's panel; absent or empty, precheck B abstains.
        recorder (_Recorder | None): Optional trace sink. When None (the default
            and the labeling path) decide() is unchanged; when provided, the
            intermediates are recorded for trace() with no effect on the result.

    Returns:
        Label: Evidence packet with bucket, confidence, expression evidence, etc.
    """
    panel_scores = {bucket_score.bucket: bucket_score.score for bucket_score in scores}
    states = _detect_states(scores)

    # Recover the effective total weight from the first score (all BucketScores
    # share it). With no blend this equals the raw total, so the default path and
    # every existing fixture are byte-for-byte unchanged.
    total_weight = scores[0].total_effective_weight if scores else 0.0

    # Compute state-only weight to derive the identity-only denominator.
    state_only_weight = _state_only_weight(scores)
    identity_denom = total_weight - state_only_weight

    # Sort identity buckets that actually matched markers, by adjusted score
    # descending. Dropping zero-marker buckets here is what keeps them from
    # padding the near-tie contender set and forcing a false "mixed" abstention.
    identity = sorted(
        [
            bucket_score
            for bucket_score in scores
            if bucket_score.kind == KIND_IDENTITY and bucket_score.matched_markers
        ],
        key=lambda bucket_score: (-_adj(bucket_score, identity_denom), bucket_score.bucket),
    )

    if recorder is not None:
        recorder.adj_by_bucket = {bucket_score.bucket: _adj(bucket_score, identity_denom) for bucket_score in identity}

    # --- Precheck A: no identity evidence at all ---
    if not identity:
        if recorder is not None:
            recorder.branch = BRANCH_PRECHECK_A
        return _abstain("provisional", states, panel_scores, ood="no_signal")

    top = identity[0]
    top_adj = _adj(top, identity_denom)
    second_adj = _adj(identity[1], identity_denom) if len(identity) > 1 else 0.0
    # The near-tie candidate set and the raw margin -- the forcing evidence surfaced on every Label
    # below. Computed once, now that the top exists.
    candidates = _candidates(identity, identity_denom, top_adj)
    margin = top_adj - second_adj

    # --- Precheck B: signal too weak ---
    if top_adj < MIN_SIGNAL:
        # Specificity rescue: the fraction denominator buries a single canonical marker among many
        # off-panel ones, but a sharply lineage-specific marker (IDF >= MARKER_SPECIFICITY_MIN) is
        # strong evidence on its own -- so rescue from the veto and name from that marker's panel,
        # the way a human calls the lineage off one specific marker. Contained to this branch.
        if marker_specificity:
            best = max(identity, key=lambda bucket_score: _best_marker_specificity(bucket_score, marker_specificity))
            if _best_marker_specificity(best, marker_specificity) >= MARKER_SPECIFICITY_MIN:
                if recorder is not None:
                    recorder.branch = BRANCH_PRECHECK_B_RESCUE
                    recorder.winner_bucket = best.bucket
                return _assign_named(
                    top=best,
                    top_adj=_adj(best, identity_denom),
                    # second_adj keeps the original runner-up; for a rescued (non-top) bucket it can
                    # exceed top_adj, intentionally driving the margin component low -> low confidence.
                    second_adj=second_adj,
                    anchors=anchors,
                    expression_map=expression_map,
                    zfa_ontology=zfa_ontology,
                    stage_hpf=stage_hpf,
                    states=states,
                    panel_scores=panel_scores,
                    symbols=symbols or [],
                    information_content=information_content or {},
                    candidates=candidates,
                    margin=margin,
                    recorder=recorder,
                )
        if recorder is not None:
            recorder.branch = BRANCH_PRECHECK_B
        # OOD: does the descent seed under the top panel's anchor? If it does, the markers converge on
        # reachable anatomy and only the weak gate vetoed them (in_set, force-able); if not, their
        # anatomy converges nowhere -- a structural blind-spot. Needs the descent machinery; without it
        # (pure decide() tests omit symbols/IC) we do not claim structural.
        ood: Ood = OOD_IN_SET
        if symbols and information_content:
            seeds = resolve_label(
                symbols,
                expression_map=expression_map,
                zfa_ontology=zfa_ontology,
                information_content=information_content,
                anchor=anchors.get(top.bucket, frozenset()),
            )
            if not seeds:
                ood = "structural"
        return _abstain("provisional", states, panel_scores, ood=ood, candidates=candidates, margin=margin)

    # --- C / D: dominance test ---
    gap = top_adj - second_adj
    if len(identity) == 1 or gap >= DOMINANCE_GAP:
        # Clear winner: name from ZFA convergence descent when symbols/information_content are
        # provided; fall back to the coarse panel bucket otherwise.
        if recorder is not None:
            recorder.branch = BRANCH_CLEAR_WINNER
            recorder.winner_bucket = top.bucket
        return _assign_named(
            top=top,
            top_adj=top_adj,
            second_adj=second_adj,
            anchors=anchors,
            expression_map=expression_map,
            zfa_ontology=zfa_ontology,
            stage_hpf=stage_hpf,
            states=states,
            panel_scores=panel_scores,
            symbols=symbols or [],
            information_content=information_content or {},
            candidates=candidates,
            margin=margin,
            recorder=recorder,
        )

    # Near-tie: collect contenders within DOMINANCE_GAP of the top.
    contenders = [
        bucket_score for bucket_score in identity if top_adj - _adj(bucket_score, identity_denom) <= DOMINANCE_GAP
    ]
    germ_layers = {bucket_score.germ_layer for bucket_score in contenders if bucket_score.germ_layer}

    if recorder is not None:
        recorder.contender_buckets = tuple(bucket_score.bucket for bucket_score in contenders)

    if len(germ_layers) == 1:
        # All contenders share a germ layer — assign at germ-layer tier.
        germ_layer = next(iter(germ_layers))
        if recorder is not None:
            recorder.branch = BRANCH_ROLLUP
        return _assign_rollup(
            germ_layer=germ_layer,
            contenders=contenders,
            top_adj=top_adj,
            second_adj=second_adj,
            anchors=anchors,
            expression_map=expression_map,
            zfa_ontology=zfa_ontology,
            stage_hpf=stage_hpf,
            states=states,
            panel_scores=panel_scores,
            candidates=candidates,
            margin=margin,
        )

    # Contradictory germ layers -> mixed.
    if recorder is not None:
        recorder.branch = BRANCH_MIXED
    return _abstain("mixed", states, panel_scores, ood="doublet", candidates=candidates, margin=margin)


def _assign_named(
    *,
    top: BucketScore,
    top_adj: float,
    second_adj: float,
    anchors: Mapping[str, frozenset[str]],
    expression_map: Mapping[str, list[ZfinExpressionRecord]],
    zfa_ontology: nx.MultiDiGraph,
    stage_hpf: float | None,
    states: tuple[str, ...],
    panel_scores: dict[str, float],
    symbols: list[str],
    information_content: Mapping[str, float],
    candidates: tuple[Candidate, ...],
    margin: float,
    recorder: _Recorder | None = None,
) -> Label:
    """Build a Label for a clear single-bucket assignment, named from ZFA convergence.

    Runs resolve_label to descend from the winning panel's ontology anchor to the most specific
    ZFA term the markers converge on. Because the descent stays at or under the anchor by
    construction, a named term is always grounded -- there is no separate guardrail check. When no
    anchor id is supported (no descent seed) resolve_label returns nothing (named=None) and the
    coarse panel bucket is used as the fallback. Depth and levels are derived from the named ZFA
    term when one is found; otherwise the static panel triple is used.

    When symbols is empty or information_content is empty (pure decide() tests that omit them),
    resolve_label returns nothing and the behavior is identical to the old
    _assign_top fallback: panel bucket, static levels, panel anchor as zfa_id.

    Args:
        top (BucketScore): The winning panel bucket.
        top_adj (float): Its adjusted identity score.
        second_adj (float): Runner-up adjusted score (0 when none).
        anchors (Mapping[str, frozenset[str]]): Bucket -> ZFA anchor ids.
        expression_map (Mapping[str, list[ZfinExpressionRecord]]): Expression data.
        zfa_ontology (nx.MultiDiGraph): ZFA ontology graph.
        stage_hpf (float | None): Dataset stage in hpf, or None.
        states (tuple[str, ...]): Detected state programs.
        panel_scores (dict[str, float]): Raw panel scores.
        symbols (list[str]): Already-normalized current ZFIN symbols of all
            cluster markers, in rank order. May be empty.
        information_content (Mapping[str, float]): IC model from build_information_content. May be empty.
        candidates (tuple[Candidate, ...]): The near-tie candidate set, surfaced on the Label.
        margin (float): Raw lead of the top adjusted score over the runner-up.
        recorder (_Recorder | None): Optional trace sink. When provided, the full
            convergence descent (with gate near-misses) and the selected term are
            recorded for trace(); None leaves behavior unchanged.

    Returns:
        Label: Assigned evidence packet with the data-derived ZFA bucket when
        available, or the coarse panel bucket as fallback.
    """
    anchor = anchors.get(top.bucket, frozenset())

    # Name by descending from the panel's ontology anchor (resolve_label). The descent stays at
    # or under the anchor by construction, so the old post-hoc guardrail is folded in: a named
    # term is always grounded, and an unsupported anchor yields no term -> fall back to the bucket.
    votes = resolve_label(
        symbols,
        expression_map=expression_map,
        zfa_ontology=zfa_ontology,
        information_content=information_content,
        anchor=anchor,
        vote_trace=recorder.term_votes if recorder is not None else None,
    )
    named: TermVote | None = votes[0] if votes else None

    if recorder is not None:
        recorder.selected_zfa_id = named.zfa_id if named is not None else None
        recorder.grounded_winner = named is not None

    # Grounding evidence: when a term was named, check markers against that
    # term as anchor (measures how many panel markers express in the named
    # anatomy). When no term was named, fall back to the panel anchor so
    # existing grounding-based tests are unaffected.
    grounding_anchor = frozenset({named.zfa_id}) if named is not None else anchor
    hits, counts = _compute_grounding_evidence(
        top.matched_markers, grounding_anchor, expression_map, zfa_ontology, stage_hpf
    )

    conf_score, tier, components = _grade_confidence(top, second_adj, top_adj, counts, stage_hpf, rollup=False)
    positive = tuple(matched_marker.symbol for matched_marker in top.matched_markers)

    if named is not None:
        bucket = named.zfa_name
        zfa_id = named.zfa_id
        levels = _levels_chain(zfa_ontology, named.zfa_id, named.zfa_name)
        depth = len(levels)
        convergent_genes = named.genes
        rationale = (
            f"{named.zfa_name} (IC {named.information_content:.2f}) -- "
            f"{len(named.genes)}/{len(symbols)} markers converge; "
            f"panel prior: {top.bucket}"
        )
    else:
        # Fallback: use the coarse panel bucket (same as the old _assign_top).
        bucket = top.bucket
        zfa_id = sorted(anchor)[0] if anchor else None
        levels = tuple(level for level in (top.germ_layer, top.tissue, top.lineage) if level)
        depth = len(levels)
        convergent_genes = ()
        markers_txt = ", ".join(matched_marker.symbol for matched_marker in top.matched_markers[:3])
        rationale = f"{top.bucket} supported by {markers_txt} (adj_score={top_adj:.2f}; no convergent ZFA term)"

    return Label(
        bucket=bucket,
        levels=levels,
        depth=depth,
        abstained=False,
        confidence=tier,
        confidence_score=round(conf_score, 4),
        confidence_components={name: round(value, 4) for name, value in components.items()},
        ambiguity_flag="none",
        states=states,
        panel_bucket=top.bucket,
        panel_germ_layer=top.germ_layer,
        zfa_id=zfa_id,
        panel_scores=panel_scores,
        positive_markers=positive,
        convergent_genes=convergent_genes,
        expression_evidence=hits,
        rationale=rationale,
        next_step="subcluster",
        candidates=candidates,
        margin=margin,
    )


def _assign_rollup(
    *,
    germ_layer: str,
    contenders: list[BucketScore],
    top_adj: float,
    second_adj: float,
    anchors: Mapping[str, frozenset[str]],
    expression_map: Mapping[str, list[ZfinExpressionRecord]],
    zfa_ontology: nx.MultiDiGraph,
    stage_hpf: float | None,
    states: tuple[str, ...],
    panel_scores: dict[str, float],
    candidates: tuple[Candidate, ...],
    margin: float,
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
        expression_map (Mapping[str, list[ZfinExpressionRecord]]): Expression data.
        zfa_ontology (nx.MultiDiGraph): ZFA ontology graph.
        stage_hpf (float | None): Dataset stage in hpf, or None.
        states (tuple[str, ...]): Detected state programs.
        panel_scores (dict[str, float]): Raw panel scores.
        candidates (tuple[Candidate, ...]): The near-tie candidate set (the contender band).
        margin (float): Raw lead of the top adjusted score over the runner-up.

    Returns:
        Label: Rollup evidence packet.
    """
    # Union of all contenders' matched markers (deduplicated by symbol).
    seen: set[str] = set()
    union_markers = []
    for bucket_score in contenders:
        for matched_marker in bucket_score.matched_markers:
            if matched_marker.symbol not in seen:
                seen.add(matched_marker.symbol)
                union_markers.append(matched_marker)
    union_matched = tuple(union_markers)

    # Union of all contenders' anchors.
    union_anchor: frozenset[str] = frozenset().union(
        *(anchors.get(bucket_score.bucket, frozenset()) for bucket_score in contenders)
    )

    hits, counts = _compute_grounding_evidence(union_matched, union_anchor, expression_map, zfa_ontology, stage_hpf)

    # Use the top contender as a proxy for coherence/margin.
    top = contenders[0]
    conf_score, tier, components = _grade_confidence(top, second_adj, top_adj, counts, stage_hpf, rollup=True)

    positive = tuple(matched_marker.symbol for matched_marker in union_matched)

    return Label(
        bucket=germ_layer,
        levels=(germ_layer,),
        depth=1,
        abstained=False,
        confidence=tier,
        confidence_score=round(conf_score, 4),
        confidence_components={name: round(value, 4) for name, value in components.items()},
        ambiguity_flag="underclustered",
        states=states,
        panel_bucket=germ_layer,
        panel_germ_layer=germ_layer,
        zfa_id=None,
        panel_scores=panel_scores,
        positive_markers=positive,
        convergent_genes=(),
        expression_evidence=hits,
        rationale=f"{germ_layer} rollup: contenders {[bucket_score.bucket for bucket_score in contenders]}",
        next_step="subcluster",
        candidates=candidates,
        margin=margin,
    )


# ---------------------------------------------------------------------------
# Introspection trace
# ---------------------------------------------------------------------------


def trace(
    scores: list[BucketScore],
    normalized_markers: list[NormalizedSymbol],
    *,
    anchors: Mapping[str, frozenset[str]],
    expression_map: Mapping[str, list[ZfinExpressionRecord]],
    zfa_ontology: nx.MultiDiGraph,
    stage_hpf: float | None,
    symbols: list[str] | None = None,
    information_content: Mapping[str, float] | None = None,
    marker_specificity: Mapping[str, float] | None = None,
) -> LabelTrace:
    """Run decide() with a recorder and return a faithful LabelTrace.

    Parallels decide(): the same inputs plus the normalized markers (which decide()
    does not receive), so a caller with shared resources can trace at an arbitrary
    stage. The embedded LabelTrace.label is exactly what decide() returns for the
    same inputs -- the trace records the decision, it does not re-decide.

    Args:
        scores (list[BucketScore]): From score_markers.
        normalized_markers (list[NormalizedSymbol]): From genes.normalize_markers;
            supplies the normalization outcomes and the resolved-symbol view.
        anchors (Mapping[str, frozenset[str]]): Bucket name to ZFA anchor ids.
        expression_map (Mapping[str, list[ZfinExpressionRecord]]): ZFIN expression data.
        zfa_ontology (nx.MultiDiGraph): ZFA ontology graph.
        stage_hpf (float | None): Dataset developmental stage in hpf, or None.
        symbols (list[str] | None): Resolved current ZFIN symbols in rank order.
        information_content (Mapping[str, float] | None): IC model for the vote.
        marker_specificity (Mapping[str, float] | None): Per-gene panel-IDF from
            resolve.build_marker_specificity; passed through to decide() for the precheck-B
            specificity rescue.

    Returns:
        LabelTrace: The decision plus its intermediates (normalization, panel
        ladder, convergence descent with gates, branch) and the embedded Label.
    """
    recorder = _Recorder()
    label = decide(
        scores,
        anchors=anchors,
        expression_map=expression_map,
        zfa_ontology=zfa_ontology,
        stage_hpf=stage_hpf,
        symbols=symbols,
        information_content=information_content,
        marker_specificity=marker_specificity,
        recorder=recorder,
    )
    return _assemble_trace(normalized_markers, scores, recorder, label, stage_hpf)


def _ordered_term_votes(recorder: _Recorder) -> tuple[TermVoteTrace, ...]:
    """Stamp the named terminal and order the descent path (broad->specific) before the rest.

    The terminal (recorder.selected_zfa_id) is marked selected and grounded (it sits under the
    anchor by construction); the descent-path terms come first, ordered anchor-to-terminal
    (ascending ancestor depth); every other tallied term follows by descending support. The
    output reads as the walk and is deterministic.

    Args:
        recorder (_Recorder): The trace sink, with term_votes already collected.

    Returns:
        tuple[TermVoteTrace, ...]: The vote rows, stamped and ordered.
    """
    stamped = [
        term_vote.model_copy(update={"selected": True, "grounded_under_anchor": recorder.grounded_winner})
        if term_vote.zfa_id == recorder.selected_zfa_id
        else term_vote
        for term_vote in recorder.term_votes
    ]
    on_path = sorted(
        (term_vote for term_vote in stamped if term_vote.on_descent_path),
        key=lambda tv: (tv.ancestor_depth, tv.zfa_id),
    )
    off_path = sorted(
        (term_vote for term_vote in stamped if not term_vote.on_descent_path),
        key=lambda tv: (-tv.gene_count, -tv.information_content, tv.zfa_id),
    )
    return tuple(on_path + off_path)


def _assemble_trace(
    normalized_markers: list[NormalizedSymbol],
    scores: list[BucketScore],
    recorder: _Recorder,
    label: Label,
    stage_hpf: float | None,
) -> LabelTrace:
    """Convert a finished decision and its recorder into a LabelTrace.

    Args:
        normalized_markers (list[NormalizedSymbol]): The cluster's normalized markers.
        scores (list[BucketScore]): The panel score table decide() ranked.
        recorder (_Recorder): The trace sink decide()/resolve_label filled.
        label (Label): The decision decide() returned (embedded verbatim).
        stage_hpf (float | None): Dataset stage in hpf, or None.

    Returns:
        LabelTrace: The assembled, YAML-serialisable trace.
    """
    normalized = tuple(
        NormalizedMarkerTrace(
            input=normalized_marker.input,
            status=normalized_marker.status,
            symbols=tuple(sorted(normalized_marker.symbols)),
            note=normalized_marker.note,
            rank=rank,
            dropped=normalized_marker.status != STATUS_RESOLVED,
        )
        for rank, normalized_marker in enumerate(normalized_markers, start=1)
    )
    panel = tuple(
        BucketScoreTrace(
            bucket=bucket_score.bucket,
            score=bucket_score.score,
            adjusted_score=recorder.adj_by_bucket.get(bucket_score.bucket, 0.0),
            germ_layer=bucket_score.germ_layer,
            kind=bucket_score.kind,
            matched_markers=tuple(matched_marker.symbol for matched_marker in bucket_score.matched_markers),
            is_winner=bucket_score.bucket == recorder.winner_bucket,
            is_contender=bucket_score.bucket in recorder.contender_buckets,
        )
        for bucket_score in scores
    )
    return LabelTrace(
        markers_in=tuple(normalized_marker.input for normalized_marker in normalized_markers),
        stage_hpf=stage_hpf,
        normalized_markers=normalized,
        resolved_symbols=tuple(resolved_symbols(normalized_markers)),
        panel_scores=panel,
        branch=recorder.branch,
        term_votes=_ordered_term_votes(recorder),
        label=label,
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

        self._zfa_ontology = load_zfa(zfa_p)
        self._expression_map = load_zfin_expression(expr_p)
        self._synonyms = load_gene_synonym_map(gaf_p)
        self._panels: list[Panel] = load_panels(panels_p)
        self._anchors: dict[str, frozenset[str]] = {panel.bucket: panel.ontology_anchor for panel in self._panels}
        # IC model built once from the loaded expression corpus.
        # Passed to decide() so resolve_label can rank convergent ZFA terms.
        self._information_content: dict[str, float] = build_information_content(
            self._expression_map, self._zfa_ontology
        )
        # Per-gene panel-IDF, built once: how lineage-specific each marker is. decide() uses it
        # for the precheck-B specificity rescue (a sharply specific marker survives the dilution veto).
        identity_anchors = [panel.ontology_anchor for panel in self._panels if panel.kind == KIND_IDENTITY]
        self._marker_specificity: dict[str, float] = build_marker_specificity(
            self._expression_map, identity_anchors, self._zfa_ontology
        )

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
        # Normalize once: the panel scorer and the convergence descent both consume
        # the same normalized markers. resolve_label requires already-normalized
        # symbols; without this, aliases like fli1a -> fli1 (314 expression
        # records) would be missed.
        normalized_markers = normalize_markers(markers, self._synonyms)
        symbols = resolved_symbols(normalized_markers)
        scores = score_markers(normalized_markers, self._panels)
        return decide(
            scores,
            anchors=self._anchors,
            expression_map=self._expression_map,
            zfa_ontology=self._zfa_ontology,
            stage_hpf=self.stage_hpf,
            symbols=symbols,
            information_content=self._information_content,
            marker_specificity=self._marker_specificity,
        )

    def trace(self, markers: list[str]) -> LabelTrace:
        """Label one cluster and return a faithful LabelTrace for introspection.

        Same inputs and decision as label(), plus the recorded intermediates:
        the normalization outcomes, the panel ladder, the full convergence descent
        with gate near-misses, and the branch taken. The embedded LabelTrace.label
        is identical to label(markers).

        Args:
            markers (list[str]): Marker gene symbols ordered by significance
                (rank 1 = most significant = index 0). May use old ZFIN names.

        Returns:
            LabelTrace: The decision plus its step-by-step intermediates.
        """
        normalized_markers = normalize_markers(markers, self._synonyms)
        symbols = resolved_symbols(normalized_markers)
        scores = score_markers(normalized_markers, self._panels)
        # trace() here is the module-level function above, not this method.
        return trace(
            scores,
            normalized_markers,
            anchors=self._anchors,
            expression_map=self._expression_map,
            zfa_ontology=self._zfa_ontology,
            stage_hpf=self.stage_hpf,
            symbols=symbols,
            information_content=self._information_content,
            marker_specificity=self._marker_specificity,
        )
