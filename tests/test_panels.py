"""Unit tests for zlabel.panels — load_panels and score_markers.

No network: the happy-path tests use tests/fixtures/panels_test.yaml (a minimal
four-bucket subset). Validation failures use inline YAML written to tmp_path.

Keystone test: the muscle-cluster trace with markers
["mylpfa","acta1b","tnnt3a","myod1","myog","hbae1.1","kdrl"] asserts that
muscle tops the chart (score > 0.8) and dominates every other bucket (> 5x
the second-highest identity bucket). The exact scores are computed from the
rank-weight formula w(r) = 1/log2(r+1), not hardcoded.
"""

import math
from pathlib import Path

import pytest

import zlabel
from zlabel import (
    KIND_IDENTITY,
    KIND_STATE,
    Panel,
    load_panels,
    score_markers,
)

FIXTURES = Path(__file__).parent / "fixtures"
# The shipped model-as-data file, located the same way the Phase 2 notebook does.
PANELS_YAML = Path(zlabel.__file__).parent / "panels.yaml"


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
    assert "mylpfa" in muscle.markers
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


def test_load_panels_ontology_anchor_loaded(test_panels):
    # muscle and endothelium fixtures both carry anchors; blood_erythroid has
    # no ontology_anchor key and should default to an empty frozenset.
    muscle = next(p for p in test_panels if p.bucket == "muscle")
    assert muscle.ontology_anchor == frozenset({"ZFA:0000548"})
    endothelium = next(p for p in test_panels if p.bucket == "endothelium")
    assert endothelium.ontology_anchor == frozenset({"ZFA:0005307"})
    blood = next(p for p in test_panels if p.bucket == "blood_erythroid")
    assert blood.ontology_anchor == frozenset()


def test_load_panels_scalar_ontology_anchor_raises(tmp_path):
    # A bare scalar would silently become a frozenset of characters; reject it.
    path = tmp_path / "bad.yaml"
    path.write_text(
        "bucket_x:\n  kind: identity\n  markers: [abc]\n  germ_layer: ''\n  tissue: ''\n"
        "  lineage: ''\n  ontology_anchor: ZFA:0000548\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="ontology_anchor must be a list"):
        load_panels(path)


def test_load_panels_invalid_kind_raises(tmp_path):
    path = tmp_path / "bad.yaml"
    path.write_text(
        "bucket_x:\n  kind: invalid\n  cite: test\n  markers: [abc]\n  germ_layer: ''\n  tissue: ''\n  lineage: ''\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="invalid kind"):
        load_panels(path)


def test_load_panels_missing_kind_raises(tmp_path):
    path = tmp_path / "bad.yaml"
    path.write_text(
        "bucket_x:\n  cite: test\n  markers: [abc]\n  germ_layer: ''\n  tissue: ''\n  lineage: ''\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="missing required field 'kind'"):
        load_panels(path)


def test_load_panels_empty_markers_raises(tmp_path):
    path = tmp_path / "bad.yaml"
    path.write_text(
        "bucket_x:\n  kind: identity\n  cite: test\n  markers: []\n  germ_layer: ''\n  tissue: ''\n  lineage: ''\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="no markers"):
        load_panels(path)


@pytest.mark.parametrize(
    "content",
    ["", "- muscle\n- neural\n", "42\n"],
    ids=["empty", "sequence", "scalar"],
)
def test_load_panels_rejects_empty_or_non_mapping(tmp_path, content):
    # An empty file (None), a sequence, or a scalar is not a bucket -> panel map;
    # each must fail cleanly rather than crash on .items().
    path = tmp_path / "bad.yaml"
    path.write_text(content, encoding="utf-8")
    with pytest.raises(ValueError, match="non-empty mapping"):
        load_panels(path)


def test_production_panels_yaml_loads_and_is_well_formed():
    # Exercise the shipped model-as-data file, not just the fixture. load_panels
    # already raises on a bad kind or empty markers, so loading is most of the
    # check; assert a few invariants on top to catch typos or schema drift.
    panels = load_panels(PANELS_YAML)
    assert panels
    buckets = [p.bucket for p in panels]
    assert len(buckets) == len(set(buckets))  # no duplicate bucket names
    assert {p.kind for p in panels} == {KIND_IDENTITY, KIND_STATE}
    for p in panels:
        assert all(m == m.lower() for m in p.markers)
        # The shipped model's anchor invariant: identity panels ground somewhere,
        # state panels (a transcriptional program) carry no anatomy anchor.
        if p.kind == KIND_IDENTITY:
            assert p.ontology_anchor, f"identity panel {p.bucket!r} must have an ontology_anchor"
        else:
            assert not p.ontology_anchor, f"state panel {p.bucket!r} must not have an ontology_anchor"


# --- score_markers: keystone trace -------------------------------------------


def test_score_markers_muscle_keystone_trace(test_panels):
    # Canonical 7-marker muscle cluster from the plan's worked example.
    # All are current ZFIN symbols and resolve cleanly.
    all_markers = ["mylpfa", "acta1b", "tnnt3a", "myod1", "myog", "hbae1.1", "kdrl"]
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
    syn = _make_synonym_map("mylpfa", "acta1b", "myod1")
    scores = score_markers(["mylpfa", "acta1b", "myod1"], test_panels, syn)
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
    # Only mylpfa (resolved, rank 1) contributes weight 1.0.
    # mylpfa is in muscle: muscle score should be 1.0 exactly.
    syn: dict[str, set[str]] = {
        "hbae1": {"hbae1.1", "hbae1.2"},  # ambiguous
        "mylpfa": {"mylpfa"},  # resolved
    }
    scores = score_markers(["mylpfa", "hbae1"], test_panels, syn)
    muscle = next(s for s in scores if s.bucket == "muscle")
    assert math.isclose(muscle.score, 1.0, rel_tol=1e-9)


def test_score_markers_matched_markers_recorded_in_rank_order(test_panels):
    syn = _make_synonym_map("mylpfa", "acta1b")
    scores = score_markers(["mylpfa", "acta1b"], test_panels, syn)
    muscle = next(s for s in scores if s.bucket == "muscle")
    assert len(muscle.matched_markers) == 2
    assert muscle.matched_markers[0].rank == 1
    assert muscle.matched_markers[0].symbol == "mylpfa"
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
