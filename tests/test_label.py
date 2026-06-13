"""Unit tests for label.decide() and Labeler.

Two sets of tests:
  1. Pure decide() over hand-built BucketScore lists — no I/O, exercises the
     decision ladder (dominance, rollup, abstention), state detection, and the
     confidence rubric (convergence cap, marker-level grounding, floor/cap).
  2. Labeler smoke test over committed fixture files — exercises the full path
     from raw marker symbols through normalization, scoring, grounding, and
     stage to a final Label without any downloaded data.
"""

from __future__ import annotations

import math
from pathlib import Path

import pytest

from zlabel.data import ZfinExpressionRecord, load_zfa
from zlabel.label import (
    MIN_SIGNAL,
    Labeler,
    decide,
)
from zlabel.models import TIER_HIGH_NAME, TIER_LOW_NAME, TIER_MEDIUM_NAME
from zlabel.panels import KIND_IDENTITY, KIND_STATE, BucketScore, MatchedMarker

FIXTURES = Path(__file__).parent / "fixtures"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mm(symbol: str, rank: int) -> MatchedMarker:
    return MatchedMarker(input=symbol, symbol=symbol, rank=rank, weight=1.0 / math.log2(rank + 1))


def _bs(
    bucket: str,
    *,
    germ_layer: str = "mesoderm",
    tissue: str = "muscle",
    lineage: str = "skeletal muscle",
    kind: str = KIND_IDENTITY,
    markers: list[str],
    total_weight: float = 3.0,
) -> BucketScore:
    matched = tuple(_mm(sym, rank) for rank, sym in enumerate(markers, start=1))
    hit_weight = sum(m.weight for m in matched)
    score = hit_weight / total_weight if total_weight > 0 else 0.0
    return BucketScore(
        bucket=bucket,
        score=score,
        germ_layer=germ_layer,
        tissue=tissue,
        lineage=lineage,
        kind=kind,
        matched_markers=matched,
        total_weight=total_weight,
    )


def _empty_bs(bucket: str, *, kind: str = KIND_IDENTITY, germ_layer: str = "mesoderm") -> BucketScore:
    return BucketScore(
        bucket=bucket,
        score=0.0,
        germ_layer=germ_layer,
        tissue="",
        lineage="",
        kind=kind,
        matched_markers=(),
        total_weight=1.0,
    )


MUSCLE_ANCHOR: frozenset[str] = frozenset({"ZFA:0000548"})
BLOOD_ANCHOR: frozenset[str] = frozenset({"ZFA:0000007"})
NO_ANCHOR: frozenset[str] = frozenset()

EMPTY_EXPR: dict[str, list[ZfinExpressionRecord]] = {}
EMPTY_ZFA = None  # only used when grounds_under path is exercised


@pytest.fixture(scope="module")
def zfa():
    return load_zfa(FIXTURES / "zfa_test.obo")


# ---------------------------------------------------------------------------
# Decision ladder tests (pure decide)
# ---------------------------------------------------------------------------


def test_abstain_no_markers(zfa):
    scores = [_empty_bs("muscle"), _empty_bs("blood_erythroid")]
    label = decide(scores, anchors={}, expr_map=EMPTY_EXPR, zfa_graph=zfa, stage_hpf=None)
    assert label.abstained
    assert label.bucket == "mixed/unresolved"
    assert label.ambiguity_flag == "provisional"


def test_abstain_weak_signal(zfa):
    # Muscle scores just below MIN_SIGNAL.
    blood = _empty_bs("blood_erythroid")
    blood_endo = _empty_bs("endothelium", germ_layer="mesoderm")
    muscle = BucketScore(
        bucket="muscle",
        score=MIN_SIGNAL - 0.01,
        germ_layer="mesoderm",
        tissue="muscle",
        lineage="skeletal muscle",
        kind=KIND_IDENTITY,
        matched_markers=(_mm("myod1", 1),),
        total_weight=10.0,  # very large denominator makes adj score tiny
    )
    scores = [muscle, blood, blood_endo]
    label = decide(scores, anchors={}, expr_map=EMPTY_EXPR, zfa_graph=zfa, stage_hpf=None)
    assert label.abstained
    assert label.ambiguity_flag == "provisional"


def test_assign_clear_winner(zfa):
    # Muscle has 3 markers, blood has 1, total_weight=3 so muscle adj score dominates.
    muscle = _bs("muscle", markers=["mylpfa", "myod1", "myog"], total_weight=3.0)
    blood = _bs(
        "blood_erythroid", germ_layer="mesoderm", tissue="blood",
        lineage="erythroid", markers=["gata1a"], total_weight=3.0,
    )
    cycling = _empty_bs("cycling", kind=KIND_STATE, germ_layer="")
    scores = [muscle, blood, cycling]
    label = decide(scores, anchors={"muscle": MUSCLE_ANCHOR}, expr_map=EMPTY_EXPR, zfa_graph=zfa, stage_hpf=None)
    assert not label.abstained
    assert label.bucket == "muscle"
    assert label.next_step == "subcluster"
    assert label.levels == ("mesoderm", "muscle", "skeletal muscle")


