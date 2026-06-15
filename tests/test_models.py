"""Unit tests for zlabel.models — Label + ExprHit construction and serialisation."""

from typing import Any

import pytest
import yaml

from zlabel.models import (
    TIER_HIGH_NAME,
    TIER_LOW_NAME,
    TIER_MEDIUM_NAME,
    BucketScoreTrace,
    ExprHit,
    Label,
    LabelTrace,
    NormalizedMarkerTrace,
    TermVoteTrace,
)


def _make_valid_label(**overrides: Any) -> Label:
    """Build a minimal valid assigned Label; overrides replace specific fields."""
    defaults = dict(
        bucket="muscle",
        levels=("mesoderm", "muscle", "skeletal muscle"),
        abstained=False,
        confidence=TIER_HIGH_NAME,
        confidence_score=0.85,
        confidence_components={"coherence": 1.0, "margin": 1.0, "grounding": 0.75, "stage": 1.0},
        panel_scores={"muscle": 0.85, "blood_erythroid": 0.1},
        positive_markers=("mylpfa", "myod1"),
        expression_evidence=(ExprHit(symbol="mylpfa", zfa_id="ZFA:0000548", zfa_name="musculature system"),),
        rationale="muscle supported by mylpfa, myod1",
        next_step="subcluster",
    )
    defaults.update(overrides)
    return Label(**defaults)  # type: ignore[arg-type]


# --- ExprHit -----------------------------------------------------------------


def test_exprhit_fields():
    hit = ExprHit(symbol="mylpfa", zfa_id="ZFA:0000548", zfa_name="musculature system")
    assert hit.symbol == "mylpfa"
    assert hit.zfa_id == "ZFA:0000548"
    assert hit.zfa_name == "musculature system"


# --- Label construction ------------------------------------------------------


def test_label_assigned_round_trips():
    label = _make_valid_label()
    assert label.bucket == "muscle"
    assert label.abstained is False
    assert label.confidence == TIER_HIGH_NAME


def test_label_abstained_round_trips():
    label = Label(
        bucket="mixed/unresolved",
        levels=(),
        abstained=True,
        confidence=None,
        confidence_score=None,
        confidence_components={},
        panel_scores={"muscle": 0.05},
        positive_markers=(),
        expression_evidence=(),
        rationale="abstained: provisional",
    )
    assert label.abstained is True
    assert label.confidence is None
    assert label.next_step is None


def test_label_with_states():
    label = _make_valid_label(states=("cycling",))
    assert "cycling" in label.states


def test_label_validator_rejects_abstained_with_confidence():
    with pytest.raises(Exception, match="abstained Label"):
        Label(
            bucket="mixed/unresolved",
            levels=(),
            abstained=True,
            confidence=TIER_LOW_NAME,  # invalid: abstained must have None
            confidence_score=0.3,
            confidence_components={},
            panel_scores={},
            positive_markers=(),
            expression_evidence=(),
            rationale="bad",
        )


def test_label_validator_rejects_abstained_with_score():
    with pytest.raises(Exception, match="abstained Label"):
        Label(
            bucket="mixed/unresolved",
            levels=(),
            abstained=True,
            confidence=None,
            confidence_score=0.3,  # invalid: abstained must have score=None too
            confidence_components={},
            panel_scores={},
            positive_markers=(),
            expression_evidence=(),
            rationale="bad",
        )


def test_label_validator_rejects_assigned_without_confidence():
    with pytest.raises(Exception, match="confidence tier and score"):
        Label(
            bucket="muscle",
            levels=("mesoderm",),
            abstained=False,
            confidence=None,  # invalid: assigned must have a tier
            confidence_score=None,
            confidence_components={},
            panel_scores={},
            positive_markers=("myod1",),
            expression_evidence=(),
            rationale="bad",
        )


