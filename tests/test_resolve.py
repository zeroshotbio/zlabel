"""Unit tests for zlabel.resolve — build_information_content and resolve_label (the IC-weighted namer).

Two sets of tests:
  1. build_information_content: background model properties (monotonicity, root=0, absent-id safety,
     specific numeric values on the 7-gene test fixture).
  2. resolve_label: the keystone worked examples — muscle -> muscle cell, endothelium
     -> endothelial cell (IC-first, depth tiebreak) — plus the edge cases: below
     CONVERGENCE_MIN, stoplisted terms, absent-from-graph ids, determinism, empty input.
"""

from __future__ import annotations

import math

import pytest

from zlabel.data import ZfinExpressionRecord
from zlabel.resolve import (
    INFORMATION_CONTENT_MIN,
    STOPLIST,
    build_information_content,
    resolve_label,
)

# The zfa_ontology, expression_map, and information_content fixtures are shared via tests/conftest.py.


# ---------------------------------------------------------------------------
# build_information_content
# ---------------------------------------------------------------------------


def test_build_information_content_empty_corpus(zfa_ontology):
    assert build_information_content({}, zfa_ontology) == {}


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
    phantom_expr = {
        "gene_x": [
            ZfinExpressionRecord(
                zfa_id="ZFA:9999999",
                zfa_name="phantom term",
                start_stage="x",
                end_stage="y",
            )
        ]
    }
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
# resolve_label — worked examples
# ---------------------------------------------------------------------------


def test_resolve_label_muscle_markers_name_muscle_cell(expression_map, zfa_ontology, information_content):
    # Three of the four muscle markers express in muscle cell (ZFA:0009234, IC>INFORMATION_CONTENT_MIN);
    # the broader musculature system (ZFA:0000548) has IC below INFORMATION_CONTENT_MIN in this fixture
    # and is filtered by the IC gate. Muscle cell is the sole surviving candidate.
    votes = resolve_label(
        ["mylpfa", "myod1", "acta1b", "myog"],
        expression_map=expression_map,
        zfa_ontology=zfa_ontology,
        information_content=information_content,
    )
    assert votes, "expected at least one candidate for muscle markers"
    top = votes[0]
    assert top.zfa_id == "ZFA:0009234"
    assert top.zfa_name == "muscle cell"
    assert set(top.genes) == {"mylpfa", "acta1b", "myog"}
    assert top.information_content > INFORMATION_CONTENT_MIN
    assert top.ancestor_depth >= 1


def test_resolve_label_endothelium_names_endothelial_cell_not_cardiovascular(
    expression_map, zfa_ontology, information_content
):
    # IC-first, ancestor_depth tiebreak: endothelial cell (ZFA:0005307) and
    # cardiovascular system (ZFA:0001262) tie on IC and gene count. ancestor_depth
    # breaks the tie: endothelial cell has more ancestors, so it ranks first.
    votes = resolve_label(
        ["kdrl", "cdh5", "flt1"],
        expression_map=expression_map,
        zfa_ontology=zfa_ontology,
        information_content=information_content,
    )
    assert votes, "expected candidates for endothelial markers"
    top = votes[0]
    assert top.zfa_id == "ZFA:0005307"
    assert top.zfa_name == "endothelial cell"
    assert top.information_content > INFORMATION_CONTENT_MIN
    # Cardiovascular system must appear later — ancestor_depth tiebreak proves IC-first ranking.
    ids = [vote.zfa_id for vote in votes]
    assert "ZFA:0001262" in ids
    assert ids.index("ZFA:0005307") < ids.index("ZFA:0001262")


# ---------------------------------------------------------------------------
# resolve_label — gate tests
# ---------------------------------------------------------------------------


def test_resolve_label_below_convergence_min_returns_empty(expression_map, zfa_ontology, information_content):
    # 2 muscle genes — below CONVERGENCE_MIN=3, so no term survives.
    votes = resolve_label(
        ["mylpfa", "acta1b"],
        expression_map=expression_map,
        zfa_ontology=zfa_ontology,
        information_content=information_content,
    )
    assert votes == []


def test_resolve_label_stoplist_filtered(zfa_ontology):
    # ZFA:0001094 (whole organism) is in STOPLIST. Supplying a forced-high IC
    # isolates the stoplist gate: the term must not appear even with IC >> INFORMATION_CONTENT_MIN.
    stoplist_id = "ZFA:0001094"
    assert stoplist_id in STOPLIST
    minimal_expression_map: dict[str, list[ZfinExpressionRecord]] = {
        "ga": [ZfinExpressionRecord(zfa_id=stoplist_id, zfa_name="whole organism", start_stage="s", end_stage="e")],
        "gb": [ZfinExpressionRecord(zfa_id=stoplist_id, zfa_name="whole organism", start_stage="s", end_stage="e")],
        "gc": [ZfinExpressionRecord(zfa_id=stoplist_id, zfa_name="whole organism", start_stage="s", end_stage="e")],
    }
    forced_information_content = {stoplist_id: 5.0}
    result = resolve_label(
        ["ga", "gb", "gc"],
        expression_map=minimal_expression_map,
        zfa_ontology=zfa_ontology,
        information_content=forced_information_content,
    )
    assert result == []


def test_resolve_label_absent_from_graph_no_crash(zfa_ontology):
    # A gene expressing in a ZFA id absent from the loaded graph must not crash.
    # The absent id gets no ancestor walk; its IC stays at 0.0, failing INFORMATION_CONTENT_MIN.
    phantom_expr: dict[str, list[ZfinExpressionRecord]] = {
        "g1": [ZfinExpressionRecord(zfa_id="ZFA:9999999", zfa_name="ghost", start_stage="s", end_stage="e")],
        "g2": [ZfinExpressionRecord(zfa_id="ZFA:9999999", zfa_name="ghost", start_stage="s", end_stage="e")],
        "g3": [ZfinExpressionRecord(zfa_id="ZFA:9999999", zfa_name="ghost", start_stage="s", end_stage="e")],
    }
    fresh_information_content = build_information_content(phantom_expr, zfa_ontology)
    result = resolve_label(
        ["g1", "g2", "g3"],
        expression_map=phantom_expr,
        zfa_ontology=zfa_ontology,
        information_content=fresh_information_content,
    )
    assert isinstance(result, list)
    assert result == []  # IC(ZFA:9999999) = 0.0 < INFORMATION_CONTENT_MIN


def test_resolve_label_empty_symbols(expression_map, zfa_ontology, information_content):
    assert (
        resolve_label(
            [], expression_map=expression_map, zfa_ontology=zfa_ontology, information_content=information_content
        )
        == []
    )


def test_resolve_label_deterministic(expression_map, zfa_ontology, information_content):
    # Two identical calls must return the same ordered list.
    symbols = ["kdrl", "cdh5", "flt1", "mylpfa", "myod1", "acta1b", "myog"]
    first = resolve_label(
        symbols, expression_map=expression_map, zfa_ontology=zfa_ontology, information_content=information_content
    )
    second = resolve_label(
        symbols, expression_map=expression_map, zfa_ontology=zfa_ontology, information_content=information_content
    )
    assert first == second