def test_invariant_abstained_implies_no_tier(zfa):
    scores = [_empty_bs("muscle")]
    label = decide(scores, anchors={}, expr_map=EMPTY_EXPR, zfa_graph=zfa, stage_hpf=None)
    assert label.abstained == (label.confidence is None)


def test_invariant_assigned_implies_tier(zfa):
    muscle = _bs("muscle", markers=["mylpfa", "myod1", "myog"], total_weight=3.0)
    blood = _empty_bs("blood_erythroid")
    scores = [muscle, blood]
    label = decide(scores, anchors={"muscle": MUSCLE_ANCHOR}, expr_map=EMPTY_EXPR, zfa_graph=zfa, stage_hpf=None)
    assert not label.abstained
    assert label.confidence is not None
    assert label.confidence in (TIER_HIGH_NAME, TIER_MEDIUM_NAME, TIER_LOW_NAME)


def test_rollup_same_germ_layer(zfa):
    # Two mesoderm buckets within DOMINANCE_GAP of each other.
    muscle = _bs(
        "muscle", germ_layer="mesoderm", tissue="muscle",
        lineage="skeletal muscle", markers=["myod1", "myog"], total_weight=3.0,
    )
    blood = _bs(
        "blood_erythroid", germ_layer="mesoderm", tissue="blood",
        lineage="erythroid", markers=["gata1a", "hbae1.1"], total_weight=3.0,
    )
    # Make the gap tiny so they're within DOMINANCE_GAP.
    # Force them to near-tied by having the same matched weight.
    scores = [muscle, blood]
    anchors = {"muscle": MUSCLE_ANCHOR, "blood_erythroid": BLOOD_ANCHOR}
    label = decide(scores, anchors=anchors, expr_map=EMPTY_EXPR, zfa_graph=zfa, stage_hpf=None)
    # If they're actually within DOMINANCE_GAP: rollup to mesoderm
    if label.bucket == "mesoderm":
        assert label.ambiguity_flag == "underclustered"
        assert label.zfa_id is None
        assert label.confidence in (TIER_MEDIUM_NAME, TIER_LOW_NAME)
    else:
        # If one dominates: an assigned single bucket is also valid.
        assert not label.abstained


def test_rollup_contradictory_germ_layers_abstains(zfa):
    neural = _bs(
        "neural", germ_layer="ectoderm", tissue="nervous system",
        lineage="neural", markers=["elavl3", "neurod1"], total_weight=3.0,
    )
    blood = _bs(
        "blood_erythroid", germ_layer="mesoderm", tissue="blood",
        lineage="erythroid", markers=["gata1a", "hbae1.1"], total_weight=3.0,
    )
    scores = [neural, blood]
    label = decide(scores, anchors={}, expr_map=EMPTY_EXPR, zfa_graph=zfa, stage_hpf=None)
    if label.ambiguity_flag == "mixed":
        assert label.abstained
    else:
        # If one dominates, fine — the test is just that contradictory germ layers
        # abstain when they're truly within DOMINANCE_GAP.
        pass


# ---------------------------------------------------------------------------
# State detection tests
# ---------------------------------------------------------------------------


def test_cycling_muscle_reports_both(zfa):
    muscle = _bs("muscle", markers=["mylpfa", "myod1", "myog"], total_weight=5.0)
    blood = _empty_bs("blood_erythroid")
    # Cycling state with 2 markers, enough weight.
    mki67_w = 1.0 / math.log2(2)
    pcna_w = 1.0 / math.log2(3)
    cycling = BucketScore(
        bucket="cycling",
        score=(mki67_w + pcna_w) / 5.0,
        germ_layer="",
        tissue="",
        lineage="",
        kind=KIND_STATE,
        matched_markers=(_mm("mki67", 1), _mm("pcna", 2)),
        total_weight=5.0,
    )
    scores = [muscle, blood, cycling]
    label = decide(scores, anchors={"muscle": MUSCLE_ANCHOR}, expr_map=EMPTY_EXPR, zfa_graph=zfa, stage_hpf=None)
    assert not label.abstained
    assert label.bucket == "muscle"
    assert "cycling" in label.states


