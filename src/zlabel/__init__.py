"""zlabel — label one whole-organism zebrafish scRNA-seq cluster from its markers."""

from zlabel.data import (
    ALL_RELATION_EDGE_TYPES,
    DEFAULT_ANCESTOR_EDGE_TYPES,
    ZfinExpressionRecord,
    ancestors,
    get_term,
    load_gene_synonym_map,
    load_zfa,
    load_zfin_expression,
    term_name,
)
from zlabel.genes import (
    STATUS_AMBIGUOUS,
    STATUS_RESOLVED,
    STATUS_UNRESOLVED,
    NormalizedSymbol,
    normalize_markers,
    normalize_symbol,
)
from zlabel.ground import expression_lookup, grounds_under, stage_plausibility
from zlabel.label import Labeler, decide
from zlabel.models import (
    TIER_HIGH_NAME,
    TIER_LOW_NAME,
    TIER_MEDIUM_NAME,
    Confidence,
    ExprHit,
    Label,
)
from zlabel.panels import (
    KIND_IDENTITY,
    KIND_STATE,
    BucketScore,
    MatchedMarker,
    Panel,
    load_panels,
    score_markers,
)

__version__ = "0.1.0"

__all__ = [
    # data
    "ALL_RELATION_EDGE_TYPES",
    "DEFAULT_ANCESTOR_EDGE_TYPES",
    "ZfinExpressionRecord",
    "__version__",
    "ancestors",
    "get_term",
    "load_gene_synonym_map",
    "load_zfa",
    "load_zfin_expression",
    "term_name",
    # genes
    "STATUS_AMBIGUOUS",
    "STATUS_RESOLVED",
    "STATUS_UNRESOLVED",
    "NormalizedSymbol",
    "normalize_markers",
    "normalize_symbol",
    # ground
    "expression_lookup",
    "grounds_under",
    "stage_plausibility",
    # label
    "Labeler",
    "decide",
    # models
    "TIER_HIGH_NAME",
    "TIER_LOW_NAME",
    "TIER_MEDIUM_NAME",
    "Confidence",
    "ExprHit",
    "Label",
    # panels
    "KIND_IDENTITY",
    "KIND_STATE",
    "BucketScore",
    "MatchedMarker",
    "Panel",
    "load_panels",
    "score_markers",
]
