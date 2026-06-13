"""Unit tests for zlabel.models — Label + ExprHit construction and serialisation."""

from typing import Any

import pytest
import yaml

from zlabel.models import TIER_HIGH_NAME, TIER_LOW_NAME, TIER_MEDIUM_NAME, ExprHit, Label


def _valid_label(**overrides: Any) -> Label:
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
    label = _valid_label()
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
    label = _valid_label(states=("cycling",))
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
    label = _valid_label()
    raw = yaml.safe_load(label.to_yaml())
    assert raw["bucket"] == "muscle"
    assert raw["abstained"] is False
    assert raw["confidence"] == TIER_HIGH_NAME


def test_to_yaml_preserves_field_order():
    label = _valid_label()
    yaml_str = label.to_yaml()
    # bucket appears before confidence in the declaration order.
    assert yaml_str.index("bucket:") < yaml_str.index("confidence:")


def test_to_yaml_exprhit_serialised_as_dict():
    label = _valid_label()
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
