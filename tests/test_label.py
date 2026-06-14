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

from zlabel.data import ZfinExpressionRecord
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
        "blood_erythroid",
        germ_layer="mesoderm",
        tissue="blood",
        lineage="erythroid",
        markers=["gata1a"],
        total_weight=3.0,
    )
    cycling = _empty_bs("cycling", kind=KIND_STATE, germ_layer="")
    scores = [muscle, blood, cycling]
    label = decide(scores, anchors={"muscle": MUSCLE_ANCHOR}, expr_map=EMPTY_EXPR, zfa_graph=zfa, stage_hpf=None)
    assert not label.abstained
    assert label.bucket == "muscle"
    assert label.next_step == "subcluster"
    assert label.levels == ("mesoderm", "muscle", "skeletal muscle")


def test_decide_names_from_zfa_when_symbols_provided(zfa, expr_map, ic):
    # With symbols + ic, the clear-winner branch names the bucket from the ZFA
    # convergence vote (muscle cell) instead of the coarse panel bucket (muscle).
    muscle = _bs("muscle", markers=["mylpfa", "acta1b", "myog"], total_weight=3.0)
    blood = _empty_bs("blood_erythroid")
    label = decide(
        [muscle, blood],
        anchors={"muscle": MUSCLE_ANCHOR},
        expr_map=expr_map,
        zfa_graph=zfa,
        stage_hpf=None,
        symbols=["mylpfa", "acta1b", "myog"],
        ic=ic,
    )
    assert not label.abstained
    assert label.bucket == "muscle cell"  # named ZFA term, not the panel bucket
    assert label.panel_bucket == "muscle"  # coarse prior kept visible
    assert set(label.convergent_genes) == {"mylpfa", "acta1b", "myog"}
    assert label.depth == len(label.levels)  # the restored len(levels) contract


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
    # Two evidence-bearing mesoderm buckets, exactly tied (same matched weight) so
    # they are within DOMINANCE_GAP -> roll up to the shared germ layer.
    muscle = _bs(
        "muscle",
        germ_layer="mesoderm",
        tissue="muscle",
        lineage="skeletal muscle",
        markers=["myod1", "myog"],
        total_weight=3.0,
    )
    blood = _bs(
        "blood_erythroid",
        germ_layer="mesoderm",
        tissue="blood",
        lineage="erythroid",
        markers=["gata1a", "hbae1.1"],
        total_weight=3.0,
    )
    scores = [muscle, blood]
    anchors = {"muscle": MUSCLE_ANCHOR, "blood_erythroid": BLOOD_ANCHOR}
    label = decide(scores, anchors=anchors, expr_map=EMPTY_EXPR, zfa_graph=zfa, stage_hpf=None)
    assert label.bucket == "mesoderm"
    assert label.ambiguity_flag == "underclustered"
    assert label.zfa_id is None
    assert label.confidence in (TIER_MEDIUM_NAME, TIER_LOW_NAME)


def test_rollup_contradictory_germ_layers_abstains(zfa):
    # Two evidence-bearing buckets in different germ layers, exactly tied -> mixed.
    neural = _bs(
        "neural",
        germ_layer="ectoderm",
        tissue="nervous system",
        lineage="neural",
        markers=["elavl3", "neurod1"],
        total_weight=3.0,
    )
    blood = _bs(
        "blood_erythroid",
        germ_layer="mesoderm",
        tissue="blood",
        lineage="erythroid",
        markers=["gata1a", "hbae1.1"],
        total_weight=3.0,
    )
    scores = [neural, blood]
    label = decide(scores, anchors={}, expr_map=EMPTY_EXPR, zfa_graph=zfa, stage_hpf=None)
    assert label.abstained
    assert label.ambiguity_flag == "mixed"


