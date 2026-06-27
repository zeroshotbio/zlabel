"""Unit tests for the Phase 4b evaluation harness and the benchmark builder transforms.

Three groups:
  1. Builder pure transforms (representative stage, marker selection, row assembly) -- the
     scanpy/IO path is a one-off and not unit-tested.
  2. evaluate.py scoring: the fail-closed crosswalk, the tally replay pinned against
     resolve_label, the parent-child overcall audit, and an end-to-end evaluate() pass.
"""

import dataclasses
from pathlib import Path

import build_daniocell_eval as build_eval
import pytest

from zlabel import Label, evaluate
from zlabel.resolve import resolve_label

REPO = Path(__file__).parent.parent
FIXTURES = Path(__file__).parent / "fixtures"

MUSCLE_MARKERS = ["mylz2", "acta1b", "tnnt3a", "myod1", "myog"]
MUSCLE_SYMBOLS = ["mylpfa", "acta1b", "myog"]  # the convergent subset, already current symbols


@pytest.fixture(scope="module")
def resources():
    return evaluate.load_resources(
        zfa_path=FIXTURES / "zfa_test.obo",
        expr_path=FIXTURES / "zfin_expr_test.txt",
        gaf_path=FIXTURES / "zfin_go_test.gaf",
        panels_path=FIXTURES / "panels_test.yaml",
    )


# ---------------------------------------------------------------------------
# Builder pure transforms
# ---------------------------------------------------------------------------


def test_representative_stage_mode():
    assert build_eval.representative_stage([24, 24, 24, 36]) == 24.0


def test_representative_stage_tie_uses_median():
    # 24 and 36 each appear twice (a modal tie) -> median of [24, 24, 36, 36] = 30.0.
    assert build_eval.representative_stage([24, 24, 36, 36]) == 30.0


def test_top_positive_markers_filters_negatives_and_caps():
    ranked = [("a", 2.0), ("b", -1.0), ("c", 0.5), ("d", 3.0)]
    assert build_eval.top_positive_markers(ranked, n=2) == ["a", "c"]


def test_top_positive_markers_drops_technical():
    # mito (mt-) and ribosomal (rps/rpl) genes are technical, not identity.
    ranked = [("mt-co1", 5.0), ("rps12", 4.0), ("rpl7", 3.5), ("myod1", 3.0), ("acta1b", 2.0)]
    assert build_eval.top_positive_markers(ranked, n=5) == ["myod1", "acta1b"]


def test_modal():
    assert build_eval._modal(["musc", "musc", "neur"]) == "musc"
    assert build_eval._modal([]) == ""


def test_assemble_rows_sorted_and_joined():
    markers = {"musc.2": ["a", "b"], "musc.1": ["c"]}
    cluster_metadata = {
        "musc.1": {"tissue": "musc", "tissue_name": "somites", "stage_hpf": 24.0},
        "musc.2": {"tissue": "musc", "tissue_name": "fast muscle", "stage_hpf": 36.0},
    }
    rows = build_eval.assemble_rows(markers, cluster_metadata)
    assert [row["cluster_id"] for row in rows] == ["musc.1", "musc.2"]  # sorted by cluster_id
    assert rows[1]["markers"] == "a;b"
    assert rows[0]["broad_tissue"] == "musc"
    assert rows[0]["stage_hpf"] == "24"


# ---------------------------------------------------------------------------
# Crosswalk (fail closed)
# ---------------------------------------------------------------------------


def test_load_crosswalk_real_file():
    crosswalk = evaluate.load_crosswalk(REPO / "benchmarks" / "daniocell_tissue_crosswalk.yaml")
    assert "ZFA:0000548" in (crosswalk.gold("musc") or frozenset())
    assert crosswalk.gold("blas") is None  # blastomeres are explicitly not_scored
    # Daniocell "axia" means notochord/prechordal plate/hatching gland. Notochord (ZFA:0000135)
    # and hatching gland (ZFA:0000026) are not reachable under axial mesoderm via is_a+part_of,
    # so each needs an explicit anchor or a legitimate axia call would not ground.
    axia = crosswalk.gold("axia") or frozenset()
    assert "ZFA:0000135" in axia  # notochord
    assert "ZFA:0000026" in axia  # hatching gland


