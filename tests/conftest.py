"""Shared test fixtures for zlabel tests."""

from pathlib import Path

import pytest

from zlabel.data import load_zfa, load_zfin_expression
from zlabel.resolve import build_ic

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def gaf_row():
    """Return a builder for one GAF row.

    Only column 3 (symbol) and column 11 (synonyms) are read by the loader;
    the rest are stable fillers that keep the row shape realistic.
    """

    def _row(symbol: str, synonyms: str) -> str:
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

    return _row


@pytest.fixture
def write_gaf(tmp_path: Path):
    """Return a writer that saves GAF rows to a temp file and returns its path."""

    def _write(rows: list[str]) -> Path:
        path = tmp_path / "syn.gaf"
        path.write_text("\n".join(rows) + "\n", encoding="utf-8")
        return path

    return _write


@pytest.fixture(scope="module")
def zfa_graph():
    """The ZFA test ontology graph, shared by resolve and label tests."""
    return load_zfa(FIXTURES / "zfa_test.obo")


@pytest.fixture(scope="module")
def zfa(zfa_graph):
    """Alias for zfa_graph; lets label tests keep the shorter name."""
    return zfa_graph


@pytest.fixture(scope="module")
def expr_map():
    """ZFIN in-vivo expression records from the test fixture."""
    return load_zfin_expression(FIXTURES / "zfin_expr_test.txt")


@pytest.fixture(scope="module")
def ic(expr_map, zfa_graph):
    """IC background model built once from the test expression fixture."""
    return build_ic(expr_map, zfa_graph)
