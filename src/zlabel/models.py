"""Evidence packet for a single cluster label decision.

Label is the stable, structured output of decide() and Labeler.label(): it carries
not just the bucket name but the confidence rubric, the grounding evidence, and
enough context for a human (or a future LLM narrator) to understand and verify the
call without digging into the library internals.

pydantic is used for two reasons: validation (the abstained/confidence invariant is
enforced at construction, not asserted at call sites) and clean YAML serialisation
via to_yaml(). Every field is a Python primitive so model_dump() is YAML-safe.
"""

from __future__ import annotations

from typing import Literal

import yaml
from pydantic import BaseModel, model_validator

# --- Confidence tier names ----------------------------------------------------
# Named constants so the rest of the codebase never hard-codes the strings.

TIER_HIGH_NAME: Literal["high"] = "high"
TIER_MEDIUM_NAME: Literal["medium"] = "medium"
TIER_LOW_NAME: Literal["low"] = "low"

Confidence = Literal["high", "medium", "low"]


# --- Sub-models ---------------------------------------------------------------


class ExprHit(BaseModel):
    """One grounded marker's in-vivo anatomy evidence.

    Recorded for each of the winner's matched markers that grounds under the
    bucket's ontology anchor (i.e. it has a ZFIN expression record pointing at
    a ZFA term that is the anchor or a descendant of it). One hit per grounded
    marker, using the first grounding record in file order (deterministic).
    Stage data is a separate confidence component, not included here.

    Attributes:
        symbol (str): The resolved current ZFIN symbol of the matched marker.
        zfa_id (str): A ZFA id the marker expresses in that grounds under the
            bucket anchor (e.g. ZFA:0000548 for a muscle marker in musculature
            system).
        zfa_name (str): Human-readable name of that ZFA term (from the ontology),
            for readable evidence packets.
    """

    symbol: str
    zfa_id: str
    zfa_name: str


# --- Main evidence packet -----------------------------------------------------


class Label(BaseModel):
    """Evidence packet for one cluster label decision.

    Emitted by decide() and Labeler.label(). Every field is a Python primitive so
    model_dump() / to_yaml() are lossless and YAML-safe.

    The invariant bucket == mixed/unresolved <-> abstained == True <-> confidence
    is None is enforced by the model validator; constructing a contradictory Label
    raises ValidationError.

    Attributes:
        bucket (str): The assigned identity bucket (e.g. muscle, endothelium),
            the rollup germ layer (e.g. mesoderm), or mixed/unresolved.
        levels (tuple[str, ...]): Lineage hierarchy from broad to specific
            (germ_layer, tissue, lineage) with empty strings trimmed. Empty tuple
            when abstained. len(levels) is the granularity signal.
        abstained (bool): True when no decision was made (mixed/unresolved).
        confidence (Confidence | None): Tier name (high, medium, or low). None
            iff abstained.
        confidence_score (float | None): The raw weighted confidence in [0, 1].
            None iff abstained.
        confidence_components (dict[str, float]): The four rubric components
            (coherence, margin, grounding, stage) each in [0, 1]. Absent
            components use NEUTRAL (0.5). Empty dict when abstained.
        ambiguity_flag (str): One of none, mixed, underclustered, provisional.
            none for a clean single-bucket call.
        states (tuple[str, ...]): Detected state programs orthogonal to identity
            (e.g. cycling). Reported on every Label, including abstentions.
        zfa_id (str | None): The bucket's ontology anchor (sorted-first id when
            the anchor has several, for determinism). None for germ-layer rollups
            and abstentions.
        cl_id (str | None): Deferred: Cell Ontology bridge. Field is present but
            no logic populates it yet.
        panel_scores (dict[str, float]): Raw BucketScore.score for every panel
            bucket (a direct echo of the scorer output; the adjusted identity
            scores used inside decide() are internal).
        positive_markers (tuple[str, ...]): Resolved current ZFIN symbols of
            markers that supported the call.
        expression_evidence (tuple[ExprHit, ...]): Grounded anatomy hits for the
            winner's matched markers that expressed under the bucket anchor.
        rationale (str): One-line human-readable reason for the call.
        next_step (str | None): Suggested next action. Subcluster when a bucket
            or rollup was assigned; None when abstained.
    """

    bucket: str
    levels: tuple[str, ...]
    abstained: bool
    confidence: Confidence | None
    confidence_score: float | None
    confidence_components: dict[str, float]
    ambiguity_flag: str = "none"
    states: tuple[str, ...] = ()
    zfa_id: str | None = None
    cl_id: str | None = None
    panel_scores: dict[str, float]
    positive_markers: tuple[str, ...]
    expression_evidence: tuple[ExprHit, ...]
    rationale: str
    next_step: str | None = None

    @model_validator(mode="after")
    def _check_abstain_consistency(self) -> Label:
        """Enforce that abstained == (confidence is None).

        Returns:
            Label: self, after validation.

        Raises:
            ValueError: If abstained and confidence are inconsistent.
        """
        if self.abstained and self.confidence is not None:
            raise ValueError("abstained Label must have confidence=None")
        if not self.abstained and self.confidence is None:
            raise ValueError("assigned Label must have a confidence tier")
        return self

    def to_yaml(self) -> str:
        """Serialise the evidence packet to YAML.

        Field order is preserved (sort_keys=False) so the packet reads in
        declaration order: bucket/levels first, then confidence components,
        then evidence. model_dump() converts nested ExprHit sub-models to dicts
        recursively; pydantic tuples serialise as lists. YAML round-trips
        cleanly for any downstream consumer.

        Returns:
            str: YAML string representation of the evidence packet.
        """
        return yaml.safe_dump(self.model_dump(), sort_keys=False, allow_unicode=True)
