"""Unit tests for the Phase 4b evaluation harness and the benchmark builder transforms.

Three groups:
  1. Builder pure transforms (representative stage, marker selection, row assembly) -- the
     scanpy/IO path is a one-off and not unit-tested.
  2. evaluate.py scoring: the fail-closed crosswalk, the tally replay pinned against
     resolve_label, the parent-child overcall audit, and an end-to-end evaluate() pass.
"""

from pathlib import Path

import build_daniocell_eval as bd
import pytest

from zlabel import evaluate as ev
from zlabel.resolve import CONVERGENCE_MIN, IC_MIN, STOPLIST, resolve_label

REPO = Path(__file__).parent.parent
FIXTURES = Path(__file__).parent / "fixtures"

MUSCLE_MARKERS = ["mylz2", "acta1b", "tnnt3a", "myod1", "myog"]
MUSCLE_SYMBOLS = ["mylpfa", "acta1b", "myog"]  # the convergent subset, already current symbols


@pytest.fixture(scope="module")
def res():
    return ev.load_resources(
        zfa_path=FIXTURES / "zfa_test.obo",
        expr_path=FIXTURES / "zfin_expr_test.txt",
        gaf_path=FIXTURES / "zfin_go_test.gaf",
        panels_path=FIXTURES / "panels_test.yaml",
    )


# ---------------------------------------------------------------------------
# Builder pure transforms
# ---------------------------------------------------------------------------


def test_representative_stage_mode():
    assert bd.representative_stage([24, 24, 24, 36]) == 24.0


def test_representative_stage_tie_uses_median():
    # 24 and 36 each appear twice (a modal tie) -> median of [24, 24, 36, 36] = 30.0.
    assert bd.representative_stage([24, 24, 36, 36]) == 30.0


def test_top_positive_markers_filters_negatives_and_caps():
    ranked = [("a", 2.0), ("b", -1.0), ("c", 0.5), ("d", 3.0)]
    assert bd.top_positive_markers(ranked, n=2) == ["a", "c"]


def test_top_positive_markers_drops_technical():
    # mito (mt-) and ribosomal (rps/rpl) genes are technical, not identity.
    ranked = [("mt-co1", 5.0), ("rps12", 4.0), ("rpl7", 3.5), ("myod1", 3.0), ("acta1b", 2.0)]
    assert bd.top_positive_markers(ranked, n=5) == ["myod1", "acta1b"]


def test_modal():
    assert bd._modal(["musc", "musc", "neur"]) == "musc"
    assert bd._modal([]) == ""


def test_assemble_rows_sorted_and_joined():
    markers = {"musc.2": ["a", "b"], "musc.1": ["c"]}
    per = {
        "musc.1": {"tissue": "musc", "tissue_name": "somites", "stage_hpf": 24.0},
        "musc.2": {"tissue": "musc", "tissue_name": "fast muscle", "stage_hpf": 36.0},
    }
    rows = bd.assemble_rows(markers, per)
    assert [r["cluster_id"] for r in rows] == ["musc.1", "musc.2"]  # sorted by cluster_id
    assert rows[1]["markers"] == "a;b"
    assert rows[0]["broad_tissue"] == "musc"
    assert rows[0]["stage_hpf"] == "24"


# ---------------------------------------------------------------------------
# Crosswalk (fail closed)
# ---------------------------------------------------------------------------


def test_load_crosswalk_real_file():
    xw = ev.load_crosswalk(REPO / "benchmarks" / "daniocell_tissue_crosswalk.yaml")
    assert "ZFA:0000548" in (xw.gold("musc") or frozenset())
    assert xw.gold("blas") is None  # blastomeres are explicitly not_scored


def test_crosswalk_fails_closed_on_unknown_tissue():
    xw = ev.Crosswalk(anchors={"musc": frozenset({"ZFA:0000548"})}, not_scored=frozenset())
    with pytest.raises(KeyError):
        xw.gold("not_a_tissue")


# ---------------------------------------------------------------------------
# Replay tally consistency (drift guard vs resolve_label)
# ---------------------------------------------------------------------------


