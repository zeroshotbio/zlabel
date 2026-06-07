"""Unit tests for the three loaders in `zlabel.data`, on small committed fixtures.

No network: ZFA and GAF read fixture files under `tests/fixtures/`; ZFIN expression
rows are built inline (the 15-col format is self-documenting in `_expr_row`).
"""

from pathlib import Path

import pytest

from zlabel import (
    ALL_RELATION_EDGE_TYPES,
    DEFAULT_ANCESTOR_EDGE_TYPES,
    ancestors,
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


# --- ZFA ---------------------------------------------------------------------


@pytest.fixture
def zfa():
    return load_zfa(FIXTURES / "zfa_test.obo")


def test_load_zfa_returns_populated_graph(zfa):
    # Superset, not equality: obonet may also add [Typedef] entries as nodes.
    assert {WHOLE_ORGANISM, CELL, ENDOTHELIAL_CELL, ARTERIAL_EC}.issubset(zfa.nodes)


def test_get_term_returns_attrs(zfa):
    assert get_term(zfa, ENDOTHELIAL_CELL)["name"] == "endothelial cell"


def test_get_term_unknown_id_raises(zfa):
    with pytest.raises(KeyError):
        get_term(zfa, "ZFA:9999999")


def test_term_name(zfa):
    assert term_name(zfa, ARTERIAL_EC) == "arterial endothelial cell"


def test_ancestors_default_mixes_is_a_and_part_of(zfa):
    # is_a chain (endothelial cell, cell) AND part_of chain (cardiovascular
    # system, whole organism) both surface under the default edge types.
    assert set(ancestors(zfa, ARTERIAL_EC)) == {
        ENDOTHELIAL_CELL,
        CELL,
        CARDIOVASCULAR_SYSTEM,
        WHOLE_ORGANISM,
    }


def test_ancestors_is_a_only_excludes_part_of(zfa):
    result = set(ancestors(zfa, ARTERIAL_EC, edge_types={"is_a"}))
    assert result == {ENDOTHELIAL_CELL, CELL}
    assert CARDIOVASCULAR_SYSTEM not in result  # part_of edge must not be followed


def test_ancestors_develops_from_is_a_separate_axis(zfa):
    assert ancestors(zfa, ARTERIAL_EC, edge_types={"develops_from"}) == [ENDOTHELIAL_CELL]


def test_ancestors_of_root_is_empty(zfa):
    assert ancestors(zfa, WHOLE_ORGANISM) == []


def test_ancestors_unknown_id_raises(zfa):
    with pytest.raises(KeyError):
        ancestors(zfa, "ZFA:9999999")


def test_load_zfa_missing_file_raises():
    with pytest.raises(FileNotFoundError):
        load_zfa(FIXTURES / "does_not_exist.obo")


def test_edge_type_constants():
    assert DEFAULT_ANCESTOR_EDGE_TYPES == {"is_a", "part_of"}
    assert "develops_from" in ALL_RELATION_EDGE_TYPES
    assert "develops_from" not in DEFAULT_ANCESTOR_EDGE_TYPES


# --- ZFIN wildtype expression ------------------------------------------------


def _expr_row(symbol, super_id, super_name, sub_id, sub_name, start, end):
    """Build one real-format ZFIN expression row (15 tab cols, no header)."""
    return "\t".join(
        [
            "ZDB-GENE-x",
            symbol,
            "WT",
            super_id,
            super_name,
            sub_id,
            sub_name,
            start,
            end,
            "ISH",
            "MMO:1",
            "ZDB-PUB",
            "",
            "",
            "ZDB-FISH",
        ]
    )


def _write_expr(tmp_path, rows):
    path = tmp_path / "wt_expr.txt"
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")
    return path


def test_expression_keys_are_lowercased_symbols(tmp_path):
    rows = [
        _expr_row("Kdrl", "ZFA:0000009", "blood vessel", "", "", "Long-pec", "Day 5"),
        _expr_row("hbbe1.1", "ZFA:0000007", "blood", "", "", "Gastrula:Bud", "Larval:Day 4"),
    ]
    assert set(load_zfin_expression(_write_expr(tmp_path, rows))) == {"kdrl", "hbbe1.1"}


def test_expression_record_carries_anatomy_and_stage(tmp_path):
    rows = [_expr_row("hbbe1.1", "ZFA:0000007", "blood", "", "", "Gastrula:Bud", "Larval:Day 4")]
    rec = load_zfin_expression(_write_expr(tmp_path, rows))["hbbe1.1"][0]
    assert (rec.zfa_id, rec.zfa_name) == ("ZFA:0000007", "blood")
    assert (rec.start_stage, rec.end_stage) == ("Gastrula:Bud", "Larval:Day 4")


def test_expression_sub_structure_wins_over_super(tmp_path):
    rows = [
        _expr_row("kdrl", "ZFA:0000009", "blood vessel", "", "", "Long-pec", "Long-pec"),
        _expr_row("kdrl", "ZFA:0000009", "blood vessel", "ZFA:0000010", "dorsal aorta", "Long-pec", "Long-pec"),
    ]
    structures = {(r.zfa_id, r.zfa_name) for r in load_zfin_expression(_write_expr(tmp_path, rows))["kdrl"]}
    assert structures == {("ZFA:0000009", "blood vessel"), ("ZFA:0000010", "dorsal aorta")}


def test_expression_short_row_is_skipped(tmp_path):
    rows = ["too\tfew\tcolumns", _expr_row("kdrl", "ZFA:0000009", "blood vessel", "", "", "Long-pec", "Long-pec")]
    assert set(load_zfin_expression(_write_expr(tmp_path, rows))) == {"kdrl"}


def test_expression_missing_file_returns_empty(tmp_path):
    assert load_zfin_expression(tmp_path / "nope.txt") == {}


# --- GAF gene-synonym map ----------------------------------------------------


def _gaf_row(symbol, synonyms):
    """Build one GAF row carrying through column 11 (the synonym column)."""
    return "\t".join(
        [
            "ZFIN",
            "ZDB-GENE-x",
            symbol,
            "involved_in",
            "GO:0",
            "PMID:0",
            "IEA",
            "GO_REF:0",
            "P",
            f"{symbol} name",
            synonyms,
        ]
    )


def _write_gaf(tmp_path, rows):
    path = tmp_path / "syn.gaf"
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")
    return path


def test_synonym_previous_name_maps_to_all_paralogs(tmp_path):
    # `hbae1` is a ZFIN previous-name of both paralogs — the map fans out to both.
    rows = [_gaf_row("hbae1.1", "hbae1"), _gaf_row("hbae1.2", "hbae1")]
    assert load_gene_synonym_map(_write_gaf(tmp_path, rows))["hbae1"] == {"hbae1.1", "hbae1.2"}


def test_synonym_keys_are_case_folded(tmp_path):
    rows = [_gaf_row("ppardb", "NR1C2-B|PPARb")]
    syn = load_gene_synonym_map(_write_gaf(tmp_path, rows))
    assert syn["nr1c2-b"] == {"ppardb"}
    assert syn["pparb"] == {"ppardb"}


def test_synonym_current_symbol_maps_to_itself(tmp_path):
    rows = [_gaf_row("kdrl", "kdr|flk1")]
    assert load_gene_synonym_map(_write_gaf(tmp_path, rows))["kdrl"] == {"kdrl"}


def test_synonym_comments_and_short_rows_skipped(tmp_path):
    rows = ["!gaf-version: 2.2", "", "too\tshort", _gaf_row("kdrl", "flk1")]
    syn = load_gene_synonym_map(_write_gaf(tmp_path, rows))
    assert syn["flk1"] == {"kdrl"}


def test_synonym_loads_committed_fixture():
    syn = load_gene_synonym_map(FIXTURES / "zfin_go_test.gaf")
    assert syn["kdr"] == {"kdrl"}
    assert syn["flk1"] == {"kdrl"}
    assert syn["kdrl"] == {"kdrl"}


def test_synonym_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_gene_synonym_map(tmp_path / "nope.gaf")