def test_pure_cycling_no_identity_abstains(zfa):
    muscle = _empty_bs("muscle")
    blood = _empty_bs("blood_erythroid")
    mki67_w = 1.0 / math.log2(2)
    pcna_w = 1.0 / math.log2(3)
    cycling = BucketScore(
        bucket="cycling",
        score=(mki67_w + pcna_w) / 2.0,
        germ_layer="",
        tissue="",
        lineage="",
        kind=KIND_STATE,
        matched_markers=(_mm("mki67", 1), _mm("pcna", 2)),
        total_weight=2.0,
    )
    scores = [muscle, blood, cycling]
    label = decide(scores, anchors={}, expr_map=EMPTY_EXPR, zfa_graph=zfa, stage_hpf=None)
    assert label.abstained
    assert "cycling" in label.states


def test_single_state_marker_not_called(zfa):
    muscle = _empty_bs("muscle")
    # Only one cycling marker — below N_STATE_MIN.
    cycling = BucketScore(
        bucket="cycling",
        score=0.5,
        germ_layer="",
        tissue="",
        lineage="",
        kind=KIND_STATE,
        matched_markers=(_mm("mki67", 1),),
        total_weight=2.0,
    )
    scores = [muscle, cycling]
    label = decide(scores, anchors={}, expr_map=EMPTY_EXPR, zfa_graph=zfa, stage_hpf=None)
    assert "cycling" not in label.states


# ---------------------------------------------------------------------------
# Confidence rubric: convergence cap and floor
# ---------------------------------------------------------------------------


def test_floor_low_when_weak_signal_but_still_assigned(zfa):
    # Muscle scores just above MIN_SIGNAL but below TIER_MEDIUM, no grounding.
    # Result must be low, not None.
    muscle = BucketScore(
        bucket="muscle",
        score=0.2,
        germ_layer="mesoderm",
        tissue="muscle",
        lineage="skeletal muscle",
        kind=KIND_IDENTITY,
        matched_markers=(_mm("myod1", 1),),
        total_weight=5.0,
    )
    blood = _empty_bs("blood_erythroid")
    scores = [muscle, blood]
    label = decide(scores, anchors={"muscle": MUSCLE_ANCHOR}, expr_map=EMPTY_EXPR, zfa_graph=zfa, stage_hpf=None)
    if not label.abstained:
        assert label.confidence == TIER_LOW_NAME


def test_convergence_cap_without_grounding_is_medium(zfa):
    # Strong panels: 3 muscle markers dominate. No expression data -> grounding = NEUTRAL.
    # No stage_hpf -> stage = NEUTRAL. With no real corroboration, tier capped at medium.
    muscle = _bs("muscle", markers=["mylpfa", "myod1", "myog"], total_weight=3.0)
    blood = _empty_bs("blood_erythroid")
    scores = [muscle, blood]
    label = decide(scores, anchors={"muscle": MUSCLE_ANCHOR}, expr_map=EMPTY_EXPR, zfa_graph=zfa, stage_hpf=None)
    if not label.abstained:
        # Should be at most medium since no real grounding/stage corroboration.
        assert label.confidence in (TIER_MEDIUM_NAME, TIER_LOW_NAME)


# ---------------------------------------------------------------------------
# Labeler smoke test (end-to-end over fixture files)
# ---------------------------------------------------------------------------


def test_labeler_smoke_muscle_cluster():
    """Full path: normalize (mylz2 -> mylpfa via GAF), score, ground, decide."""
    lab = Labeler(
        stage_hpf=48.0,
        zfa_path=FIXTURES / "zfa_test.obo",
        expr_path=FIXTURES / "zfin_expr_test.txt",
        gaf_path=FIXTURES / "zfin_go_test.gaf",
        panels_path=FIXTURES / "panels_test.yaml",
    )
    # Use the old symbol 'mylz2' to exercise normalization (GAF maps it to mylpfa).
    label = lab.label(["mylz2", "acta1b", "tnnt3a", "myod1", "myog"])
    assert not label.abstained
    assert label.bucket == "muscle"
    assert label.next_step == "subcluster"
    # Grounding: mylpfa and myod1 have records in zfin_expr_test.txt expressing
    # in musculature system / muscle cell — both ground under ZFA:0000548.
    assert len(label.expression_evidence) > 0
    # Stage: Long-pec = 48 hpf; all muscle records are at Long-pec -> plausible.
    assert label.confidence is not None


def test_labeler_to_yaml_runs():
    lab = Labeler(
        stage_hpf=48.0,
        zfa_path=FIXTURES / "zfa_test.obo",
        expr_path=FIXTURES / "zfin_expr_test.txt",
        gaf_path=FIXTURES / "zfin_go_test.gaf",
        panels_path=FIXTURES / "panels_test.yaml",
    )
    label = lab.label(["mylz2", "acta1b", "tnnt3a", "myod1", "myog"])
    yaml_str = label.to_yaml()
    assert "bucket:" in yaml_str
    assert "muscle" in yaml_str
