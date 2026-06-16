"""Unit tests for the three loaders in zlabel.data, on small committed fixtures.

No network: ZFA and GAF read fixture files under tests/fixtures/; ZFIN expression
rows are built inline (the 15-col format is self-documenting in _expr_row).
"""

from pathlib import Path

import pytest
from helpers import expr_row, write_expr

from zlabel import (
    ALL_RELATION_EDGE_TYPES,
    DEFAULT_ANCESTOR_EDGE_TYPES,
    ancestors,
    children,
    get_term,
    load_gene_synonym_map,
    load_zfa,
    load_zfin_expression,
    term_name,
)

FIXTURES = Path(__file__).parent / "fixtures"

# ZFA fixture term ids (see tests/fixtures/zfa_test.obo).
WHOLE_ORGANISM = "ZFA:0001094"
CELL = "ZFA:0009000"
CARDIOVASCULAR_SYSTEM = "ZFA:0001262"
ENDOTHELIAL_CELL = "ZFA:0005307"
ARTERIAL_EC = "ZFA:0009073"
VENOUS_EC = "ZFA:0005304"
NAMELESS_TERM = "ZFA:0000001"  # a stub term with no name: field


# --- ZFA ---------------------------------------------------------------------


@pytest.fixture
def zfa_ontology():
    return load_zfa(FIXTURES / "zfa_test.obo")


def test_load_zfa_returns_populated_graph(zfa_ontology):
    # Superset, not equality: obonet may also add [Typedef] entries as nodes.
    assert {WHOLE_ORGANISM, CELL, ENDOTHELIAL_CELL, ARTERIAL_EC}.issubset(zfa_ontology.nodes)


def test_get_term_returns_attrs(zfa_ontology):
    assert get_term(zfa_ontology, ENDOTHELIAL_CELL)["name"] == "endothelial cell"


def test_get_term_unknown_id_raises(zfa_ontology):
    with pytest.raises(KeyError):
        get_term(zfa_ontology, "ZFA:9999999")


def test_term_name(zfa_ontology):
    assert term_name(zfa_ontology, ARTERIAL_EC) == "arterial endothelial cell"


def test_term_name_returns_none_for_nameless_term(zfa_ontology):
    assert term_name(zfa_ontology, NAMELESS_TERM) is None


def test_ancestors_default_mixes_is_a_and_part_of(zfa_ontology):
    # is_a chain (endothelial cell, cell) AND part_of chain (cardiovascular
    # system, whole organism) both surface under the default edge types.
    assert set(ancestors(zfa_ontology, ARTERIAL_EC)) == {
        ENDOTHELIAL_CELL,
        CELL,
        CARDIOVASCULAR_SYSTEM,
        WHOLE_ORGANISM,
    }


def test_ancestors_is_a_only_excludes_part_of(zfa_ontology):
    result = set(ancestors(zfa_ontology, ARTERIAL_EC, edge_types={"is_a"}))
    assert result == {ENDOTHELIAL_CELL, CELL}
    assert CARDIOVASCULAR_SYSTEM not in result  # part_of edge must not be followed


def test_ancestors_develops_from_is_a_separate_axis(zfa_ontology):
    # set(): BFS order is not part of the contract, only the membership.
    assert set(ancestors(zfa_ontology, ARTERIAL_EC, edge_types={"develops_from"})) == {ENDOTHELIAL_CELL}


def test_ancestors_of_root_is_empty(zfa_ontology):
    assert ancestors(zfa_ontology, WHOLE_ORGANISM) == []


def test_ancestors_unknown_id_raises(zfa_ontology):
    with pytest.raises(KeyError):
        ancestors(zfa_ontology, "ZFA:9999999")


def test_children_is_the_inverse_of_ancestors(zfa_ontology):
    # endothelial cell's is_a children are the arterial/venous EC; cardiovascular system's part_of
    # child is endothelial cell. children walks the same edges as ancestors, one hop the other way.
    assert set(children(zfa_ontology, ENDOTHELIAL_CELL)) == {ARTERIAL_EC, VENOUS_EC}
    assert children(zfa_ontology, CARDIOVASCULAR_SYSTEM) == [ENDOTHELIAL_CELL]


def test_children_sorted_and_excludes_develops_from(zfa_ontology):
    # Deterministic sorted output; develops_from (a separate axis) is not followed by default,
    # even though arterial/venous EC also develops_from endothelial cell.
    assert children(zfa_ontology, ENDOTHELIAL_CELL) == sorted({ARTERIAL_EC, VENOUS_EC})