def test_replay_tally_matches_resolve_label(zfa_graph, expr_map, ic):
    tally = ev._replay_tally(MUSCLE_SYMBOLS, expr_map, zfa_graph)
    votes = resolve_label(MUSCLE_SYMBOLS, expr_map=expr_map, zfa_graph=zfa_graph, ic=ic)
    assert votes, "consistency test needs at least one vote candidate to be non-vacuous"
    # every engine candidate carries the same gene set in the raw tally
    for v in votes:
        assert set(tally[v.zfa_id]) == set(v.genes)
    # and the raw tally, put through the same three gates, yields exactly the engine's ids
    gated = {
        t
        for t, genes in tally.items()
        if len(genes) >= CONVERGENCE_MIN and t not in STOPLIST and ic.get(t, 0.0) >= IC_MIN
    }
    assert gated == {v.zfa_id for v in votes}


# ---------------------------------------------------------------------------
# Parent-child overcall audit
# ---------------------------------------------------------------------------


def test_audit_flags_thin_support_overcall(zfa_graph):
    # muscle cell (3 genes = CONVERGENCE_MIN) wins while its ancestor musculature system
    # has broader support (5) -> a thin-support overcall.
    tally = {"ZFA:0009234": {"g1", "g2", "g3"}, "ZFA:0000548": {"g1", "g2", "g3", "g4", "g5"}}
    rec = ev._audit_from_tally("c1", "ZFA:0009234", "muscle cell", tally, zfa_graph)
    assert rec.named_support == 3
    assert rec.parent_id == "ZFA:0000548"
    assert rec.parent_support == 5
    assert rec.won_at_min
    assert rec.thin_support_overcall
    assert rec.support_fraction == pytest.approx(0.6)


def test_audit_no_overcall_on_broad_consensus(zfa_graph):
    # winner has 5 genes (above the minimum) -> not flagged as a thin-support overcall.
    full = {"g1", "g2", "g3", "g4", "g5"}
    tally = {"ZFA:0009234": set(full), "ZFA:0000548": set(full)}
    rec = ev._audit_from_tally("c1", "ZFA:0009234", "muscle cell", tally, zfa_graph)
    assert not rec.won_at_min
    assert not rec.thin_support_overcall


# ---------------------------------------------------------------------------
# End-to-end evaluate()
# ---------------------------------------------------------------------------


def test_evaluate_muscle_agrees_and_not_scored_excluded(res):
    benchmark = [
        ev.BenchmarkRow("musc.1", MUSCLE_MARKERS, "musc", "somites", 48.0),
        ev.BenchmarkRow("blas.1", ["sox2"], "blas", "blastomeres", 4.0),
    ]
    xw = ev.Crosswalk(anchors={"musc": frozenset({"ZFA:0000548"})}, not_scored=frozenset({"blas"}))
    rep = ev.evaluate(benchmark, xw, res)
    assert rep.total == 2
    assert rep.not_scored == 1  # blas is not_scored: labeled, but excluded from report counts and agreement
    assert rep.counts[ev.NAMED] == 1
    assert rep.correct[ev.NAMED] == 1  # muscle cell grounds under musculature system
    assert len(rep.audits) == 1
    report = ev.render_report(rep)
    assert "Broad agreement" in report
    assert "overcall audit" in report


def test_cluster_outcomes_named_agrees_with_audit(res):
    bench = [ev.BenchmarkRow("musc.1", MUSCLE_MARKERS, "musc", "somites", 48.0)]
    xw = ev.Crosswalk(anchors={"musc": frozenset({"ZFA:0000548"})}, not_scored=frozenset())
    o = ev.cluster_outcomes(bench, xw, res)[0]
    assert o.kind == ev.NAMED
    assert o.scored is True
    assert o.agrees is True
    assert o.audit is not None
    assert o.abstain_reason is None
    assert set(o.convergent_genes) == {"mylpfa", "acta1b", "myog"}


def test_cluster_outcomes_abstain_reason_no_panel(res):
    # empty markers -> no panel hit -> abstain with abstain_reason "no_panel".
    bench = [ev.BenchmarkRow("empty.1", [], "musc", "somites", 48.0)]
    xw = ev.Crosswalk(anchors={"musc": frozenset({"ZFA:0000548"})}, not_scored=frozenset())
    o = ev.cluster_outcomes(bench, xw, res)[0]
    assert o.kind == ev.ABSTAIN
    assert o.abstain_reason == "no_panel"
    assert o.agrees is None
