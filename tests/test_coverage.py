"""Completeness check: every population in the coverage checklist maps to a panel.

benchmarks/cell_population_coverage.yaml is the record that the panel set covers
every major zebrafish cell population (signature -> correct anchor). These tests
keep it honest against the shipped panels.yaml -- no ontology data needed, so they
run in CI. scripts/audit_panels.py separately proves each bucket converges on its
anchor from real ZFIN expression.
"""

from pathlib import Path

import yaml

import zlabel
from zlabel.panels import KIND_IDENTITY, KIND_STATE, load_panels

PANELS_YAML = Path(zlabel.__file__).parent / "panels.yaml"
COVERAGE_YAML = Path(__file__).resolve().parent.parent / "benchmarks" / "cell_population_coverage.yaml"

_PANELS = {panel.bucket: panel for panel in load_panels(PANELS_YAML)}
_COVERAGE = yaml.safe_load(COVERAGE_YAML.read_text(encoding="utf-8"))


def test_every_population_maps_to_a_real_bucket_with_consistent_anchor():
    # The core completeness invariant: each listed population names a real bucket,
    # and its expected anchor is a subset of that bucket's ontology_anchor.
    for population in _COVERAGE["populations"]:
        bucket = population["bucket"]
        assert bucket in _PANELS, f"population {population['name']!r} maps to unknown bucket {bucket!r}"
        panel = _PANELS[bucket]
        anchor = set(population["anchor"])
        assert anchor.issubset(panel.ontology_anchor), (
            f"population {population['name']!r} anchor {anchor} not in {bucket!r} anchors {set(panel.ontology_anchor)}"
        )
        # State populations carry no anchor and must map to a state panel; identity
        # populations carry an anchor and must map to an identity panel.
        assert panel.kind == (KIND_STATE if not anchor else KIND_IDENTITY)


def test_regional_labels_resolve_to_real_lineage_buckets():
    for region, buckets in _COVERAGE["regional_to_lineage"].items():
        for bucket in buckets:
            assert bucket in _PANELS, f"regional label {region!r} maps to unknown bucket {bucket!r}"


def test_deferred_populations_have_no_bucket():
    # Deferred populations are intentionally unsupported (they abstain), so they must
    # not silently correspond to a bucket.
    for name in _COVERAGE["deferred"]:
        assert name not in _PANELS