def test_weak_single_signal_assigns_not_mixed(zfa):
    # Regression guard: a lone, weak-but-genuine identity signal (one neural marker,
    # adj 0.25) alongside empty buckets in other germ layers must assign neural.
    # Zero-marker buckets used to pad the contender set and force a false "mixed".
    neural = BucketScore(
        bucket="neural",
        score=0.25,
        germ_layer="ectoderm",
        tissue="nervous system",
        lineage="neural",
        kind=KIND_IDENTITY,
        matched_markers=(_mm("elavl3", 1),),
        total_weight=4.0,  # off-panel filler in the denominator -> adj 0.25
    )
    muscle = _empty_bs("muscle", germ_layer="mesoderm")
    gut = _empty_bs("endoderm_gut", germ_layer="endoderm")
    scores = [neural, muscle, gut]
    label = decide(scores, anchors={}, expr_map=EMPTY_EXPR, zfa_graph=zfa, stage_hpf=None)
    assert not label.abstained
    assert label.bucket == "neural"


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
    # Muscle is the only evidence-bearing bucket, scoring just above MIN_SIGNAL
    # (adj 0.2) with no grounding -> assigned (not rolled up), floored at low.
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
    assert not label.abstained
    assert label.bucket == "muscle"
    assert label.confidence == TIER_LOW_NAME


def test_convergence_cap_without_grounding_is_medium(zfa):
    # Strong panels: 3 muscle markers dominate (score -> high). No expression data
    # and no stage_hpf -> grounding/stage are NEUTRAL, so the convergence cap pulls
    # the tier down to exactly medium.
    muscle = _bs("muscle", markers=["mylpfa", "myod1", "myog"], total_weight=3.0)
    blood = _empty_bs("blood_erythroid")
    scores = [muscle, blood]
    label = decide(scores, anchors={"muscle": MUSCLE_ANCHOR}, expr_map=EMPTY_EXPR, zfa_graph=zfa, stage_hpf=None)
    assert not label.abstained
    assert label.bucket == "muscle"
    assert label.confidence == TIER_MEDIUM_NAME


def test_high_blocked_by_contradictory_grounding(zfa):
    # Strong muscle panel, but only 1 of 4 markers grounds under the muscle anchor;
    # the other 3 express under endothelial anatomy. All are on-stage at 48 hpf.
    # Grounding 0.25 (< NEUTRAL) must block high even though stage is fully
    # supportive — anatomy that contradicts the call is not "converging evidence".
    muscle = _bs("muscle", markers=["mylpfa", "acta1b", "tnnt3a", "myog"], total_weight=3.0)
    blood = _empty_bs("blood_erythroid")
    on_stage = ("Hatching:Long-pec", "Larval:Day 5")
    expr_map = {
        "mylpfa": [ZfinExpressionRecord("ZFA:0009234", "muscle cell", *on_stage)],  # under ZFA:0000548
        "acta1b": [ZfinExpressionRecord("ZFA:0005307", "endothelial cell", *on_stage)],
        "tnnt3a": [ZfinExpressionRecord("ZFA:0005307", "endothelial cell", *on_stage)],
        "myog": [ZfinExpressionRecord("ZFA:0005307", "endothelial cell", *on_stage)],
    }
    label = decide([muscle, blood], anchors={"muscle": MUSCLE_ANCHOR}, expr_map=expr_map, zfa_graph=zfa, stage_hpf=48.0)
    assert not label.abstained
    assert label.bucket == "muscle"
    assert label.confidence_components["grounding"] == 0.25
    assert label.confidence_components["stage"] == 1.0
    assert label.confidence == TIER_MEDIUM_NAME  # contradictory anatomy caps high -> medium


# ---------------------------------------------------------------------------
# Labeler smoke test (end-to-end over fixture files)
# ---------------------------------------------------------------------------


def test_labeler_smoke_muscle_cluster():
    """Full path: normalize (mylz2 -> mylpfa via GAF), score, ground, name from ZFA."""
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
    # The convergence vote names the most specific ZFA term: mylpfa + acta1b + myog
    # all express under ZFA:0009234 (muscle cell), which has higher IC than
    # musculature system and clears CONVERGENCE_MIN=3.
    assert label.bucket == "muscle cell"
    assert label.panel_bucket == "muscle"  # coarse prior is still visible
    assert label.zfa_id == "ZFA:0009234"
    assert label.next_step == "subcluster"
    assert label.depth >= 1
    assert len(label.levels) == label.depth
    # Convergent genes are the three that co-expressed in muscle cell.
    assert set(label.convergent_genes) == {"mylpfa", "acta1b", "myog"}
    # mylz2 normalized to mylpfa via the GAF synonym map before scoring.
    assert "mylpfa" in label.positive_markers
    # Expression evidence: markers expressing at/under the named ZFA term.
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