def test_label_validator_rejects_assigned_without_score():
    with pytest.raises(Exception, match="confidence tier and score"):
        Label(
            bucket="muscle",
            levels=("mesoderm",),
            abstained=False,
            confidence=TIER_LOW_NAME,
            confidence_score=None,  # invalid: assigned must have a score too
            confidence_components={},
            panel_scores={},
            positive_markers=("myod1",),
            expression_evidence=(),
            rationale="bad",
        )


# --- tier name constants -----------------------------------------------------


def test_tier_name_constants():
    assert TIER_HIGH_NAME == "high"
    assert TIER_MEDIUM_NAME == "medium"
    assert TIER_LOW_NAME == "low"


# --- to_yaml -----------------------------------------------------------------


def test_to_yaml_round_trips():
    label = _make_valid_label()
    raw = yaml.safe_load(label.to_yaml())
    assert raw["bucket"] == "muscle"
    assert raw["abstained"] is False
    assert raw["confidence"] == TIER_HIGH_NAME


def test_to_yaml_preserves_field_order():
    label = _make_valid_label()
    yaml_str = label.to_yaml()
    # bucket appears before confidence in the declaration order.
    assert yaml_str.index("bucket:") < yaml_str.index("confidence:")


def test_to_yaml_exprhit_serialised_as_dict():
    label = _make_valid_label()
    raw = yaml.safe_load(label.to_yaml())
    # ExprHit should serialise as a dict (model_dump recursively converts sub-models).
    evidence = raw["expression_evidence"]
    assert isinstance(evidence, list)
    assert evidence[0]["symbol"] == "mylpfa"
    assert evidence[0]["zfa_id"] == "ZFA:0000548"


def test_to_yaml_abstained_label():
    label = Label(
        bucket="mixed/unresolved",
        levels=(),
        abstained=True,
        confidence=None,
        confidence_score=None,
        confidence_components={},
        panel_scores={"muscle": 0.05},
        positive_markers=(),
        expression_evidence=(),
        rationale="abstained: provisional",
    )
    raw = yaml.safe_load(label.to_yaml())
    assert raw["bucket"] == "mixed/unresolved"
    assert raw["confidence"] is None


# --- Phase 4 new fields -------------------------------------------------------


def test_label_new_fields_default_values():
    # All four new fields have defaults so callers that pre-date Phase 4 need no changes.
    label = _make_valid_label()
    assert label.depth == 0
    assert label.panel_bucket == ""
    assert label.panel_germ_layer == ""
    assert label.convergent_genes == ()


def test_to_yaml_new_fields_round_trip():
    label = _make_valid_label(
        depth=2,
        panel_bucket="muscle",
        panel_germ_layer="mesoderm",
        convergent_genes=("acta1b", "mylpfa", "myog"),
    )
    raw = yaml.safe_load(label.to_yaml())
    assert raw["depth"] == 2
    assert raw["panel_bucket"] == "muscle"
    assert raw["panel_germ_layer"] == "mesoderm"
    assert raw["convergent_genes"] == ["acta1b", "mylpfa", "myog"]


def test_to_yaml_new_field_order():
    label = _make_valid_label(
        depth=2,
        panel_bucket="muscle",
        panel_germ_layer="mesoderm",
        convergent_genes=("acta1b", "mylpfa"),
    )
    yaml_str = label.to_yaml()
    # depth comes after levels, before abstained
    assert yaml_str.index("depth:") > yaml_str.index("levels:")
    assert yaml_str.index("depth:") < yaml_str.index("abstained:")
    # panel_bucket comes after confidence_components, before zfa_id
    assert yaml_str.index("panel_bucket:") > yaml_str.index("confidence_components:")
    assert yaml_str.index("panel_bucket:") < yaml_str.index("zfa_id:")
    # convergent_genes comes after positive_markers, before expression_evidence
    assert yaml_str.index("convergent_genes:") > yaml_str.index("positive_markers:")
    assert yaml_str.index("convergent_genes:") < yaml_str.index("expression_evidence:")


# --- Trace models (introspection) --------------------------------------------


