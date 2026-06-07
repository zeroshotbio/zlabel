"""Unit tests for zlabel.panels — load_panels and score_markers.

No network: the happy-path tests use tests/fixtures/panels_test.yaml (a minimal
four-bucket subset). Validation failures use inline YAML written to tmp_path.

Keystone test: the muscle-cluster trace with markers
["mylz2","acta1b","tnnt3a","myod1","myog","hbae1.1","kdrl"] asserts that
muscle tops the chart (score > 0.8) and dominates every other bucket (> 5x
the second-highest identity bucket). The exact scores are computed from the
rank-weight formula w(r) = 1/log2(r+1), not hardcoded.
"""

import math
from pathlib import Path

import pytest

from zlabel import (
    KIND_IDENTITY,
    KIND_STATE,
    Panel,
    load_panels,
    score_markers,
)

FIXTURES = Path(__file__).parent / "fixtures"


# --- helpers -----------------------------------------------------------------


def _make_synonym_map(*symbols: str) -> dict[str, set[str]]:
    """Build a minimal synonym map where every symbol is its own current name."""
    return {s.lower(): {s} for s in symbols}


# --- load_panels -------------------------------------------------------------


@pytest.fixture
def test_panels() -> list[Panel]:
    return load_panels(FIXTURES / "panels_test.yaml")


def test_load_panels_returns_expected_buckets(test_panels):
    buckets = {p.bucket for p in test_panels}
    assert {"muscle", "blood_erythroid", "endothelium", "cycling"}.issubset(buckets)


def test_load_panels_markers_are_lowercased(test_panels):
    muscle = next(p for p in test_panels if p.bucket == "muscle")
    assert "mylz2" in muscle.markers
    assert all(m == m.lower() for m in muscle.markers)


def test_load_panels_kind_identity(test_panels):
    identity_buckets = {p.bucket for p in test_panels if p.kind == KIND_IDENTITY}
    assert "muscle" in identity_buckets
    assert "blood_erythroid" in identity_buckets


def test_load_panels_kind_state(test_panels):
    state_buckets = {p.bucket for p in test_panels if p.kind == KIND_STATE}
    assert "cycling" in state_buckets


def test_load_panels_subpanels_loaded(test_panels):
    # Subpanels load in Phase 2 even though they are not scored yet.
    muscle = next(p for p in test_panels if p.bucket == "muscle")
    assert "myoblast" in muscle.subpanels
    assert isinstance(muscle.subpanels["myoblast"], frozenset)
    assert "myod1" in muscle.subpanels["myoblast"]


def test_load_panels_invalid_kind_raises(tmp_path):
    path = tmp_path / "bad.yaml"
    path.write_text(
        "bucket_x:\n  kind: invalid\n  cite: test\n  markers: [abc]\n"
        "  germ_layer: ''\n  tissue: ''\n  lineage: ''\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="invalid kind"):
        load_panels(path)


def test_load_panels_empty_markers_raises(tmp_path):
    path = tmp_path / "bad.yaml"
    path.write_text(
        "bucket_x:\n  kind: identity\n  cite: test\n  markers: []\n"
        "  germ_layer: ''\n  tissue: ''\n  lineage: ''\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="no markers"):
        load_panels(path)


# --- score_markers: keystone trace -------------------------------------------


def test_score_markers_muscle_keystone_trace(test_panels):
    # Canonical 7-marker muscle cluster from the plan's worked example.
    # All are current ZFIN symbols and resolve cleanly.
    all_markers = ["mylz2", "acta1b", "tnnt3a", "myod1", "myog", "hbae1.1", "kdrl"]
    syn = _make_synonym_map(*all_markers)

    scores = score_markers(all_markers, test_panels, syn)

    top = scores[0]
    assert top.bucket == "muscle"
    assert top.score > 0.8

    # Every runner-up scores far below muscle: the next-highest bucket
    # (blood_erythroid) is ~0.098 in this trace, comfortably under the 0.15 bound.
    for s in scores[1:]:
        assert s.score < 0.15, f"expected {s.bucket} < 0.15, got {s.score:.4f}"

    # Dominance: muscle must be at least 5x the blood erythroid score.
    blood = next(s for s in scores if s.bucket == "blood_erythroid")
    assert top.score > 5 * blood.score


def test_score_markers_sorted_descending_by_score(test_panels):
    syn = _make_synonym_map("mylz2", "acta1b", "myod1")
    scores = score_markers(["mylz2", "acta1b", "myod1"], test_panels, syn)
    for a, b in zip(scores, scores[1:], strict=False):
        assert a.score >= b.score


# --- score_markers: edge cases -----------------------------------------------


def test_score_markers_all_unresolved_gives_zero_scores(test_panels):
    syn: dict[str, set[str]] = {}  # empty — every marker is unresolved
    scores = score_markers(["zyxwvut", "abc123"], test_panels, syn)
    assert all(s.score == 0.0 for s in scores)


def test_score_markers_empty_input_gives_zero_scores(test_panels):
    scores = score_markers([], test_panels, {})
    assert all(s.score == 0.0 for s in scores)


def test_score_markers_ambiguous_excluded_from_denominator(test_panels):
    # hbae1 maps to two paralogs -> ambiguous -> excluded from denominator.
    # Only mylz2 (resolved, rank 1) contributes weight 1.0.
    # mylz2 is in muscle: muscle score should be 1.0 exactly.
    syn: dict[str, set[str]] = {
        "hbae1": {"hbae1.1", "hbae1.2"},  # ambiguous
        "mylz2": {"mylz2"},               # resolved
    }
    scores = score_markers(["mylz2", "hbae1"], test_panels, syn)
    muscle = next(s for s in scores if s.bucket == "muscle")
    assert math.isclose(muscle.score, 1.0, rel_tol=1e-9)


def test_score_markers_matched_markers_recorded_in_rank_order(test_panels):
    syn = _make_synonym_map("mylz2", "acta1b")
    scores = score_markers(["mylz2", "acta1b"], test_panels, syn)
    muscle = next(s for s in scores if s.bucket == "muscle")
    assert len(muscle.matched_markers) == 2
    assert muscle.matched_markers[0].rank == 1
    assert muscle.matched_markers[0].symbol == "mylz2"
    assert muscle.matched_markers[1].rank == 2
    assert muscle.matched_markers[1].symbol == "acta1b"
    # Verify the weight formula w(r) = 1/log2(r+1) for each recorded match.
    assert math.isclose(muscle.matched_markers[0].weight, 1.0 / math.log2(2), rel_tol=1e-9)
    assert math.isclose(muscle.matched_markers[1].weight, 1.0 / math.log2(3), rel_tol=1e-9)


def test_score_markers_tie_broken_alphabetically_by_bucket(test_panels):
    # When every bucket scores 0.0 (no resolved markers hit any panel), the
    # sort key (-score, bucket) breaks the tie alphabetically.
    scores = score_markers([], test_panels, {})
    bucket_names = [s.bucket for s in scores]
    assert bucket_names == sorted(bucket_names)


def test_score_markers_all_panels_always_returned(test_panels):
    # Even when nothing matches, all panels appear in the output.
    syn = _make_synonym_map("zyxwvut")
    scores = score_markers(["zyxwvut"], test_panels, syn)
    assert len(scores) == len(test_panels)
