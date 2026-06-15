"""Unit tests for the introspection trace: label.trace() and Labeler.trace().

Three sets of tests:
  1. Faithfulness + structure of the module-level trace() over hand-built scores
     (the embedded Label equals decide(); normalized markers and panel ladder
     are populated).
  2. The decision branch recorded for each ladder path.
  3. The convergence-vote gate table (eligible terms and near-misses), plus the
     end-to-end Labeler.trace() smoke over the committed fixtures.
"""

from __future__ import annotations

import math
from pathlib import Path

import yaml

from zlabel.genes import STATUS_AMBIGUOUS, STATUS_RESOLVED, STATUS_UNRESOLVED, NormalizedSymbol
from zlabel.label import Labeler, decide, trace
from zlabel.panels import KIND_IDENTITY, BucketScore, MatchedMarker

FIXTURES = Path(__file__).parent / "fixtures"

MUSCLE_ANCHOR: frozenset[str] = frozenset({"ZFA:0000548"})
BLOOD_ANCHOR: frozenset[str] = frozenset({"ZFA:0000007"})


# ---------------------------------------------------------------------------
# Helpers (mirror tests/test_label.py)
# ---------------------------------------------------------------------------


def _mm(symbol: str, rank: int) -> MatchedMarker:
    return MatchedMarker(input=symbol, symbol=symbol, rank=rank, weight=1.0 / math.log2(rank + 1))


