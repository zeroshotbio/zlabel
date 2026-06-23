"""Unit tests for zlabel.resolve — build_information_content and resolve_label (the anchor-rooted namer).

Two sets of tests:
  1. build_information_content: background model properties (monotonicity, root=0, absent-id safety,
     specific numeric values on the 7-gene test fixture).
  2. resolve_label: the keystone worked examples — muscle anchor -> muscle cell, endothelium anchor
     -> endothelial cell (descend from the panel anchor) — plus the edge cases: the support floor
     stopping a thin child, an unsupported anchor, stoplisted/absent anchors, determinism, empty input.
"""

from __future__ import annotations

import math

import pytest

from zlabel.data import ZfinExpressionRecord
from zlabel.resolve import (
    STOPLIST,
    build_information_content,
    build_marker_specificity,
    resolve_label,
)

# The zfa_ontology, expression_map, and information_content fixtures are shared via tests/conftest.py.

MUSCLE_ANCHOR = frozenset({"ZFA:0000548"})  # musculature system
ENDOTHELIUM_ANCHOR = frozenset({"ZFA:0001262"})  # cardiovascular system


def _rec(zfa_id: str, zfa_name: str) -> ZfinExpressionRecord:
    return ZfinExpressionRecord(zfa_id=zfa_id, zfa_name=zfa_name, start_stage="s", end_stage="e")


# ---------------------------------------------------------------------------
# build_information_content
# ---------------------------------------------------------------------------


def test_build_information_content_empty_corpus(zfa_ontology):
    assert build_information_content({}, zfa_ontology) == {}


# ---------------------------------------------------------------------------
# build_marker_specificity (the panel-IDF signal for label.decide's specificity rescue)
# ---------------------------------------------------------------------------


def test_build_marker_specificity_single_anchor_gene(expression_map, zfa_ontology):
    # With two disjoint identity anchors, each gene grounds under exactly one of them ->
    # idf 1.0, maximally lineage-specific.
    anchors = [frozenset({"ZFA:0000548"}), frozenset({"ZFA:0005307"})]
    idf = build_marker_specificity(expression_map, anchors, zfa_ontology)
    assert idf["mylpfa"] == 1.0  # grounds only under musculature system
    assert idf["kdrl"] == 1.0  # grounds only under endothelial cell


def test_build_marker_specificity_counts_every_grounded_anchor(expression_map, zfa_ontology):
    # idf = 1 / (#identity anchors the gene grounds under). mylpfa expresses in muscle cell
    # (ZFA:0009234), so it grounds under BOTH muscle cell and its ancestor musculature system;
    # with both as separate anchors (+ a disjoint endothelial one) it grounds under 2 of 3 -> 1/2.
    # myod1 expresses only in musculature system (no subterm), so it grounds under 1 of 3 -> 1.0.
    anchors = [frozenset({"ZFA:0000548"}), frozenset({"ZFA:0009234"}), frozenset({"ZFA:0005307"})]
    idf = build_marker_specificity(expression_map, anchors, zfa_ontology)
    assert idf["mylpfa"] == pytest.approx(1 / 2)
    assert idf["myod1"] == 1.0


def test_build_information_content_descendant_ic_ge_ancestor(information_content):
    # A child term is credited by a subset of the genes that credit its parent,
    # so IC(child) >= IC(parent) always holds.
    # muscle cell (ZFA:0009234) is part_of musculature system (ZFA:0000548)
    information_content_muscle_cell = information_content.get("ZFA:0009234", 0.0)
    information_content_musculature_system = information_content.get("ZFA:0000548", 0.0)
    assert information_content_muscle_cell >= information_content_musculature_system, (
        f"IC(muscle cell)={information_content_muscle_cell:.3f} < "
        f"IC(musculature system)={information_content_musculature_system:.3f}"
    )
    # endothelial cell (ZFA:0005307) is part_of cardiovascular system (ZFA:0001262)
    information_content_endothelial_cell = information_content.get("ZFA:0005307", 0.0)
    information_content_cardiovascular_system = information_content.get("ZFA:0001262", 0.0)
    assert information_content_endothelial_cell >= information_content_cardiovascular_system, (
        f"IC(endothelial cell)={information_content_endothelial_cell:.3f} < "
        f"IC(cardiovascular system)={information_content_cardiovascular_system:.3f}"
    )


