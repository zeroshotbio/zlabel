"""Unit tests for the Stage-G baseline regression wall's pure parser.

Only the markdown parser is unit-tested here: the full gate regenerates the Daniocell baseline and
needs data/ontologies (the gitignored corpus), so it is exercised by make gate, not pytest.
"""

import check_baseline


def test_committed_overcall_count_reads_the_numerator():
    """The thin-support overcall count is parsed from the audit line's numerator."""
    report = (
        "## Parent-child overcall audit (named calls)\n"
        "- named calls audited: 146\n"
        "- won with exactly CONVERGENCE_MIN=3 genes: 4.8% (7/146)\n"
        "- thin-support overcalls (won at min, broader parent had more support): 4.8% (7/146)\n"
    )
    assert check_baseline.committed_overcall_count(report) == 7


def test_committed_overcall_count_absent_line_returns_none():
    """A report without the overcall line returns None so the caller falls back to a plain drift fail."""
    assert check_baseline.committed_overcall_count("# some other report\n- agreement: 71.3%\n") is None