def _bucket(
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
    return BucketScore(
        bucket=bucket,
        score=hit_weight / total_weight if total_weight > 0 else 0.0,
        germ_layer=germ_layer,
        tissue=tissue,
        lineage=lineage,
        kind=kind,
        matched_markers=matched,
        total_weight=total_weight,
    )


def _empty_bucket(bucket: str, *, kind: str = KIND_IDENTITY, germ_layer: str = "mesoderm") -> BucketScore:
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


def _norm(symbol: str, *, status: str = STATUS_RESOLVED, symbols: tuple[str, ...] | None = None) -> NormalizedSymbol:
    resolved_to = symbols if symbols is not None else ((symbol,) if status == STATUS_RESOLVED else ())
    return NormalizedSymbol(input=symbol, status=status, symbols=frozenset(resolved_to), note=None)


# ---------------------------------------------------------------------------
# Faithfulness + structure
# ---------------------------------------------------------------------------


def test_trace_label_equals_decide(zfa_ontology, expression_map, information_content):
    # The embedded Label must be identical to a direct decide() over the same inputs.
    muscle = _bucket("muscle", markers=["mylpfa", "acta1b", "myog"], total_weight=3.0)
    blood = _empty_bucket("blood_erythroid")
    normalized = [_norm("mylpfa"), _norm("acta1b"), _norm("myog")]
    symbols = ["mylpfa", "acta1b", "myog"]
    kwargs = dict(
        anchors={"muscle": MUSCLE_ANCHOR},
        expression_map=expression_map,
        zfa_ontology=zfa_ontology,
        stage_hpf=None,
        symbols=symbols,
        information_content=information_content,
    )
    label = decide([muscle, blood], **kwargs)  # type: ignore[arg-type]
    result = trace([muscle, blood], normalized, **kwargs)  # type: ignore[arg-type]
    assert result.label == label  # faithfulness invariant
    assert result.label.bucket == "muscle cell"


def test_trace_records_clear_winner_branch_and_ladder(zfa_ontology, expression_map, information_content):
    muscle = _bucket("muscle", markers=["mylpfa", "acta1b", "myog"], total_weight=3.0)
    blood = _empty_bucket("blood_erythroid")
    normalized = [_norm("mylpfa"), _norm("acta1b"), _norm("myog")]
    result = trace(
        [muscle, blood],
        normalized,
        anchors={"muscle": MUSCLE_ANCHOR},
        expression_map=expression_map,
        zfa_ontology=zfa_ontology,
        stage_hpf=None,
        symbols=["mylpfa", "acta1b", "myog"],
        information_content=information_content,
    )
    assert result.branch == "clear-winner"
    assert result.markers_in == ("mylpfa", "acta1b", "myog")
    assert result.resolved_symbols == ("mylpfa", "acta1b", "myog")
    # The panel ladder marks exactly one winner: muscle.
    winners = [b for b in result.panel_scores if b.is_winner]
    assert [b.bucket for b in winners] == ["muscle"]
    assert winners[0].adjusted_score > 0.0


def test_trace_flags_dropped_markers(zfa_ontology, expression_map, information_content):
    # Unresolved and ambiguous markers are surfaced as dropped, with their input rank.
    muscle = _bucket("muscle", markers=["mylpfa", "acta1b", "myog"], total_weight=3.0)
    normalized = [
        _norm("mylpfa"),
        _norm("acta1b"),
        _norm("myog"),
        _norm("zzz", status=STATUS_UNRESOLVED),
        _norm("hbae1", status=STATUS_AMBIGUOUS, symbols=("hbae1.1", "hbae1.2")),
    ]
    result = trace(
        [muscle],
        normalized,
        anchors={"muscle": MUSCLE_ANCHOR},
        expression_map=expression_map,
        zfa_ontology=zfa_ontology,
        stage_hpf=None,
        symbols=["mylpfa", "acta1b", "myog"],
        information_content=information_content,
    )
    by_input = {nm.input: nm for nm in result.normalized_markers}
    assert by_input["zzz"].dropped is True
    assert by_input["hbae1"].dropped is True
    assert by_input["hbae1"].symbols == ("hbae1.1", "hbae1.2")  # sorted, both paralogs kept
    assert by_input["mylpfa"].dropped is False
    assert by_input["zzz"].rank == 4  # 1-based input position preserved


# ---------------------------------------------------------------------------
# Decision branch per ladder path
# ---------------------------------------------------------------------------


def _trace_branch(scores, normalized, zfa_ontology, *, anchors=None):
    return trace(
        scores,
        normalized,
        anchors=anchors if anchors is not None else {},
        expression_map={},
        zfa_ontology=zfa_ontology,
        stage_hpf=None,
        symbols=None,
        information_content=None,
    )


def test_branch_precheck_a_no_identity(zfa_ontology):
    scores = [_empty_bucket("muscle"), _empty_bucket("blood_erythroid")]
    result = _trace_branch(scores, [_norm("zzz", status=STATUS_UNRESOLVED)], zfa_ontology)
    assert result.branch == "precheck-a-no-identity"
    assert result.label.abstained
    assert result.term_votes == ()  # convergence vote not run on the precheck branch


def test_branch_precheck_b_weak_signal(zfa_ontology):
    muscle = BucketScore(
        bucket="muscle",
        score=0.01,
        germ_layer="mesoderm",
        tissue="muscle",
        lineage="skeletal muscle",
        kind=KIND_IDENTITY,
        matched_markers=(_mm("myod1", 1),),
        total_weight=10.0,  # huge denominator -> adj below MIN_SIGNAL
    )
    result = _trace_branch([muscle], [_norm("myod1")], zfa_ontology)
    assert result.branch == "precheck-b-weak-signal"
    assert result.label.abstained
    assert result.term_votes == ()  # convergence vote not run on the precheck branch


def test_branch_rollup_marks_contenders(zfa_ontology):
    muscle = _bucket("muscle", germ_layer="mesoderm", markers=["myod1", "myog"], total_weight=3.0)
    blood = _bucket(
        "blood_erythroid",
        germ_layer="mesoderm",
        tissue="blood",
        lineage="erythroid",
        markers=["gata1a", "hbae1.1"],
        total_weight=3.0,
    )
    result = _trace_branch(
        [muscle, blood],
        [_norm("myod1"), _norm("myog"), _norm("gata1a"), _norm("hbae1.1")],
        zfa_ontology,
        anchors={"muscle": MUSCLE_ANCHOR, "blood_erythroid": BLOOD_ANCHOR},
    )
    assert result.branch == "germ-layer-rollup"
    contenders = {b.bucket for b in result.panel_scores if b.is_contender}
    assert contenders == {"muscle", "blood_erythroid"}
    assert result.term_votes == ()  # rollup does not run the convergence vote


def test_branch_mixed_contradictory_germ_layers(zfa_ontology):
    neural = _bucket(
        "neural",
        germ_layer="ectoderm",
        tissue="nervous system",
        lineage="neural",
        markers=["elavl3", "neurod1"],
        total_weight=3.0,
    )
    blood = _bucket(
        "blood_erythroid",
        germ_layer="mesoderm",
        tissue="blood",
        lineage="erythroid",
        markers=["gata1a", "hbae1.1"],
        total_weight=3.0,
    )
    result = _trace_branch(
        [neural, blood], [_norm("elavl3"), _norm("neurod1"), _norm("gata1a"), _norm("hbae1.1")], zfa_ontology
    )
    assert result.branch == "mixed-abstain"
    assert result.label.abstained


# ---------------------------------------------------------------------------
# Convergence-vote gate table (the "why" data, including near-misses)
# ---------------------------------------------------------------------------


def test_trace_gate_table_includes_near_misses(zfa_ontology, expression_map, information_content):
    muscle = _bucket("muscle", markers=["mylpfa", "acta1b", "myog"], total_weight=3.0)
    normalized = [_norm("mylpfa"), _norm("acta1b"), _norm("myog")]
    result = trace(
        [muscle],
        normalized,
        anchors={"muscle": MUSCLE_ANCHOR},
        expression_map=expression_map,
        zfa_ontology=zfa_ontology,
        stage_hpf=None,
        symbols=["mylpfa", "acta1b", "myog"],
        information_content=information_content,
    )
    votes = {tv.zfa_id: tv for tv in result.term_votes}

    # Selected term: muscle cell, eligible, grounded under the muscle anchor.
    selected = votes["ZFA:0009234"]
    assert selected.selected is True
    assert selected.eligible is True
    assert selected.grounded_under_anchor is True
    assert selected.gene_count == 3
    assert sum(tv.selected for tv in result.term_votes) == 1  # exactly one selected

    # Near-miss: musculature system has enough genes but fails the IC gate.
    musculature = votes["ZFA:0000548"]
    assert musculature.passed_convergence is True
    assert musculature.passed_information_content is False
    assert musculature.eligible is False
    assert musculature.selected is False

    # Near-miss: whole organism is tallied but fails the stoplist gate.
    assert votes["ZFA:0001094"].passed_stoplist is False

    # Eligible terms are ordered before near-misses.
    eligible_idx = [i for i, tv in enumerate(result.term_votes) if tv.eligible]
    near_idx = [i for i, tv in enumerate(result.term_votes) if not tv.eligible]
    assert eligible_idx and near_idx
    assert max(eligible_idx) < min(near_idx)


def test_trace_no_selected_term_when_below_convergence_min(zfa_ontology, expression_map, information_content):
    # Two muscle markers: below CONVERGENCE_MIN, so no ZFA term is eligible. The engine
    # still clears MIN_SIGNAL, so it does NOT abstain -- it falls back to the panel bucket.
    # The gate table records the near-miss with passed_convergence False.
    muscle = _bucket("muscle", markers=["mylpfa", "acta1b"], total_weight=2.0)
    result = trace(
        [muscle],
        [_norm("mylpfa"), _norm("acta1b")],
        anchors={"muscle": MUSCLE_ANCHOR},
        expression_map=expression_map,
        zfa_ontology=zfa_ontology,
        stage_hpf=None,
        symbols=["mylpfa", "acta1b"],
        information_content=information_content,
    )
    assert all(not tv.selected for tv in result.term_votes)
    assert result.label.abstained is False  # falls back to the panel bucket, not an abstention
    assert result.label.bucket == "muscle"  # coarse panel fallback
    muscle_cell = {tv.zfa_id: tv for tv in result.term_votes}.get("ZFA:0009234")
    assert muscle_cell is not None
    assert muscle_cell.passed_convergence is False  # 2 genes < CONVERGENCE_MIN


# ---------------------------------------------------------------------------
# Labeler.trace() end to end over the committed fixtures
# ---------------------------------------------------------------------------


def _fixture_labeler() -> Labeler:
    return Labeler(
        stage_hpf=48.0,
        zfa_path=FIXTURES / "zfa_test.obo",
        expr_path=FIXTURES / "zfin_expr_test.txt",
        gaf_path=FIXTURES / "zfin_go_test.gaf",
        panels_path=FIXTURES / "panels_test.yaml",
    )


def test_labeler_trace_matches_label():
    # The faithfulness invariant, end to end: the embedded Label is exactly what
    # lab.label() returns for the same markers.
    lab = _fixture_labeler()
    markers = ["mylz2", "acta1b", "tnnt3a", "myod1", "myog"]
    result = lab.trace(markers)
    assert result.label == lab.label(markers)
    assert result.branch == "clear-winner"
    assert result.markers_in == tuple(markers)


def test_labeler_trace_surfaces_normalization_and_vote():
    lab = _fixture_labeler()
    result = lab.trace(["mylz2", "acta1b", "tnnt3a", "myod1", "myog"])
    by_input = {nm.input: nm for nm in result.normalized_markers}
    # mylz2 normalizes to mylpfa via the GAF synonym map (resolved, not dropped).
    assert by_input["mylz2"].symbols == ("mylpfa",)
    assert by_input["mylz2"].dropped is False
    # The selected term is muscle cell; tnnt3a has no expression record so it
    # never becomes a convergent gene.
    selected = [tv for tv in result.term_votes if tv.selected]
    assert [tv.zfa_id for tv in selected] == ["ZFA:0009234"]
    assert "tnnt3a" not in selected[0].genes


def test_labeler_trace_to_yaml_round_trips():
    lab = _fixture_labeler()
    raw = yaml.safe_load(lab.trace(["mylz2", "acta1b", "myog"]).to_yaml())
    assert raw["branch"] == "clear-winner"
    assert raw["label"]["bucket"] == "muscle cell"
    assert raw["term_votes"][0]["zfa_id"]  # at least one vote captured