def test_build_information_content_root_is_zero(information_content):
    # ZFA:0001094 (whole organism) is credited by every gene in the corpus.
    # IC = -log2(n/n) = 0.
    assert information_content.get("ZFA:0001094", 0.0) == pytest.approx(0.0, abs=1e-9)


def test_build_information_content_absent_zfa_id_no_crash(zfa_ontology):
    # A gene with a record pointing at an id absent from the graph is credited
    # for itself only (no ancestor walk). build_information_content must not raise.
    phantom_expr = {"gene_x": [_rec("ZFA:9999999", "phantom term")]}
    result = build_information_content(phantom_expr, zfa_ontology)
    # The absent id gets self-credit: 1/1 gene -> IC = -log2(1) = 0.
    assert "ZFA:9999999" in result
    assert result["ZFA:9999999"] == pytest.approx(0.0, abs=1e-9)


def test_build_information_content_specific_value_muscle_cell(information_content):
    # 7 genes total; ZFA:0009234 (muscle cell) is credited by 3 of them
    # (mylpfa, acta1b, myog). IC = -log2(3/7).
    expected = -math.log2(3 / 7)
    assert information_content.get("ZFA:0009234", 0.0) == pytest.approx(expected, rel=1e-6)


# ---------------------------------------------------------------------------
# resolve_label — worked examples (descend from the panel anchor)
# ---------------------------------------------------------------------------


def test_resolve_label_muscle_markers_name_muscle_cell(expression_map, zfa_ontology, information_content):
    # Descend from the muscle anchor (musculature system, 4 genes) into muscle cell: 3 of the 4
    # markers credit muscle cell -- a clear majority of the anchor's support -- so the walk steps
    # down to it and stops (no supported child below). The named terminal is muscle cell.
    votes = resolve_label(
        ["mylpfa", "myod1", "acta1b", "myog"],
        expression_map=expression_map,
        zfa_ontology=zfa_ontology,
        information_content=information_content,
        anchor=MUSCLE_ANCHOR,
    )
    assert len(votes) == 1, "the descent names a single terminal term"
    top = votes[0]
    assert top.zfa_id == "ZFA:0009234"
    assert top.zfa_name == "muscle cell"
    assert set(top.genes) == {"mylpfa", "acta1b", "myog"}
    assert top.ancestor_depth >= 1


def test_resolve_label_endothelium_names_endothelial_cell(expression_map, zfa_ontology, information_content):
    # Descend from the endothelium anchor (cardiovascular system) into endothelial cell: all three
    # markers credit endothelial cell, which has no supported child below it, so the walk stops there.
    votes = resolve_label(
        ["kdrl", "cdh5", "flt1"],
        expression_map=expression_map,
        zfa_ontology=zfa_ontology,
        information_content=information_content,
        anchor=ENDOTHELIUM_ANCHOR,
    )
    assert len(votes) == 1
    assert votes[0].zfa_id == "ZFA:0005307"
    assert votes[0].zfa_name == "endothelial cell"


# ---------------------------------------------------------------------------
# resolve_label — descent floor and edge cases
# ---------------------------------------------------------------------------


def test_resolve_label_descent_stops_at_anchor_when_child_thin(zfa_ontology):
    # The overcall fix: the anchor (cardiovascular system) is well-supported (4 genes), but its only
    # in-tally child endothelial cell carries just 1 gene -- below CONVERGENCE_MIN and the support
    # floor. The descent must STOP at the anchor rather than overcall the thin child.
    expr = {
        "a": [_rec("ZFA:0001262", "cardiovascular system")],
        "b": [_rec("ZFA:0001262", "cardiovascular system")],
        "c": [_rec("ZFA:0001262", "cardiovascular system")],
        "d": [_rec("ZFA:0005307", "endothelial cell")],  # the lone, thin child
    }
    fresh_ic = build_information_content(expr, zfa_ontology)
    votes = resolve_label(
        ["a", "b", "c", "d"],
        expression_map=expr,
        zfa_ontology=zfa_ontology,
        information_content=fresh_ic,
        anchor=ENDOTHELIUM_ANCHOR,
    )
    assert len(votes) == 1
    assert votes[0].zfa_id == "ZFA:0001262", "should stop at the anchor, not overcall the 1-gene child"