def _make_label_trace(**overrides: Any) -> LabelTrace:
    """Build a minimal LabelTrace mirroring the muscle worked example."""
    defaults = dict(
        markers_in=("mylz2", "acta1b", "myog"),
        stage_hpf=48.0,
        normalized_markers=(
            NormalizedMarkerTrace(
                input="mylz2", status="resolved", symbols=("mylpfa",), note=None, rank=1, dropped=False
            ),
            NormalizedMarkerTrace(
                input="acta1b", status="resolved", symbols=("acta1b",), note=None, rank=2, dropped=False
            ),
            NormalizedMarkerTrace(input="myog", status="resolved", symbols=("myog",), note=None, rank=3, dropped=False),
        ),
        resolved_symbols=("mylpfa", "acta1b", "myog"),
        panel_scores=(
            BucketScoreTrace(
                bucket="muscle",
                score=1.0,
                adjusted_score=1.0,
                germ_layer="mesoderm",
                kind="identity",
                matched_markers=("mylpfa", "acta1b", "myog"),
                is_winner=True,
                is_contender=False,
            ),
        ),
        branch="clear-winner",
        term_votes=(
            TermVoteTrace(
                zfa_id="ZFA:0009234",
                zfa_name="muscle cell",
                gene_count=3,
                genes=("acta1b", "mylpfa", "myog"),
                information_content=1.22,
                ancestor_depth=3,
                passed_convergence=True,
                passed_stoplist=True,
                passed_information_content=True,
                grounded_under_anchor=True,
                eligible=True,
                selected=True,
            ),
        ),
        label=_make_valid_label(),
    )
    defaults.update(overrides)
    return LabelTrace(**defaults)  # type: ignore[arg-type]


def test_normalized_marker_trace_fields():
    nmt = NormalizedMarkerTrace(
        input="hbae1", status="ambiguous", symbols=("hbae1.1", "hbae1.2"), note="2 paralogs", rank=4, dropped=True
    )
    assert nmt.input == "hbae1"
    assert nmt.dropped is True
    assert nmt.symbols == ("hbae1.1", "hbae1.2")


def test_term_vote_trace_gate_fields():
    # A near-miss: enough genes, not stoplisted, but IC below the gate -> not eligible.
    near_miss = TermVoteTrace(
        zfa_id="ZFA:0000548",
        zfa_name="musculature system",
        gene_count=4,
        genes=("acta1b", "myod1", "mylpfa", "myog"),
        information_content=0.81,
        ancestor_depth=1,
        passed_convergence=True,
        passed_stoplist=True,
        passed_information_content=False,
        grounded_under_anchor=False,
        eligible=False,
        selected=False,
    )
    assert near_miss.passed_convergence is True
    assert near_miss.passed_information_content is False
    assert near_miss.eligible is False


def test_label_trace_constructs_and_embeds_label():
    trace = _make_label_trace()
    assert trace.branch == "clear-winner"
    assert trace.label.bucket == "muscle"  # the embedded Label is the real packet
    assert trace.term_votes[0].selected is True


def test_label_trace_to_yaml_round_trips():
    trace = _make_label_trace()
    raw = yaml.safe_load(trace.to_yaml())
    assert raw["branch"] == "clear-winner"
    assert raw["markers_in"] == ["mylz2", "acta1b", "myog"]
    # Nested models serialise as dicts recursively.
    assert raw["term_votes"][0]["zfa_id"] == "ZFA:0009234"
    assert raw["label"]["bucket"] == "muscle"


def test_label_trace_to_yaml_field_order():
    trace = _make_label_trace()
    yaml_str = trace.to_yaml()
    # Declaration order follows the pipeline: markers_in -> ... -> term_votes -> label.
    assert yaml_str.index("markers_in:") < yaml_str.index("panel_scores:")
    assert yaml_str.index("panel_scores:") < yaml_str.index("branch:")
    assert yaml_str.index("branch:") < yaml_str.index("term_votes:")
    assert yaml_str.index("term_votes:") < yaml_str.index("\nlabel:")
