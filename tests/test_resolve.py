"""Unit tests for zlabel.resolve — build_ic and resolve_label (the IC-weighted namer).

Two sets of tests:
  1. build_ic: background model properties (monotonicity, root=0, absent-id safety,
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
    IC_MIN,
    STOPLIST,
    build_ic,
    resolve_label,
)

# The zfa_graph, expr_map, and ic fixtures are shared via tests/conftest.py.


# ---------------------------------------------------------------------------
# build_ic
# ---------------------------------------------------------------------------


def test_build_ic_empty_corpus(zfa_graph):
    assert build_ic({}, zfa_graph) == {}


def test_build_ic_descendant_ic_ge_ancestor(ic):
    # A child term is credited by a subset of the genes that credit its parent,
    # so IC(child) >= IC(parent) always holds.
    # muscle cell (ZFA:0009234) is part_of musculature system (ZFA:0000548)
    ic_muscle_cell = ic.get("ZFA:0009234", 0.0)
    ic_musc_system = ic.get("ZFA:0000548", 0.0)
    assert ic_muscle_cell >= ic_musc_system, (
        f"IC(muscle cell)={ic_muscle_cell:.3f} < IC(musculature system)={ic_musc_system:.3f}"
    )
    # endothelial cell (ZFA:0005307) is part_of cardiovascular system (ZFA:0001262)
    ic_endo = ic.get("ZFA:0005307", 0.0)
    ic_cardio = ic.get("ZFA:0001262", 0.0)
    assert ic_endo >= ic_cardio, f"IC(endothelial cell)={ic_endo:.3f} < IC(cardiovascular system)={ic_cardio:.3f}"


def test_build_ic_root_is_zero(ic):
    # ZFA:0001094 (whole organism) is credited by every gene in the corpus.
    # IC = -log2(n/n) = 0.
    assert ic.get("ZFA:0001094", 0.0) == pytest.approx(0.0, abs=1e-9)


def test_build_ic_absent_zfa_id_no_crash(zfa_graph):
    # A gene with a record pointing at an id absent from the graph is credited
    # for itself only (no ancestor walk). build_ic must not raise.
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
    result = build_ic(phantom_expr, zfa_graph)
    # The absent id gets self-credit: 1/1 gene -> IC = -log2(1) = 0.
    assert "ZFA:9999999" in result
    assert result["ZFA:9999999"] == pytest.approx(0.0, abs=1e-9)


def test_build_ic_specific_value_muscle_cell(ic):
    # 7 genes total; ZFA:0009234 (muscle cell) is credited by 3 of them
    # (mylpfa, acta1b, myog). IC = -log2(3/7).
    expected = -math.log2(3 / 7)
    assert ic.get("ZFA:0009234", 0.0) == pytest.approx(expected, rel=1e-6)


# ---------------------------------------------------------------------------
# resolve_label — worked examples
# ---------------------------------------------------------------------------


def test_resolve_label_muscle_markers_name_muscle_cell(expr_map, zfa_graph, ic):
    # Three of the four muscle markers express in muscle cell (ZFA:0009234, IC>IC_MIN);
    # the broader musculature system (ZFA:0000548) has IC below IC_MIN in this fixture
    # and is filtered by the IC gate. Muscle cell is the sole surviving candidate.
    votes = resolve_label(
        ["mylpfa", "myod1", "acta1b", "myog"],
        expr_map=expr_map,
        zfa_graph=zfa_graph,
        ic=ic,
    )
    assert votes, "expected at least one candidate for muscle markers"
    top = votes[0]
    assert top.zfa_id == "ZFA:0009234"
    assert top.zfa_name == "muscle cell"
    assert set(top.genes) == {"mylpfa", "acta1b", "myog"}
    assert top.ic > IC_MIN
    assert top.ancestor_depth >= 1


def test_resolve_label_endothelium_names_endothelial_cell_not_cardiovascular(expr_map, zfa_graph, ic):
    # IC-first, ancestor_depth tiebreak: endothelial cell (ZFA:0005307) and
    # cardiovascular system (ZFA:0001262) tie on IC and gene count. ancestor_depth
    # breaks the tie: endothelial cell has more ancestors, so it ranks first.
    votes = resolve_label(
        ["kdrl", "cdh5", "flt1"],
        expr_map=expr_map,
        zfa_graph=zfa_graph,
        ic=ic,
    )
    assert votes, "expected candidates for endothelial markers"
    top = votes[0]
    assert top.zfa_id == "ZFA:0005307"
    assert top.zfa_name == "endothelial cell"
    assert top.ic > IC_MIN
    # Cardiovascular system must appear later — ancestor_depth tiebreak proves IC-first ranking.
    ids = [v.zfa_id for v in votes]
    assert "ZFA:0001262" in ids
    assert ids.index("ZFA:0005307") < ids.index("ZFA:0001262")


# ---------------------------------------------------------------------------
# resolve_label — gate tests
# ---------------------------------------------------------------------------


def test_resolve_label_below_convergence_min_returns_empty(expr_map, zfa_graph, ic):
    # 2 muscle genes — below CONVERGENCE_MIN=3, so no term survives.
    votes = resolve_label(
        ["mylpfa", "acta1b"],
        expr_map=expr_map,
        zfa_graph=zfa_graph,
        ic=ic,
    )
    assert votes == []


def test_resolve_label_stoplist_filtered(zfa_graph):
    # ZFA:0001094 (whole organism) is in STOPLIST. Supplying a forced-high IC
    # isolates the stoplist gate: the term must not appear even with IC >> IC_MIN.
    stoplist_id = "ZFA:0001094"
    assert stoplist_id in STOPLIST
    minimal_expr: dict[str, list[ZfinExpressionRecord]] = {
        "ga": [ZfinExpressionRecord(zfa_id=stoplist_id, zfa_name="whole organism", start_stage="s", end_stage="e")],
        "gb": [ZfinExpressionRecord(zfa_id=stoplist_id, zfa_name="whole organism", start_stage="s", end_stage="e")],
        "gc": [ZfinExpressionRecord(zfa_id=stoplist_id, zfa_name="whole organism", start_stage="s", end_stage="e")],
    }
    forced_ic = {stoplist_id: 5.0}
    result = resolve_label(["ga", "gb", "gc"], expr_map=minimal_expr, zfa_graph=zfa_graph, ic=forced_ic)
    assert result == []


def test_resolve_label_absent_from_graph_no_crash(zfa_graph):
    # A gene expressing in a ZFA id absent from the loaded graph must not crash.
    # The absent id gets no ancestor walk; its IC stays at 0.0, failing IC_MIN.
    phantom_expr: dict[str, list[ZfinExpressionRecord]] = {
        "g1": [ZfinExpressionRecord(zfa_id="ZFA:9999999", zfa_name="ghost", start_stage="s", end_stage="e")],
        "g2": [ZfinExpressionRecord(zfa_id="ZFA:9999999", zfa_name="ghost", start_stage="s", end_stage="e")],
        "g3": [ZfinExpressionRecord(zfa_id="ZFA:9999999", zfa_name="ghost", start_stage="s", end_stage="e")],
    }
    fresh_ic = build_ic(phantom_expr, zfa_graph)
    result = resolve_label(["g1", "g2", "g3"], expr_map=phantom_expr, zfa_graph=zfa_graph, ic=fresh_ic)
    assert isinstance(result, list)
    assert result == []  # IC(ZFA:9999999) = 0.0 < IC_MIN


def test_resolve_label_empty_symbols(expr_map, zfa_graph, ic):
    assert resolve_label([], expr_map=expr_map, zfa_graph=zfa_graph, ic=ic) == []


def test_resolve_label_deterministic(expr_map, zfa_graph, ic):
    # Two identical calls must return the same ordered list.
    symbols = ["kdrl", "cdh5", "flt1", "mylpfa", "myod1", "acta1b", "myog"]
    first = resolve_label(symbols, expr_map=expr_map, zfa_graph=zfa_graph, ic=ic)
    second = resolve_label(symbols, expr_map=expr_map, zfa_graph=zfa_graph, ic=ic)
    assert first == second