def test_resolve_label_support_tie_stops_at_parent(zfa_ontology):
    # The unique-winner stop: when the markers spread equally across sibling subtypes, the descent
    # stops at the parent rather than picking one arbitrarily. Three genes each express in BOTH
    # arterial and venous endothelial cell, so the two siblings tie at 3 -- each clears the support
    # floor (>= 0.6 of endothelial cell's 3), so it is the TIE, not the floor, that halts the walk.
    expr = {
        gene: [_rec("ZFA:0009073", "arterial endothelial cell"), _rec("ZFA:0005304", "venous endothelial cell")]
        for gene in ("a", "b", "c")
    }
    fresh_ic = build_information_content(expr, zfa_ontology)
    votes = resolve_label(
        ["a", "b", "c"],
        expression_map=expr,
        zfa_ontology=zfa_ontology,
        information_content=fresh_ic,
        anchor=ENDOTHELIUM_ANCHOR,
    )
    assert len(votes) == 1
    assert votes[0].zfa_id == "ZFA:0005307", "tied siblings -> stop at endothelial cell, not a subtype"


def test_resolve_label_unsupported_anchor_returns_empty(expression_map, zfa_ontology, information_content):
    # 2 muscle genes -> the muscle anchor has only 2 supporting genes, below CONVERGENCE_MIN=3, so no
    # descent seed exists: the cluster does not converge under this panel and we fall back (empty).
    votes = resolve_label(
        ["mylpfa", "acta1b"],
        expression_map=expression_map,
        zfa_ontology=zfa_ontology,
        information_content=information_content,
        anchor=MUSCLE_ANCHOR,
    )
    assert votes == []


def test_resolve_label_no_anchor_returns_empty(expression_map, zfa_ontology, information_content):
    # With no anchor there is no descent root, so strong convergence still names nothing.
    votes = resolve_label(
        ["mylpfa", "myod1", "acta1b", "myog"],
        expression_map=expression_map,
        zfa_ontology=zfa_ontology,
        information_content=information_content,
    )
    assert votes == []


def test_resolve_label_stoplist_anchor_not_seeded(zfa_ontology):
    # ZFA:0001094 (whole organism) is in STOPLIST. Even as a well-supported anchor it is never seeded,
    # so the descent finds no root and returns empty.
    stoplist_id = "ZFA:0001094"
    assert stoplist_id in STOPLIST
    expr = {gene: [_rec(stoplist_id, "whole organism")] for gene in ("ga", "gb", "gc")}
    forced_ic = {stoplist_id: 5.0}
    votes = resolve_label(
        ["ga", "gb", "gc"],
        expression_map=expr,
        zfa_ontology=zfa_ontology,
        information_content=forced_ic,
        anchor=frozenset({stoplist_id}),
    )
    assert votes == []


def test_resolve_label_absent_anchor_no_crash(zfa_ontology):
    # An anchor id absent from the loaded graph is not a valid seed; the descent returns empty
    # without crashing (no child walk is attempted on an absent node).
    phantom = {gene: [_rec("ZFA:9999999", "ghost")] for gene in ("g1", "g2", "g3")}
    fresh_ic = build_information_content(phantom, zfa_ontology)
    votes = resolve_label(
        ["g1", "g2", "g3"],
        expression_map=phantom,
        zfa_ontology=zfa_ontology,
        information_content=fresh_ic,
        anchor=frozenset({"ZFA:9999999"}),
    )
    assert votes == []


def test_resolve_label_empty_symbols(expression_map, zfa_ontology, information_content):
    assert (
        resolve_label(
            [],
            expression_map=expression_map,
            zfa_ontology=zfa_ontology,
            information_content=information_content,
            anchor=MUSCLE_ANCHOR,
        )
        == []
    )


def test_resolve_label_deterministic(expression_map, zfa_ontology, information_content):
    # Two identical calls must return the same single terminal.
    symbols = ["kdrl", "cdh5", "flt1"]
    first = resolve_label(
        symbols,
        expression_map=expression_map,
        zfa_ontology=zfa_ontology,
        information_content=information_content,
        anchor=ENDOTHELIUM_ANCHOR,
    )
    second = resolve_label(
        symbols,
        expression_map=expression_map,
        zfa_ontology=zfa_ontology,
        information_content=information_content,
        anchor=ENDOTHELIUM_ANCHOR,
    )
    assert first == second
