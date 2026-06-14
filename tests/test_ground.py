"""Unit tests for zlabel.ground — the pure grounding functions.

No network: the ZFA fixture has an endothelial sub-DAG (from Phase 1) and a
muscle sub-DAG added for Phase 3 (ZFA:0000548 musculature system,
ZFA:0009234 muscle cell part_of musculature system).
"""

from pathlib import Path

import pytest
from helpers import expr_row, write_expr

from zlabel.data import load_zfa, load_zfin_expression
from zlabel.ground import expression_lookup, grounds_under, stage_plausibility

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="module")
def zfa():
    return load_zfa(FIXTURES / "zfa_test.obo")


@pytest.fixture
def tiny_expr(tmp_path):
    rows = [
        expr_row(
            "mylpfa",
            "ZFA:0000548",
            "musculature system",
            "ZFA:0009234",
            "muscle cell",
            "Hatching:Long-pec",
            "Larval:Day 5",
        ),
        expr_row(
            "kdrl",
            "ZFA:0001262",
            "cardiovascular system",
            "ZFA:0005307",
            "endothelial cell",
            "Pharyngula:Prim-5",
            "Larval:Day 5",
        ),
    ]
    path = write_expr(tmp_path, rows)
    return load_zfin_expression(path)


# --- expression_lookup -------------------------------------------------------


def test_expression_lookup_hit(tiny_expr):
    recs = expression_lookup(tiny_expr, "mylpfa")
    assert len(recs) == 1
    assert recs[0].zfa_id == "ZFA:0009234"


def test_expression_lookup_lowercases(tiny_expr):
    assert expression_lookup(tiny_expr, "MYLPFA") == expression_lookup(tiny_expr, "mylpfa")


def test_expression_lookup_miss_returns_empty(tiny_expr):
    assert expression_lookup(tiny_expr, "notareal") == []


# --- grounds_under -----------------------------------------------------------

MUSCLE_ANCHOR = frozenset({"ZFA:0000548"})
ENDOTHELIAL_ANCHOR = frozenset({"ZFA:0001262"})  # cardiovascular system


def test_grounds_under_self_match(zfa):
    assert grounds_under(zfa, "ZFA:0000548", MUSCLE_ANCHOR)


def test_grounds_under_ancestor_match(zfa):
    # ZFA:0009234 (muscle cell) is part_of ZFA:0000548 (musculature system)
    assert grounds_under(zfa, "ZFA:0009234", MUSCLE_ANCHOR)


def test_grounds_under_non_match(zfa):
    # Endothelial cell is not under musculature system.
    assert not grounds_under(zfa, "ZFA:0005307", MUSCLE_ANCHOR)


def test_grounds_under_id_absent_from_graph(zfa):
    # An expression record pointing at an unknown ZFA id should return False,
    # not raise.
    assert not grounds_under(zfa, "ZFA:9999999", MUSCLE_ANCHOR)


def test_grounds_under_empty_anchor_returns_false(zfa):
    assert not grounds_under(zfa, "ZFA:0000548", frozenset())


# --- stage_plausibility ------------------------------------------------------


def test_stage_plausibility_overlap_is_true():
    from zlabel.data import ZfinExpressionRecord

    recs = [ZfinExpressionRecord("ZFA:0000548", "musculature system", "Hatching:Long-pec", "Larval:Day 5")]
    # Long-pec = 48 hpf; query 48 with default window 12 -> overlap
    assert stage_plausibility(recs, 48.0) is True


def test_stage_plausibility_no_overlap_is_false():
    from zlabel.data import ZfinExpressionRecord

    recs = [ZfinExpressionRecord("ZFA:0000548", "musculature system", "Zygote:1-cell", "Cleavage:2-cell")]
    # Zygote is at 0 hpf; query 48 hpf with window 12 -> no overlap
    assert stage_plausibility(recs, 48.0) is False


def test_stage_plausibility_no_stage_hpf_is_none():
    from zlabel.data import ZfinExpressionRecord

    recs = [ZfinExpressionRecord("ZFA:0000548", "musculature system", "Hatching:Long-pec", "Larval:Day 5")]
    assert stage_plausibility(recs, None) is None


def test_stage_plausibility_unparseable_stage_is_none():
    from zlabel.data import ZfinExpressionRecord

    recs = [ZfinExpressionRecord("ZFA:0000548", "musculature system", "UNKNOWN_STAGE", "ALSO_UNKNOWN")]
    assert stage_plausibility(recs, 48.0) is None


def test_stage_plausibility_any_record_on_stage_is_true():
    from zlabel.data import ZfinExpressionRecord

    # First record is off-stage, second is on-stage — result is True.
    recs = [
        ZfinExpressionRecord("ZFA:x", "x", "Zygote:1-cell", "Cleavage:2-cell"),
        ZfinExpressionRecord("ZFA:x", "x", "Hatching:Long-pec", "Larval:Day 5"),
    ]
    assert stage_plausibility(recs, 48.0) is True


def test_stage_plausibility_empty_records_is_none():
    assert stage_plausibility([], 48.0) is None
