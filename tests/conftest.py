"""Shared test fixtures for zlabel tests."""

from pathlib import Path

import pytest


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


@pytest.fixture
def write_zfin_expr(tmp_path: Path):
    """Return a writer that saves ZFIN expression rows to a temp file."""

    def _write(rows: list[str]) -> Path:
        path = tmp_path / "wt_expr.txt"
        path.write_text("\n".join(rows) + "\n", encoding="utf-8")
        return path

    return _write
