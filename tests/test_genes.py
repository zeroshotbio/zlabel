"""Unit tests for zlabel.genes — normalize_symbol and normalize_markers.

No network: happy-path alias tests use the committed GAF fixture; paralog
fan-out and edge cases are built inline with tmp_path (same pattern as
test_data.py).
"""

from pathlib import Path

import pytest

from zlabel import (
    STATUS_AMBIGUOUS,
    STATUS_RESOLVED,
    STATUS_UNRESOLVED,
    load_gene_synonym_map,
    normalize_markers,
    normalize_symbol,
)

FIXTURES = Path(__file__).parent / "fixtures"


# --- normalize_symbol: happy paths from committed fixture --------------------


@pytest.fixture
def synonym_map():
    """Synonym map from the committed GAF fixture (kdrl, cdh5, gata1a, dll4)."""
    return load_gene_synonym_map(FIXTURES / "zfin_go_test.gaf")


def test_normalize_symbol_alias_resolves_to_current(synonym_map):
    # flk1 and kdr are listed as synonyms for kdrl in the committed fixture.
    result = normalize_symbol("flk1", synonym_map)
    assert result.status == STATUS_RESOLVED
    assert result.symbols == frozenset({"kdrl"})
    assert result.note is None


def test_normalize_symbol_current_symbol_is_identity(synonym_map):
    result = normalize_symbol("kdrl", synonym_map)
    assert result.status == STATUS_RESOLVED
    assert result.symbols == frozenset({"kdrl"})


def test_normalize_symbol_case_insensitive(synonym_map):
    result = normalize_symbol("KDRL", synonym_map)
    assert result.status == STATUS_RESOLVED
    assert result.symbols == frozenset({"kdrl"})


def test_normalize_symbol_input_preserved_before_lowercasing(synonym_map):
    # The input field is the original string, before any case folding.
    result = normalize_symbol("FLK1", synonym_map)
    assert result.input == "FLK1"
    assert result.status == STATUS_RESOLVED


def test_normalize_symbol_strips_surrounding_whitespace(synonym_map):
    # A marker copied from a CSV/TSV may carry stray whitespace; it should still
    # resolve, with the original string preserved verbatim in input.
    result = normalize_symbol(" kdrl ", synonym_map)
    assert result.status == STATUS_RESOLVED
    assert result.symbols == frozenset({"kdrl"})
    assert result.input == " kdrl "


# --- normalize_symbol: paralog fan-out (ambiguous) ---------------------------


def test_normalize_symbol_paralog_fanout_is_ambiguous(gaf_row, write_gaf):
    # hbae1 is a ZFIN previous-name shared by hbae1.1 and hbae1.2 — two
    # current symbols for one old name. The result must be ambiguous, not
    # collapsed to either paralog.
    rows = [gaf_row("hbae1.1", "hbae1"), gaf_row("hbae1.2", "hbae1")]
    syn = load_gene_synonym_map(write_gaf(rows))
    result = normalize_symbol("hbae1", syn)
    assert result.status == STATUS_AMBIGUOUS
    assert result.symbols == frozenset({"hbae1.1", "hbae1.2"})
    assert result.note is not None
    assert "2" in result.note  # note mentions the count of paralogs


def test_normalize_symbol_current_symbol_wins_over_paralog_alias():
    # kdr is a current symbol that ZFIN also lists as a legacy alias of kdrl, so
    # the synonym map carries kdr -> {kdr, kdrl}. The exact current-symbol match
    # must win: kdr resolves to itself, never flagged ambiguous and dropped.
    syn = {"kdr": {"kdr", "kdrl"}, "kdrl": {"kdrl"}}
    result = normalize_symbol("kdr", syn)
    assert result.status == STATUS_RESOLVED
    assert result.symbols == frozenset({"kdr"})
    assert result.note is None


# --- normalize_symbol: miss (unresolved) -------------------------------------


def test_normalize_symbol_miss_is_unresolved_and_empty(synonym_map):
    result = normalize_symbol("zyxwvut99", synonym_map)
    assert result.status == STATUS_UNRESOLVED
    assert result.symbols == frozenset()
    assert result.note is not None


# --- normalize_markers -------------------------------------------------------


def test_normalize_markers_preserves_order_status_and_length(gaf_row, write_gaf):
    rows = [gaf_row("hbae1.1", "hbae1"), gaf_row("hbae1.2", "hbae1")]
    syn = load_gene_synonym_map(write_gaf(rows))
    # Three markers covering all three statuses in order.
    results = normalize_markers(["hbae1.1", "hbae1", "zyxwvut"], syn)
    assert len(results) == 3
    assert results[0].status == STATUS_RESOLVED
    assert results[1].status == STATUS_AMBIGUOUS
    assert results[2].status == STATUS_UNRESOLVED


def test_normalize_markers_empty_input_returns_empty(synonym_map):
    assert normalize_markers([], synonym_map) == []