def test_crosswalk_fails_closed_on_unknown_tissue():
    crosswalk = evaluate.Crosswalk(anchors={"musc": frozenset({"ZFA:0000548"})}, not_scored=frozenset())
    with pytest.raises(KeyError):
        crosswalk.gold("not_a_tissue")


# ---------------------------------------------------------------------------
# Replay tally consistency (drift guard vs resolve_label)
# ---------------------------------------------------------------------------


def test_replay_tally_matches_resolve_label(zfa_ontology, expression_map, information_content):
    # The audit replays the same per-term gene tally the namer builds. Pin the named terminal's
    # gene set against the replayed tally, plus a known ancestor, so the two cannot drift.
    tally = evaluate._replay_tally(MUSCLE_SYMBOLS, expression_map, zfa_ontology)
    votes = resolve_label(
        MUSCLE_SYMBOLS,
        expression_map=expression_map,
        zfa_ontology=zfa_ontology,
        information_content=information_content,
        anchor=frozenset({"ZFA:0000548"}),  # musculature system -- the muscle panel anchor
    )
    assert votes, "muscle markers should descend to a named term under the muscle anchor"
    for vote in votes:
        assert set(tally[vote.zfa_id]) == set(vote.genes)
    # The replay credits ancestors too -- the descent and the audit share the gene-credit unit.
    assert set(tally["ZFA:0009234"]) == {"mylpfa", "acta1b", "myog"}  # muscle cell
    assert set(tally["ZFA:0000548"]) == {"mylpfa", "acta1b", "myog"}  # musculature system (ancestor credit)


# ---------------------------------------------------------------------------
# Parent-child overcall audit
# ---------------------------------------------------------------------------


def test_audit_flags_thin_support_overcall(zfa_ontology):
    # muscle cell (3 genes = CONVERGENCE_MIN) wins while its ancestor musculature system
    # has broader support (5) -> a thin-support overcall.
    tally = {"ZFA:0009234": {"g1", "g2", "g3"}, "ZFA:0000548": {"g1", "g2", "g3", "g4", "g5"}}
    record = evaluate._audit_from_tally("c1", "ZFA:0009234", "muscle cell", tally, zfa_ontology)
    assert record.named_support == 3
    assert record.parent_id == "ZFA:0000548"
    assert record.parent_support == 5
    assert record.won_at_min
    assert record.thin_support_overcall
    assert record.support_fraction == pytest.approx(0.6)


def test_audit_no_overcall_on_broad_consensus(zfa_ontology):
    # winner has 5 genes (above the minimum) -> not flagged as a thin-support overcall.
    full = {"g1", "g2", "g3", "g4", "g5"}
    tally = {"ZFA:0009234": set(full), "ZFA:0000548": set(full)}
    record = evaluate._audit_from_tally("c1", "ZFA:0009234", "muscle cell", tally, zfa_ontology)
    assert not record.won_at_min
    assert not record.thin_support_overcall


# ---------------------------------------------------------------------------
# End-to-end evaluate()
# ---------------------------------------------------------------------------


def test_evaluate_muscle_agrees_and_not_scored_excluded(resources):
    benchmark = [
        evaluate.BenchmarkRow("musc.1", MUSCLE_MARKERS, "musc", "somites", 48.0),
        evaluate.BenchmarkRow("blas.1", ["sox2"], "blas", "blastomeres", 4.0),
    ]
    crosswalk = evaluate.Crosswalk(anchors={"musc": frozenset({"ZFA:0000548"})}, not_scored=frozenset({"blas"}))
    report = evaluate.evaluate(benchmark, crosswalk, resources)
    assert report.total == 2
    assert report.not_scored == 1  # blas is not_scored: labeled, but excluded from report counts and agreement
    assert report.counts[evaluate.NAMED] == 1
    assert report.correct[evaluate.NAMED] == 1  # muscle cell grounds under musculature system
    assert len(report.audits) == 1
    rendered = evaluate.render_report(report)
    assert "Broad agreement" in rendered
    assert "overcall audit" in rendered