def test_children_of_leaf_is_empty(zfa_ontology):
    assert children(zfa_ontology, ARTERIAL_EC) == []


def test_children_unknown_id_raises(zfa_ontology):
    with pytest.raises(KeyError):
        children(zfa_ontology, "ZFA:9999999")


def test_load_zfa_missing_file_raises():
    with pytest.raises(FileNotFoundError):
        load_zfa(FIXTURES / "does_not_exist.obo")


def test_edge_type_constants():
    assert DEFAULT_ANCESTOR_EDGE_TYPES == {"is_a", "part_of"}
    assert "develops_from" in ALL_RELATION_EDGE_TYPES
    assert "develops_from" not in DEFAULT_ANCESTOR_EDGE_TYPES


# --- ZFIN wildtype expression ------------------------------------------------


def test_expression_keys_are_lowercased_symbols(tmp_path):
    rows = [
        expr_row("Kdrl", "ZFA:0000009", "blood vessel", "", "", "Long-pec", "Day 5"),
        expr_row("hbbe1.1", "ZFA:0000007", "blood", "", "", "Gastrula:Bud", "Larval:Day 4"),
    ]
    assert set(load_zfin_expression(write_expr(tmp_path, rows))) == {"kdrl", "hbbe1.1"}


def test_expression_record_carries_anatomy_and_stage(tmp_path):
    rows = [expr_row("hbbe1.1", "ZFA:0000007", "blood", "", "", "Gastrula:Bud", "Larval:Day 4")]
    record = load_zfin_expression(write_expr(tmp_path, rows))["hbbe1.1"][0]
    assert (record.zfa_id, record.zfa_name) == ("ZFA:0000007", "blood")
    assert (record.start_stage, record.end_stage) == ("Gastrula:Bud", "Larval:Day 4")


def test_expression_sub_structure_wins_over_super(tmp_path):
    rows = [
        expr_row("kdrl", "ZFA:0000009", "blood vessel", "", "", "Long-pec", "Long-pec"),
        expr_row("kdrl", "ZFA:0000009", "blood vessel", "ZFA:0000010", "dorsal aorta", "Long-pec", "Long-pec"),
    ]
    records = load_zfin_expression(write_expr(tmp_path, rows))["kdrl"]
    structures = {(record.zfa_id, record.zfa_name) for record in records}
    assert structures == {("ZFA:0000009", "blood vessel"), ("ZFA:0000010", "dorsal aorta")}


def test_expression_short_row_is_skipped(tmp_path):
    rows = ["too\tfew\tcolumns", expr_row("kdrl", "ZFA:0000009", "blood vessel", "", "", "Long-pec", "Long-pec")]
    assert set(load_zfin_expression(write_expr(tmp_path, rows))) == {"kdrl"}


def test_expression_missing_file_returns_empty(tmp_path):
    assert load_zfin_expression(tmp_path / "nope.txt") == {}


# --- GAF gene-synonym map ----------------------------------------------------


def test_synonym_previous_name_maps_to_all_paralogs(gaf_row, write_gaf):
    # hbae1 is a ZFIN previous-name of both paralogs — the map fans out to both.
    rows = [gaf_row("hbae1.1", "hbae1"), gaf_row("hbae1.2", "hbae1")]
    assert load_gene_synonym_map(write_gaf(rows))["hbae1"] == {"hbae1.1", "hbae1.2"}


def test_synonym_keys_are_case_folded(gaf_row, write_gaf):
    rows = [gaf_row("ppardb", "NR1C2-B|PPARb")]
    syn = load_gene_synonym_map(write_gaf(rows))
    assert syn["nr1c2-b"] == {"ppardb"}
    assert syn["pparb"] == {"ppardb"}


def test_synonym_current_symbol_maps_to_itself(gaf_row, write_gaf):
    rows = [gaf_row("kdrl", "kdr|flk1")]
    assert load_gene_synonym_map(write_gaf(rows))["kdrl"] == {"kdrl"}


def test_synonym_comments_and_short_rows_skipped(gaf_row, write_gaf):
    rows = ["!gaf-version: 2.2", "", "too\tshort", gaf_row("kdrl", "flk1")]
    syn = load_gene_synonym_map(write_gaf(rows))
    assert syn["flk1"] == {"kdrl"}


def test_synonym_loads_committed_fixture():
    syn = load_gene_synonym_map(FIXTURES / "zfin_go_test.gaf")
    assert syn["kdr"] == {"kdrl"}
    assert syn["flk1"] == {"kdrl"}
    assert syn["kdrl"] == {"kdrl"}


def test_synonym_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_gene_synonym_map(tmp_path / "nope.gaf")