def test_cluster_outcomes_named_agrees_with_audit(resources):
    bench = [evaluate.BenchmarkRow("musc.1", MUSCLE_MARKERS, "musc", "somites", 48.0)]
    crosswalk = evaluate.Crosswalk(anchors={"musc": frozenset({"ZFA:0000548"})}, not_scored=frozenset())
    outcome = evaluate.cluster_outcomes(bench, crosswalk, resources)[0]
    assert outcome.kind == evaluate.NAMED
    assert outcome.scored is True
    assert outcome.agrees is True
    assert outcome.audit is not None
    assert outcome.abstain_reason is None
    assert set(outcome.convergent_genes) == {"mylpfa", "acta1b", "myog"}


def test_cluster_outcomes_abstain_reason_no_panel(resources):
    # empty markers -> no panel hit -> abstain with abstain_reason "no_panel".
    bench = [evaluate.BenchmarkRow("empty.1", [], "musc", "somites", 48.0)]
    crosswalk = evaluate.Crosswalk(anchors={"musc": frozenset({"ZFA:0000548"})}, not_scored=frozenset())
    outcome = evaluate.cluster_outcomes(bench, crosswalk, resources)[0]
    assert outcome.kind == evaluate.ABSTAIN
    assert outcome.abstain_reason == "no_panel"
    assert outcome.agrees is None


def test_label_row_forwards_specificity_blend(resources):
    # The evaluator must forward Resources.alpha + marker_specificity into the scorer.
    # mylpfa+acta1b (ranks 1-2) hit muscle; kdrl (rank 3) hits endothelium. At alpha=0
    # muscle wins outright on rank. With a crafted specificity that makes the muscle
    # markers promiscuous and kdrl sharp, alpha=1 flips the clear call to endothelium --
    # which only happens if alpha actually reaches score_markers through _label_row.
    row = evaluate.BenchmarkRow("x.1", ["mylpfa", "acta1b", "kdrl"], "musc", "somites", 48.0)
    spec = {"mylpfa": 0.05, "acta1b": 0.05, "kdrl": 1.0}

    label_zero, _ = evaluate._label_row(row, dataclasses.replace(resources, alpha=0.0, marker_specificity=spec))
    label_one, _ = evaluate._label_row(row, dataclasses.replace(resources, alpha=1.0, marker_specificity=spec))

    assert label_zero.panel_bucket == "muscle"
    assert label_one.panel_bucket == "endothelium"


# ---------------------------------------------------------------------------
# Fallback anchor recovery (multi-anchor panels)
# ---------------------------------------------------------------------------


def _fallback_label(panel_bucket: str, zfa_id: str) -> Label:
    """A minimal non-abstained fallback Label (only panel_bucket and zfa_id matter here)."""
    return Label(
        bucket=panel_bucket,
        levels=(panel_bucket,),
        depth=1,
        abstained=False,
        confidence="low",
        confidence_score=0.5,
        confidence_components={"coherence": 0.5, "margin": 0.5, "grounding": 0.5, "stage": 0.5},
        ambiguity_flag="none",
        states=(),
        panel_bucket=panel_bucket,
        panel_germ_layer="",
        zfa_id=zfa_id,
        panel_scores={},
        positive_markers=(),
        convergent_genes=(),
        expression_evidence=(),
        rationale="fallback",
        next_step="subcluster",
    )


def test_prediction_anchor_ids_fallback_uses_full_panel_anchor(resources):
    # A fallback prediction is scored against the panel's FULL ontology_anchor (recovered from
    # panel_bucket), not the single truncated anchor kept on Label.zfa_id -- this is what keeps
    # the real multi-anchor panels from undercounting agreement.
    two_anchor = dataclasses.replace(resources, anchors={"endo": frozenset({"ZFA:0005307", "ZFA:0009618"})})
    label = _fallback_label(panel_bucket="endo", zfa_id="ZFA:0005307")  # zfa_id holds only one
    anchor_ids = evaluate._prediction_anchor_ids(label, evaluate.FALLBACK, two_anchor)
    assert anchor_ids == frozenset({"ZFA:0005307", "ZFA:0009618"})
